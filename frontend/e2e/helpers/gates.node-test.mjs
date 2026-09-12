import assert from "node:assert/strict";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { test } from "node:test";
import { PNG } from "pngjs";
import { partitionViolations } from "./axe-helper.mjs";
import { compareScreenshot } from "./visual-regression.mjs";

const known = { rule: "region", target: [".navigation-resizer"], maxNodes: 1, issue: "WP1-001" };
const node = (target) => ({ target: [target], html: `<div class="${target.slice(1)}">` });

test("a known rule exception preserves additional unexpected nodes and bounds matches", () => {
  const result = partitionViolations(
    [
      { id: "region", nodes: [node(".navigation-resizer"), node(".new-content"), node(".navigation-resizer")] },
      { id: "color-contrast", nodes: [node(".navigation-resizer")] },
    ],
    [known],
  );
  assert.equal(result.allowed[0].nodes.length, 1);
  assert.deepEqual(
    result.violations[0].nodes.map((n) => n.target),
    [[".new-content"], [".navigation-resizer"]],
  );
  assert.equal(result.violations[1].id, "color-contrast");
});

test("exceptions apply only to their named page and require tracked bounded targets", () => {
  const violations = [{ id: "region", nodes: [node(".navigation-resizer")] }];
  const scoped = [{ ...known, pages: ["detail-system"] }];
  assert.equal(partitionViolations(violations, scoped, "detail-system").violations.length, 0);
  assert.equal(partitionViolations(violations, scoped, "collection-system").violations.length, 1);
  assert.throws(() => partitionViolations(violations, [{ rule: "region", issue: "WP1-001" }]), /exact target/);
});

test("visual comparison refuses missing baselines until explicitly updated and catches changes", async () => {
  const temporary = await mkdtemp(resolve(tmpdir(), "rdm-gate-helper-"));
  const baselineDir = resolve(temporary, "baselines");
  const outputDir = resolve(temporary, "evidence");
  const png = new PNG({ width: 20, height: 20 });
  png.data.fill(255);
  let buffer = PNG.sync.write(png);
  const page = { screenshot: async () => buffer };
  const options = { baselineDir, outputDir };
  const path = resolve(baselineDir, "test-page.png");
  try {
    let result = await compareScreenshot(page, "test-page", options);
    assert.equal(result.passed, false);
    assert.equal(result.baselineCreated, false);
    assert.equal(existsSync(path), false);
    assert.match(result.message, /Missing baseline/);
    assert.deepEqual(await readFile(resolve(outputDir, "test-page-actual.png")), buffer);
    process.argv.push("--update-baselines");
    try {
      result = await compareScreenshot(page, "test-page", options);
      assert.equal(result.passed, true);
      assert.equal(result.baselineCreated, true);
    } finally {
      process.argv.pop();
    }
    assert.equal((await compareScreenshot(page, "test-page", options)).passed, true);
    for (let i = 0; i < png.data.length; i += 4) png.data.fill(0, i, i + 3);
    buffer = PNG.sync.write(png);
    assert.equal((await compareScreenshot(page, "test-page", options)).passed, false);
    assert.equal(existsSync(resolve(outputDir, "test-page-diff.png")), true);
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
});

test("a duplicate landmark exception cannot hide a new related node", () => {
  const exception = { ...known, rule: "landmark-unique", relatedTargets: [[".known-duplicate"]] };
  const existing = { ...node(".navigation-resizer"), any: [{ relatedNodes: [node(".known-duplicate")] }] };
  assert.equal(partitionViolations([{ id: "landmark-unique", nodes: [existing] }], [exception]).violations.length, 0);
  const added = { ...existing, any: [{ relatedNodes: [node(".known-duplicate"), node(".new-duplicate")] }] };
  assert.equal(partitionViolations([{ id: "landmark-unique", nodes: [added] }], [exception]).violations.length, 1);
});
