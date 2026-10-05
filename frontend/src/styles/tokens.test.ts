/**
 * Contrast of the semantic roles in `tokens.css`, light and dark (Track U U2, U-D9).
 *
 * Text is held to WCAG AA (4.5:1, 3:1 for the 30px page title). A control's border, the focus
 * indicator and a marker that is the only sign of a state are held to 3:1 (WCAG 1.4.11). The
 * separator rules are decorative and listed as exempt, so the exemption is visible here.
 */
import { describe, expect, it } from "vitest";
import css from "./tokens.css?raw";

/** The declarations of the first block opened by `selector {`. */
function block(selector: string, from = 0): Map<string, string> {
  const start = css.indexOf(`${selector} {`, from);
  if (start < 0) throw new Error(`No block ${selector}`);
  let depth = 0;
  let end = start;
  for (let index = css.indexOf("{", start); index < css.length; index++) {
    if (css[index] === "{") depth++;
    if (css[index] === "}" && --depth === 0) {
      end = index;
      break;
    }
  }
  const body = css.slice(css.indexOf("{", start) + 1, end).replace(/\/\*[\s\S]*?\*\//g, "");
  const declarations = new Map<string, string>();
  for (const match of body.matchAll(/--([a-z0-9-]+):\s*([^;]+);/g)) declarations.set(match[1], match[2].trim());
  return declarations;
}

const light = block(":root");
const darkExplicit = block(':root[data-theme="dark"]');
const darkSystem = block(':root:not([data-theme="light"])', css.indexOf("@media (prefers-color-scheme: dark)"));
const themes = { light, dark: new Map([...light, ...darkExplicit]) };

function resolve(theme: Map<string, string>, name: string, seen: string[] = []): string {
  const value = theme.get(name);
  if (!value) throw new Error(`--${name} is not defined (via ${seen.join(" → ") || "the pair list"})`);
  const reference = value.match(/^var\(--([a-z0-9-]+)\)$/);
  if (reference) return resolve(theme, reference[1], [...seen, name]);
  if (!/^#[0-9a-f]{6}$/i.test(value)) throw new Error(`--${name} resolves to ${value}, not a #rrggbb colour`);
  return value.toLowerCase();
}

function luminance(hex: string) {
  const [r, g, b] = [1, 3, 5].map((offset) => {
    const channel = parseInt(hex.slice(offset, offset + 2), 16) / 255;
    return channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function ratio(a: string, b: string) {
  const [high, low] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (high + 0.05) / (low + 0.05);
}

const SURFACES = ["surface-app", "surface-top", "surface-nav", "surface-raised", "surface-sunken", "surface-hover"];
const CONTEXTS = ["live", "change-set", "publication"].map((tone) => `context-${tone}`);
const STATUSES = ["success", "warning", "error", "draft"].map((tone) => `status-${tone}`);

/** [foreground, background, minimum] */
const PAIRS: Array<[string, string, number]> = [
  ...["text-primary", "text-secondary", "text-tertiary"].flatMap((text) =>
    SURFACES.map((surface): [string, string, number] => [text, surface, 4.5]),
  ),
  ...["text-primary", "text-secondary"].map((text): [string, string, number] => [text, "state-selected", 4.5]),
  ["text-placeholder", "surface-raised", 4.5],
  ["link", "surface-app", 4.5],
  ["link", "surface-nav", 4.5],
  ["state-selected-text", "state-selected", 4.5],
  ["text-on-action", "action-primary", 4.5],
  ["text-on-action", "action-primary-hover", 4.5],
  ["text-on-action", "status-error-action", 4.5],
  ["status-error-action", "surface-raised", 4.5],
  ...[...CONTEXTS, ...STATUSES].map((tone): [string, string, number] => [`${tone}-text`, `${tone}-surface`, 4.5]),
  // Non-text: a control's boundary, the focus indicator, the primary action's fill, and markers.
  ...["surface-app", "surface-nav", "surface-raised", "surface-sunken"].map((surface): [string, string, number] => [
    "border-control",
    surface,
    3,
  ]),
  ...["surface-app", "surface-top", "surface-nav", "surface-raised"].map((surface): [string, string, number] => [
    "focus-color",
    surface,
    3,
  ]),
  ["action-primary", "surface-app", 3],
  ...[...CONTEXTS, ...STATUSES].flatMap((tone): Array<[string, string, number]> => [
    [`${tone}-marker`, `${tone}-surface`, 3],
    [`${tone}-marker`, "surface-app", 3],
    [`${tone}-marker`, "surface-nav", 3],
  ]),
];

/** Decorative rules: they separate regions and rows but never identify a control or a state. */
const EXEMPT = [
  "border-faint",
  "border-subtle",
  "border-strong",
  "state-selected-line",
  ...[...CONTEXTS, ...STATUSES].map((tone) => `${tone}-line`),
];

describe("design tokens", () => {
  it("defines the dark roles identically for the explicit choice and the system preference", () => {
    expect([...darkSystem.entries()]).toEqual([...darkExplicit.entries()]);
  });

  it("redefines only semantic roles in dark mode", () => {
    const primitives = [...darkExplicit.keys()].filter((name) =>
      /^(neutral|night|indigo|green|amber|violet|red)-/.test(name),
    );
    expect(primitives).toEqual([]);
  });

  for (const [name, theme] of Object.entries(themes)) {
    it(`meets the contrast minimums in the ${name} theme`, () => {
      const failures = PAIRS.flatMap(([foreground, background, minimum]) => {
        const [fg, bg] = [resolve(theme, foreground), resolve(theme, background)];
        const value = ratio(fg, bg);
        return value >= minimum
          ? []
          : [`--${foreground} ${fg} on --${background} ${bg}: ${value.toFixed(2)}:1, needs ${minimum}:1`];
      });
      expect(failures).toEqual([]);
    });

    it(`resolves every exempt rule to a colour in the ${name} theme`, () => {
      for (const rule of EXEMPT) expect(resolve(theme, rule)).toMatch(/^#/);
    });
  }
});
