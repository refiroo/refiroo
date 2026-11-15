import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { StalePreviewDialog } from "./StalePreviewDialog";

describe("StalePreviewDialog", () => {
  it("says why, that nothing was done and what to do, with a second action and no dismiss button", () => {
    const onConfirm = vi.fn();
    const onOpen = vi.fn();
    render(
      <StalePreviewDialog
        title="The mapping changed after this dry run"
        reason="The mapping was changed."
        past="moved"
        next="Run the dry run again."
        confirmLabel="Dry run again"
        secondary={{ label: "Open the mapping", onClick: onOpen }}
        dismissable={false}
        onCancel={vi.fn()}
        onConfirm={onConfirm}
      />,
    );
    expect(screen.getByRole("alertdialog")).toHaveTextContent(
      "The mapping was changed. Nothing was moved. Run the dry run again.",
    );
    expect(screen.queryByRole("button", { name: "Cancel" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Open the mapping" }));
    expect(onOpen).toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Dry run again" }));
    expect(onConfirm).toHaveBeenCalled();
  });

  it("keeps its label while it works and closes with its own word", () => {
    const onCancel = vi.fn();
    render(
      <StalePreviewDialog
        title="Changed"
        reason="Records were saved."
        past="migrated"
        next="Preview again."
        confirmLabel="Preview again"
        dismissLabel="Close"
        pending
        onCancel={onCancel}
        onConfirm={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: "Preview again" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Close" })).toBeDisabled();
  });
});
