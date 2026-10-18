import { act, fireEvent, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useRailScroll } from "@/ui/navigationRail";

/** jsdom has no layout: each rail holds `content` px in a 300px view, which clamps its scroll. */
function rail(content: { height: number }) {
  const element = document.createElement("div");
  let top = 0;
  Object.defineProperty(element, "scrollTop", {
    get: () => top,
    set: (value: number) => {
      top = Math.max(0, Math.min(value, content.height - 300));
      element.dispatchEvent(new Event("scroll"));
    },
  });
  element.appendChild(document.createElement("div"));
  return element;
}

function Rail({ container, scope }: { container: HTMLElement; scope: string }) {
  useRailScroll(container, scope);
  return null;
}

let grow: (() => void) | undefined;
vi.stubGlobal(
  "ResizeObserver",
  class {
    constructor(callback: () => void) {
      grow = callback;
    }
    observe() {}
    disconnect() {}
  },
);
afterEach(() => {
  grow = undefined;
});

// Reported by the user (2026-10-18): the rail kept another application's offset, and jumped to its
// top on pages that mount the frame afresh (a change set, a publication).
describe("useRailScroll", () => {
  it("keeps the rail's place within its scope, even in a frame mounted afresh, and opens another scope at the top", () => {
    const content = { height: 2000 };
    const first = rail(content);
    const view = render(<Rail container={first} scope="app:west" />);
    act(() => {
      fireEvent.wheel(first);
      first.scrollTop = 900;
    });
    view.unmount();

    // A change set mounts the frame afresh: its tree loads first, then the place comes back.
    content.height = 400;
    const second = rail(content);
    render(<Rail container={second} scope="app:west" />);
    expect(second.scrollTop).toBe(100);
    content.height = 2000;
    act(() => grow?.());
    expect(second.scrollTop).toBe(900);

    // Another application in the same frame opens at the top.
    const third = rail(content);
    const other = render(<Rail container={third} scope="app:west" />);
    expect(third.scrollTop).toBe(900);
    other.rerender(<Rail container={third} scope="other:west" />);
    expect(third.scrollTop).toBe(0);
  });

  it("stops restoring as soon as the reader scrolls, so the rail never moves under them", () => {
    const content = { height: 2000 };
    const first = rail(content);
    const view = render(<Rail container={first} scope="app:east" />);
    act(() => {
      first.scrollTop = 1200;
    });
    view.unmount();

    content.height = 500;
    const second = rail(content);
    render(<Rail container={second} scope="app:east" />);
    act(() => {
      fireEvent.wheel(second);
      second.scrollTop = 50;
    });
    content.height = 2000;
    act(() => grow?.());
    expect(second.scrollTop).toBe(50);
  });
});
