// Accessibility gate helper: runs axe-core on a Playwright page and reports violations.
import AxeBuilder from "@axe-core/playwright";

/**
 * @typedef {Object} AllowlistEntry
 * @property {string} rule - The axe rule id (e.g. "color-contrast").
 * @property {string[]} target - Exact axe node target.
 * @property {string[][]} [relatedTargets] - Exact related targets, when a rule compares nodes.
 * @property {number} maxNodes - Maximum permitted matching nodes.
 * @property {string[]} [pages] - Page names where the exception applies.
 * @property {string} issue - A tracking reference explaining why this is permitted.
 */

/**
 * Run axe-core on the current page state and return violations not covered by the allowlist.
 *
 * @param {import("playwright").Page} page
 * @param {AllowlistEntry[]} allowlist
 * @param {string} [pageName] - Named gate page for scoped exceptions.
 * @returns {Promise<{violations: object[], allowed: object[]}>}
 */
export async function runAxe(page, allowlist = [], pageName) {
  // A dialog fades in: read the colours once every animation and transition has finished.
  await page.evaluate(() =>
    Promise.all(
      document
        .getAnimations()
        .filter((animation) => animation.effect?.getComputedTiming().iterations !== Infinity)
        .map((animation) => animation.finished.catch(() => undefined)),
    ),
  );
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "best-practice"])
    .analyze();
  return partitionViolations(results.violations, allowlist, pageName);
}

// Match individual known nodes, with a bounded count and optional page scope.
export function partitionViolations(results, allowlist = [], pageName) {
  for (const entry of allowlist) {
    if (
      !entry.issue ||
      !Array.isArray(entry.target) ||
      entry.target.length === 0 ||
      !Number.isInteger(entry.maxNodes) ||
      entry.maxNodes < 1
    ) {
      throw new Error("Accessibility exceptions require an issue, exact target and positive maxNodes");
    }
  }
  const counts = new Map();
  const violations = [];
  const allowed = [];
  for (const violation of results) {
    const permitted = [];
    const unexpected = [];
    for (const node of violation.nodes) {
      const entry = allowlist.find(
        (item) =>
          item.rule === violation.id &&
          (!item.pages || item.pages.includes(pageName)) &&
          JSON.stringify(item.target) === JSON.stringify(node.target) &&
          JSON.stringify((item.relatedTargets ?? []).map((target) => JSON.stringify(target)).sort()) ===
            JSON.stringify(
              [...(node.any ?? []), ...(node.all ?? []), ...(node.none ?? [])]
                .flatMap((check) => check.relatedNodes ?? [])
                .map((related) => JSON.stringify(related.target))
                .sort(),
            ) &&
          (counts.get(item) ?? 0) < item.maxNodes,
      );
      if (entry) {
        counts.set(entry, (counts.get(entry) ?? 0) + 1);
        permitted.push(node);
      } else {
        unexpected.push(node);
      }
    }
    if (permitted.length) allowed.push({ ...violation, nodes: permitted });
    if (unexpected.length) violations.push({ ...violation, nodes: unexpected });
  }
  return { violations, allowed };
}

/**
 * Format violations into a human-readable report string.
 * @param {object[]} violations
 * @returns {string}
 */
export function formatViolations(violations) {
  if (violations.length === 0) return "No accessibility violations found.";
  const lines = [`${violations.length} accessibility violation(s):\n`];
  for (const v of violations) {
    lines.push(`  [${v.impact}] ${v.id}: ${v.description}`);
    lines.push(`    Help: ${v.helpUrl}`);
    for (const node of v.nodes.slice(0, 3)) {
      lines.push(`    Element: ${node.html.slice(0, 120)}`);
      lines.push(`    Target: ${JSON.stringify(node.target)}`);
      if (node.failureSummary) lines.push(`    ${node.failureSummary.split("\n")[0]}`);
    }
    if (v.nodes.length > 3) lines.push(`    ... and ${v.nodes.length - 3} more`);
    lines.push("");
  }
  return lines.join("\n");
}
