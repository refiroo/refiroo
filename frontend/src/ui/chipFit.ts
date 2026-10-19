/**
 * How many related-record chips a table cell shows, computed rather than measured (0.11 X6).
 *
 * A chip is its padding, its marker and the gap after it, plus its name's text. Those lengths are
 * read once per page from one sample chip drawn unseen, and each name's width is the text's width in
 * the chip's font, from a canvas, kept per text. A cell then knows what fits from its column's width
 * alone: it draws once, reads nothing back from the page and keeps no observer. Measuring each cell
 * (drawing every chip, reading their widths, drawing again) made a table with relation columns
 * stutter while scrolling (the user, 2026-10-19).
 *
 * The lengths are read again when the page's fonts finish loading, since the first reading may
 * have used a fallback font; `subscribe` tells the cells.
 */

import { fittingChips } from "@/ui/relatedFit";

interface Metrics {
  /** A chip's width less its name: padding, marker and the gap between them. */
  chipExtra: number;
  chipFont: string;
  /** The space between two items of the cell. */
  gap: number;
  moreFont: string;
  /** The room the hidden edit icons keep beside a value (`ui/EditInPlace`): one icon, and the gap. */
  editIcon: number;
  editGap: number;
}

let metrics: Metrics | undefined;
let context: CanvasRenderingContext2D | null | undefined;
const widths = new Map<string, number>();
const listeners = new Set<() => void>();
let version = 0;
let watchingFonts = false;

/** Whether the page can compute widths: a laid-out document with a canvas (not jsdom). */
function canCompute(): boolean {
  if (typeof document === "undefined") return false;
  if (context === undefined) {
    try {
      context = document.createElement("canvas").getContext("2d");
    } catch {
      context = null;
    }
  }
  return context !== null;
}

function read(): Metrics | undefined {
  if (!canCompute()) return undefined;
  const sample = document.createElement("span");
  sample.className = "related-records";
  sample.setAttribute("aria-hidden", "true");
  sample.style.cssText = "position:absolute;visibility:hidden;left:-9999px;top:0;width:auto";
  sample.innerHTML =
    '<span class="related-records-chip"><span class="record-chip"><span class="record-chip-marker"></span>' +
    '<span class="record-chip-name">M</span></span></span><span class="related-records-more">+1 more</span>' +
    '<span class="cell-edit"><span class="cell-edit-value"></span><span class="cell-edit-actions">' +
    '<button class="icon-button icon-button-quiet" tabindex="-1"></button></span></span>';
  document.body.appendChild(sample);
  try {
    const chip = sample.querySelector<HTMLElement>(".record-chip")!;
    const name = sample.querySelector<HTMLElement>(".record-chip-name")!;
    const more = sample.querySelector<HTMLElement>(".related-records-more")!;
    const edit = sample.querySelector<HTMLElement>(".cell-edit")!;
    const icon = sample.querySelector<HTMLElement>(".cell-edit-actions .icon-button")!;
    const nameStyle = getComputedStyle(name);
    const fontOf = (style: CSSStyleDeclaration) =>
      style.font || `${style.fontStyle} ${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
    const chipFont = fontOf(nameStyle);
    const textNow = textWidth("M", chipFont);
    const result: Metrics = {
      // The chip's own box less the name's text: whatever its CSS holds, read as drawn.
      chipExtra: chip.getBoundingClientRect().width - textNow,
      chipFont,
      gap: Number.parseFloat(getComputedStyle(sample).columnGap) || 0,
      moreFont: fontOf(getComputedStyle(more)),
      editIcon: icon.getBoundingClientRect().width,
      editGap: Number.parseFloat(getComputedStyle(edit).columnGap) || 0,
    };
    // Not laid out (a hidden page): nothing to compute from yet.
    if (!(result.chipExtra > 0) || !(result.editIcon > 0)) return undefined;
    return result;
  } finally {
    sample.remove();
  }
}

function textWidth(text: string, font: string): number {
  const key = `${font}\n${text}`;
  const known = widths.get(key);
  if (known !== undefined) return known;
  context!.font = font;
  const width = context!.measureText(text).width;
  widths.set(key, width);
  return width;
}

function current(): Metrics | undefined {
  if (!metrics) metrics = read();
  if (metrics && !watchingFonts && typeof document !== "undefined" && document.fonts) {
    watchingFonts = true;
    document.fonts.addEventListener?.("loadingdone", () => {
      widths.clear();
      metrics = read();
      version++;
      listeners.forEach((listener) => listener());
    });
  }
  return metrics;
}

/** Notifies when the lengths were read again (the page's fonts loaded). */
export function subscribeChipMetrics(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Changes whenever the lengths are read again. */
export const chipMetricsVersion = () => version;

/** The room the hidden edit icons keep beside a value: `icons` icons and the gap before them. */
export function editIconsRoom(icons: number): number | undefined {
  const known = current();
  return known ? icons * known.editIcon + known.editGap : undefined;
}

/**
 * How many of `texts` fit in `available` pixels beside "+N more" for the rest of `total`, at least
 * one; `undefined` where the page cannot compute widths (the cell then measures, as it did).
 */
export function chipsThatFit(texts: readonly string[], total: number, available: number): number | undefined {
  const known = current();
  if (!known) return undefined;
  return fittingChips({
    // Whole pixels, as the cell measured its chips before (`offsetWidth`): the computed widths
    // match the drawn ones to a hundredth of a pixel, and a cell shows the chips it showed before.
    widths: texts.map((text) => Math.round(textWidth(text, known.chipFont) + known.chipExtra)),
    gap: known.gap,
    available,
    total,
    moreWidth: (hidden) => Math.round(textWidth(`+${hidden} more`, known.moreFont)),
  });
}
