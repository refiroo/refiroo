// The browser runners and gate scenarios a diff touches, and a run of them in lanes (TS1).
//
//   npm --prefix frontend run test:changed -- <commit> [--list] [--lanes N] [--out DIR] [--keep] [--update-baselines [--changed-only]]
//
// Lists what changed since <commit> (the working tree included, new files too) selects in e2e/manifest.mjs,
// then runs it with `test:lanes` (TS3): the runners, and the accessibility and visual gates limited to the
// scenario groups the diff touches. `--list` prints the selection and runs nothing. The two runners that
// need Docker (HEAVY) are listed and not run; name them to run them.
import { spawn } from "node:child_process";
import { resolve } from "node:path";
import { SCENARIOS } from "./manifest.mjs";
import { changedSince, importGraph, select } from "./helpers/changed.mjs";
import { HEAVY } from "./helpers/lanes.mjs";

const frontend = resolve(import.meta.dirname, "..");
const argv = process.argv.slice(2);
let commit;
let list = false;
const passed = []; // options for test:lanes
for (let at = 0; at < argv.length; at++) {
  const arg = argv[at];
  if (arg === "--list") list = true;
  else if (arg === "--lanes" || arg === "--out") passed.push(arg, argv[++at]);
  else if (arg.startsWith("--")) passed.push(arg);
  else commit ??= arg;
}
if (!commit) {
  console.error("Name the commit to compare with: test:changed -- <commit> [--list] [--lanes N] [--out DIR] [--keep]");
  process.exit(2);
}

const changed = changedSince(commit, frontend);
const chosen = select(changed, { graph: importGraph(frontend) });
const runners = chosen.runners.filter((name) => !HEAVY.has(name));
const heavy = chosen.runners.filter((name) => HEAVY.has(name));
const everyGroup = chosen.groups.length === SCENARIOS.length;

console.log(`${changed.length} paths changed since ${commit}.`);
console.log(`Runners (${runners.length}): ${runners.join(" ") || "none"}`);
if (heavy.length) console.log(`Not run, they need Docker (name them to run): ${heavy.join(" ")}`);
console.log(
  `Accessibility and visual scenarios (${chosen.groups.length} of ${SCENARIOS.length} groups): ${chosen.groups.join("; ") || "none"}`,
);
if (chosen.unowned.length)
  console.log(
    `Changed paths of src/ that no manifest entry covers, so nothing runs for them (add the screen that shows them to e2e/manifest.mjs), ${chosen.unowned.length}: ${chosen.unowned.slice(0, 20).join(" ")}${chosen.unowned.length > 20 ? " ..." : ""}`,
  );
console.log(
  "Guide pictures are not run: retake the ones whose control, field order or label changed (EXECUTION_GUIDE).",
);

const gates = chosen.groups.length ? ["a11y", "visual"] : [];
const names = [...runners, ...gates];
if (list || !names.length) process.exit(0);

const args = [
  "e2e/lanes.mjs",
  ...names,
  ...(chosen.groups.length && !everyGroup ? ["--scenario", chosen.groups.join(",")] : []),
  ...passed,
];
const child = spawn(process.execPath, args, { cwd: frontend, stdio: "inherit" });
for (const signal of ["SIGINT", "SIGTERM", "SIGHUP"]) process.on(signal, () => child.kill(signal));
child.on("close", (code) => process.exit(code ?? 1));
