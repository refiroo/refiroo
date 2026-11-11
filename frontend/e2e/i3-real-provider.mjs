// 0.12 E1 prep: a real sign-in provider try (docs/testing/REAL_PROVIDER_TRY_PLAN.md). Heavy: it needs
// Docker and runs only before E1 and at R, never in a default set. The runner pulls (once) and starts
// a pinned Keycloak, imports backend/tests/keycloak/refiroo-realm.json with the harness's per-run
// engine address and a random client secret patched in, and walks the plan's ten cases in Chromium
// against a real backend, on two models (the starter, and the starter under another product name).
// The servers are reached as localhost, as in i4-sign-in.mjs part c. A case that throws or fails is
// recorded with the evidence and the walk goes on, so one run reports every case. The container is
// removed in `finally` (`docker rm -f`); the pulled image is left.
import { execFileSync, spawnSync } from "node:child_process";
import { randomBytes } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import { createServer } from "node:net";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { bootHarness } from "./helpers/harness.mjs";

const IMAGE = "quay.io/keycloak/keycloak:26.8.1";
const REALM = "refiroo";
const REALM_FILE = resolve(dirname(fileURLToPath(import.meta.url)), "../../backend/tests/keycloak/refiroo-realm.json");
const MODELS = [{ name: "starter" }, { name: "renamed", product: "Northfield Reference Data" }];

const checks = [];
const failures = [];
const results = [];
const started = performance.now();

function expect(condition, message) {
  if (!condition) throw new Error(message);
}

function docker(args, options = {}) {
  return execFileSync("docker", args, { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"], ...options }).trim();
}

async function freePort() {
  const server = createServer();
  await new Promise((done, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", done);
  });
  const value = server.address().port;
  await new Promise((done) => server.close(done));
  return value;
}

/** Pull the pinned image once when it is not here yet; what it cost. */
function ensureImage() {
  try {
    docker(["image", "inspect", IMAGE]);
    return { pulled: false };
  } catch {
    const at = performance.now();
    docker(["pull", "--quiet", IMAGE], { timeout: 600000 });
    return { pulled: true, seconds: Math.round((performance.now() - at) / 1000) };
  }
}

/** A Keycloak for one walk: the realm file patched for the engine's address, started, discovery read. */
async function startKeycloak(engineUrl, output) {
  const port = await freePort();
  const admin = { user: "admin", password: randomBytes(12).toString("hex") };
  const secret = randomBytes(16).toString("hex");
  const patched = (await readFile(REALM_FILE, "utf8"))
    .replaceAll("__ENGINE_URL__", engineUrl)
    .replaceAll("__CLIENT_SECRET__", secret);
  const realm = JSON.parse(patched);
  const realmPath = resolve(output, "refiroo-realm.json");
  await writeFile(realmPath, patched, { mode: 0o644 });
  const name = `refiroo-kc-${randomBytes(4).toString("hex")}`;
  docker([
    "run",
    "-d",
    "--rm",
    "--name",
    name,
    "-p",
    `127.0.0.1:${port}:8080`,
    "-e",
    `KC_BOOTSTRAP_ADMIN_USERNAME=${admin.user}`,
    "-e",
    `KC_BOOTSTRAP_ADMIN_PASSWORD=${admin.password}`,
    "-v",
    `${realmPath}:/opt/keycloak/data/import/refiroo-realm.json:ro`,
    IMAGE,
    "start-dev",
    "--import-realm",
  ]);
  const base = `http://127.0.0.1:${port}`;
  const keycloak = {
    name,
    base,
    issuer: `${base}/realms/${REALM}`,
    secret,
    realm,
    redirectUri: realm.clients[0].redirectUris[0],
    password: (who) => realm.users.find((user) => user.username === who).credentials[0].value,
  };
  const at = performance.now();
  for (let attempt = 0; attempt < 900; attempt++) {
    try {
      if ((await fetch(`${keycloak.issuer}/.well-known/openid-configuration`)).ok) break;
    } catch {
      /* starting */
    }
    const running = spawnSync("docker", ["inspect", "-f", "{{.State.Running}}", name], { encoding: "utf8" });
    if (running.stdout.trim() !== "true")
      throw new Error(
        `Keycloak stopped:\n${spawnSync("docker", ["logs", "--tail", "30", name], { encoding: "utf8" }).stdout}`,
      );
    if (attempt === 899) throw new Error("Keycloak did not answer in 3 minutes");
    await new Promise((done) => setTimeout(done, 200));
  }
  keycloak.startSeconds = Math.round((performance.now() - at) / 1000);
  return keycloak;
}

function stopKeycloak(keycloak) {
  if (!keycloak) return;
  spawnSync("docker", ["rm", "-f", keycloak.name], { stdio: "ignore" });
}

/** Keycloak's admin API, as the master realm's administrator. */
async function admin(keycloak, adminLogin, path, { method, body } = {}) {
  const token = await fetch(`${keycloak.base}/realms/master/protocol/openid-connect/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "password",
      client_id: "admin-cli",
      username: adminLogin.user,
      password: adminLogin.password,
    }),
  });
  if (!token.ok) throw new Error(`Keycloak admin sign-in: ${token.status} ${(await token.text()).slice(0, 200)}`);
  const response = await fetch(`${keycloak.base}/admin/realms/${REALM}${path}`, {
    method: method ?? (body ? "POST" : "GET"),
    headers: { Authorization: `Bearer ${(await token.json()).access_token}`, "Content-Type": "application/json" },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  if (!response.ok)
    throw new Error(`Keycloak admin ${path}: ${response.status} ${(await response.text()).slice(0, 200)}`);
  const text = await response.text();
  return text ? JSON.parse(text) : undefined;
}

/** Sign a person in on Keycloak's own page from a browser that holds no session. */
async function signIn(c, who, { context, landing = "/settings/account", password } = {}) {
  const outside = context ?? (await c.signedOutContext({ viewport: { width: 1440, height: 900 } }));
  const page = await outside.newPage();
  page.setDefaultTimeout(20000);
  await page.goto(`${c.uiUrl}${landing}`);
  await page.getByRole("heading", { level: 1, name: "Sign in" }).waitFor();
  await page.getByRole("button", { name: "Continue with Keycloak" }).click();
  await page.locator("#username").waitFor();
  await page.locator("#username").fill(who);
  await page.locator("#password").fill(password ?? c.kc.password(who));
  await page.locator("#kc-login").click();
  return { context: outside, page };
}

async function signedInAs(c, who, options = {}) {
  const landing = options.landing ?? "/settings/account";
  const session = await signIn(c, who, options);
  try {
    await session.page.waitForURL(`${c.uiUrl}${landing}`);
  } catch {
    // The evidence of where the browser stopped: its address and what the page says.
    const text = await session.page
      .locator("body")
      .innerText({ timeout: 3000 })
      .catch(() => "");
    throw new Error(`the browser stopped at ${session.page.url()} saying "${text.replace(/\s+/g, " ").slice(0, 300)}"`);
  }
  await session.page.getByText("Signed in with Keycloak").waitFor();
  return session;
}

const person = async (c, who) => (await c.api(`/users?q=${encodeURIComponent(`${who}@refiroo.test`)}`)).items;
const groupsOf = async (c) => (await c.api("/groups?pageSize=100")).items;

/** The names of the provider groups a person is a member of, read from each group's members. */
async function providerGroupsOf(c, user) {
  const held = [];
  for (const group of await groupsOf(c)) {
    if (!group.source) continue;
    const members = (await c.api(`/groups/${group.id}/members?pageSize=100`)).items;
    if (members.some((member) => member.id === user.id)) held.push(group.name);
  }
  return held.sort();
}

/** One case: the walk goes on whatever it does, so a run reports every case. */
async function runCase(c, number, title, body) {
  try {
    await body();
    results.push({ model: c.tag, number, title, status: "passed" });
    checks.push(`${c.tag}: case ${number} ${title}`);
  } catch (error) {
    const detail = String(error?.message ?? error)
      .split("\n")
      .slice(0, 6)
      .join(" | ");
    results.push({ model: c.tag, number, title, status: "failed", detail });
    failures.push(`${c.tag}: case ${number} (${title}): ${detail}`);
  }
}

async function walk(configuration) {
  const harness = await bootHarness({
    host: "localhost",
    transformModel: configuration.product
      ? (model) => {
          model.product.name = configuration.product;
        }
      : undefined,
  });
  let kc;
  try {
    const { uiUrl, apiUrl, api, output, browser, signedOutContext, harnessIdentity } = harness;
    const tag = configuration.name;
    kc = await startKeycloak(apiUrl, output);
    const adminLogin = { user: "admin", password: "" };
    // The admin password is the one the container was started with; read it back from its environment.
    adminLogin.password = docker(["inspect", "-f", "{{range .Config.Env}}{{println .}}{{end}}", kc.name])
      .split("\n")
      .find((line) => line.startsWith("KC_BOOTSTRAP_ADMIN_PASSWORD="))
      .split("=")[1];
    const c = { tag, uiUrl, apiUrl, api, kc, signedOutContext, browser };
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    page.setDefaultTimeout(20000);
    page.on("pageerror", (error) => failures.push(`${tag}: ${error.message}`));
    const ada = { pending: true };

    await runCase(c, 1, "Register", async () => {
      await page.goto(`${uiUrl}/settings/sign-in`);
      await page.getByRole("heading", { level: 1, name: "Sign-in" }).waitFor();
      await page.getByRole("button", { name: "New provider" }).click();
      const dialog = page.getByRole("dialog", { name: "New sign-in provider" });
      await page.keyboard.type("Keycloak");
      for (const [label, value] of [
        ["Issuer", kc.issuer],
        ["Client ID", "refiroo-engine"],
        ["Client secret", kc.secret],
        ["Groups claim", "groups"],
      ])
        await dialog.getByLabel(label, { exact: true }).fill(value);
      expect(
        (await dialog.getByLabel("Key", { exact: true }).inputValue()) === "keycloak",
        "the key does not follow the name",
      );
      await page.keyboard.press("Enter");
      await dialog.waitFor({ state: "detached" });
      await page.getByRole("heading", { level: 2, name: "Keycloak" }).waitFor();
      const address = `${apiUrl}/oauth/providers/keycloak/callback`;
      await page.getByText(address).first().waitFor();
      expect(address === kc.redirectUri, `the page shows ${address}, the realm file registers ${kc.redirectUri}`);
      const saved = await api("/sign-in-providers/keycloak");
      expect(saved.enabled, "the provider is not enabled after saving");
    });

    await runCase(c, 2, "First sign-in", async () => {
      const session = await signedInAs(c, "ada");
      await session.page.getByText("Ada Lövelace").first().waitFor();
      const [found] = await person(c, "ada");
      expect(found, "no person with ada's e-mail");
      Object.assign(ada, found, { pending: false });
      expect(found.name === "Ada Lövelace", `the person's name is "${found.name}"`);
      expect(found.email === "ada@refiroo.test", `the person's e-mail is "${found.email}"`);
      await session.context.close();
    });

    await runCase(c, 3, "Groups", async () => {
      expect(!ada.pending, "ada was not signed in (case 2)");
      await page.goto(`${uiUrl}/settings/groups`);
      const nav = page.getByRole("navigation", { name: "Groups" });
      await nav.getByRole("heading", { name: "From Keycloak" }).waitFor();
      for (const name of ["finance", "audit"]) {
        await nav.getByRole("button", { name: new RegExp(name) }).click();
        await page.getByRole("heading", { level: 2, name }).waitFor();
        await page.getByRole("group", { name: "Members" }).getByRole("link", { name: "Ada Lövelace" }).waitFor();
      }
      expect(!(await nav.innerText()).includes("/finance"), "a group is listed with its path (leading /)");
      const held = await providerGroupsOf(c, ada);
      expect(held.join() === "audit,finance", `ada's provider groups are [${held}]`);
    });

    await runCase(c, 4, "A person with no group", async () => {
      const session = await signedInAs(c, "cy");
      await session.context.close();
      const [cy] = await person(c, "cy");
      expect(cy, "cy was not made");
      const held = await providerGroupsOf(c, cy);
      expect(!held.length, `cy holds provider groups [${held}]`);
    });

    await runCase(c, 5, "A wrong password", async () => {
      const before = await person(c, "bo");
      const session = await signIn(c, "bo", { password: "not-the-password" });
      await session.page.getByText(/Invalid username or password/).waitFor();
      expect(session.page.url().startsWith(kc.base), `the browser left Keycloak's page for ${session.page.url()}`);
      await session.context.close();
      const after = await person(c, "bo");
      expect(before.length === 0 && after.length === 0, `bo exists after a wrong password (${after.length})`);
    });

    await runCase(c, 6, "Groups change at the provider", async () => {
      const first = await signedInAs(c, "bo");
      await first.context.close();
      const [bo] = await person(c, "bo");
      expect(bo, "bo was not made");
      const before = await providerGroupsOf(c, bo);
      expect(before.join() === "finance", `bo's groups before: [${before}]`);
      const [user] = await admin(kc, adminLogin, "/users?username=bo&exact=true");
      const [audit] = await admin(kc, adminLogin, "/groups?search=audit&exact=true");
      await admin(kc, adminLogin, `/users/${user.id}/groups/${audit.id}`, { method: "PUT" });
      const second = await signedInAs(c, "bo");
      await second.context.close();
      const after = await providerGroupsOf(c, bo);
      expect(after.join() === "audit,finance", `bo's groups after: [${after}]`);
    });

    await runCase(c, 7, "Second sign-in", async () => {
      expect(!ada.pending, "ada was not signed in (case 2)");
      const session = await signedInAs(c, "ada");
      await session.context.close();
      const found = await person(c, "ada");
      expect(
        found.length === 1 && found[0].id === ada.id,
        `ada is now ${found.length} person(s), first id ${found[0]?.id} vs ${ada.id}`,
      );
    });

    await runCase(c, 8, "Sign out of the provider too", async () => {
      await page.goto(`${uiUrl}/settings/sign-in/keycloak`);
      await page.getByRole("heading", { level: 2, name: "Signing out" }).waitFor();
      await page.getByRole("checkbox", { name: /Sign people out of Keycloak too/ }).check();
      await page.getByText(`${apiUrl}/oauth/providers/keycloak/signed-out`).waitFor();
      await page.getByRole("button", { name: "Save", exact: true }).first().click();
      await page.getByText("are signed out of it too").waitFor();
      const session = await signedInAs(c, "ada");
      const visited = [];
      session.page.on("request", (request) => visited.push(request.url()));
      await session.page.getByRole("button", { name: "Sign out", exact: true }).click();
      await session.page.getByRole("heading", { level: 1, name: "Sign in" }).waitFor();
      expect(
        visited.some((url) => url.startsWith(`${kc.issuer}/protocol/openid-connect/logout`)),
        "the browser did not go through Keycloak's end-session endpoint",
      );
      await session.page.getByRole("button", { name: "Continue with Keycloak" }).click();
      await session.page.locator("#password").waitFor();
      expect(session.page.url().startsWith(kc.base), "Continue with Keycloak did not ask for the password again");
      await session.context.close();
    });

    await runCase(c, 9, "Local sign-in off", async () => {
      const [kept] = (await api(`/users?q=${encodeURIComponent(harnessIdentity.person.email)}`)).items;
      await api(`/users/${kept.id}`, { expectedVersion: kept.version, localKept: true }, "PATCH");
      await page.goto(`${uiUrl}/settings/sign-in/local`);
      await page.getByRole("heading", { level: 2, name: "Local accounts" }).waitFor();
      await page.getByRole("button", { name: "Turn off…" }).click();
      const confirm = page.getByRole("alertdialog", { name: "Turn local sign-in off?" });
      await confirm.getByRole("button", { name: "Turn off" }).click();
      await page.getByRole("button", { name: "Turn on" }).waitFor();
      const locked = await signedOutContext({ viewport: { width: 1440, height: 900 } });
      const door = await locked.newPage();
      door.setDefaultTimeout(20000);
      await door.goto(`${uiUrl}/settings/about`);
      await door.getByRole("button", { name: "Continue with Keycloak" }).waitFor();
      await door.getByRole("button", { name: "Sign in with a local administrator account" }).waitFor();
      expect(!(await door.getByLabel("Password").count()), "a password form is offered while local sign-in is off");
      await locked.close();
    });

    await runCase(c, 10, "Keys rotate at the provider (probe)", async () => {
      const keysBefore = (await (await fetch(`${kc.issuer}/protocol/openid-connect/certs`)).json()).keys.map(
        (key) => key.kid,
      );
      const realmId = (await admin(kc, adminLogin, "")).id;
      await admin(kc, adminLogin, "/components", {
        body: {
          name: "rotated-rsa",
          providerId: "rsa-generated",
          providerType: "org.keycloak.keys.KeyProvider",
          parentId: realmId,
          config: { priority: ["500"], keySize: ["2048"], enabled: ["true"], active: ["true"] },
        },
      });
      const keysAfter = (await (await fetch(`${kc.issuer}/protocol/openid-connect/certs`)).json()).keys.map(
        (key) => key.kid,
      );
      expect(
        keysAfter.some((kid) => !keysBefore.includes(kid)),
        "Keycloak published no new key after the rotation",
      );
      const session = await signedInAs(c, "ada");
      await session.context.close();
    });

    await context.close();
    const report = {
      browser: browser.version(),
      model: tag,
      image: IMAGE,
      keycloakStartSeconds: kc.startSeconds,
      results: results.filter((r) => r.model === tag),
    };
    await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
    console.log(`Real provider try (${tag}): ${output}`);
  } finally {
    stopKeycloak(kc);
    harness.cleanup();
  }
}

process.on("SIGINT", () => process.exit(130));
try {
  docker(["info", "--format", "{{.ServerVersion}}"]);
  const image = ensureImage();
  console.log(image.pulled ? `Pulled ${IMAGE} in ${image.seconds}s` : `${IMAGE} already pulled`);
  console.log(`Image size: ${(Number(docker(["image", "inspect", "-f", "{{.Size}}", IMAGE])) / 1e6).toFixed(0)} MB`);
  for (const configuration of MODELS) await walk(configuration);
} catch (error) {
  console.error("Real provider try failed:", error);
  failures.push(String(error?.message ?? error).split("\n")[0]);
}
console.log(`Cases (${Math.round((performance.now() - started) / 1000)}s):`);
for (const result of results)
  console.log(
    `  ${result.model} case ${result.number} ${result.title}: ${result.status}${result.detail ? ` - ${result.detail}` : ""}`,
  );
if (failures.length) {
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
}
