// Which browser runners and scenarios a diff touches (TS1). A changed file selects the entries of
// `e2e/manifest.mjs` naming its path; a change in a shared layer (ui, state, lib, model, ...) selects the
// entries naming any file that imports it, read from the imports of `src/`, so no list of importers is kept.
// A changed file under `e2e/` selects the runners and gates that import it, read the same way.
import { execFileSync } from "node:child_process";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, resolve, sep } from "node:path";
import { EVERY_PICTURE, FRAME_FILES, RUNNERS, SCENARIOS, SHARED_LAYERS } from "../manifest.mjs";
import { catalogue } from "./lanes.mjs";
import { groupOf } from "./scenarios.mjs";

const CODE = /\.(tsx?|mjs)$/;
const IMPORT = /(?:from\s*|import\s*\(\s*|import\s+)["']([^"']+)["']/g;

/** Every code file under `dir` (a path relative to `root`), skipping tests and node_modules. */
function walk(root, dir, out = []) {
  const absolute = resolve(root, dir);
  if (!existsSync(absolute)) return out;
  for (const entry of readdirSync(absolute)) {
    const path = join(dir, entry);
    if (entry === "node_modules" || entry === "baselines" || entry === "__pycache__") continue;
    if (statSync(resolve(root, path)).isDirectory()) walk(root, path, out);
    else if (CODE.test(entry) && !/\.(test|node-test)\.|\.d\.ts$/.test(entry)) out.push(path.split(sep).join("/"));
  }
  return out;
}

/** The file `spec` (written in `from`) names, as a path relative to `root`, or undefined. */
function resolveImport(root, from, spec) {
  let base;
  if (spec.startsWith("@/")) base = `src/${spec.slice(2)}`;
  else if (spec.startsWith(".")) base = join(dirname(from), spec);
  else return undefined;
  base = base.split(sep).join("/");
  for (const candidate of [base, `${base}.ts`, `${base}.tsx`, `${base}.mjs`, `${base}/index.ts`, `${base}/index.tsx`])
    if (existsSync(resolve(root, candidate)) && statSync(resolve(root, candidate)).isFile()) return candidate;
  return undefined;
}

/** The import graph of `src/` and `e2e/`: file -> the files it imports (a map of sets). */
export function importGraph(root) {
  const graph = new Map();
  for (const file of [...walk(root, "src"), ...walk(root, "e2e")]) {
    const targets = new Set();
    for (const [, spec] of readFileSync(resolve(root, file), "utf8").matchAll(IMPORT)) {
      const target = resolveImport(root, file, spec);
      if (target) targets.add(target);
    }
    graph.set(file, targets);
  }
  return graph;
}

const under = (path, base) => path === base || path.startsWith(`${base}/`);
/** The feature folder a file lies in (`src/features/<name>`), or undefined. */
const featureOf = (path) => /^src\/features\/[^/]+/.exec(path)?.[0];
const isShared = (path, shared) => shared.some((layer) => under(path, layer));

/**
 * Every file whose behaviour includes `changed`'s: the file itself, the files importing it when it lies in a
 * shared layer, and, when it lies in a feature folder, the importers outside that folder (another feature
 * showing it, e.g. a dialog of one feature opened from another). Any other file outside the layers is
 * reached but not followed. Files under `e2e/` follow every importer.
 */
export function reached(changed, graph, shared = SHARED_LAYERS) {
  const importers = new Map();
  for (const [file, targets] of graph)
    for (const target of targets) (importers.get(target) ?? importers.set(target, []).get(target)).push(file);
  const seen = new Set([changed]);
  const queue = [changed];
  while (queue.length) {
    const file = queue.pop();
    const own = featureOf(file);
    if (file.startsWith("src/") && !isShared(file, shared) && !own) continue;
    for (const importer of importers.get(file) ?? []) {
      if (seen.has(importer)) continue;
      // a feature's file is followed out only into other features, never into the shell that mounts it
      if (own && !isShared(file, shared) && (!featureOf(importer) || featureOf(importer) === own)) continue;
      seen.add(importer);
      queue.push(importer);
    }
  }
  return seen;
}

/** Does any of `files` lie on one of `paths` (a file or a folder)? */
const touches = (files, paths) => paths.some((path) => [...files].some((file) => under(file, path)));

/**
 * What the changed paths select: `runners` (names), `groups` (scenario groups, for both gates) and
 * `unowned` (changed files of `src/` that no entry covers, so nothing would run for them).
 * @param {string[]} changedFiles paths relative to `frontend/`
 */
export function select(
  changedFiles,
  {
    graph,
    runners = RUNNERS,
    scenarios = SCENARIOS,
    everyPicture = EVERY_PICTURE,
    frame = FRAME_FILES,
    shared = SHARED_LAYERS,
    gates = ["a11y", "visual"],
  },
) {
  const names = new Set();
  const groups = new Set();
  const unowned = [];
  const gateFiles = { a11y: "e2e/accessibility-gate.mjs", visual: "e2e/visual-regression-gate.mjs" };
  for (const file of changedFiles) {
    if (/\.(test|node-test)\.|\.d\.ts$/.test(file) || file.startsWith("src/test/")) continue;
    const files = reached(file, graph, shared);
    const hit = { runners: [], groups: [] };
    for (const [name, paths] of Object.entries(runners))
      if (touches(files, [...paths, `e2e/${name}.mjs`])) hit.runners.push(name);
    for (const entry of scenarios) if (touches(files, entry.paths)) hit.groups.push(entry.group);
    // a change to how everything looks (the styles, the shell's frame files), or to a gate or a helper the gates import, selects every scenario
    if (
      touches(files, everyPicture) ||
      frame.includes(file) ||
      Object.values(gateFiles).some((gate) => files.has(gate))
    )
      hit.groups.push(...scenarios.map((entry) => entry.group));
    // a baseline picture changed by hand selects its own scenario
    const picture = /^e2e\/baselines\/(.+)\.png$/.exec(file);
    if (picture) {
      const group = groupOf(picture[1], scenarios);
      if (group) hit.groups.push(group.group);
    }
    hit.runners.forEach((name) => names.add(name));
    hit.groups.forEach((group) => groups.add(group));
    if (file.startsWith("src/") && !hit.runners.length && !hit.groups.length) unowned.push(file);
  }
  return { runners: [...names].sort(), groups: [...groups], unowned };
}

/** The paths that differ from `commit` in the working tree and still exist, relative to `frontend/`, new ones included. */
export function changedSince(commit, cwd) {
  const run = (...args) =>
    execFileSync("git", args, { cwd, encoding: "utf8", maxBuffer: 64 * 1024 * 1024 })
      .split("\n")
      .filter(Boolean);
  const files = new Set([
    ...run("diff", "--name-only", "--relative", commit, "--", "."),
    ...run("ls-files", "--others", "--exclude-standard"),
  ]);
  // a deleted file selects nothing: whatever imported it changed too
  return [...files].filter((file) => existsSync(resolve(cwd, file)));
}

/** The paths under `backend/` that differ from `commit` in the working tree and still exist, relative to the repository root. */
export function backendChangedSince(commit, cwd) {
  const run = (...args) =>
    execFileSync("git", args, { cwd, encoding: "utf8", maxBuffer: 64 * 1024 * 1024 })
      .split("\n")
      .filter(Boolean);
  const root = run("rev-parse", "--show-toplevel")[0];
  const files = new Set([
    ...run("diff", "--name-only", commit, "--", ":/backend"),
    ...run("ls-files", "--others", "--exclude-standard", "--full-name", ":/backend"),
  ]);
  return [...files].filter((file) => existsSync(resolve(root, file)));
}

/** The seeds the runners share: a change to them can change every screen's data, so every runner is selected. */
export const BROWSER_SEEDS = "backend/tests/browser_seeds.py";

/** What changed backend paths mean for the browser runners: every runner (the shared seeds), or a note only. */
export function backendEffect(paths) {
  return { everyRunner: paths.includes(BROWSER_SEEDS), others: paths.filter((path) => path !== BROWSER_SEEDS) };
}

/** The runners of the catalogue the manifest has no entry for, and the entries naming no runner. */
export function entryDifferences(packageJson, runners = RUNNERS) {
  const inCatalogue = catalogue(packageJson)
    .filter((runner) => !runner.baselines && !/^a11y/.test(runner.name))
    .map((runner) => runner.name);
  return {
    missing: inCatalogue.filter((name) => !(name in runners)),
    stale: Object.keys(runners).filter((name) => !inCatalogue.includes(name)),
  };
}
