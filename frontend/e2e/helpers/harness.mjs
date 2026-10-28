// Shared test harness: starts isolated backend + frontend, seeds data, provides cleanup.
import { spawn } from "node:child_process";
import { createHash, randomBytes } from "node:crypto";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createServer } from "node:net";
import { chromium } from "playwright";
import { cloneDatabase } from "./database.mjs";

const helpers = dirname(fileURLToPath(import.meta.url));
const frontend = resolve(helpers, "..", "..");
const root = resolve(frontend, "..");

/**
 * Report to `push` every uncaught error in the context's pages and every page part the app's error
 * boundary replaced (React handles those itself, so they are no page error). Once per context.
 */
const watched = new WeakSet();
export function watchPageErrors(context, push) {
  if (watched.has(context)) return context;
  watched.add(context);
  context.on("weberror", (error) => push(error.error().message));
  context.on("console", (message) => {
    if (message.type() === "error" && message.text().startsWith("This page stopped working")) push(message.text());
  });
  return context;
}

/** The requests a signed-in page keeps open for as long as it is shown: the inbox's and a job's event streams. */
export const LONG_LIVED = /\/events(\?|$)/;

/**
 * Make `page.waitForLoadState("networkidle")` mean what the runners meant: no request but the event streams
 * in flight for 500 ms. A signed-in page keeps the inbox's stream open (0.12 I2), so Playwright's own
 * "networkidle" never arrives. Any other state is Playwright's. Safe to call twice for a page.
 */
export function ignoreEventStreams(page) {
  if (page.__ignoresEventStreams) return page;
  page.__ignoresEventStreams = true;
  const pending = new Set();
  const track = (request) => {
    if (!LONG_LIVED.test(new URL(request.url()).pathname + new URL(request.url()).search)) pending.add(request);
  };
  page.on("request", track);
  page.on("requestfinished", (request) => pending.delete(request));
  page.on("requestfailed", (request) => pending.delete(request));
  const original = page.waitForLoadState.bind(page);
  page.waitForLoadState = async (state, options) => {
    if (state !== "networkidle") return original(state, options);
    await original("load", options);
    const timeout = options?.timeout ?? 10000;
    const until = Date.now() + timeout;
    let quietSince = null;
    while (Date.now() < until) {
      if (pending.size === 0) {
        quietSince ??= Date.now();
        if (Date.now() - quietSince >= 500) return;
      } else quietSince = null;
      await new Promise((done) => setTimeout(done, 50));
    }
    throw new Error(
      `page.waitForLoadState: Timeout ${timeout}ms exceeded (in flight: ${[...pending].map((request) => request.url()).join(", ")}).`,
    );
  };
  return page;
}

/** Every page of the context, now and later, waits for network idle without counting the event streams. */
export function ignoreEventStreamsIn(context) {
  context.pages().forEach(ignoreEventStreams);
  context.on("page", ignoreEventStreams);
  return context;
}

/**
 * A token for the seed's harness client (`database.payload.harness`, backend/tests/browser_seeds.py)
 * from the client credentials grant: every route but the open ones needs one (0.12 I1).
 */
export async function harnessToken(apiUrl, harness, scope) {
  const response = await fetch(`${apiUrl}/oauth/token`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      Authorization: `Basic ${Buffer.from(`${harness.clientId}:${harness.clientSecret}`).toString("base64")}`,
    },
    body: scope ? `grant_type=client_credentials&scope=${scope}` : "grant_type=client_credentials",
  });
  if (!response.ok)
    throw new Error(`The harness could not obtain a token: ${response.status} ${await response.text()}`);
  return `Bearer ${(await response.json()).access_token}`;
}

/**
 * Sign a browser context in as the seed's harness person (0.12 I2, D274), through the engine's real
 * sign-in form and code exchange with PKCE. Playwright's request context shares the context's
 * cookies, so the session's refresh cookie lands where the app's pages renew from it.
 */
export async function signInContext(context, { apiUrl, uiUrl, person }) {
  const base64Url = (bytes) => bytes.toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  const verifier = base64Url(randomBytes(48));
  const redirectUri = `${uiUrl}/signed-in`;
  const form = await context.request.post(`${apiUrl}/oauth/authorize`, {
    form: {
      response_type: "code",
      client_id: "browser",
      redirect_uri: redirectUri,
      code_challenge: base64Url(createHash("sha256").update(verifier).digest()),
      code_challenge_method: "S256",
      state: "harness",
      username: person.username,
      password: person.password,
    },
    maxRedirects: 0,
  });
  const location = form.headers().location;
  if (form.status() !== 303 || !location)
    throw new Error(`The harness person could not sign in: ${form.status()} ${(await form.text()).slice(0, 300)}`);
  const exchanged = await context.request.post(`${apiUrl}/oauth/token`, {
    form: {
      grant_type: "authorization_code",
      client_id: "browser",
      code: new URL(location).searchParams.get("code"),
      code_verifier: verifier,
      redirect_uri: redirectUri,
    },
  });
  if (!exchanged.ok()) throw new Error(`The harness person's sign-in was refused: ${await exchanged.text()}`);
  return context;
}

/**
 * Add the token to every `fetch` this process makes to `apiUrl` without an Authorization header of
 * its own, so a runner's direct API calls reach the backend as its pages do.
 */
export function sendTokenTo(apiUrl, token, identity) {
  const original = globalThis.fetch;
  const consumer = { token: undefined };
  const path = (url) => new URL(url).pathname;
  // The consumer routes take a `consumer` token; the routes describing them take either (D266).
  const needsConsumer = (url) => {
    const at = path(url).replace(/\/$/, "");
    return at.startsWith("/api/consumer") && at !== "/api/consumer" && !at.endsWith("/openapi.json");
  };
  const consumerToken = async () => {
    consumer.token ??= await harnessToken(apiUrl, identity(), "consumer");
    return consumer.token;
  };
  globalThis.fetch = async (input, init = {}) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    if (!url.startsWith(apiUrl) || !token()) return original(input, init);
    const headers = new Headers(init.headers ?? (input instanceof Request ? input.headers : undefined));
    if (headers.has("Authorization")) return original(input, { ...init, headers });
    const consumerRoute = identity() && needsConsumer(url);
    headers.set("Authorization", consumerRoute ? await consumerToken() : token());
    const response = await original(input, { ...init, headers });
    if (!consumerRoute || response.status !== 403) return response;
    // A consumer API is read only with a grant of it in the workspace read (Z3, D306): grant the
    // harness client the API the route refused, as a Security administrator would, and ask again (D312).
    const details = (
      await response
        .clone()
        .json()
        .catch(() => ({}))
    ).error?.details;
    if (!details?.consumerApi || !details?.workspaceKey) return response;
    const granted = await original(`${apiUrl}/api/v1/grants`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: token() },
      body: JSON.stringify({
        principal: { kind: "client", id: identity().clientId },
        consumerApi: details.consumerApi,
        scope: { workspaceKey: details.workspaceKey },
      }),
    });
    if (!granted.ok) return response;
    return original(input, { ...init, headers });
  };
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

/**
 * Boot an isolated backend + Vite dev server on a database of its own, cloned from a seed on the
 * development server (`scripts/postgres.sh start`; the starter records unless `prepare` gives
 * one), launch a Chromium browser and return everything the caller needs.
 *
 * @param {object} options
 * @param {boolean} [options.modelAdmin=true] - Enable model admin mutations.
 * @param {boolean} [options.workspaceAdmin=true] - Enable workspace admin mutations.
 * @param {(model: object) => void} [options.transformModel] - Adjust the starter model before startup.
 * @param {(output: string) => Promise<{modelPath: string, database: {databaseUrl: string, drop: () => void}}>} [options.prepare] -
 *   Provide a prepared model and database (from `cloneDatabase`) instead of the starter model and records.
 * @param {{width: number, height: number}} [options.viewport] - Browser viewport; 1440×900 by default.
 * @param {Record<string, string>} [options.backendEnv] - Further backend settings, such as a capability turned on.
 * @param {boolean} [options.oneAddress] - The application and the engine on one address (0.12 DP1, D404):
 *   no `VITE_API_URL`; the Vite server forwards the engine's paths to the engine, and `PUBLIC_URL` is the
 *   application's address. The runner's own calls still reach the engine directly.
 * @param {string} [options.host] - The host the browser reaches the servers by, 127.0.0.1 by default;
 *   `localhost` where a passkey is made (WebAuthn takes no IP address as its relying party, 0.12 I4c).
 * @returns {Promise<{page, browser, apiUrl, uiUrl, output, records, cleanup}>}
 */
export async function bootHarness(options = {}) {
  const {
    modelAdmin = true,
    workspaceAdmin = true,
    transformModel,
    prepare,
    viewport,
    backendEnv = {},
    host = "127.0.0.1",
    oneAddress = false,
  } = options;
  const started = performance.now();
  // Setup phase durations in milliseconds, separated from the runner's own checks (WP-13B).
  const timings = {};
  const mark = (phase, since) => {
    timings[phase] = Math.round(performance.now() - since);
    return performance.now();
  };
  const output = await mkdtemp(resolve(tmpdir(), "rdm-ui07-gate-"));
  const processes = [];
  let log = "";
  // Uncaught errors in any page the run opens, and a page part the error boundary replaced: either
  // fails the run at cleanup, whatever its checks said (a dialog blanked the page unnoticed, 2026-10-14).
  const pageErrors = [];

  function start(command, args, cwd, env) {
    const child = spawn(command, args, { cwd, env: { ...process.env, ...env }, stdio: ["ignore", "pipe", "pipe"] });
    processes.push(child);
    child.stdout.on("data", (data) => {
      log += data;
    });
    child.stderr.on("data", (data) => {
      log += data;
    });
    child.on("error", (error) => {
      log += error.message;
    });
    return child;
  }

  async function ready(url, child) {
    for (let attempt = 0; attempt < 200; attempt++) {
      if (child.exitCode !== null) throw new Error(`Server exited: ${log}`);
      try {
        if ((await fetch(url)).ok) return;
      } catch {
        /* starting */
      }
      await new Promise((done) => setTimeout(done, 100));
    }
    throw new Error(`Server did not become ready: ${url}\n${log}`);
  }

  const apiPort = await freePort();
  const uiPort = await freePort();
  const apiUrl = `http://${host}:${apiPort}`;
  const uiUrl = `http://${host}:${uiPort}`;
  // The harness client's access token, sent with the runners' own API calls (0.12 I1, D263); the
  // pages sign in as the harness person instead (I2, D274).
  let authorization = "";
  sendTokenTo(
    apiUrl,
    () => authorization,
    () => database?.payload.harness,
  );

  async function api(path, body, method) {
    const response = await fetch(`${apiUrl}/api/v1${path}`, {
      method: method || (body ? "POST" : "GET"),
      headers: { "Content-Type": "application/json" },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
    if (!response.ok) throw new Error(`${path}: ${response.status} ${await response.text()}`);
    const text = await response.text();
    return text ? JSON.parse(text) : undefined;
  }

  let modelPath = resolve(output, "model.json");
  let database;
  const records = { domain: [], system: [] };
  if (prepare) ({ modelPath, database } = await prepare(output));
  else {
    const model = JSON.parse(await readFile(resolve(root, "model/rdm-starter.json"), "utf8"));
    transformModel?.(model);
    await writeFile(modelPath, JSON.stringify(model));
    // The starter records, created through the API when the seed was built (browser_seeds.py).
    database = cloneDatabase("starter", { model: modelPath });
    Object.assign(records, database.payload.records);
  }
  let phase = mark("seed", started);

  let browser;
  let page;
  // A context that is not signed in, for a runner that walks the sign-in itself (0.12 I2).
  let signedOutContext;
  try {
    const backend = start(
      resolve(root, "backend/.venv/bin/python"),
      ["-m", "uvicorn", "app.main:app", "--host", host, "--port", String(apiPort)],
      resolve(root, "backend"),
      {
        DATABASE_URL: database.databaseUrl,
        RDM_MODEL_PATH: modelPath,
        CORS_ORIGINS: uiUrl,
        // The engine's address as the browser reaches it: the token issuer and its pages (0.12 I1, I2).
        PUBLIC_URL: oneAddress ? uiUrl : apiUrl,
        MODEL_ADMIN_MUTATIONS_ENABLED: String(modelAdmin),
        WORKSPACE_ADMIN_MUTATIONS_ENABLED: String(workspaceAdmin),
        WEB_CONCURRENCY: "1",
        // Export files (0.9 J1) stay in the run's own folder, never the project's var/.
        JOB_FILE_DIR: resolve(output, "job-files"),
        // The seed's harness client and the key its signing key is sealed with (0.12 I1).
        ...database.payload.harness.settings,
        ...backendEnv,
      },
    );
    await ready(`${apiUrl}/health`, backend);
    authorization = await harnessToken(apiUrl, database.payload.harness);
    phase = mark("backendReady", phase);

    const ui = start(
      process.execPath,
      ["node_modules/vite/bin/vite.js", "--host", host, "--port", String(uiPort), "--strictPort"],
      frontend,
      oneAddress ? { ENGINE_URL: apiUrl } : { VITE_API_URL: apiUrl },
    );
    await ready(uiUrl, ui);
    phase = mark("viteReady", phase);

    browser = await chromium.launch({
      headless: true,
      ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}),
    });

    const watch = (context) => ignoreEventStreamsIn(watchPageErrors(context, (error) => pageErrors.push(error)));
    // Every context is signed in as the harness person through the sign-in form (0.12 I2, D274);
    // the pages carry no injected token, so a page that forgets the header fails here.
    const person = database.payload.harness.person;
    const signedIn = (context) => signInContext(context, { apiUrl, uiUrl, person });
    const newContext = browser.newContext.bind(browser);
    signedOutContext = async (...args) => watch(await newContext(...args));
    browser.newContext = async (...args) => watch(await signedIn(await newContext(...args)));
    const newPage = browser.newPage.bind(browser);
    browser.newPage = async (...args) => {
      const context = await browser.newContext(...args);
      return context.newPage();
    };

    const context = await browser.newContext({ hasTouch: true, viewport: viewport ?? { width: 1440, height: 900 } });
    page = await context.newPage();
    page.setDefaultTimeout(10000);
    mark("browserLaunch", phase);
    timings.setupTotal = Math.round(performance.now() - started);
  } catch (error) {
    for (const child of processes) {
      try {
        child.kill();
      } catch {
        /* ignore */
      }
    }
    await browser?.close().catch(() => {});
    database.drop();
    throw error;
  }

  function cleanup() {
    timings.total = Math.round(performance.now() - started);
    timings.checks = timings.total - timings.setupTotal;
    console.error(`harness timings (ms): ${JSON.stringify(timings)}`);
    if (pageErrors.length) {
      console.error(`page errors (the run fails):\n${pageErrors.map((error) => `- ${error}`).join("\n")}`);
      process.exitCode = 1;
    }
    try {
      browser?.close();
    } catch {
      /* ignore */
    }
    for (const child of processes) {
      try {
        child.kill();
      } catch {
        /* ignore */
      }
    }
    // Dropped WITH (FORCE), which closes any connection the stopping backend still holds.
    database.drop();
  }

  return {
    page,
    browser,
    apiUrl,
    uiUrl,
    output,
    records,
    signedOutContext,
    // The person every context is signed in as, and the harness client's credentials (0.12 I2).
    harnessIdentity: database.payload.harness,
    api,
    timings,
    pageErrors,
    // The run's own database, for a runner that works on it from outside the API (0.11 O2).
    databaseUrl: database.databaseUrl,
    log: () => log,
    cleanup,
  };
}
