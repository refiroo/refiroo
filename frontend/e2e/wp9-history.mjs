// Real-backend SC-08 regression. All model/data mutations target a temporary database.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createServer } from "node:net";
import { chromium } from "playwright";

const frontend = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const root = resolve(frontend, "..");
const output = await mkdtemp(resolve(tmpdir(), "rdm-wp9-history-"));
const processes = [];
const failures = [];
const checks = [];
let browser;
let log = "";

async function port() {
  const server = createServer();
  await new Promise((done, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", done);
  });
  const value = server.address().port;
  await new Promise((done) => server.close(done));
  return value;
}
function start(command, args, cwd, env) {
  const child = spawn(command, args, { cwd, env: { ...process.env, ...env }, stdio: ["ignore", "pipe", "pipe"] });
  processes.push(child);
  child.stdout.on("data", (data) => (log += data));
  child.stderr.on("data", (data) => (log += data));
  return child;
}
async function ready(url, child) {
  for (let attempt = 0; attempt < 200; attempt++) {
    if (child.exitCode !== null) throw new Error(`Server exited: ${log}`);
    try {
      if ((await fetch(url)).ok) return;
    } catch {
      // Server is still starting.
    }
    await new Promise((done) => setTimeout(done, 100));
  }
  throw new Error(`Server did not become ready: ${url}\n${log}`);
}

const apiPort = await port();
const uiPort = await port();
const apiUrl = `http://127.0.0.1:${apiPort}`;
const uiUrl = `http://127.0.0.1:${uiPort}`;
async function api(path, body, method = body ? "POST" : "GET") {
  const response = await fetch(`${apiUrl}/api/v1${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  assert(response.ok, `${path}: ${response.status} ${await response.clone().text()}`);
  return response.status === 204 ? undefined : response.json();
}

try {
  const model = JSON.parse(await readFile(resolve(root, "model/rdm-starter.json"), "utf8"));
  const oldModelVersion = model.release.version;
  model.attributeTypes.push({
    key: "qa-history-count",
    name: "History count",
    valueType: "integer",
    features: { filterable: true, sortable: true },
  });
  model.objectTypes.find((item) => item.key === "domain").attributes.push({ attributeTypeKey: "qa-history-count" });
  for (const app of model.applications) {
    for (const view of app.views.filter((item) => item.objectTypeKey === "domain"))
      view.config.columns.push("qa-history-count");
    for (const detail of app.details.filter((item) => item.objectTypeKey === "domain")) {
      const attributes = detail.panels.find((item) => item.type === "attributes");
      if (attributes) attributes.config.fields.push("qa-history-count");
    }
  }
  const modelPath = resolve(output, "model.json");
  await writeFile(modelPath, JSON.stringify(model));
  const backend = start(
    resolve(root, "backend/.venv/bin/python"),
    ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(apiPort)],
    resolve(root, "backend"),
    {
      DATABASE_URL: `sqlite:///${resolve(output, "database.sqlite")}`,
      RDM_MODEL_PATH: modelPath,
      CORS_ORIGINS: uiUrl,
      MODEL_ADMIN_MUTATIONS_ENABLED: "true",
      WORKSPACE_ADMIN_MUTATIONS_ENABLED: "true",
      WEB_CONCURRENCY: "1",
    },
  );
  await ready(`${apiUrl}/health`, backend);
  const ui = start(
    process.execPath,
    ["node_modules/vite/bin/vite.js", "--host", "127.0.0.1", "--port", String(uiPort), "--strictPort"],
    frontend,
    { VITE_API_URL: apiUrl },
  );
  await ready(uiUrl, ui);

  const workspaceKey = "history";
  await api("/workspaces", { key: workspaceKey, label: "History acceptance" });
  const domain = await api("/objects", {
    workspaceKey,
    applicationKey: "rdm-master",
    objectTypeKey: "domain",
    name: "Published old domain",
    attributes: [
      { attributeTypeKey: "domain-code", value: "HISTORY" },
      { attributeTypeKey: "qa-history-count", value: 7 },
    ],
  });
  async function publish(name, expectedActiveRevisionId) {
    const draft = await api(`/workspaces/${workspaceKey}/drafts`, { name, source: "currentLive" });
    return api(`/workspace-drafts/${draft.id}/activation`, {
      expectedDraftVersion: draft.version,
      expectedActiveRevisionId,
    });
  }
  const oldRevision = await publish("Old publication", null);
  const changed = await api(
    `/objects/domain/${domain.id}`,
    {
      expectedVersion: domain.version,
      name: "Current live domain",
      attributes: [
        { attributeTypeKey: "domain-code", value: "HISTORY" },
        { attributeTypeKey: "qa-history-count", value: 9 },
      ],
    },
    "PATCH",
  );

  const runtimeBefore = await api("/model-runtime-state");
  const candidate = structuredClone(model);
  candidate.release.version = `${oldModelVersion}-history-new`;
  candidate.product.description = "Current definition after historical publication";
  const modelDraft = await api("/model-drafts", {
    name: "History model change",
    baseReleaseId: runtimeBefore.activeReleaseId,
    model: candidate,
  });
  const installed = await api(`/model-drafts/${modelDraft.id}/installation`, { expectedVersion: modelDraft.version });
  await api(`/model-releases/${installed.id}/activation`, {
    expectedRuntimeVersion: runtimeBefore.version,
    expectedActiveReleaseId: runtimeBefore.activeReleaseId,
  });
  const currentRevision = await publish("Current publication", oldRevision.id);

  browser = await chromium.launch({
    headless: true,
    ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}),
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.setDefaultTimeout(10000);
  page.on("pageerror", (error) => failures.push(error.message));
  const historicalReads = [];
  page.on("request", (request) => {
    if (request.url().includes("workspaceRevisionId=")) historicalReads.push(request.url());
  });

  await page.goto(`${uiUrl}/apps/rdm-master/history?workspaceKey=${workspaceKey}`);
  await page.getByRole("heading", { name: new RegExp(`Revision ${oldRevision.revisionNumber} · Historical snapshot`) }).waitFor();
  const revisionHeadings = await page.locator("article.history-card h2").allTextContents();
  assert.match(revisionHeadings[0], new RegExp(`Revision ${currentRevision.revisionNumber} · Current publication`));
  assert.match(revisionHeadings[1], new RegExp(`Revision ${oldRevision.revisionNumber} · Historical snapshot`));
  const oldCard = page.locator("article.history-card").filter({
    has: page.getByRole("heading", { name: new RegExp(`Revision ${oldRevision.revisionNumber} · Historical snapshot`) }),
  });
  await oldCard.getByRole("button", { name: "Inspect snapshot" }).click();
  await page.locator("main table").getByRole("button", { name: "Published old domain", exact: true }).click();
  await page.getByRole("heading", { name: "Published old domain", exact: true }).waitFor();
  assert.match(await page.locator("main").innerText(), /History count\s*7/i);
  await page.getByText("Information", { exact: true }).click();
  await page.getByText(`Model version ${oldModelVersion}`, { exact: true }).waitFor();
  await page.getByText("Information", { exact: true }).click();
  await page.getByRole("button", { name: "Record actions", exact: true }).click();
  assert.equal(await page.getByRole("menuitem", { name: "Edit all fields", exact: true }).count(), 0);
  await page.keyboard.press("Escape");
  assert(historicalReads.some((url) => url.includes(`workspaceRevisionId=${oldRevision.id}`)));
  await page.screenshot({ path: resolve(output, "historical-snapshot.png"), fullPage: true });
  checks.push("Older snapshot remains typed and unchanged under its pinned model; shared list/detail reads carry the immutable revision and expose no write controls");

  await page.getByRole("button", { name: "Back to publication history" }).click();
  const sourceCard = oldCard;
  await sourceCard.getByRole("button", { name: "Start a draft from this revision" }).click();
  await page.getByRole("dialog").getByLabel("Draft name").fill("Historical review");
  await page.getByRole("dialog").getByRole("button", { name: "Create draft" }).click();
  await page.getByRole("heading", { name: /Historical review · Draft v/ }).waitFor();
  const draftText = await page.locator("main").innerText();
  assert.match(draftText, new RegExp(`Source: Historical revision ${oldRevision.id}`));
  assert.match(draftText, /Draft model differs from the current model/);
  checks.push("Historical derivation is explicitly labelled, keeps the old model pin and explains that Base 0.6 requires migration instead of promising restore or implicit override");

  await page.goto(`${uiUrl}/apps/rdm-master/history?workspaceKey=${workspaceKey}`);
  const currentCard = page.locator("article.history-card").filter({
    has: page.getByRole("heading", { name: new RegExp(`Revision ${currentRevision.revisionNumber} · Current publication`) }),
  });
  await currentCard.getByRole("button", { name: "Retire publication" }).click();
  const confirmation = page.getByRole("alertdialog");
  assert.match(await confirmation.innerText(), /Live records and all historical snapshots remain available/);
  await confirmation.getByRole("button", { name: "Retire publication" }).click();
  await page.getByText(/no longer the current publication/).waitFor();
  const afterRetirement = await api(`/workspaces/${workspaceKey}/revisions`);
  assert.equal(afterRetirement.items[0].status, "retired");
  assert.equal((await api(`/objects/domain/${changed.id}?workspaceKey=${workspaceKey}`)).name, "Current live domain");
  await page.screenshot({ path: resolve(output, "publication-retired.png"), fullPage: true });
  checks.push("Publication retirement names the selected revision and removes only its designation; current live data and both immutable snapshots remain readable");

  await api("/workspaces", { key: "other", label: "Other workspace" });
  const workspaceState = await api("/workspace-runtime-state");
  await api("/workspace-runtime-state", { defaultWorkspaceKey: "other", expectedVersion: workspaceState.version }, "PATCH");
  const workspace = await api(`/workspaces/${workspaceKey}`);
  await api(`/workspaces/${workspaceKey}`, { expectedVersion: workspace.version, status: "retired" }, "PATCH");
  await page.reload();
  await page.getByText("Read-only workspace").waitFor();
  assert.equal(await page.getByRole("button", { name: "Start a draft from this revision" }).count(), 0);
  assert.equal(await page.getByRole("button", { name: "Retire publication" }).count(), 0);
  checks.push("Catalogue retirement is a separate read-only state: history stays visible while draft and publication mutations disappear");

  assert.deepEqual(failures, []);
  const report = {
    browser: browser.version(),
    viewports: ["1440x1000"],
    checks,
    pageErrors: failures,
    historicalReadCount: historicalReads.length,
    isolatedDatabase: resolve(output, "database.sqlite"),
  };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ ...report, output }, null, 2));
} catch (error) {
  if (browser) {
    const page = browser.contexts()[0]?.pages()[0];
    if (page) {
      await page.screenshot({ path: resolve(output, "failure.png"), fullPage: true }).catch(() => {});
      await writeFile(resolve(output, "failure.html"), await page.content()).catch(() => {});
    }
  }
  console.error(`Browser evidence: ${output}`);
  throw error;
} finally {
  await browser?.close();
  for (const child of processes) child.kill("SIGTERM");
  await writeFile(resolve(output, "servers.log"), log);
}
