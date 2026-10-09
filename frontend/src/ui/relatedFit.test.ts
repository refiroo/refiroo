import { describe, expect, it } from "vitest";
import { fittingChips } from "@/ui/relatedFit";

const more = () => 50;
const fit = (widths: number[], available: number, total = widths.length) =>
  fittingChips({ widths, gap: 4, available, total, moreWidth: more });

describe("how many related records a cell shows (0.9 K5b)", () => {
  it("shows every chip, without +N more, when all the row's records fit", () => {
    expect(fit([100, 100, 100], 308)).toBe(3);
    expect(fit([], 300)).toBe(0);
  });

  it("keeps room for +N more when some do not fit", () => {
    // Three chips need 308; two chips and "+1 more" need 204 + 4 + 50.
    expect(fit([100, 100, 100], 307)).toBe(2);
    expect(fit([100, 100, 100], 258)).toBe(2);
    expect(fit([100, 100, 100], 257)).toBe(1);
  });

  it("counts records the list did not return: every returned chip may fit, +N more still shows", () => {
    expect(fit([100, 100], 204, 5)).toBe(1);
    expect(fit([100, 100], 258, 5)).toBe(2);
  });

  it("shows the first chip, clipped, when not even one fits", () => {
    expect(fit([300, 100], 120)).toBe(1);
  });

  it("measures +N more for the records it hides", () => {
    const widths = [100, 100, 100];
    const moreWidth = (hidden: number) => (hidden > 1 ? 80 : 50);
    expect(fittingChips({ widths, gap: 4, available: 258, total: 3, moreWidth })).toBe(2);
    expect(fittingChips({ widths, gap: 4, available: 187, total: 3, moreWidth })).toBe(1);
  });
});
