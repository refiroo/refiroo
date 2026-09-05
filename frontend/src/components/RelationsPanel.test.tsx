import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../api/client";
import { codelistObject, domainObject, testModel } from "../test/fixtures";
import type { RelationsPanelDefinition } from "../types";
import { RelationsPanel } from "./RelationsPanel";

vi.mock("../api/client", () => ({ api: { relations: vi.fn() } }));

const panel: RelationsPanelDefinition = { key: "relations", title: "Relations", type: "relations", region: "main", order: 1, visible: true, config: { relationTypeKeys: ["domain-contains-codelist"], direction: "outgoing", columns: ["name"] } };

describe("RelationsPanel", () => {
  beforeEach(() => vi.mocked(api.relations).mockResolvedValue({ items: [{ direction: "outgoing", relation: { id: "relation", relationTypeKey: "domain-contains-codelist", fromObjectId: domainObject.id, toObjectId: codelistObject.id, attributes: {}, version: 1 }, object: codelistObject }], nextCursor: null }));

  it("shows direction-correct labels and protects managed containment rows", async () => {
    render(<RelationsPanel model={testModel} object={domainObject} panel={panel} onOpen={vi.fn()} />);
    expect(await screen.findByText("Contains")).toBeInTheDocument();
    expect(screen.getByText("Managed through Parent")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Add relationship/ })).not.toBeInTheDocument();
  });

  it("can hide a redundant relationship label and show a configured ancestor", async () => {
    render(
      <RelationsPanel
        model={testModel}
        object={domainObject}
        panel={{
          ...panel,
          config: {
            ...panel.config,
            columns: ["ancestor:domain", "name"],
            showRelationshipColumn: false,
          },
        }}
        onOpen={vi.fn()}
      />,
    );

    expect(await screen.findByText("Timetable types")).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Domain" })).toBeInTheDocument();
    expect(screen.getByText("Connections")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Timetable types" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Connections" })).not.toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "Relationship" })).not.toBeInTheDocument();
    expect(screen.queryByText("Contains")).not.toBeInTheDocument();
  });

  it("offers dependent object creation for a required outgoing relation", async () => {
    vi.mocked(api.relations).mockResolvedValue({ items: [], nextCursor: null });
    const translationType = {
      ...testModel.objectTypes[0],
      key: "translation",
      name: "Translation",
      pluralName: "Translations",
      features: { rootCreatable: false },
    };
    const model = {
      ...testModel,
      objectTypes: [...testModel.objectTypes, translationType],
      relationTypes: [
        ...testModel.relationTypes,
        { key: "object-has-translation", reverseKey: "translation-translates-object", name: "Has translation", reverseName: "Translates object", isOriented: true, features: {} },
      ],
      objectTypeRelations: [
        ...testModel.objectTypeRelations,
        { relationTypeKey: "object-has-translation", fromObjectTypeKey: "domain", toObjectTypeKey: "translation", cardinality: "one-to-many" as const, required: true },
      ],
      applications: [
        testModel.applications[0],
        { ...testModel.applications[0], key: "translations", objectTypeKeys: ["translation"] },
      ],
    };
    const translationPanel: RelationsPanelDefinition = {
      ...panel,
      config: {
        relationTypeKeys: ["object-has-translation"],
        direction: "outgoing",
        columns: ["name"],
      },
    };

    render(<RelationsPanel model={model} object={domainObject} panel={translationPanel} onOpen={vi.fn()} />);

    expect(await screen.findByRole("button", { name: "+ Add Translation" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "+ Add relationship" })).not.toBeInTheDocument();
  });
});
