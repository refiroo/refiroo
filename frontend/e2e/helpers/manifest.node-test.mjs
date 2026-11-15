import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { test } from "node:test";
import { EVERY_PICTURE, FRAME_FILES, RUNNERS, SCENARIOS, SHARED_LAYERS } from "../manifest.mjs";
import { backendEffect, entryDifferences, importGraph, reached, select } from "./changed.mjs";
import { groupOf, matches, scenarioFilter } from "./scenarios.mjs";

const frontend = resolve(import.meta.dirname, "..", "..");
const packageJson = JSON.parse(readFileSync(resolve(frontend, "package.json"), "utf8"));

test("every path the manifest names exists", () => {
  const paths = [
    ...Object.values(RUNNERS).flat(),
    ...SCENARIOS.flatMap((entry) => entry.paths),
    ...SHARED_LAYERS,
    ...EVERY_PICTURE,
    ...FRAME_FILES,
  ];
  const missing = [...new Set(paths)].filter((path) => !existsSync(resolve(frontend, path)));
  assert.deepEqual(missing, [], `the manifest names paths that are not there: ${missing.join(", ")}`);
});

test("every browser runner has an entry, and every entry names a runner", () => {
  const { missing, stale } = entryDifferences(packageJson);
  assert.deepEqual(missing, [], `runners with no entry in e2e/manifest.mjs: ${missing.join(", ")}`);
  assert.deepEqual(stale, [], `entries naming no runner: ${stale.join(", ")}`);
  for (const [name, paths] of Object.entries(RUNNERS)) assert.ok(paths.length > 0, `${name} names no path`);
});

/** The names a gate's source gives literally: runAxe(page, ALLOWLIST, "name"), a ["name", "/path"] row and capture(page, "name", ...). */
function literalNames() {
  const names = new Set();
  for (const [file, pattern] of [
    ["accessibility-gate.mjs", /runAxe\(\w+, ALLOWLIST, "([^"$]+)"|\[\s*"([\w-]+)",\s*"\//g],
    ["visual-regression-gate.mjs", /capture\(\w+, "([^"$]+)"/g],
  ])
    for (const [, name, listed] of readFileSync(resolve(frontend, "e2e", file), "utf8").matchAll(pattern))
      names.add(name ?? listed);
  return names;
}

test("every baseline and every scenario the gates name belongs to a group, and every group has one", () => {
  const baselines = readdirSync(resolve(frontend, "e2e/baselines"))
    .filter((file) => file.endsWith(".png"))
    .map((file) => file.replace(/\.png$/, ""));
  const names = [...baselines, ...literalNames()];
  assert.ok(baselines.length > 150);
  const ungrouped = names.filter((name) => !groupOf(name));
  assert.deepEqual(ungrouped, [], `scenarios no group names: ${ungrouped.join(", ")}`);
  for (const entry of SCENARIOS) {
    assert.ok(entry.paths.length > 0, `${entry.group} names no path`);
    const unused = entry.names.filter((pattern) => !names.some((name) => matches(pattern, name)));
    assert.deepEqual(unused, [], `${entry.group}: patterns that match no scenario: ${unused.join(", ")}`);
  }
});

test("a scenario filter keeps its groups, refuses an unknown group and a scenario no group names", () => {
  const filter = scenarioFilter(["--scenario", "bulk changes"]);
  assert.equal(filter.selected("bulk-delete-light"), true);
  assert.equal(filter.selected("dark-collection-domain"), false);
  assert.equal(scenarioFilter([]).selected("collection-table-domain-dark"), true);
  assert.throws(() => scenarioFilter(["--scenario", "nothing"]), /Unknown scenario group/);
  assert.throws(() => scenarioFilter([]).selected("a-new-screen-light"), /no group/);
  assert.equal(matches("security-home*", "security-home-phone-dark"), true);
  assert.equal(matches("bulk-*", "dark-bulk-delete"), true);
});

/** A small source tree: one feature per screen, shared layers and a runner helper. */
function tree(files) {
  const root = mkdtempSync(resolve(tmpdir(), "rdm-manifest-"));
  for (const [path, text] of Object.entries(files)) {
    mkdirSync(dirname(resolve(root, path)), { recursive: true });
    writeFileSync(resolve(root, path), text);
  }
  return root;
}

test("a change in a shared layer selects what imports it, directly or through other shared files", () => {
  const root = tree({
    "src/lib/words.ts": "export const words = 1;",
    "src/ui/Chip.tsx": 'import { words } from "@/lib/words"; export const Chip = words;',
    "src/features/alpha/Page.tsx": 'import { Chip } from "../../ui/Chip"; export default Chip;',
    "src/features/beta/Page.tsx": "export default 2;",
    "src/features/gamma/Page.tsx": 'import { words } from "@/lib/words"; export default words;',
    "src/features/delta/Page.tsx": 'import Alpha from "@/features/alpha/Page"; export default Alpha;',
    "e2e/helpers/seeds.mjs": "export const seed = 1;",
    "e2e/a-runner.mjs": 'import { seed } from "./helpers/seeds.mjs"; seed;',
  });
  try {
    const graph = importGraph(root);
    const runners = {
      alpha: ["src/features/alpha"],
      beta: ["src/features/beta"],
      gamma: ["src/features/gamma"],
      delta: ["src/features/delta"],
      "a-runner": ["src/features/beta"],
    };
    const scenarios = [{ group: "alpha screens", names: ["alpha-*"], paths: ["src/features/alpha"] }];
    const pick = (...files) =>
      select(files, { graph, runners, scenarios, shared: ["src/ui", "src/lib"], everyPicture: ["src/styles"] });
    // lib reaches ui, the features importing either, and the features importing those (delta shows alpha's page)
    assert.deepEqual(pick("src/lib/words.ts").runners, ["alpha", "delta", "gamma"]);
    assert.deepEqual(pick("src/lib/words.ts").groups, ["alpha screens"]);
    assert.deepEqual(pick("src/ui/Chip.tsx").runners, ["alpha", "delta"]);
    // a feature's own file selects the entries naming it, nothing else
    assert.deepEqual(pick("src/features/beta/Page.tsx").runners, ["a-runner", "beta"]);
    // a runner's own file and a helper it imports
    assert.deepEqual(pick("e2e/a-runner.mjs").runners, ["a-runner"]);
    assert.deepEqual(pick("e2e/helpers/seeds.mjs").runners, ["a-runner"]);
    // a style selects every scenario; a file no entry covers is reported
    assert.deepEqual(pick("src/styles/x.css").groups, ["alpha screens"]);
    assert.deepEqual(pick("src/features/zeta/Page.tsx").unowned, ["src/features/zeta/Page.tsx"]);
    assert.deepEqual(reached("src/lib/words.ts", graph, ["src/ui", "src/lib"]).size, 5);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("the real source tree: a shared helper selects the features that import it", () => {
  const graph = importGraph(frontend);
  const files = reached("src/lib/count.ts", graph);
  assert.ok(files.size > 1, "src/lib/count.ts is imported by something");
  const { runners } = select(["src/lib/count.ts"], { graph });
  assert.ok(runners.length > 0);
});

test("a feature file shown by another feature selects the importing feature, not the shell that mounts it", () => {
  const root = tree({
    "src/app/Shell.tsx": 'import Alpha from "@/features/alpha/Page"; export default Alpha;',
    "src/app/TopBar.tsx": "export default 1;",
    "src/features/alpha/Page.tsx": 'import Panel from "@/features/beta/Panel"; export default Panel;',
    "src/features/alpha/Own.tsx": 'import Page from "./Page"; export default Page;',
    "src/features/beta/Panel.tsx": "export default 2;",
    "src/features/gamma/Page.tsx": 'import Alpha from "@/features/alpha/Page"; export default Alpha;',
  });
  try {
    const graph = importGraph(root);
    const runners = {
      alpha: ["src/features/alpha"],
      beta: ["src/features/beta"],
      gamma: ["src/features/gamma"],
      shell: ["src/app"],
    };
    const scenarios = [{ group: "all", names: ["all-*"], paths: ["src/features/alpha"] }];
    const pick = (file) =>
      select([file], {
        graph,
        runners,
        scenarios,
        shared: ["src/ui"],
        everyPicture: ["src/styles"],
        frame: ["src/app/TopBar.tsx"],
      });
    // beta's panel is shown by alpha's page, which gamma shows in turn; the shell that mounts them is not followed
    assert.deepEqual(pick("src/features/beta/Panel.tsx").runners, ["alpha", "beta", "gamma"]);
    assert.deepEqual(pick("src/features/beta/Panel.tsx").groups, ["all"]);
    assert.deepEqual(pick("src/features/alpha/Page.tsx").runners, ["alpha", "gamma"]);
    // a frame file selects every scenario for the gates
    assert.deepEqual(pick("src/app/TopBar.tsx").groups, ["all"]);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("the shell's frame files select every scenario; a file they import does not", () => {
  const graph = importGraph(frontend);
  for (const file of FRAME_FILES) assert.equal(select([file], { graph }).groups.length, SCENARIOS.length, file);
  assert.ok(select(["src/app/useRouter.ts"], { graph }).groups.length < SCENARIOS.length);
});

test("backend changes: the shared seeds select every runner, other paths are only noted", () => {
  assert.deepEqual(backendEffect(["backend/tests/browser_seeds.py", "backend/app/x.py"]), {
    everyRunner: true,
    others: ["backend/app/x.py"],
  });
  assert.deepEqual(backendEffect(["backend/app/x.py"]), { everyRunner: false, others: ["backend/app/x.py"] });
});

test("changed.mjs fails when a changed src/ path is unowned and names it", () => {
  const root = mkdtempSync(resolve(tmpdir(), "rdm-changed-test-"));
  try {
    const run = (...args) => spawnSync("git", args, { cwd: root, encoding: "utf8" });
    run("init", "-q");
    run("-c", "user.email=a@b", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "base");
    const base = run("rev-parse", "HEAD").stdout.trim();
    mkdirSync(resolve(root, "frontend/src/features/zeta"), { recursive: true });
    writeFileSync(resolve(root, "frontend/src/features/zeta/Page.tsx"), "export default 1;");
    // the real tool, pointed at a frontend/ of its own: copy nothing, run it against the temporary tree
    const result = spawnSync(process.execPath, [resolve(frontend, "e2e/changed.mjs"), base, "--list"], {
      cwd: resolve(root, "frontend"),
      encoding: "utf8",
      env: { ...process.env, RDM_FRONTEND_ROOT: resolve(root, "frontend") },
    });
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /src\/features\/zeta\/Page\.tsx/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
