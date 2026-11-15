// Browser runners, the accessibility gate and the visual gate in lanes (TS3).
//
//   npm --prefix frontend run test:lanes -- <runner>... | all [--lanes N] [--out DIR] [--update-baselines [--changed-only]] [--scenario GROUP,GROUP] [--keep]
//   npm --prefix frontend run test:lanes -- --list
//
// Each lane runs one runner at a time as a process of its own; the runner starts its own backend on a
// reserved port (helpers/ports.mjs) with a database cloned for it (named by TS2's run ID) and a folder of its
// own for export files. Lanes are sized to the memory available now, at most four, and `--lanes` or
// RDM_LANES overrides. One summary (per runner: lane, result, duration, log) is printed and written to the
// output folder with every runner's log, each kept to a bounded size. Each runner gets a temporary folder of
// its own (TMPDIR, so every evidence folder its helpers make is inside it): removed when the runner passes,
// kept and named in the summary when it fails or with --keep; an interrupted command removes them too. The exit code is 1 when any runner failed.
import { spawn } from "node:child_process";
import { createWriteStream, readFileSync } from "node:fs";
import { rmSync } from "node:fs";
import { mkdir, mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { catalogue, availableMemory, laneCount, runLanes, select, settleTemp, summaryText } from "./helpers/lanes.mjs";

const frontend = resolve(import.meta.dirname, "..");
const options = parse(process.argv.slice(2));
// Each runner is a process group of its own (its servers and browser belong to it), so stopping this command
// stops them all: nothing is left running by an interrupted command.
const running = new Set();
const roots = new Set(); // temporary roots of runners still running
const sharedPorts = resolve(tmpdir(), "rdm-test-ports");
function dropRoots() {
  if (options.keep) return;
  for (const root of roots) rmSync(root, { recursive: true, force: true });
}
function stopAll() {
  for (const child of running) {
    try {
      process.kill(-child.pid, "SIGTERM");
    } catch {
      /* already gone */
    }
  }
}
for (const signal of ["SIGINT", "SIGTERM", "SIGHUP"])
  process.on(signal, () => {
    stopAll();
    dropRoots();
    process.exit(130);
  });
const HEAD_BYTES = 3 * 1024 * 1024;
const TAIL_BYTES = 512 * 1024;

function parse(argv) {
  const options = { list: [], lanes: process.env.RDM_LANES, updateBaselines: false, show: false };
  for (let at = 0; at < argv.length; at++) {
    const arg = argv[at];
    if (arg === "--lanes") options.lanes = argv[++at];
    else if (arg === "--out") options.out = argv[++at];
    else if (arg === "--scenario") options.scenario = argv[++at];
    else if (arg === "--update-baselines") options.updateBaselines = true;
    else if (arg === "--changed-only") options.changedOnly = true;
    else if (arg === "--list") options.show = true;
    else if (arg === "--keep") options.keep = true;
    else if (arg.startsWith("--")) throw new Error(`Unknown option ${arg}.`);
    else options.list.push(arg);
  }
  return options;
}

/** Run one runner; its output goes to a log kept to a head and a tail, never to the terminal. */
async function execute(runner, lane, { out, updateBaselines, changedOnly }) {
  const log = resolve(out, `${runner.name.replace(/[^\w.-]/g, "_")}.log`);
  // The runner's helpers make their evidence folders in the system temporary folder (`mkdtemp(tmpdir()…)`),
  // so TMPDIR is the one place that holds them all: a folder of the runner's own, removed when it passes.
  const temp = resolve(out, "tmp", runner.name.replace(/[^\w.-]/g, "_"));
  await mkdir(temp, { recursive: true });
  roots.add(temp);
  return new Promise((done) => {
    const started = performance.now();
    const stream = createWriteStream(log);
    const args = [
      "e2e/" + runner.file,
      ...runner.args,
      ...(updateBaselines && runner.baselines
        ? ["--update-baselines", ...(changedOnly ? ["--changed-only"] : [])]
        : []),
    ];
    const child = spawn(process.execPath, args, {
      cwd: frontend,
      env: {
        ...process.env,
        TMPDIR: temp,
        RDM_PORTS_DIR: sharedPorts,
        RDM_LANE: String(lane),
        JOB_FILE_DIR: resolve(out, "job-files", runner.name),
      },
      stdio: ["ignore", "pipe", "pipe"],
      detached: true,
    });
    running.add(child);
    let written = 0;
    let omitted = 0;
    let tail = Buffer.alloc(0);
    const take = (chunk) => {
      if (written < HEAD_BYTES) {
        const room = HEAD_BYTES - written;
        stream.write(chunk.subarray(0, room));
        written += Math.min(room, chunk.length);
        chunk = chunk.subarray(room);
      }
      if (!chunk.length) return;
      tail = Buffer.concat([tail, chunk]);
      if (tail.length > TAIL_BYTES) {
        omitted += tail.length - TAIL_BYTES;
        tail = tail.subarray(tail.length - TAIL_BYTES);
      }
    };
    child.stdout.on("data", take);
    child.stderr.on("data", take);
    const finish = (code, note) => {
      running.delete(child);
      try {
        process.kill(-child.pid, "SIGTERM"); // whatever the runner left running
      } catch {
        /* nothing left */
      }
      if (omitted) stream.write(`\n[... ${omitted} bytes left out of the log ...]\n`);
      stream.end(tail, () => {
        const passed = code === 0;
        roots.delete(temp);
        const kept = settleTemp(temp, passed, options.keep);
        done({
          passed,
          durationMs: Math.round(performance.now() - started),
          log,
          ...(kept ? { temp: kept } : {}),
          ...(note ? { note } : {}),
        });
      });
    };
    child.on("error", (error) => finish(1, error.message));
    child.on("close", (code) => finish(code ?? 1));
  });
}

const runners = catalogue(JSON.parse(readFileSync(resolve(frontend, "package.json"), "utf8")));
if (options.show) {
  for (const runner of runners)
    console.log(
      `${runner.name}${runner.notInAll ? " (named only, not in all)" : ""}${runner.ports.length ? ` ports ${runner.ports}` : ""}`,
    );
  process.exit(0);
}
if (!options.list.length) {
  console.error(
    "Name the runners to run, or `all`: test:lanes -- <runner>... | all [--lanes N] [--out DIR] [--update-baselines [--changed-only]] [--scenario GROUP,GROUP] [--keep]",
  );
  process.exit(2);
}
// `--scenario` limits the full accessibility and visual gates to the named groups of e2e/manifest.mjs (TS1).
const chosen = select(options.list, runners).map((runner) =>
  options.scenario && (runner.name === "a11y" || runner.name === "visual")
    ? { ...runner, args: [...runner.args, "--scenario", options.scenario] }
    : runner,
);
if (options.updateBaselines && !chosen.some((runner) => runner.baselines)) {
  console.error("--update-baselines names no visual runner: add `visual` or `visual:security`.");
  process.exit(2);
}
const available = availableMemory();
const lanes = Math.min(laneCount(available, options.lanes), chosen.length);
const out = options.out ? resolve(options.out) : await mkdtemp(resolve(tmpdir(), "rdm-lanes-"));
await mkdir(out, { recursive: true });
console.log(
  `${chosen.length} runners in ${lanes} lanes (${(available / 1024 ** 3).toFixed(1)} GiB available); logs in ${out}`,
);

const started = performance.now();
const results = await runLanes(chosen, {
  lanes,
  updateBaselines: options.updateBaselines,
  execute: async (runner, lane) => {
    const result = await execute(runner, lane, {
      out,
      updateBaselines: options.updateBaselines,
      changedOnly: options.changedOnly,
    });
    console.log(
      `lane ${lane}: ${runner.name} ${result.passed ? "passed" : "FAILED"} (${(result.durationMs / 1000).toFixed(1)} s)`,
    );
    return result;
  },
});
const text = summaryText(results, { lanes, wallMs: performance.now() - started, availableGiB: available / 1024 ** 3 });
await writeFile(resolve(out, "summary.txt"), text + "\n");
await writeFile(resolve(out, "summary.json"), JSON.stringify(results, null, 2));
console.log("\n" + text + `\n\nSummary: ${resolve(out, "summary.txt")}`);
process.exit(results.some((result) => !result.passed) ? 1 : 0);
