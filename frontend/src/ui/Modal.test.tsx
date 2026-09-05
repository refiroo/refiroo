import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ConfirmDialog } from "./ConfirmDialog";
import { Modal } from "./Modal";

function openFrom(ui: React.ReactElement) {
  const trigger = document.createElement("button");
  trigger.textContent = "Open";
  document.body.append(trigger);
  trigger.focus();
  return { trigger, ...render(ui) };
}

describe("Modal", () => {
  it("labels itself with a generated id, so two open dialogs cannot collide", () => {
    render(
      <>
        <Modal title="First" onClose={vi.fn()}>
          <p>one</p>
        </Modal>
        <Modal title="Second" onClose={vi.fn()}>
          <p>two</p>
        </Modal>
      </>,
    );
    const [first, second] = screen.getAllByRole("dialog");
    expect(first).toHaveAccessibleName("First");
    expect(second).toHaveAccessibleName("Second");
    expect(first.getAttribute("aria-labelledby")).not.toBe(second.getAttribute("aria-labelledby"));
  });

  it("closes on Escape and restores focus to whatever opened it", () => {
    const onClose = vi.fn();
    const { trigger, unmount } = openFrom(
      <Modal title="Edit" onClose={onClose}>
        <button>Inside</button>
      </Modal>,
    );

    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);

    unmount();
    expect(document.activeElement).toBe(trigger);
    trigger.remove();
  });

  it("refuses to close while a write is in flight", () => {
    const onClose = vi.fn();
    render(
      <Modal title="Saving" busy onClose={onClose}>
        <button>Inside</button>
      </Modal>,
    );

    fireEvent.keyDown(window, { key: "Escape" });
    fireEvent.mouseDown(screen.getByRole("dialog").parentElement!);

    expect(onClose).not.toHaveBeenCalled();
  });

  it("moves focus into the dialog when no child claims it", () => {
    const { trigger } = openFrom(
      <Modal title="Connect" onClose={vi.fn()} showClose={false}>
        <p>No autofocus anywhere</p>
      </Modal>,
    );
    expect(document.activeElement).toBe(screen.getByRole("dialog"));
    trigger.remove();
  });

  it("leaves focus where a child claimed it with autoFocus", () => {
    render(
      <Modal title="Named" onClose={vi.fn()}>
        <input autoFocus aria-label="Name" />
      </Modal>,
    );
    expect(document.activeElement).toBe(screen.getByLabelText("Name"));
  });

  it("restores the opener after an autoFocus child unmounts", () => {
    const { trigger, unmount } = openFrom(
      <Modal title="Named" onClose={vi.fn()}>
        <input autoFocus aria-label="Name" />
      </Modal>,
    );

    expect(document.activeElement).toBe(screen.getByLabelText("Name"));
    unmount();
    expect(document.activeElement).toBe(trigger);
    trigger.remove();
  });

  it("keeps Tab inside the dialog in both directions", () => {
    render(
      <Modal title="Trapped" onClose={vi.fn()} showClose={false}>
        <button>First</button>
        <button>Last</button>
      </Modal>,
    );
    const first = screen.getByRole("button", { name: "First" });
    const last = screen.getByRole("button", { name: "Last" });

    last.focus();
    fireEvent.keyDown(window, { key: "Tab" });
    expect(document.activeElement).toBe(first);

    fireEvent.keyDown(window, { key: "Tab", shiftKey: true });
    expect(document.activeElement).toBe(last);
  });

  it("sends Escape only to the innermost dialog", () => {
    const outer = vi.fn();
    const inner = vi.fn();
    render(
      <>
        <Modal title="Outer" onClose={outer}>
          <p>outer</p>
        </Modal>
        <Modal title="Inner" onClose={inner}>
          <p>inner</p>
        </Modal>
      </>,
    );

    fireEvent.keyDown(window, { key: "Escape" });
    expect(inner).toHaveBeenCalledTimes(1);
    expect(outer).not.toHaveBeenCalled();
  });

  it("locks page scrolling until the last dialog closes", () => {
    const { unmount } = render(
      <Modal title="Locked" onClose={vi.fn()}>
        <p>content</p>
      </Modal>,
    );
    expect(document.body.style.overflow).toBe("hidden");
    unmount();
    expect(document.body.style.overflow).not.toBe("hidden");
  });
});

describe("ConfirmDialog", () => {
  it("is an alertdialog that opens on Cancel, so confirming is always deliberate", () => {
    render(
      <ConfirmDialog title="Delete “Connections”?" confirmLabel="Delete object" onCancel={vi.fn()} onConfirm={vi.fn()}>
        <p>This cannot be undone.</p>
      </ConfirmDialog>,
    );

    expect(screen.getByRole("alertdialog")).toHaveAccessibleName("Delete “Connections”?");
    expect(document.activeElement).toBe(screen.getByRole("button", { name: "Cancel" }));
    // No dismiss affordance in the header: the choice is Cancel or the destructive action.
    expect(screen.queryByRole("button", { name: "Close" })).not.toBeInTheDocument();
  });

  it("disables both actions while the delete is in flight", () => {
    render(
      <ConfirmDialog title="Delete?" confirmLabel="Delete object" pending onCancel={vi.fn()} onConfirm={vi.fn()}>
        <p>body</p>
      </ConfirmDialog>,
    );
    expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Working…" })).toBeDisabled();
  });
});
