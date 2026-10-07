import { describe, expect, it } from "vitest";
import { planWheel, wheelPixels } from "./treeWheel";

describe("planWheel", () => {
  it("scrolls the owner while it has room, by no more than that room", () => {
    expect(planWheel(-120, 300, [])).toEqual({ kind: "own", by: -120 });
    expect(planWheel(120, 40, [{ hidden: 50, room: 500 }])).toEqual({ kind: "own", by: 40 });
  });

  it("at the owner's end, reveals its hidden frame through the nearest scroller that hides it", () => {
    // The parent window hides 72px of the group's top and can scroll up 120px: it moves 72, then stops.
    expect(planWheel(-200, 0, [{ hidden: 72, room: 120 }])).toEqual({ kind: "enclosing", index: 0, by: -72 });
    expect(planWheel(-40, 0, [{ hidden: 72, room: 120 }])).toEqual({ kind: "enclosing", index: 0, by: -40 });
    // The nearest shows the whole frame; the page hides its bottom.
    expect(
      planWheel(100, 0, [
        { hidden: 0, room: 300 },
        { hidden: 30, room: 800 },
      ]),
    ).toEqual({
      kind: "enclosing",
      index: 1,
      by: 30,
    });
  });

  it("never moves a scroller past its own end, and passes over one that cannot move", () => {
    expect(planWheel(-200, 0, [{ hidden: 72, room: 10 }])).toEqual({ kind: "enclosing", index: 0, by: -10 });
    expect(
      planWheel(-200, 0, [
        { hidden: 72, room: 0 },
        { hidden: 20, room: 50 },
      ]),
    ).toEqual({
      kind: "enclosing",
      index: 1,
      by: -20,
    });
  });

  it("stops once the owner is at its end and its frame is in full view", () => {
    expect(
      planWheel(-200, 0, [
        { hidden: 0, room: 120 },
        { hidden: 0, room: 900 },
      ]),
    ).toEqual({ kind: "stop" });
    expect(planWheel(200, 0, [])).toEqual({ kind: "stop" });
  });
});

describe("wheelPixels", () => {
  it("reads pixels, lines and pages", () => {
    expect(wheelPixels({ deltaY: -53, deltaMode: 0 }, 400)).toBe(-53);
    expect(wheelPixels({ deltaY: 3, deltaMode: 1 }, 400)).toBe(48);
    expect(wheelPixels({ deltaY: -1, deltaMode: 2 }, 400)).toBe(-400);
  });
});
