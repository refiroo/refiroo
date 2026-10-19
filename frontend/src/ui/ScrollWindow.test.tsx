import { describe, expect, it } from "vitest";
import { outerScroller } from "@/ui/ScrollWindow";

describe("where a list carries the wheel at its ends (found 2026-10-19)", () => {
  it("stops at the dialog it stands in, not the page behind", () => {
    document.body.innerHTML = '<div class="dialog"><div><div class="scroll-window"></div></div></div>';
    const list = document.querySelector<HTMLElement>(".scroll-window")!;
    expect(outerScroller(list)).toBe(document.querySelector(".dialog"));
  });

  it("reaches the page for a list on the page", () => {
    document.body.innerHTML = '<main><div class="scroll-window"></div></main>';
    const list = document.querySelector<HTMLElement>(".scroll-window")!;
    expect(outerScroller(list)).toBe(document.scrollingElement ?? document.documentElement);
  });
});
