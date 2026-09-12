// Visual regression helper: screenshot capture, pixel-diff comparison against named baselines.
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { PNG } from "pngjs";
import pixelmatch from "pixelmatch";

const helpers = dirname(fileURLToPath(import.meta.url));
const committedBaselineDir = resolve(helpers, "..", "baselines");

/**
 * Capture a viewport screenshot and compare against a named baseline.
 *
 * When `--update-baselines` is in process.argv, the screenshot is saved as the new baseline
 * and the comparison is skipped.
 *
 * @param {import("playwright").Page} page
 * @param {string} name - Unique baseline name (e.g. "collection-table-domain-light").
 * @param {object} options
 * @param {string} [options.outputDir] - Directory for diff/actual images (defaults to temp evidence dir).
 * @param {string} [options.baselineDir] - Baseline directory (defaults to committed baselines).
 * @param {number} [options.threshold=0.1] - pixelmatch color threshold (0-1). Default 0.1.
 * @param {number} [options.maxDiffPercent=0.5] - Maximum percentage of differing pixels before failure.
 * @returns {Promise<{passed: boolean, diffPercent: number, baselineCreated: boolean, message: string}>}
 */
export async function compareScreenshot(page, name, options = {}) {
  const { outputDir, threshold = 0.1, maxDiffPercent = 0.5, baselineDir = committedBaselineDir } = options;
  const updateMode = process.argv.includes("--update-baselines");
  const baselinePath = resolve(baselineDir, `${name}.png`);
  const actualBuffer = await page.screenshot({ fullPage: false });

  await mkdir(baselineDir, { recursive: true });

  if (updateMode) {
    await writeFile(baselinePath, actualBuffer);
    return {
      passed: true,
      diffPercent: 0,
      baselineCreated: true,
      message: `Baseline updated: ${name}`,
    };
  }

  if (!existsSync(baselinePath)) {
    if (outputDir) {
      await mkdir(outputDir, { recursive: true });
      await writeFile(resolve(outputDir, `${name}-actual.png`), actualBuffer);
    }
    return {
      passed: false,
      diffPercent: 100,
      baselineCreated: false,
      message: `Missing baseline: ${name}. Run test:visual:update and review the new baseline before committing.`,
    };
  }

  const baselineBuffer = await readFile(baselinePath);
  const baseline = PNG.sync.read(baselineBuffer);
  const actual = PNG.sync.read(actualBuffer);

  if (baseline.width !== actual.width || baseline.height !== actual.height) {
    if (outputDir) {
      await mkdir(outputDir, { recursive: true });
      await writeFile(resolve(outputDir, `${name}-actual.png`), actualBuffer);
    }
    return {
      passed: false,
      diffPercent: 100,
      baselineCreated: false,
      message: `Size mismatch for ${name}: baseline ${baseline.width}x${baseline.height} vs actual ${actual.width}x${actual.height}. Run with --update-baselines to accept.`,
    };
  }

  const diffPng = new PNG({ width: baseline.width, height: baseline.height });
  const diffPixels = pixelmatch(baseline.data, actual.data, diffPng.data, baseline.width, baseline.height, {
    threshold,
  });
  const totalPixels = baseline.width * baseline.height;
  const diffPercent = (diffPixels / totalPixels) * 100;
  const passed = diffPercent <= maxDiffPercent;

  if (outputDir) {
    await mkdir(outputDir, { recursive: true });
    await writeFile(resolve(outputDir, `${name}-actual.png`), actualBuffer);
    if (!passed) {
      await writeFile(resolve(outputDir, `${name}-diff.png`), PNG.sync.write(diffPng));
    }
  }

  return {
    passed,
    diffPercent: Math.round(diffPercent * 100) / 100,
    baselineCreated: false,
    message: passed
      ? `Visual match: ${name} (${diffPercent.toFixed(2)}% diff, threshold ${maxDiffPercent}%)`
      : `Visual regression: ${name} — ${diffPercent.toFixed(2)}% diff exceeds ${maxDiffPercent}% threshold. Run with --update-baselines to accept intentional changes.`,
  };
}
