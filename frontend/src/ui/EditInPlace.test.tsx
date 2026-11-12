import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { InlineEditForm } from "./EditInPlace";

function field(
  kind: "text" | "area" | "select" = "text",
  handlers: { onSubmit?: () => void; onClose?: () => void } = {},
) {
  const onSubmit = handlers.onSubmit ?? vi.fn();
  const onClose = handlers.onClose ?? vi.fn();
  render(
    <InlineEditForm
      label="Edit Name"
      saving={false}
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
      onClose={onClose}
    >
      {kind === "text" && <input name="v" aria-label="Name" defaultValue="Old" autoFocus />}
      {kind === "area" && <textarea name="v" aria-label="Name" defaultValue="Old" autoFocus />}
      {kind === "select" && (
        <select name="v" aria-label="Name" defaultValue="a" autoFocus>
          <option value="a">A</option>
          <option value="b">B</option>
        </select>
      )}
    </InlineEditForm>,
  );
  return { onSubmit, onClose, input: screen.getByLabelText("Name") };
}
const leave = (input: HTMLElement) => act(() => input.blur());

describe("InlineEditForm", () => {
  it("saves when the field is left, and has no Save or Cancel button before a refusal", async () => {
    const { onSubmit, input } = field();
    expect(screen.queryByRole("button", { name: "Save" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument();
    fireEvent.change(input, { target: { value: "New" } });
    leave(input);
    await waitFor(() => expect(onSubmit).toHaveBeenCalledOnce());
  });
  it("saves on Enter in a one-line input", () => {
    const { onSubmit, input } = field();
    fireEvent.change(input, { target: { value: "New" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onSubmit).toHaveBeenCalledOnce();
  });
  it("keeps Enter as a new line in a text of several lines, and saves on Ctrl+Enter", () => {
    const { onSubmit, input } = field("area");
    fireEvent.change(input, { target: { value: "New" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onSubmit).not.toHaveBeenCalled();
    fireEvent.keyDown(input, { key: "Enter", ctrlKey: true });
    expect(onSubmit).toHaveBeenCalledOnce();
  });
  it("closes without saving an input left as it opened", async () => {
    const { onSubmit, onClose, input } = field();
    leave(input);
    await waitFor(() => expect(onClose).toHaveBeenCalledOnce());
    expect(onSubmit).not.toHaveBeenCalled();
  });
  it("closes on Escape and saves nothing", () => {
    const { onSubmit, onClose, input } = field();
    fireEvent.change(input, { target: { value: "New" } });
    fireEvent.keyDown(input, { key: "Escape" });
    expect(onClose).toHaveBeenCalledOnce();
    expect(onSubmit).not.toHaveBeenCalled();
  });
  it("saves a choice from a list as it is made", () => {
    const { onSubmit, input } = field("select");
    fireEvent.change(input, { target: { value: "b" } });
    expect(onSubmit).toHaveBeenCalledOnce();
  });
  it("after a refusal saves on leaving only a changed input, and always on Save again", async () => {
    const onSubmit = vi.fn();
    const onClose = vi.fn();
    render(
      <InlineEditForm
        label="Edit Name"
        saving={false}
        onSubmit={(event) => (event.preventDefault(), onSubmit())}
        onClose={onClose}
      >
        <input name="v" aria-label="Name" defaultValue="Old" autoFocus />
      </InlineEditForm>,
    );
    const input = screen.getByLabelText("Name");
    fireEvent.change(input, { target: { value: "Bad" } });
    leave(input);
    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    // The refusal stands: the field is open with Cancel and Save again.
    expect(await screen.findByRole("button", { name: "Save again" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();
    // Left again with the same input: nothing is sent.
    act(() => input.focus());
    leave(input);
    await act(async () => new Promise((resolve) => setTimeout(resolve, 20)));
    expect(onSubmit).toHaveBeenCalledTimes(1);
    // A changed input is sent on leaving.
    act(() => input.focus());
    fireEvent.change(input, { target: { value: "Better" } });
    leave(input);
    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(2));
    // Save again sends the input as it is.
    fireEvent.click(screen.getByRole("button", { name: "Save again" }));
    expect(onSubmit).toHaveBeenCalledTimes(3);
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onClose).toHaveBeenCalledOnce();
  });
  it("does not save again while a save is under way", () => {
    function Saving() {
      const [saving, setSaving] = useState(false);
      return (
        <InlineEditForm
          label="Edit Name"
          saving={saving}
          onSubmit={(event) => (event.preventDefault(), setSaving(true))}
          onClose={vi.fn()}
        >
          <input name="v" aria-label="Name" defaultValue="Old" autoFocus />
        </InlineEditForm>
      );
    }
    render(<Saving />);
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "New" } });
    fireEvent.keyDown(screen.getByLabelText("Name"), { key: "Enter" });
    expect(screen.getByText("Saving…")).toBeInTheDocument();
  });
});
