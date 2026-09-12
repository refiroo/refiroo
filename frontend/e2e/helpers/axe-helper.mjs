// Accessibility gate helper: runs axe-core on a Playwright page and reports violations.
import AxeBuilder from "@axe-core/playwright";

/**
 * @typedef {Object} AllowlistEntry
 * @property {string} rule - The axe rule id (e.g. "color-contrast").
 * @property {string} issue - A tracking reference explaining why this is permitted.
 */

/**
 * Run axe-core on the current page state and return violations not covered by the allowlist.
 *
 * @param {import("playwright").Page} page
 * @param {AllowlistEntry[]} allowlist
 * @returns {Promise<{violations: object[], allowed: object[]}>}
 */
export async function runAxe(page, allowlist = []) {
  const allowedRules = new Set(allowlist.map((entry) => entry.rule));
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "best-practice"])
    .analyze();
  const violations = [];
  const allowed = [];
  for (const violation of results.violations) {
    if (allowedRules.has(violation.id)) {
      allowed.push(violation);
    } else {
      violations.push(violation);
    }
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
