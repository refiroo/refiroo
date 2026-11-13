// Base 0.11 O2: Settings › Operations (J12.13, J12.16, J12.17 in the browser) against a real backend
// whose workspaces run two models: the journey configurations generated-a and generated-b, each
// installed and given a workspace of its own. Rehearsals are real: the run's database dumped with
// pg_dump, restored with pg_restore into a scratch database and checked with
// `python -m app.cli.restore_check`, as an operator runs them. The runner names no key of either
// model. Cases (the O2 plan):
//   1. Settings › Operations reached by keyboard: every workspace served, the one process live and
//      ready with its threads, no backup rehearsed yet;
//   2. a rehearsal recorded, then Refresh by keyboard: passed, each workspace of the copy with its
//      release and counts;
//   3. a rehearsal into a copy with the wrong collation: failed with its reason; the earlier one
//      shown on demand by keyboard;
//   4. axe; 1440px and 390px without sideways scroll; light and dark screenshots.
// Brought up to date (0.14 + 0.17 release review, ST1): earlier rehearsals are setting rows, not a list; the backup's name is their code text.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";

const root = resolve(import.meta.dirname, "..", "..");
const backend = resolve(root, "backend");
const checks = [];

function python(code, env = {}) {
  return execFileSync(resolve(backend, ".venv/bin/python"), ["-c", code], {
    cwd: backend,
    env: { ...process.env, ...env },
  }).toString();
}

const models = JSON.parse(
  python(`
import json, sys
sys.path[:0] = ['tests/journeys', 'tests']
from configurations import generated
print(json.dumps({variant: generated(variant).model for variant in ('a', 'b')}))
`),
);

/** The run's database dumped, restored into a scratch database (with `options`), checked with the
 * engine's command and dropped: the command's exit status. */
function rehearse(databaseUrl, backup, options = "") {
  const code = `
import os, subprocess, sys, tempfile
sys.path[:0] = ['tests']
import postgres_server
from sqlalchemy import create_engine, make_url, text
from sqlalchemy.pool import NullPool
url = make_url(os.environ['DATABASE_URL'])
copy = url.set(database='rdm_o2_restore_check')
def libpq(target):
    host = target.query.get('host') or target.host
    port = target.query.get('port') or str(target.port or 5432)
    return ['-h', str(host), '-p', str(port), '-U', target.username or 'postgres', '-d', target.database]
admin = create_engine(url.set(database='postgres'), poolclass=NullPool, isolation_level='AUTOCOMMIT')
with admin.connect() as server:
    server.execute(text('DROP DATABASE IF EXISTS rdm_o2_restore_check WITH (FORCE)'))
    server.execute(text('CREATE DATABASE rdm_o2_restore_check TEMPLATE template0 ' + os.environ['OPTIONS']))
try:
    with tempfile.TemporaryDirectory() as folder:
        dump = os.path.join(folder, 'run.dump')
        subprocess.run([postgres_server._binary('pg_dump'), '-Fc', '--exclude-table-data=engine_processes', '-f', dump, *libpq(url)], check=True)
        subprocess.run([postgres_server._binary('pg_restore'), '--no-owner', *libpq(copy), dump], check=True)
    done = subprocess.run([sys.executable, '-m', 'app.cli.restore_check', '--restored', copy.render_as_string(hide_password=False), '--backup', os.environ['BACKUP']], capture_output=True, text=True)
    print(done.returncode)
finally:
    with admin.connect() as server:
        server.execute(text('DROP DATABASE IF EXISTS rdm_o2_restore_check WITH (FORCE)'))
    admin.dispose()
`;
  return Number(
    python(code, { DATABASE_URL: databaseUrl, BACKUP: backup, OPTIONS: options }).trim().split("\n").at(-1),
  );
}

async function assertAccessible(target, name) {
  const result = await runAxe(target, [], name);
  assert.equal(result.violations.length, 0, `${name}: ${formatViolations(result.violations)}`);
}

const harness = await bootHarness();
const { page, api, uiUrl, output } = harness;
const shot = (name) => page.screenshot({ path: resolve(output, `o2-${name}.png`), fullPage: true });
const shotBoth = async (name) => {
  await shot(`${name}-light`);
  await page.emulateMedia({ colorScheme: "dark" });
  await page.waitForTimeout(400);
  await shot(`${name}-dark`);
  await page.emulateMedia({ colorScheme: "light" });
  await page.waitForTimeout(400);
};
const noSidewaysScroll = async (what) =>
  assert.equal(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    true,
    `${what} scrolls sideways`,
  );

try {
  const workspaces = [];
  for (const [variant, model] of Object.entries(models)) {
    const draft = await api("/model-drafts", { name: `Model ${variant}`, model });
    const release = await api(`/model-drafts/${draft.id}/installation`, { expectedVersion: draft.version });
    const key = `site-${variant}`;
    await api("/workspaces", { key, label: `Site ${variant.toUpperCase()}`, modelReleaseId: release.id });
    workspaces.push(key);
  }

  // 1. Reached by keyboard from Settings.
  await page.goto(`${uiUrl}/settings/about`);
  const navigation = page.getByRole("navigation", { name: "Settings" });
  const link = navigation.getByRole("link", { name: "Operations" });
  await link.focus();
  await page.keyboard.press("Enter");
  await page.waitForURL(/\/settings\/operations$/);
  await page.getByRole("heading", { level: 1, name: "Operations" }).waitFor();
  const readiness = page.getByRole("group", { name: "Workspaces" });
  for (const key of workspaces) await readiness.getByRole("row").filter({ hasText: key }).getByText("Served").waitFor();
  const served = await api("/system/summary");
  assert.equal(served.workspaces.unavailable, 0);
  await page.getByText(`${served.workspaces.served} of ${served.workspaces.served} served`).waitFor();
  await page.getByText("1 live", { exact: true }).waitFor();
  await page.getByText("Job worker", { exact: true }).waitFor();
  await page.getByText("No backup has been rehearsed").waitFor();
  await assertAccessible(page, "the Operations page, nothing rehearsed");
  checks.push("1. Settings › Operations by keyboard: every workspace served, one process live with its threads, nothing rehearsed");

  // 2. A rehearsal recorded, then Refresh by keyboard.
  assert.equal(rehearse(harness.databaseUrl, "o2-run.dump"), 0, "the rehearsal passed");
  const refresh = page.getByRole("button", { name: "Refresh" });
  await refresh.focus();
  await page.keyboard.press("Enter");
  await page.getByText("Passed", { exact: true }).waitFor();
  await page.getByText("o2-run.dump").waitFor();
  const copy = page.getByRole("group", { name: "Each workspace in the restored copy" });
  for (const key of workspaces) await copy.getByRole("row").filter({ hasText: key }).getByText("Served").waitFor();
  await assertAccessible(page, "the Operations page, rehearsal passed");
  await shotBoth("passed");
  checks.push("2. a real rehearsal recorded; Refresh by keyboard shows it passed with each workspace of the copy");

  // 3. A copy with the wrong collation.
  assert.equal(rehearse(harness.databaseUrl, "o2-libc.dump", "LOCALE_PROVIDER libc LOCALE 'C'"), 1);
  await refresh.focus();
  await page.keyboard.press("Enter");
  await page.getByText("The copy has the wrong collation").waitFor();
  await page.getByText(/ICU root collation 'und'/).waitFor();
  const earlier = page.getByRole("button", { name: /^Show earlier rehearsals/ });
  await earlier.focus();
  await page.keyboard.press("Enter");
  await page.locator("code", { hasText: "o2-run.dump" }).waitFor();
  await assertAccessible(page, "the Operations page, rehearsal failed");
  await shotBoth("failed");
  checks.push("3. a rehearsal into a libc copy: failed with the collation reason; the earlier one shown by keyboard");

  // 4. 1440px and 390px.
  await noSidewaysScroll("the Operations page at 1440px");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  await page.getByRole("heading", { level: 1, name: "Operations" }).waitFor();
  await page.getByText("The copy has the wrong collation").waitFor();
  await noSidewaysScroll("the Operations page at 390px");
  await assertAccessible(page, "the Operations page at 390px");
  await shotBoth("phone");
  checks.push("4. axe clean; no sideways scroll at 1440px and 390px; light and dark screenshots");

  console.log(`operations-o2: ${checks.length} cases passed\n- ${checks.join("\n- ")}\nscreenshots: ${output}`);
} catch (error) {
  await shot("failure").catch(() => {});
  console.error(`operations-o2 failed after ${checks.length} cases: ${error.stack ?? error}\nscreenshots: ${output}`);
  console.error(harness.log().slice(-4000));
  process.exitCode = 1;
} finally {
  harness.cleanup();
}
