import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import { domainObject } from "@/test/fixtures";
import type { AttributeTypeDefinition } from "@/types";
import { ToastProvider } from "@/ui/Toast";
import { InlineAttributeEditor } from "./InlineAttributeEditor";

vi.mock("@/api/client", () => ({
  api: { createAttribute: vi.fn(), updateAttribute: vi.fn(), deleteAttribute: vi.fn(), object: vi.fn() },
}));
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.createAttribute).mockResolvedValue(domainObject);
  vi.mocked(api.updateAttribute).mockResolvedValue(domainObject);
  vi.mocked(api.deleteAttribute).mockResolvedValue(undefined as never);
  vi.mocked(api.object).mockResolvedValue(domainObject);
});
function editor(valueType: AttributeTypeDefinition["valueType"], extra = {}, required = false) {
  return (
    <ToastProvider>
      <InlineAttributeEditor
        object={domainObject}
        attribute={{ key: "test", name: "Value", valueType, features: {}, validation: {}, ui: {} }}
        binding={{ attributeTypeKey: "test", required, readOnly: false, order: 0, ui: {} }}
        onClose={vi.fn()}
        onSaved={vi.fn()}
        onConflict={vi.fn()}
        {...extra}
      />
    </ToastProvider>
  );
}
/** A record that already holds the value, for an edit and a removal. */
function holding(value: unknown, valueType = "text") {
  return {
    ...domainObject,
    attributes: [
      ...domainObject.attributes,
      { id: "77777777-7777-4777-8777-777777777777", attributeTypeKey: "test", name: "Value", valueType, value },
    ],
  } as typeof domainObject;
}
/** Leaves the field: the input is focused by autoFocus, and focus goes nowhere in the form. */
function leave() {
  act(() => (document.activeElement as HTMLElement).blur());
}
describe("InlineAttributeEditor", () => {
  it.each([
    ["text", "Some text", "Some text"],
    ["longText", "Line one\nLine two", "Line one\nLine two"],
    ["integer", "0", 0],
    ["decimal", "0.25", 0.25],
    ["date", "2026-09-11", "2026-09-11"],
    ["json", '{"enabled":false}', { enabled: false }],
  ] as const)("saves a %s value when the field is left", async (type, input, expected) => {
    render(editor(type));
    fireEvent.change(screen.getByLabelText("Value"), { target: { value: input } });
    expect(api.createAttribute).not.toHaveBeenCalled();
    leave();
    await waitFor(() =>
      expect(api.createAttribute).toHaveBeenCalledWith(
        "domain",
        domainObject.id,
        "test",
        expected,
        domainObject.version,
      ),
    );
    expect(await screen.findByText("Value saved")).toBeInTheDocument();
  });
  it("saves a tick on the click, with no Save button", async () => {
    render(editor("boolean"));
    expect(screen.queryByRole("button", { name: "Save" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("Value"));
    await waitFor(() =>
      expect(api.createAttribute).toHaveBeenCalledWith("domain", domainObject.id, "test", true, domainObject.version),
    );
  });
  it("saves false over a stored true on the click", async () => {
    render(editor("boolean", { object: holding(true, "boolean"), stored: { value: true } }));
    fireEvent.click(screen.getByLabelText("Value"));
    await waitFor(() =>
      expect(api.updateAttribute).toHaveBeenCalledWith("domain", domainObject.id, "test", false, domainObject.version),
    );
  });
  it("closes without writing or toasting when the input is left as it opened", async () => {
    const onClose = vi.fn();
    render(editor("text", { onClose, object: holding("Old"), stored: { value: "Old" } }));
    leave();
    await waitFor(() => expect(onClose).toHaveBeenCalledOnce());
    expect(api.updateAttribute).not.toHaveBeenCalled();
    expect(screen.queryByText("Value saved")).not.toBeInTheDocument();
  });
  it("removes an optional value that is set and left empty, and offers Undo", async () => {
    const onSaved = vi.fn();
    render(editor("text", { onSaved, object: holding("Old"), stored: { value: "Old" } }));
    fireEvent.change(screen.getByLabelText("Value"), { target: { value: "" } });
    leave();
    await waitFor(() =>
      expect(api.deleteAttribute).toHaveBeenCalledWith("domain", domainObject.id, "test", domainObject.version),
    );
    await waitFor(() => expect(onSaved).toHaveBeenCalledWith(domainObject));
    expect(api.object).toHaveBeenCalledWith("domain", domainObject.id, "default");
    expect(await screen.findByText("Value removed")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Undo" })).toBeInTheDocument();
    expect(api.updateAttribute).not.toHaveBeenCalled();
  });
  it("closes an optional value that is not set and left empty", async () => {
    const onClose = vi.fn();
    render(editor("text", { onClose }));
    fireEvent.change(screen.getByLabelText("Value"), { target: { value: "x" } });
    fireEvent.change(screen.getByLabelText("Value"), { target: { value: "" } });
    leave();
    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(api.deleteAttribute).not.toHaveBeenCalled();
    expect(api.createAttribute).not.toHaveBeenCalled();
  });
  it("refuses a required value left empty under the field and writes nothing", async () => {
    render(editor("text", { object: holding("Old"), stored: { value: "Old" } }, true));
    fireEvent.change(screen.getByLabelText("Value"), { target: { value: "" } });
    leave();
    expect(await screen.findByText(/Value needs a value\./)).toBeInTheDocument();
    expect(api.deleteAttribute).not.toHaveBeenCalled();
    expect(api.updateAttribute).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Save again" })).toBeInTheDocument();
  });
  it("undoes a value set for the first time by deleting it against the saved version", async () => {
    vi.mocked(api.createAttribute).mockResolvedValue({ ...domainObject, version: 5 });
    render(editor("text"));
    fireEvent.change(screen.getByLabelText("Value"), { target: { value: "New" } });
    leave();
    fireEvent.click(await screen.findByRole("button", { name: "Undo" }));
    await waitFor(() => expect(api.deleteAttribute).toHaveBeenCalledWith("domain", domainObject.id, "test", 5));
  });
  it("retains invalid input and allows Escape cancellation", async () => {
    const onClose = vi.fn();
    render(editor("json", { onClose }));
    fireEvent.change(screen.getByLabelText("Value"), { target: { value: "{" } });
    leave();
    await screen.findByText("The value was not saved");
    expect(screen.getByText(/This is not valid JSON\./)).toBeInTheDocument();
    expect(screen.getByLabelText("Value")).toHaveValue("{");
    expect(api.createAttribute).not.toHaveBeenCalled();
    fireEvent.keyDown(screen.getByLabelText("Value"), { key: "Escape" });
    expect(onClose).toHaveBeenCalledOnce();
  });
  it.each(["VERSION_CONFLICT", "CHANGE_SET_VERSION_CONFLICT"])(
    "blocks retry until current content reloads after %s",
    async (code) => {
      vi.mocked(api.createAttribute).mockRejectedValueOnce(new ApiError(409, code, "Review the latest value"));
      const onConflict = vi.fn().mockRejectedValueOnce(new Error("Reload unavailable")).mockResolvedValue(undefined);
      const view = render(editor("text", { onConflict }));
      fireEvent.change(screen.getByLabelText("Value"), { target: { value: "My edit" } });
      leave();
      await screen.findByText("Reload unavailable");
      expect(screen.getByRole("button", { name: "Save again" })).toBeDisabled();
      view.rerender(
        editor("text", {
          onConflict,
          object: {
            ...domainObject,
            version: 2,
            attributes: [...domainObject.attributes, { attributeTypeKey: "test", value: "Their edit" }],
          },
        }),
      );
      fireEvent.click(screen.getByRole("button", { name: "Reload current value" }));
      await screen.findByText(/Their edit/);
      expect(screen.getByLabelText("Value")).toHaveValue("My edit");
      fireEvent.click(screen.getByRole("button", { name: "Save again" }));
      await waitFor(() =>
        expect(api.updateAttribute).toHaveBeenCalledWith("domain", domainObject.id, "test", "My edit", 2),
      );
    },
  );
});
