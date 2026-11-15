// Browser runners and gates in lanes (TS3): the catalogue of what can run, how many lanes the free memory
// carries, and the scheduler that gives each lane its next runner while no two running runners share a
// resource (a fixed port, the baseline files). The command is `lanes.mjs`.
import { execFileSync } from "node:child_process";
import { readFileSync, rmSync } from "node:fs";
import { freemem } from "node:os";
import { isFree } from "./ports.mjs";

export const MAX_LANES = 4;
/** Memory one lane needs: the backend, the Vite server and Chromium, with room for a runner's own work. */
export const LANE_GIB = 2;
const GIB = 1024 ** 3;

/** The gates: one runner each, with the `--only` parts that run on their own. */
export const GATES = [
  { name: "a11y", file: "accessibility-gate.mjs", args: [], weight: 10 },
  { name: "a11y:security", file: "accessibility-gate.mjs", args: ["--only", "security"], weight: 2, notInAll: true },
  { name: "a11y:guide", file: "accessibility-gate.mjs", args: ["--only", "guide"], weight: 1, notInAll: true },
  { name: "visual", file: "visual-regression-gate.mjs", args: [], weight: 10, baselines: true },
  {
    name: "visual:security",
    file: "visual-regression-gate.mjs",
    args: ["--only", "security"],
    weight: 2,
    baselines: true,
    notInAll: true,
  },
];

/** Not in "all": Docker builds and a pulled provider image; named to run (EXECUTION_GUIDE). */
export const HEAVY = new Set(["i3-real-provider", "dp3-deployment"]);

/**
 * Fixed ports a runner's stand-ins need, by runner name. None does today (the OIDC provider, the SMTP and
 * webhook receivers and the browsers' servers all take a reserved free port); a runner that needs one is
 * listed here, runs alone on it, and is refused when something else holds it.
 * @type {Record<string, number[]>}
 */
export const FIXED_PORTS = {};

/** The runners: every `node e2e/<file>` script of package.json, named by the file, then the gates. */
export function catalogue(packageJson, fixedPorts = FIXED_PORTS) {
  const runners = [];
  for (const [script, command] of Object.entries(packageJson.scripts)) {
    const match = /^node e2e\/([\w.-]+\.mjs)$/.exec(command);
    if (!match || !script.startsWith("test:") || /(-gate|^lanes|^changed)\.mjs$/.test(match[1])) continue;
    const name = match[1].replace(/\.mjs$/, "");
    runners.push({ name, script, file: match[1], args: [], weight: 1, notInAll: HEAVY.has(name) });
  }
  return [...runners, ...GATES].map((runner) => ({ ...runner, ports: fixedPorts[runner.name] ?? [] }));
}

/** The runners a list names ("all", a runner's name or its npm script's suffix), each once, longest first. */
export function select(list, runners) {
  const chosen = new Map();
  const unknown = [];
  for (const entry of list) {
    if (entry === "all") {
      for (const runner of runners) if (!runner.notInAll) chosen.set(runner.name, runner);
      continue;
    }
    const found = runners.find(
      (runner) => runner.name === entry || runner.script === `test:browser:${entry}` || runner.script === entry,
    );
    if (found) chosen.set(found.name, found);
    else unknown.push(entry);
  }
  if (unknown.length) throw new Error(`Unknown runner: ${unknown.join(", ")} (--list shows the names).`);
  return [...chosen.values()].sort((a, b) => b.weight - a.weight);
}

/** Memory a new lane could use, in bytes: free and reclaimable, not the operating system's "free" alone. */
export function availableMemory() {
  try {
    if (process.platform === "darwin") {
      const text = execFileSync("vm_stat", { encoding: "utf8" });
      const size = Number(/page size of (\d+) bytes/.exec(text)?.[1] ?? 16384);
      const pages = (label) => Number(new RegExp(`${label}:\\s+(\\d+)`).exec(text)?.[1] ?? 0);
      return (
        (pages("Pages free") + pages("Pages inactive") + pages("Pages speculative") + pages("Pages purgeable")) * size
      );
    }
    if (process.platform === "linux") {
      const kib = /MemAvailable:\s+(\d+) kB/.exec(readFileSync("/proc/meminfo", "utf8"))?.[1];
      if (kib) return Number(kib) * 1024;
    }
  } catch {
    /* fall back */
  }
  return freemem();
}

/** Lanes from free memory: one per LANE_GIB, at most MAX_LANES, at least one; `override` wins when given. */
export function laneCount(availableBytes, override) {
  if (override !== undefined && override !== null && override !== "") {
    const wanted = Number(override);
    if (!Number.isInteger(wanted) || wanted < 1)
      throw new Error(`Lanes must be a whole number of 1 or more, not ${override}.`);
    return wanted;
  }
  return Math.min(MAX_LANES, Math.max(1, Math.floor(availableBytes / GIB / LANE_GIB)));
}

/** The resources a runner holds while it runs: its fixed ports, and the baseline files when they are written. */
export function resourcesOf(runner, { updateBaselines = false } = {}) {
  return [...runner.ports.map((port) => `port:${port}`), ...(updateBaselines && runner.baselines ? ["baselines"] : [])];
}

/**
 * Run `runners` in `lanes` lanes. A lane takes the first waiting runner whose resources nobody holds, and
 * waits for a release (an awaited promise, no polling) when every waiting runner needs one that is held.
 * `execute(runner, lane)` returns `{ passed, ... }`; a runner a fixed port refuses is reported without it.
 * @returns {Promise<object[]>} one result per runner, in the order they ended
 */
export async function runLanes(runners, { lanes, execute, updateBaselines = false, portFree = isFree }) {
  const waiting = [...runners];
  const held = new Set();
  const results = [];
  let wake = () => {};
  let changed = new Promise((done) => (wake = done));
  const notify = () => {
    wake();
    changed = new Promise((done) => (wake = done));
  };

  async function lane(index) {
    for (;;) {
      if (!waiting.length) return;
      const at = waiting.findIndex((runner) =>
        resourcesOf(runner, { updateBaselines }).every((item) => !held.has(item)),
      );
      if (at < 0) {
        await changed;
        continue;
      }
      const [runner] = waiting.splice(at, 1);
      const resources = resourcesOf(runner, { updateBaselines });
      resources.forEach((item) => held.add(item));
      try {
        const busy = [];
        for (const port of runner.ports) if (!(await portFree(port))) busy.push(port);
        results.push(
          busy.length
            ? {
                runner: runner.name,
                lane: index,
                passed: false,
                refused: true,
                durationMs: 0,
                note: `not started: port ${busy.join(", ")} is in use by another process; stop it or run the runner when it is free`,
              }
            : { runner: runner.name, lane: index, ...(await execute(runner, index)) },
        );
      } catch (error) {
        results.push({
          runner: runner.name,
          lane: index,
          passed: false,
          durationMs: 0,
          note: String(error?.message ?? error),
        });
      } finally {
        resources.forEach((item) => held.delete(item));
        notify();
      }
    }
  }

  await Promise.all(Array.from({ length: Math.min(lanes, runners.length) }, (_, index) => lane(index + 1)));
  return results;
}

/**
 * A runner's temporary root once it has ended: removed when it passed, kept (its path returned, for the
 * summary) when it failed or when `keep` is set.
 */
export function settleTemp(root, passed, keep) {
  if (passed && !keep) {
    rmSync(root, { recursive: true, force: true });
    return undefined;
  }
  return root;
}

/** The summary as text: one line per runner (lane, result, duration, log), then the totals. */
export function summaryText(results, { lanes, wallMs, availableGiB }) {
  const rows = [...results].sort((a, b) => a.runner.localeCompare(b.runner));
  const seconds = (ms) => `${(ms / 1000).toFixed(1)} s`;
  const lines = [
    `Runners in lanes: ${results.length} runners, ${lanes} lanes (${availableGiB.toFixed(1)} GiB available), ${seconds(wallMs)} in all`,
    "",
    "runner | lane | result | duration | log",
  ];
  for (const row of rows)
    lines.push(
      `${row.runner} | ${row.lane} | ${row.passed ? "pass" : row.refused ? "refused" : "FAIL"} | ${seconds(row.durationMs)} | ${row.log ?? row.note ?? ""}${row.temp ? ` (evidence kept in ${row.temp})` : ""}`,
    );
  const failed = rows.filter((row) => !row.passed);
  lines.push(
    "",
    `${results.length - failed.length} passed, ${failed.length} failed${failed.length ? `: ${failed.map((row) => row.runner).join(", ")}` : ""}`,
  );
  return lines.join("\n");
}
