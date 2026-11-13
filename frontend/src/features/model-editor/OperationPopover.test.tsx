import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { outlineFixture } from "@/test/draftOutline";
import { OperationDialog } from "@/features/model-editor/OperationDialog";
import {
  flipField,
  operationById,
  submitLabel,
  surfaceOf,
  type OperationSpec,
  type OperationTarget,
} from "@/features/model-editor/operations";

const outline = outlineFixture();
const shelf: OperationTarget = { on: "objectType", objectType: "shelf" };
const op = (id: string) => operationById(id) as OperationSpec;

/** An operation asked from a button on the page, as the editor does with the control that started it. */
function renderAnchored(id: string, target: OperationTarget, anchored = true) {
  const run = vi.fn().mockResolvedValue("applied");
  const onClose = vi.fn();
  const host = document.createElement("button");
  host.textContent = "Started here";
  document.body.append(host);
  // The editor drops the dialog when it closes; so does the harness.
  const Harness = () => {
    const [open, setOpen] = useState(true);
    return open ? (
      <OperationDialog
        operation={op(id)}
        target={target}
        outline={outline}
        anchor={anchored ? host : null}
        run={run}
        onClose={() => {
          onClose();
          setOpen(false);
        }}
      />
    ) : null;
  };
  render(<Harness />);
  return { run, onClose, host };
}

afterEach(() => cleanup());

describe("an operation under the control that started it (UX1, PP-D40)", () => {
  it("classifies the operations by their controls", () => {
    expect(surfaceOf(op("type-key"), shelf, outline)).toBe("popover");
    expect(surfaceOf(op("type-rename"), shelf, outline)).toBe("popover");
    expect(surfaceOf(op("type-at-least-one"), shelf, outline)).toBe("popover");
    expect(surfaceOf(op("add-type"), { on: "draft" }, outline)).toBe("sheet");
    expect(surfaceOf(op("type-remove"), shelf, outline)).toBe("sheet");
    expect(
      surfaceOf(op("attribute-list"), { on: "attribute", objectType: "shelf", attributeType: "depth" }, outline),
    ).toBe("sheet");
    expect(flipField(op("type-key"), shelf, outline)).toBeUndefined();
  });

  it("opens a one-control operation as a popover, focuses its field and sends the same request", async () => {
    const { run, onClose, host } = renderAnchored("type-key", shelf);
    const popover = await screen.findByRole("dialog", { name: "Change key" });
    expect(popover.closest(".editor-popover")).not.toBeNull();
    const key = within(popover).getByLabelText("Key");
    await waitFor(() => expect(key).toHaveFocus());
    fireEvent.change(key, { target: { value: "rack" } });
    expect(within(popover).getByRole("button", { name: "Save" })).toBeTruthy();
    fireEvent.submit(key.closest("form") as HTMLFormElement);
    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(run).toHaveBeenCalledWith([{ kind: "setKey", element: { objectType: "shelf" }, key: "rack" }]);

    await waitFor(() => expect(host).toHaveFocus());
  });

  it("holds two controls in the popover and shows a refusal in it", async () => {
    const run = vi.fn().mockRejectedValue(new Error("Nope"));
    const host = document.createElement("button");
    document.body.append(host);
    render(
      <OperationDialog
        operation={op("type-rename")}
        target={shelf}
        outline={outline}
        anchor={host}
        run={run}
        onClose={vi.fn()}
      />,
    );
    const popover = await screen.findByRole("dialog", { name: "Rename Shelf" });
    expect(within(popover).getByLabelText("Name")).toBeTruthy();
    expect(within(popover).getByLabelText("Plural name")).toBeTruthy();
    fireEvent.click(within(popover).getByRole("button", { name: "Save" }));
    expect(await within(popover).findByText("Nope")).toBeTruthy();
    host.remove();
  });

  it("marks the view name invalid while it is blank and clears the mark once it holds something", async () => {
    renderAnchored("application-add-view", { on: "application", applicationKey: "shop" } as OperationTarget, false);
    const dialog = await screen.findByRole("dialog");
    const name = within(dialog).getByLabelText("Name", { exact: true });
    expect(name.getAttribute("aria-invalid")).toBe("true");
    fireEvent.change(name, { target: { value: "   " } });
    expect(name.getAttribute("aria-invalid")).toBe("true");
    fireEvent.change(name, { target: { value: "All bins" } });
    expect(name.getAttribute("aria-invalid")).toBeNull();
  });

  it("closes on Escape and returns focus to the control", async () => {
    const { run, onClose, host } = renderAnchored("type-key", shelf);
    const popover = await screen.findByRole("dialog", { name: "Change key" });
    const key = within(popover).getByLabelText("Key");
    await waitFor(() => expect(key).toHaveFocus());
    fireEvent.keyDown(key, { key: "Escape" });
    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(run).not.toHaveBeenCalled();
    await waitFor(() => expect(host).toHaveFocus());
  });

  it("keeps the side sheet for three or more controls, and without a control to open under", async () => {
    const draft = renderAnchored("add-type", { on: "draft" });
    const sheet = await screen.findByRole("dialog", { name: "Add an object type" });
    expect(sheet.closest(".editor-popover")).toBeNull();
    expect(within(sheet).getByRole("button", { name: "Add type" })).toBeTruthy();
    expect(draft.run).not.toHaveBeenCalled();
  });

  it("opens as the sheet where no control started it", async () => {
    renderAnchored("type-key", shelf, false);
    const sheet = await screen.findByRole("dialog", { name: "Change key" });
    expect(sheet.closest(".editor-popover")).toBeNull();
    expect(within(sheet).getByRole("button", { name: "Save" })).toBeTruthy();
  });

  it("applies a pick-several list once, with one Apply at its foot", async () => {
    const { run, onClose } = renderAnchored("type-at-least-one", shelf);
    const popover = await screen.findByRole("dialog", { name: /of which one must be filled/ });
    expect(popover.closest(".editor-popover")).not.toBeNull();
    fireEvent.click(within(popover).getByRole("checkbox", { name: /Code/ }));
    fireEvent.click(within(popover).getByRole("checkbox", { name: /Depth/ }));
    expect(run).not.toHaveBeenCalled();
    fireEvent.click(within(popover).getByRole("button", { name: "Apply" }));
    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(run).toHaveBeenCalledTimes(1);
    expect(run).toHaveBeenCalledWith([
      { kind: "setObjectTypeProperty", objectType: "shelf", property: "atLeastOneOf", value: ["code", "depth"] },
    ]);
  });

  it("words the primary button as Save, Add, Move or Apply", () => {
    const words = (id: string, target: OperationTarget, surface: "popover" | "sheet") =>
      submitLabel(op(id), target, outline, {}, surface);
    expect(words("type-key", shelf, "popover")).toBe("Save");
    expect(words("add-type", { on: "draft" }, "sheet")).toBe("Add type");
    expect(words("type-new-attribute", shelf, "sheet")).toBe("Add attribute");
    expect(words("type-group", shelf, "sheet")).toBe("Move");
    expect(words("type-at-least-one", shelf, "popover")).toBe("Apply");
    expect(words("type-at-least-one", shelf, "sheet")).toBe("Save");
  });
});
