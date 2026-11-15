// @vitest-environment jsdom
import { afterEach, describe, expect, it } from "vitest";
import { scrollingAncestor, scrollingAncestorOrNull } from "@/lib/scrollAncestor";

afterEach(() => (document.body.innerHTML = ""));

/** jsdom has no layout: a box scrolls when it says so. */
function scroller(parent: HTMLElement, scrollHeight: number, clientHeight: number, className = "") {
  const box = document.createElement("div");
  box.className = className;
  box.style.overflowY = "auto";
  Object.defineProperty(box, "scrollHeight", { value: scrollHeight });
  Object.defineProperty(box, "clientHeight", { value: clientHeight });
  parent.append(box);
  return box;
}

describe("scrollingAncestor", () => {
  it("finds the nearest ancestor that scrolls, and the page where none does", () => {
    const outer = scroller(document.body, 500, 100);
    const inner = scroller(outer, 300, 100);
    const leaf = document.createElement("span");
    inner.append(leaf);
    expect(scrollingAncestor(leaf)).toBe(inner);
    expect(scrollingAncestorOrNull(document.body.appendChild(document.createElement("i")))).toBeNull();
    expect(scrollingAncestor(document.body.appendChild(document.createElement("b")))).toBe(
      document.scrollingElement ?? document.documentElement,
    );
  });

  it("counts a box as scrolling only past the tolerance", () => {
    const box = scroller(document.body, 101, 100);
    const leaf = box.appendChild(document.createElement("span"));
    expect(scrollingAncestorOrNull(leaf)).toBe(box);
    expect(scrollingAncestorOrNull(leaf, { tolerance: 1 })).toBeNull();
  });

  it("stops at a dialog, which carries the wheel for what is in it, when asked to", () => {
    const outer = scroller(document.body, 500, 100);
    const dialog = document.createElement("div");
    dialog.className = "dialog";
    outer.append(dialog);
    const leaf = dialog.appendChild(document.createElement("span"));
    expect(scrollingAncestor(leaf)).toBe(outer);
    expect(scrollingAncestor(leaf, { dialog: true })).toBe(dialog);
  });
});
