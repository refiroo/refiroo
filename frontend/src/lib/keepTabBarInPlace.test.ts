import { describe, expect, it } from "vitest";
import { scrollDelta, tallestHeight } from "@/lib/keepTabBarInPlace";

describe("scrollDelta", () => {
  it("scrolls by how far the bar moved down or up", () => {
    expect(scrollDelta(120, 180)).toBe(60);
    expect(scrollDelta(120, 90)).toBe(-30);
    expect(scrollDelta(120, 120)).toBe(0);
  });

  it("leaves a bar that was scrolled out above the viewport alone", () => {
    expect(scrollDelta(-40, 100)).toBe(0);
  });
});

describe("tallestHeight", () => {
  it("only ever grows, so a short panel cannot shorten the page", () => {
    expect(tallestHeight(0, 900)).toBe(900);
    expect(tallestHeight(900, 300)).toBe(900);
    expect(tallestHeight(900, 1200)).toBe(1200);
  });

  it("ignores a measurement that is not a number", () => {
    expect(tallestHeight(500, Number.NaN)).toBe(500);
  });
});
