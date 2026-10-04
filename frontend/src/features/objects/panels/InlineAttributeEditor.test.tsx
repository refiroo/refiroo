import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import { domainObject } from "@/test/fixtures";
import type { AttributeTypeDefinition } from "@/types";
import { InlineAttributeEditor } from "./InlineAttributeEditor";

vi.mock("@/api/client", () => ({ api: { createAttribute: vi.fn(), updateAttribute: vi.fn() } }));
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.createAttribute).mockResolvedValue(domainObject);
});
function editor(valueType: AttributeTypeDefinition["valueType"], extra = {}) {
  return (
    <InlineAttributeEditor
      object={domainObject}
      attribute={{ key: "test", name: "Value", valueType, features: {}, validation: {}, ui: {} }}
      binding={{ attributeTypeKey: "test", required: false, readOnly: false, order: 0, ui: {} }}
      onClose={vi.fn()}
      onSaved={vi.fn()}
      onConflict={vi.fn()}
      {...extra}
    />
  );
}
describe("InlineAttributeEditor", () => {
  it.each([
    ["text", "", ""],
    ["longText", "Line one\nLine two", "Line one\nLine two"],
    ["integer", "0", 0],
    ["decimal", "0.25", 0.25],
    ["date", "2026-09-11", "2026-09-11"],
    ["json", '{"enabled":false}', { enabled: false }],
  ] as const)("preserves %s values through the mutation boundary", async (type, input, expected) => {
    render(editor(type));
    fireEvent.change(screen.getByLabelText("Value"), { target: { value: input } });
    expect(api.createAttribute).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() =>
      expect(api.createAttribute).toHaveBeenCalledWith(
        "domain",
        domainObject.id,
        "test",
        expected,
        domainObject.version,
      ),
    );
  });
  it("does not autosave a checkbox and distinguishes false from explicit null", async () => {
    const rendered = render(editor("boolean"));
    fireEvent.click(screen.getByLabelText("Value"));
    fireEvent.click(screen.getByLabelText("Value"));
    expect(api.createAttribute).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() =>
      expect(api.createAttribute).toHaveBeenCalledWith("domain", domainObject.id, "test", false, domainObject.version),
    );
    rendered.unmount();
    render(editor("boolean", { stored: { attributeTypeKey: "test", value: null } }));
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() =>
      expect(api.createAttribute).toHaveBeenLastCalledWith(
        "domain",
        domainObject.id,
        "test",
        null,
        domainObject.version,
      ),
    );
  });
  it("retains invalid input and allows Escape cancellation", async () => {
    const onClose = vi.fn();
    render(editor("json", { onClose }));
    fireEvent.change(screen.getByLabelText("Value"), { target: { value: "{" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await screen.findByText("The value was not saved");
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
      fireEvent.click(screen.getByRole("button", { name: "Save" }));
      await screen.findByText("Reload unavailable");
      expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
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
      fireEvent.click(screen.getByRole("button", { name: "Save" }));
      await waitFor(() =>
        expect(api.updateAttribute).toHaveBeenCalledWith("domain", domainObject.id, "test", "My edit", 2),
      );
    },
  );
});
