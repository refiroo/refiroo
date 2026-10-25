// @vitest-environment jsdom
import { render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { fixedWindow } from "@/lib/hooks/useCursorWindow";
import { outerScroller, ScrollWindow } from "@/ui/ScrollWindow";

afterEach(() => vi.restoreAllMocks());

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

describe("the wheel over a list (0.12 LS1, D372)", () => {
  /** Whether each wheel listener added while the list is drawn is passive (the library adds its own). */
  function wheelListeners(fill: boolean) {
    const added = vi.spyOn(HTMLElement.prototype, "addEventListener");
    render(
      <ScrollWindow list={fixedWindow(["a", "b"])} label="Rows" noun={["row", "rows"]} pageSize={20} fill={fill}>
        {(drawn) => (
          <ul>
            {drawn.rows.map((row) => (
              <li key={row.index}>{row.item}</li>
            ))}
          </ul>
        )}
      </ScrollWindow>,
    );
    return added.mock.calls
      .filter(([type]) => type === "wheel")
      .map(([, , options]) => (typeof options === "object" ? options.passive : undefined));
  }

  it("is the browser's alone in a list that fills its page", () => {
    expect(wheelListeners(true)).not.toContain(false);
  });

  it("is still handled in a list nested in a page that scrolls", () => {
    expect(wheelListeners(false)).toContain(false);
  });
});
