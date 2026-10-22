// @vitest-environment jsdom
import { describe, expect, it } from "vitest";
import { EDGE, MAX_STEP, TOUCH_EDGE, scrollAtEdge } from "@/lib/edgeScroll";

/** A scroller 400 px high at the top of the window, scrolled to `scrollTop` of 2,000 px. */
function scroller(scrollTop: number, coveredTop = 0) {
  const element = document.createElement("div");
  if (coveredTop) element.style.scrollPaddingTop = `${coveredTop}px`;
  Object.defineProperty(element, "clientHeight", { value: 400 });
  Object.defineProperty(element, "scrollHeight", { value: 2000 });
  const rect = { top: 0, bottom: 400, left: 0, right: 300, height: 400, width: 300, x: 0, y: 0 };
  element.getBoundingClientRect = () => ({ ...rect, toJSON: () => rect });
  document.body.append(element);
  element.scrollTop = scrollTop;
  return element;
}

describe("scrollAtEdge", () => {
  it("scrolls within the band, faster towards the edge, and not past either end", () => {
    const middle = scroller(500);
    expect(scrollAtEdge(middle, 200)).toBe(false);
    expect(scrollAtEdge(middle, 400 - EDGE / 2)).toBe(true);
    expect(middle.scrollTop).toBe(500 + MAX_STEP / 2);
    expect(scrollAtEdge(middle, 0)).toBe(true);
    expect(middle.scrollTop).toBe(500 + MAX_STEP / 2 - MAX_STEP);
    expect(scrollAtEdge(scroller(0), 5)).toBe(false);
  });

  it("starts the top band below a sticky bar's cover, and scrolls for a point over the bar (U1)", () => {
    const covered = scroller(500, 56);
    // 60 px is within 40 px of the cover's edge at 56 px, though not of the scroller's top.
    expect(scrollAtEdge(covered, 60)).toBe(true);
    expect(covered.scrollTop).toBeLessThan(500);
    const before = covered.scrollTop;
    expect(scrollAtEdge(covered, 20)).toBe(true);
    expect(covered.scrollTop).toBe(before - MAX_STEP);
  });

  it("takes a wider band for a finger (D211)", () => {
    const touched = scroller(500);
    expect(scrollAtEdge(touched, 400 - 50)).toBe(false);
    expect(scrollAtEdge(touched, 400 - 50, TOUCH_EDGE)).toBe(true);
  });
});
