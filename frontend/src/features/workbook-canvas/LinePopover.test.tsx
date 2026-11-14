// @vitest-environment jsdom
import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { outlineFixture } from "@/test/draftOutline";
import { LinePopover } from "./LinePopover";

describe("the line popover", () => {
  it("takes focus once, as it opens, and leaves it where the person put it when the canvas draws again", () => {
    const outline = outlineFixture();
    const target = { on: "relation" as const, relationType: "stores", from: "shelf", to: "bin" };
    const props = () => ({
      title: "Shelf Stores Bin",
      target,
      outline,
      contains: false,
      onOperation: vi.fn(),
      run: vi.fn(),
      onClose: vi.fn(),
      menuOpen: false,
      onMenuOpenChange: vi.fn(),
    });
    const outside = document.createElement("input");
    document.body.append(outside);
    const { container, rerender } = render(<LinePopover {...props()} />);
    expect(container.querySelector(".canvas-line-popover")?.contains(document.activeElement)).toBe(true);
    outside.focus();
    // The canvas draws again with fresh callbacks.
    rerender(<LinePopover {...props()} />);
    expect(document.activeElement).toBe(outside);
    outside.remove();
  });
});
