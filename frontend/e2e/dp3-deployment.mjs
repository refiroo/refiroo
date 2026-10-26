// 0.12 DP3 deployment evidence (D410): the reference installation (compose.yml) built and started from
// empty, as an operator does, then reached at this computer's network address, not `localhost`, as a
// phone would reach it. Builds both images, starts the database, engine and web with a throwaway
// certificate for the address, creates the first administrator with `create_admin`, signs in from a
// desktop and a phone-sized browser context, opens an application, restarts the installation and signs
// in again with the data kept, checks the public paths and that `/metrics` and the engine's port are
// not reachable, that `web` refuses to start without a certificate, and that `WEB_TLS=proxy` serves
// plain HTTP behind a balancer. Everything it starts is removed at the end, containers, volumes and
// images included. Slow and heavy (Docker builds): run once per package and at R, announced.
import { execFileSync, spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import net from "node:net";
import { tmpdir } from "node:os";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

// The installation's certificate is the throwaway one this run makes.
process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const project = "dp3check";
const PASSWORD = "a long deployment passphrase 1";
const checks = [];
const failures = [];
const expect = (condition, message) => {
  if (!condition) failures.push(message);
};

const freePort = () =>
  new Promise((done) => {
    const server = net.createServer().listen(0, () => {
      const { port } = server.address();
      server.close(() => done(port));
    });
  });

const address = (process.env.RDM_DEV_ADDRESS || execFileSync(resolve(root, "scripts/dev.sh"), ["address"], { encoding: "utf8" })).trim();
const work = mkdtempSync(resolve(tmpdir(), "rdm-dp3-"));
const certs = resolve(work, "certs");
const emptyCerts = resolve(work, "no-certs");
mkdirSync(certs);
mkdirSync(emptyCerts);
const httpPort = await freePort();
const httpsPort = await freePort();
const publicUrl = `https://${address}:${httpsPort}`;

function writeEnv(name, extra = {}) {
  const file = resolve(work, name);
  const values = {
    PUBLIC_URL: publicUrl,
    POSTGRES_PASSWORD: execFileSync("openssl", ["rand", "-hex", "16"], { encoding: "utf8" }).trim(),
    SECRETS_ENCRYPTION_KEY: execFileSync("sh", ["-c", "openssl rand -base64 32 | tr '+/' '-_'"], { encoding: "utf8" }).trim(),
    RDM_CURSOR_SIGNING_KEY: execFileSync("openssl", ["rand", "-base64", "32"], { encoding: "utf8" }).trim(),
    WEB_HTTP_PORT: String(httpPort),
    WEB_HTTPS_PORT: String(httpsPort),
    WEB_CERTS_DIR: certs,
    ...extra,
  };
  writeFileSync(file, Object.entries(values).map(([key, value]) => `${key}=${value}`).join("\n") + "\n");
  return { file, values };
}

let env = writeEnv("tls.env");
const compose = (args, options = {}) =>
  spawnSync("docker", ["compose", "-p", project, "--env-file", env.file, "-f", "compose.yml", ...args], {
    cwd: root,
    encoding: "utf8",
    ...options,
  });
function must(result, what) {
  if (result.status !== 0) throw new Error(`${what} failed:\n${(result.stdout + result.stderr).split("\n").slice(-30).join("\n")}`);
  return result;
}
async function healthy(service, seconds = 120) {
  for (let waited = 0; waited < seconds; waited += 2) {
    const state = spawnSync("docker", ["inspect", "-f", "{{.State.Health.Status}}", `${project}-${service}-1`], { encoding: "utf8" });
    if (state.stdout.trim() === "healthy") return;
    await new Promise((done) => setTimeout(done, 2000));
  }
  throw new Error(`${service} did not become healthy:\n${compose(["logs", "--tail", "30", service]).stdout}`);
}

async function signedIn(browser, viewport, tag) {
  const context = await browser.newContext({ ignoreHTTPSErrors: true, viewport, hasTouch: viewport.width < 600 });
  const page = await context.newPage();
  page.setDefaultTimeout(20000);
  const problems = [];
  const origins = new Set();
  page.on("pageerror", (error) => problems.push(error.message));
  page.on("request", (request) => origins.add(new URL(request.url()).origin));
  page.on("response", (response) => {
    if (new URL(response.url()).pathname.startsWith("/api/") && response.status() >= 500) problems.push(`${response.status()} ${response.url()}`);
  });
  await page.goto(publicUrl);
  await page.getByRole("heading", { level: 1, name: "Sign in" }).waitFor();
  await page.getByLabel("Username").fill("ada");
  await page.getByLabel("Password").fill(PASSWORD);
  await page.keyboard.press("Enter");
  await page.getByRole("button", { name: "Account" }).waitFor();
  await page.reload();
  await page.getByRole("button", { name: "Account" }).waitFor();
  expect([...origins].every((origin) => origin === publicUrl), `${tag}: the page called other origins: ${[...origins]}`);
  // An application opens (the starter's, in the default workspace).
  await page.locator(".home-app").first().click();
  await page.locator(".data-context-band").waitFor();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow <= 0, `${tag}: scrolls sideways by ${overflow}px`);
  expect(problems.length === 0, `${tag}: ${problems.slice(0, 3).join("; ")}`);
  await context.close();
}

// A failed password sign-in at `base`, carrying `forwarded` as X-Forwarded-For when given. The sign-in
// throttle then records the address the engine saw (D271), which is what the checks below read.
async function failedSignIn(base, username, forwarded) {
  const body = new URLSearchParams({
    username,
    password: "wrong",
    response_type: "code",
    client_id: "browser",
    redirect_uri: `${publicUrl}/signed-in`,
    code_challenge: "x".repeat(43),
    code_challenge_method: "S256",
    state: "s",
  });
  const response = await fetch(`${base}/oauth/authorize`, {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded", ...(forwarded ? { "X-Forwarded-For": forwarded } : {}) },
    body,
  });
  expect(response.status === 401, `a wrong password answered ${response.status}, not 401`);
}
const throttleAddresses = () =>
  spawnSync("docker", ["compose", "-p", project, "--env-file", env.file, "-f", "compose.yml", "exec", "-T", "database", "psql", "-U", "rdm", "-d", "rdm", "-Atc", "select key from sign_in_failures where kind='address' order by key"], { cwd: root, encoding: "utf8" })
    .stdout.split("\n").map((line) => line.trim()).filter(Boolean);
const clearThrottle = () =>
  spawnSync("docker", ["compose", "-p", project, "--env-file", env.file, "-f", "compose.yml", "exec", "-T", "database", "psql", "-U", "rdm", "-d", "rdm", "-Atc", "delete from sign_in_failures"], { cwd: root, encoding: "utf8" });

async function cleanup() {
  spawnSync("docker", ["compose", "-p", project, "--env-file", env.file, "-f", "compose.yml", "down", "-v", "--rmi", "local"], { cwd: root, encoding: "utf8" });
  rmSync(work, { recursive: true, force: true });
}

let browser;
try {
  // 1. A certificate for this address, as an organisation would mount its own.
  must(
    spawnSync("openssl", ["req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1", "-subj", "/CN=refiroo", "-addext", `subjectAltName=IP:${address},DNS:localhost`, "-keyout", resolve(certs, "privkey.pem"), "-out", resolve(certs, "fullchain.pem")], { encoding: "utf8" }),
    "the certificate",
  );

  // 2. Built and started from empty.
  const started = performance.now();
  must(compose(["up", "-d", "--build"]), "docker compose up");
  await healthy("web");
  checks.push(`built and started from empty at ${publicUrl} in ${Math.round((performance.now() - started) / 1000)} s`);

  // 3. The first administrator, as the guide says.
  must(compose(["run", "--rm", "-T", "engine", "python", "-m", "app.cli.create_admin", "--username", "ada", "--name", "Ada", "--password-stdin"], { input: PASSWORD }), "create_admin");
  checks.push("the first administrator was created with create_admin");

  // 4. What is public, what is not.
  const fetched = async (path, init) => (await fetch(`${publicUrl}${path}`, init));
  for (const path of ["/health", "/.well-known/oauth-authorization-server", "/docs", "/openapi.json", "/brand/app-icon-512.png", "/settings/account"]) {
    expect((await fetched(path)).status === 200, `${path} did not answer 200`);
  }
  expect((await fetched("/metrics")).status === 404, "/metrics is reachable");
  const metadata = await (await fetched("/.well-known/oauth-authorization-server")).json();
  expect(metadata.issuer === publicUrl, `the issuer is ${metadata.issuer}, not ${publicUrl}`);
  const redirect = await fetch(`http://${address}:${httpPort}/api/v1/model?x=1`, { redirect: "manual" });
  expect(redirect.status === 301 && redirect.headers.get("location") === `${publicUrl}/api/v1/model?x=1`, `HTTP is not redirected to ${publicUrl} (${redirect.status} ${redirect.headers.get("location")})`);
  expect((await fetched("/api/v1/model")).status === 401, "the management API answered without a token");
  const published = spawnSync("docker", ["ps", "--filter", `name=${project}`, "--format", "{{.Names}} {{.Ports}}"], { encoding: "utf8" }).stdout;
  expect(!/engine-1.*0\.0\.0\.0|database-1.*0\.0\.0\.0/.test(published), `the engine or the database is published:\n${published}`);
  const spoof = await fetched("/health", { headers: { "X-Forwarded-For": "6.6.6.6" } });
  expect(spoof.status === 200, "a forged forwarded address broke a request");
  const appPage = await fetched("/settings/account");
  expect(appPage.headers.get("content-security-policy") === "frame-ancestors 'none'", `the application page's CSP is ${appPage.headers.get("content-security-policy")}`);
  expect(appPage.headers.get("x-frame-options") === "DENY", `the application page's X-Frame-Options is ${appPage.headers.get("x-frame-options")}`);
  checks.push("public paths answer at the address, /metrics is 404, HTTP redirects to PUBLIC_URL, the engine and database are not published");

  // 5. Signed in from a desktop and a phone-sized browser, at the network address.
  browser = await chromium.launch({ headless: true, ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}) });
  await signedIn(browser, { width: 1440, height: 900 }, "desktop");
  await signedIn(browser, { width: 390, height: 844 }, "phone");
  checks.push(`signed in, reloaded and opened an application at ${publicUrl}, desktop and 390px, with every request on that one address`);

  // 6. A forged forwarded address is not what the sign-in throttle counts: a wrong password carrying
  // X-Forwarded-For is recorded under the address nginx saw, never under the forged one.
  await failedSignIn(publicUrl, "ada", "6.6.6.6");
  const seen = throttleAddresses();
  expect(seen.length > 0 && !seen.includes("6.6.6.6"), `the throttle counted a forged address (${seen})`);
  checks.push(`a forged X-Forwarded-For was not the throttle's address (counted: ${seen})`);

  // 7. A restart keeps the data: the same administrator signs in again.
  must(compose(["restart"]), "docker compose restart");
  await healthy("web");
  await signedIn(browser, { width: 1440, height: 900 }, "after restart");
  checks.push("after a restart of every container the administrator signed in again with the data kept");

  // 8. web refuses to start without a certificate, and says what to do.
  const webImage = `${project}-web`;
  const bare = spawnSync("docker", ["run", "--rm", "-e", `PUBLIC_URL=${publicUrl}`, "-v", `${emptyCerts}:/certs:ro`, webImage], { encoding: "utf8" });
  expect(bare.status !== 0 && /fullchain\.pem/.test(bare.stderr), `web started without a certificate or did not say why (${bare.status}): ${bare.stderr.slice(0, 200)}`);
  checks.push("web refused to start without a certificate, naming the files and WEB_TLS=proxy");

  // 9. Behind a balancer that ends HTTPS: plain HTTP on web, no certificate needed.
  must(compose(["down"]), "docker compose down");
  env = writeEnv("proxy.env", { WEB_TLS: "proxy", WEB_CERTS_DIR: emptyCerts, POSTGRES_PASSWORD: env.values.POSTGRES_PASSWORD, SECRETS_ENCRYPTION_KEY: env.values.SECRETS_ENCRYPTION_KEY, RDM_CURSOR_SIGNING_KEY: env.values.RDM_CURSOR_SIGNING_KEY });
  must(compose(["up", "-d"]), "docker compose up (proxy)");
  await healthy("web");
  const plain = `http://${address}:${httpPort}`;
  const page = await fetch(`${plain}/settings/account`, { redirect: "manual" });
  expect(page.status === 200, `WEB_TLS=proxy redirected or failed: ${page.status}`);
  expect((await fetch(`${plain}/health`)).status === 200, "WEB_TLS=proxy: /health did not answer");
  expect((await fetch(`${plain}/metrics`)).status === 404, "WEB_TLS=proxy: /metrics is reachable");
  const balancer = await (await fetch(`${plain}/.well-known/oauth-authorization-server`, { headers: { "X-Forwarded-Proto": "https" } })).json();
  expect(balancer.issuer === publicUrl, `WEB_TLS=proxy: the issuer is ${balancer.issuer}`);
  expect((await fetch(`${plain}/settings/account`)).headers.get("x-frame-options") === "DENY", "WEB_TLS=proxy: the application page can be framed");
  expect((await fetch(`${plain}/settings/account`)).headers.get("content-security-policy") === "frame-ancestors 'none'", "WEB_TLS=proxy: no frame-ancestors");
  checks.push("WEB_TLS=proxy served plain HTTP with no certificate, /metrics kept inside and the issuer unchanged");

  // 9b. With WEB_TRUSTED_PROXIES empty nobody is trusted: the forged address is ignored and the caller
  // is the address web is connected from (learned here, since it depends on how Docker publishes ports).
  clearThrottle();
  await failedSignIn(plain, "ada", "7.7.7.7");
  const untrusted = throttleAddresses();
  expect(untrusted.length === 1 && untrusted[0] !== "7.7.7.7", `WEB_TLS=proxy, no trusted proxies: the throttle counted ${untrusted}, not the connecting address`);
  const connecting = untrusted[0];
  checks.push(`WEB_TLS=proxy with WEB_TRUSTED_PROXIES empty ignored a forged X-Forwarded-For (counted ${connecting})`);

  // 9c. With the connecting address listed, the address X-Forwarded-For names is the caller's.
  env = writeEnv("proxy-trusted.env", { WEB_TLS: "proxy", WEB_TRUSTED_PROXIES: `${connecting}/${connecting.includes(":") ? 128 : 32}`, WEB_CERTS_DIR: emptyCerts, POSTGRES_PASSWORD: env.values.POSTGRES_PASSWORD, SECRETS_ENCRYPTION_KEY: env.values.SECRETS_ENCRYPTION_KEY, RDM_CURSOR_SIGNING_KEY: env.values.RDM_CURSOR_SIGNING_KEY });
  must(compose(["up", "-d"]), "docker compose up (proxy, trusted)");
  await healthy("web");
  clearThrottle();
  // The balancer appends the address it saw; a client's own earlier entry is not believed.
  await failedSignIn(plain, "ada", "9.9.9.9, 7.7.7.7");
  const trusted = throttleAddresses();
  expect(trusted.length === 1 && trusted[0] === "7.7.7.7", `WEB_TLS=proxy, balancer trusted: the throttle counted ${trusted}, not the address the balancer named (7.7.7.7)`);
  checks.push(`WEB_TLS=proxy with ${connecting} in WEB_TRUSTED_PROXIES took the caller from X-Forwarded-For (the last untrusted entry)`);

  // 9d. A malformed WEB_TRUSTED_PROXIES stops web at start and says which entry.
  const bad = spawnSync("docker", ["run", "--rm", "-e", `PUBLIC_URL=${publicUrl}`, "-e", "WEB_TLS=proxy", "-e", "WEB_TRUSTED_PROXIES=10.0.0.0/8,bogus", webImage], { encoding: "utf8" });
  expect(bad.status !== 0 && /WEB_TRUSTED_PROXIES has 'bogus'/.test(bad.stderr), `web started with a malformed WEB_TRUSTED_PROXIES or did not say why (${bad.status}): ${bad.stderr.slice(0, 200)}`);
  checks.push("web refused a malformed WEB_TRUSTED_PROXIES entry, naming it");
} catch (error) {
  failures.push(String(error.message ?? error));
} finally {
  await browser?.close().catch(() => {});
  await cleanup();
}

console.log(checks.join("\n"));
const left = spawnSync("sh", ["-c", `docker ps -aq --filter name=${project} | wc -l; docker volume ls -q | grep -c ${project} || true; docker images | grep -c ${project} || true`], { encoding: "utf8" }).stdout.split("\n").map((n) => n.trim()).filter(Boolean);
console.log(`left behind: ${left[0]} containers, ${left[1]} volumes, ${left[2]} images`);
if (failures.length) {
  console.error(`\n${failures.length} failure(s):\n${failures.join("\n")}`);
  process.exit(1);
}
console.log(`\nDP3: ${checks.length} checks passed`);
