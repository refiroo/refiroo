import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ConfirmDialog } from "./ConfirmDialog";
import { CancelButton, Modal } from "./Modal";

function openFrom(ui: React.ReactElement) {
  const trigger = document.createElement("button");
  trigger.textContent = "Open";
  document.body.append(trigger);
  trigger.focus();
  return { trigger, ...render(ui) };
}

describe("Modal", () => {
  it("derives its accessible name from the visible title", () => {
    render(
      <Modal title="First" onClose={vi.fn()}>
        <p>one</p>
      </Modal>,
    );
    expect(screen.getByRole("dialog")).toHaveAccessibleName("First");
  });

  it("closes on Escape and restores focus to whatever opened it", async () => {
    const onClose = vi.fn();
    const { trigger, unmount } = openFrom(
      <Modal title="Edit" onClose={onClose}>
        <button>Inside</button>
      </Modal>,
    );

    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape", code: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);

    unmount();
    await waitFor(() => expect(document.activeElement).toBe(trigger));
    trigger.remove();
  });

  it("refuses to close while a write is in flight", () => {
    const onClose = vi.fn();
    render(
      <Modal title="Saving" busy onClose={onClose}>
        <button>Inside</button>
      </Modal>,
    );

    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape", code: "Escape" });
    fireEvent.mouseDown(screen.getByRole("dialog").parentElement!.parentElement!);

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

  it("restores the opener after an autoFocus child unmounts", async () => {
    const { trigger, unmount } = openFrom(
      <Modal title="Named" onClose={vi.fn()}>
        <input autoFocus aria-label="Name" />
      </Modal>,
    );

    expect(document.activeElement).toBe(screen.getByLabelText("Name"));
    unmount();
    await waitFor(() => expect(document.activeElement).toBe(trigger));
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
    fireEvent.keyDown(last, { key: "Tab", code: "Tab" });
    expect(document.activeElement).toBe(first);

    fireEvent.keyDown(first, { key: "Tab", code: "Tab", shiftKey: true });
    expect(document.activeElement).toBe(last);
  });

  it("locks page scrolling until the last dialog closes", () => {
    const { unmount } = render(
      <Modal title="Locked" onClose={vi.fn()}>
        <p>content</p>
      </Modal>,
    );
    expect(document.documentElement.style.overflow).toBe("hidden");
    unmount();
    expect(document.documentElement.style.overflow).not.toBe("hidden");
  });

  it("requires confirmation before dismissing dirty content", () => {
    const onClose = vi.fn();
    const confirmDiscard = vi.fn().mockReturnValueOnce(false).mockReturnValueOnce(true);
    render(
      <Modal title="Dirty" dirty confirmDiscard={confirmDiscard} onClose={onClose}>
        <button>Inside</button>
      </Modal>,
    );
    const dialog = screen.getByRole("dialog");
    fireEvent.keyDown(dialog, { key: "Escape", code: "Escape" });
    expect(onClose).not.toHaveBeenCalled();
    fireEvent.keyDown(dialog, { key: "Escape", code: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});

describe("CancelButton", () => {
  it("asks the one discard question while the dialog is dirty, and not while it is clean", () => {
    const onClose = vi.fn();
    const confirm = vi.spyOn(window, "confirm").mockReturnValueOnce(false).mockReturnValueOnce(true);
    const { rerender } = render(
      <Modal title="Typed" dirty onClose={onClose}>
        <CancelButton />
      </Modal>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(confirm).toHaveBeenCalledWith("Discard your unsaved changes?");
    expect(onClose).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onClose).toHaveBeenCalledTimes(1);
    rerender(
      <Modal title="Typed" onClose={onClose}>
        <CancelButton />
      </Modal>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(confirm).toHaveBeenCalledTimes(2);
    expect(onClose).toHaveBeenCalledTimes(2);
    confirm.mockRestore();
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
