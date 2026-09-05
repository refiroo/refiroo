import { render, screen } from "@testing-library/react";
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
    expect(screen.getAllByRole("button", { name: "Edit" })).toHaveLength(2);
    expect(screen.queryByRole("button", { name: "Add" })).not.toBeInTheDocument();
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
