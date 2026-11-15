import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { mkdirSync, mkdtempSync, rmSync, utimesSync, writeFileSync } from "node:fs";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { test } from "node:test";
import { catalogue, laneCount, resourcesOf, runLanes, select, settleTemp } from "./lanes.mjs";
import { isFree, reserve, reservePort, unreserve } from "./ports.mjs";

const e2e = resolve(import.meta.dirname, "..");
const packageJson = JSON.parse(readFileSync(resolve(e2e, "..", "package.json"), "utf8"));
const GIB = 1024 ** 3;

test("lanes follow free memory: one per 2 GiB, at most four, at least one, an override wins", () => {
  assert.equal(laneCount(0.5 * GIB), 1);
  assert.equal(laneCount(5 * GIB), 2);
  assert.equal(laneCount(7.9 * GIB), 3);
  assert.equal(laneCount(40 * GIB), 4);
  assert.equal(laneCount(1 * GIB, "3"), 3);
  assert.throws(() => laneCount(8 * GIB, "0"), /whole number/);
});

test("the catalogue names every runner script once, with its file present, and `all` leaves out the named-only ones", () => {
  const runners = catalogue(packageJson);
  assert.equal(new Set(runners.map((runner) => runner.name)).size, runners.length);
  for (const runner of runners) assert.ok(existsSync(resolve(e2e, runner.file)), runner.file);
  const all = select(["all"], runners).map((runner) => runner.name);
  assert.ok(all.includes("a11y") && all.includes("visual") && all.includes("wp9-navigation"));
  for (const left of ["i3-real-provider", "dp3-deployment", "a11y:guide", "visual:security"])
    assert.ok(!all.includes(left));
  assert.deepEqual(
    select(["lb", "wp9-navigation", "lb"], runners)
      .map((runner) => runner.name)
      .sort(),
    ["lb-list-browsing", "wp9-navigation"],
  );
  assert.throws(() => select(["nope"], runners), /Unknown runner: nope/);
});

const fake = (name, extra = {}) => ({ name, ports: [], weight: 1, ...extra });
const trace = () => {
  const running = new Set();
  const overlaps = [];
  let most = 0;
  return {
    overlaps,
    most: () => most,
    execute: (groups) => async (runner) => {
      for (const other of running) if (groups(runner, other)) overlaps.push([runner.name, other]);
      running.add(runner.name);
      most = Math.max(most, running.size);
      await new Promise((done) => setTimeout(done, 20));
      running.delete(runner.name);
      return { passed: true, durationMs: 20 };
    },
  };
};

test("lanes run runners side by side, and runners sharing a fixed port never overlap", async () => {
  const runners = ["a", "b", "c", "d", "e", "f"].map((name) => fake(name, name < "d" ? { ports: [8999] } : {}));
  const seen = trace();
  const results = await runLanes(runners, {
    lanes: 3,
    portFree: async () => true,
    execute: seen.execute((one, other) => one.ports.length && runners.find((r) => r.name === other).ports.length),
  });
  assert.equal(results.length, 6);
  assert.deepEqual(seen.overlaps, []);
  assert.ok(seen.most() > 1 && seen.most() <= 3);
  assert.ok(results.every((result) => result.lane >= 1 && result.lane <= 3));
});

test("a fixed port that something else holds refuses the runner with a message and starts nothing", async () => {
  const holder = createServer();
  await new Promise((done) => holder.listen(0, "127.0.0.1", done));
  const port = holder.address().port;
  let started = 0;
  const [result] = await runLanes([fake("needs-port", { ports: [port] })], {
    lanes: 1,
    execute: async () => ((started += 1), { passed: true, durationMs: 1 }),
  });
  await new Promise((done) => holder.close(done));
  assert.equal(started, 0);
  assert.equal(result.passed, false);
  assert.match(result.note, new RegExp(`port ${port} is in use`));
  assert.equal(await isFree(port), true);
});

test("baselines are written by one visual runner at a time, and only in update mode", () => {
  const runners = catalogue(packageJson);
  const visual = runners.find((runner) => runner.name === "visual");
  const security = runners.find((runner) => runner.name === "visual:security");
  assert.deepEqual(resourcesOf(visual, { updateBaselines: true }), ["baselines"]);
  assert.deepEqual(resourcesOf(security, { updateBaselines: true }), ["baselines"]);
  assert.deepEqual(resourcesOf(visual, {}), []);
  assert.deepEqual(
    resourcesOf(
      runners.find((runner) => runner.name === "a11y"),
      { updateBaselines: true },
    ),
    [],
  );
});

test("update mode serialises the runners that write baselines", async () => {
  const runners = [fake("v1", { baselines: true }), fake("v2", { baselines: true }), fake("other")];
  const seen = trace();
  await runLanes(runners, {
    lanes: 3,
    updateBaselines: true,
    execute: seen.execute((one, other) => one.baselines && runners.find((r) => r.name === other).baselines),
  });
  assert.deepEqual(seen.overlaps, []);
});

test("a reservation is exclusive, ends with its owner, and is taken over when the owner is gone", () => {
  const directory = mkdtempSync(resolve(tmpdir(), "rdm-ports-test-"));
  try {
    assert.equal(reserve(41001, directory), true);
    assert.equal(reserve(41001, directory), false);
    unreserve(41001, directory);
    assert.equal(reserve(41001, directory), true);
    writeFileSync(resolve(directory, "41002"), "999999999");
    assert.equal(reserve(41002, directory), true);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test("a reservation file that is still empty is held, and one that stays empty is taken over", () => {
  const directory = mkdtempSync(resolve(tmpdir(), "rdm-ports-test-"));
  try {
    // its owner is between creating the file and writing its process number: the port is not taken
    writeFileSync(resolve(directory, "41003"), "");
    assert.equal(reserve(41003, directory), false);
    assert.equal(readFileSync(resolve(directory, "41003"), "utf8"), "");
    // an empty file nobody fills is stale once it is old enough
    writeFileSync(resolve(directory, "41004"), "");
    const old = new Date(Date.now() - 60_000);
    utimesSync(resolve(directory, "41004"), old, old);
    assert.equal(reserve(41004, directory), true);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test("many runners starting together are never handed the same port", async () => {
  const ports = await Promise.all(Array.from({ length: 24 }, () => reservePort()));
  try {
    assert.equal(new Set(ports).size, ports.length);
    assert.ok(!ports.includes(8000));
  } finally {
    for (const port of ports) unreserve(port);
  }
});

test("a runner's temporary root is removed when it passes and kept when it fails or with --keep", () => {
  const base = mkdtempSync(resolve(tmpdir(), "rdm-settle-test-"));
  try {
    const make = (name) => {
      const root = resolve(base, name);
      mkdirSync(resolve(root, "rdm-ui07-gate-x"), { recursive: true });
      return root;
    };
    const passed = make("passed");
    assert.equal(settleTemp(passed, true, false), undefined);
    assert.equal(existsSync(passed), false);
    const failed = make("failed");
    assert.equal(settleTemp(failed, false, false), failed);
    assert.equal(existsSync(failed), true);
    const kept = make("kept");
    assert.equal(settleTemp(kept, true, true), kept);
    assert.equal(existsSync(kept), true);
  } finally {
    rmSync(base, { recursive: true, force: true });
  }
});
