import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { codelistObject, domainObject, testModel } from "@/test/fixtures";
import type { AttributesPanelDefinition } from "@/types";
import { AttributesPanel } from "@/features/objects/panels/AttributesPanel";

const panel: AttributesPanelDefinition = {
  key: "attributes",
  title: "Attributes",
  type: "attributes",
  region: "main",
  order: 1,
  visible: true,
  config: { fields: ["code", "active"] },
};

describe("AttributesPanel", () => {
  it.each([
    ["domain", domainObject, "Yes"],
    ["codelist", codelistObject, "No"],
  ])("uses the same stored-value actions for %s", (_name, object, booleanLabel) => {
    render(
      <AttributesPanel model={testModel} object={object} panel={panel} onObjectChanged={vi.fn()} onReload={vi.fn()} />,
    );
    expect(screen.getByText(booleanLabel)).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /^Edit / })).toHaveLength(2);
    expect(screen.queryByRole("button", { name: /^Add / })).not.toBeInTheDocument();
  });

  // UA4 revision: the value is the edit control; a plus on an empty field adds; an icon removes.
  it.each([
    ["domain", domainObject, "Yes"],
    ["codelist", codelistObject, "No"],
  ])("edits a %s field by its value and returns focus to it", (_name, object, booleanLabel) => {
    render(
      <AttributesPanel model={testModel} object={object} panel={panel} onObjectChanged={vi.fn()} onReload={vi.fn()} />,
    );
    const value = screen.getByRole("button", { name: `Edit Active: ${booleanLabel}` });
    fireEvent.click(value);
    const editor = screen.getByRole("form", { name: "Edit Active" });
    fireEvent.keyDown(editor, { key: "Escape" });
    expect(screen.queryByRole("form", { name: "Edit Active" })).not.toBeInTheDocument();
    return new Promise<void>((done) =>
      requestAnimationFrame(() => {
        expect(screen.getByRole("button", { name: `Edit Active: ${booleanLabel}` })).toHaveFocus();
        done();
      }),
    );
  });

  it("adds a value to an empty field by clicking it", () => {
    const object = {
      ...domainObject,
      attributes: domainObject.attributes.filter((item) => item.attributeTypeKey !== "active"),
    };
    render(
      <AttributesPanel model={testModel} object={object} panel={panel} onObjectChanged={vi.fn()} onReload={vi.fn()} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Add Active: Not set" }));
    expect(screen.getByRole("form", { name: "Edit Active" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Remove Active" })).not.toBeInTheDocument();
  });

  it("removes only an optional field, after confirmation", () => {
    render(
      <AttributesPanel
        model={testModel}
        object={domainObject}
        panel={panel}
        onObjectChanged={vi.fn()}
        onReload={vi.fn()}
      />,
    );
    expect(screen.queryByRole("button", { name: "Remove Code" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Remove Active" }));
    expect(screen.getByRole("alertdialog", { name: "Remove Active?" })).toBeInTheDocument();
  });

  it("leaves a click that selected the value's text for copying", () => {
    render(
      <AttributesPanel
        model={testModel}
        object={domainObject}
        panel={panel}
        onObjectChanged={vi.fn()}
        onReload={vi.fn()}
      />,
    );
    const value = screen.getByRole("button", { name: "Edit Code: CONNECTIONS" });
    const range = document.createRange();
    range.selectNodeContents(screen.getByText("CONNECTIONS"));
    window.getSelection()?.removeAllRanges();
    window.getSelection()?.addRange(range);
    fireEvent.click(value);
    expect(screen.queryByRole("form", { name: "Edit Code" })).not.toBeInTheDocument();
    window.getSelection()?.removeAllRanges();
    fireEvent.click(value);
    expect(screen.getByRole("form", { name: "Edit Code" })).toBeInTheDocument();
  });

  it("does not offer mutations for a read-only binding", () => {
    const model = {
      ...testModel,
      objectTypes: testModel.objectTypes.map((type, index) =>
        index ? type : { ...type, attributes: type.attributes.map((binding) => ({ ...binding, readOnly: true })) },
      ),
    };
    render(
      <AttributesPanel
        model={model}
        object={domainObject}
        panel={panel}
        onObjectChanged={vi.fn()}
        onReload={vi.fn()}
      />,
    );
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
