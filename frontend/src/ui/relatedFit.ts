/**
 * How many of a row's related-record chips a cell shows (0.9 K5b, D143 revised): as many whole chips
 * as fit beside the "+N more" the rest leave, always at least one. Pure, so the cell measures once
 * and recomputes on every resize from the measured widths.
 */

export interface FitInput {
  /** Each chip's natural width, in order. */
  widths: readonly number[];
  /** The space between two items of the cell. */
  gap: number;
  /** The cell's content width. */
  available: number;
  /** How many records the row has, the ones the list did not return included. */
  total: number;
  /** The width of "+N more" for `hidden` records. */
  moreWidth: (hidden: number) => number;
}

export function fittingChips({ widths, gap, available, total, moreWidth }: FitInput): number {
  if (!widths.length) return 0;
  const width = (count: number) =>
    widths.slice(0, count).reduce((sum, item) => sum + item, 0) + gap * Math.max(0, count - 1);
  for (let count = widths.length; count >= 1; count -= 1) {
    const hidden = total - count;
    const needed = width(count) + (hidden > 0 ? gap + moreWidth(hidden) : 0);
    if (needed <= available) return count;
  }
  return 1;
}
