import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { RotateOverlapDialog } from "./RotateOverlapDialog";

function open(overrides: { error?: string; pending?: boolean } = {}) {
  const onRotate = vi.fn();
  const onClose = vi.fn();
  render(
    <RotateOverlapDialog
      title="Rotate the thing"
      eyebrow="Test"
      lead="A new one is made. The current one keeps working for:"
      stopNowHint="For one that leaked."
      submitLabel="Make a new one"
      pendingLabel="Making…"
      errorTitle="None was made"
      pending={overrides.pending ?? false}
      error={overrides.error ?? ""}
      onClose={onClose}
      onRotate={onRotate}
    />,
  );
  return { onRotate, onClose, dialog: screen.getByRole("dialog", { name: "Rotate the thing" }) };
}

describe("RotateOverlapDialog", () => {
  it("rotates with the usual overlap of 24 hours unless another is chosen", () => {
    const { onRotate, dialog } = open();
    expect(within(dialog).getByRole("radio", { name: "24 hours" })).toBeChecked();
    expect(dialog).toHaveTextContent("The usual choice.");
    fireEvent.click(within(dialog).getByRole("button", { name: "Make a new one" }));
    expect(onRotate).toHaveBeenCalledWith(24);
  });

  it("offers an hour, a week and stopping the current one now, with what the last costs", () => {
    const { onRotate, dialog } = open();
    for (const [label, hours] of [
      ["1 hour", 1],
      ["7 days", 168],
      ["Stop it now", 0],
    ] as const) {
      fireEvent.click(within(dialog).getByRole("radio", { name: label }));
      fireEvent.click(within(dialog).getByRole("button", { name: "Make a new one" }));
      expect(onRotate).toHaveBeenLastCalledWith(hours);
    }
    expect(dialog).toHaveTextContent("For one that leaked.");
  });

  it("shows a refusal, and a busy dialog cannot be submitted again", () => {
    const { dialog } = open({ error: "The key could not be made", pending: true });
    expect(within(dialog).getByText("The key could not be made")).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Making…" })).toBeDisabled();
  });
});
