// 0.12 DP1 browser evidence: the application and the engine on one address (D404, D411), against a
// real backend behind the Vite dev server's forwarding, on two models, at 1440px and 390px. No
// `VITE_API_URL` is built in: the page calls its own address. Signed out, the application's sign-in
// screen signs the person in by keyboard (PKCE, the code exchange and the refresh cookie all through
// the page's address), a collection opens, a reload keeps the session (the cookie renews through the
// same address), and sign-out returns to the sign-in screen. No request of the page reaches the
// engine's own port. The engine's published paths answer at the page's address, its issuer names that
// address, and `/metrics` is not forwarded. At 390px the sign-in screen does not scroll sideways.
import { resolve } from "node:path";
import { SHAPED_MODELS, bootShaped, startingPoint } from "./helpers/shaped-models.mjs";

const checks = [];
const failures = [];

function expect(condition, message) {
  if (!condition) failures.push(message);
}

async function walk(configuration) {
  // `localhost`: a secure page, where the browser offers the sign-in's cryptography.
  const harness = await bootShaped(configuration, { host: "localhost", oneAddress: true });
  try {
    const { apiUrl, uiUrl, api, output, signedOutContext, harnessIdentity } = harness;
    const tag = configuration.name;
    const person = harnessIdentity.person;
    const engineOrigin = new URL(apiUrl).origin;

    // 1. The engine's paths at the page's address.
    const health = await fetch(`${uiUrl}/health`);
    expect(health.ok, `${tag}: /health answers at the page's address (${health.status})`);
    const metadata = await (await fetch(`${uiUrl}/.well-known/oauth-authorization-server`)).json();
    expect(metadata.issuer === uiUrl, `${tag}: the issuer names the page's address: ${metadata.issuer}`);
    const reference = await fetch(`${uiUrl}/docs/api`);
    expect(
      reference.ok && (await reference.text()).includes("Management API"),
      `${tag}: /docs/api answers at the page's address`,
    );
    const metrics = await fetch(`${uiUrl}/metrics`, { headers: { Accept: "text/html" } });
    expect((await metrics.text()).includes('id="root"'), `${tag}: /metrics is not forwarded (the application answers)`);
    checks.push(
      `${tag}: /health, the OAuth metadata (issuer ${uiUrl}) and /docs/api answer at the page's address; /metrics is not forwarded`,
    );

    // 2. Sign in through the page's address, by keyboard.
    const context = await signedOutContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    page.setDefaultTimeout(15000);
    page.on("pageerror", (error) => failures.push(`${tag}: ${error.message}`));
    const toEngine = [];
    page.on("request", (request) => {
      if (new URL(request.url()).origin === engineOrigin) toEngine.push(request.url());
    });

    await page.goto(uiUrl);
    await page.getByRole("heading", { level: 1, name: "Sign in" }).waitFor();
    await page.getByLabel("E-mail address").fill(person.email);
    await page.getByLabel("Password").fill(person.password);
    await page.keyboard.press("Enter");
    await page.getByRole("button", { name: "Account" }).waitFor();
    await page.screenshot({ path: resolve(output, `${tag}-signed-in.png`) });
    checks.push(`${tag}: signed in by keyboard through the page's address`);

    // 3. A collection opens, a reload keeps the session.
    const start = await startingPoint(api);
    await page.goto(`${uiUrl}${start.path}`);
    await page.getByRole("heading", { level: 1, name: start.heading }).waitFor();
    await page.getByText(start.records[0].name, { exact: true }).first().waitFor();
    checks.push(`${tag}: the collection ${start.heading} opened and lists its records`);
    await page.reload();
    await page.getByRole("heading", { level: 1, name: start.heading }).waitFor();
    await page.getByText(start.records[0].name, { exact: true }).first().waitFor();
    checks.push(`${tag}: a reload kept the session (the cookie renewed through the same address)`);

    // 4. Sign out returns to the sign-in screen.
    await page.getByRole("button", { name: "Account" }).click();
    await page.getByRole("dialog", { name: "Account" }).getByRole("button", { name: "Sign out" }).click();
    await page.getByRole("heading", { level: 1, name: "Sign in" }).waitFor();
    checks.push(`${tag}: signing out returned to the sign-in screen`);

    expect(toEngine.length === 0, `${tag}: the page called the engine's own port: ${toEngine.slice(0, 3).join(", ")}`);
    checks.push(`${tag}: no request of the page reached the engine's own address`);

    // 5. A phone's width.
    const phone = await signedOutContext({ viewport: { width: 390, height: 844 }, hasTouch: true });
    const small = await phone.newPage();
    await small.goto(uiUrl);
    await small.getByRole("heading", { level: 1, name: "Sign in" }).waitFor();
    const overflow = await small.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow <= 0, `${tag}: the sign-in screen scrolls sideways at 390px (${overflow}px)`);
    await small.screenshot({ path: resolve(output, `${tag}-phone.png`) });
    checks.push(`${tag}: 390px without horizontal scroll`);
  } finally {
    await harness.cleanup();
  }
}

for (const configuration of SHAPED_MODELS) await walk(configuration);

console.log(checks.join("\n"));
if (failures.length) {
  console.error(`\n${failures.length} failure(s):\n${failures.join("\n")}`);
  process.exit(1);
}
console.log(`\nDP1: ${checks.length} checks passed`);
