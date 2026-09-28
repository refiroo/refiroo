import { describe, expect, it } from "vitest";
import { codelistObject, domainObject, testModel } from "@/test/fixtures";
import { fallbackDetail } from "@/model/defaults";
import { attributeName, fieldValue } from "@/model/fields";
import { isManagedRelation, objectTypeFor, relationChoices } from "@/model/lookup";
import { childCollectionGroups, collectionGroups, viewSourceObjectTypeKey } from "@/model/collections";

describe("objectTypeFor", () => {
  it("resolves a known object type and returns undefined for an unknown key", () => {
    expect(objectTypeFor(testModel, "domain")?.name).toBe("Domain");
    expect(objectTypeFor(testModel, "missing")).toBeUndefined();
  });
});

describe("collection lens helpers", () => {
  it("groups arbitrary renderer definitions by model-derived source type", () => {
    const application = structuredClone(testModel.applications[0]);
    application.views.push({
      key: "domain-links",
      name: "Domain links",
      type: "mappingGrid",
      config: {
        relationTypeKey: "domain-contains-codelist",
        fromObjectTypeKey: "domain",
        toObjectTypeKey: "codelist",
        direction: "outgoing",
        sourceColumns: ["name"],
        targetDisplayColumns: ["name"],
        candidateSearchFields: ["name"],
        pageSize: 20,
      },
    });
    const groups = collectionGroups(application);
    expect(groups).toHaveLength(1);
    expect(groups[0].views.map((view) => view.key)).toEqual(["domains", "domain-links"]);
    expect(viewSourceObjectTypeKey(groups[0].views[1])).toBe("domain");
  });

  it("groups a relation matrix under its row type, beside that type's table, in either direction", () => {
    const application = structuredClone(testModel.applications[0]);
    for (const [row, direction] of [
      ["domain", "outgoing"],
      ["codelist", "incoming"],
    ] as const) {
      application.views.push({
        key: `${row}-matrix`,
        name: `${row} matrix`,
        type: "relationMatrix",
        config: {
          relationTypeKey: "links",
          direction,
          rowObjectTypeKey: row,
          columnObjectTypeKey: "column-type",
          cellObjectTypeKey: "cell-type",
          rowColumns: ["name"],
          columnLabelField: "name",
          cellFields: ["code"],
          searchFields: ["name"],
          pageSize: 20,
        },
      });
    }
    const groups = collectionGroups(application);
    expect(groups.map((group) => [group.objectTypeKey, group.views.map((view) => view.key)])).toEqual([
      ["domain", ["domains", "domain-matrix"]],
      ["codelist", ["codelist-matrix"]],
    ]);
    // The table stays the collection's default lens.
    expect(groups[0].defaultView.key).toBe("domains");
  });

  it("groups a tree under its first root type, beside that type's table", () => {
    const application = structuredClone(testModel.applications[0]);
    for (const roots of [
      ["domain", "codelist"],
      ["codelist", "domain"],
    ]) {
      application.views.push({
        key: `${roots[0]}-tree`,
        name: `${roots[0]} tree`,
        type: "tree",
        config: { rootObjectTypeKeys: roots, objectTypeKeys: ["domain", "codelist"], labelField: "name", pageSize: 50 },
      });
    }
    const groups = collectionGroups(application);
    expect(groups.map((group) => [group.objectTypeKey, group.views.map((view) => view.key)])).toEqual([
      ["domain", ["domains", "domain-tree"]],
      ["codelist", ["codelist-tree"]],
    ]);
    expect(groups[0].defaultView.key).toBe("domains");
  });

  it("derives contextual child collections only from configured containment", () => {
    const model = structuredClone(testModel);
    model.relationTypes[0].features.parentOf = true;
    const sourceView = model.applications[0].views[0];
    if (sourceView.type !== "table") throw new Error("Expected table fixture");
    model.applications[0].views.push({
      ...sourceView,
      key: "codelists",
      name: "Codelists",
      objectTypeKey: "codelist",
    });
    expect(childCollectionGroups(model, model.applications[0], "domain").map((group) => group.objectTypeKey)).toEqual([
      "codelist",
    ]);
    expect(childCollectionGroups(model, model.applications[0], "codelist")).toEqual([]);
  });
});

describe("relationship model helpers", () => {
  const model = {
    ...testModel,
    relationTypes: [
      ...testModel.relationTypes,
      {
        key: "links",
        reverseKey: "linked-by",
        name: "Links",
        reverseName: "Linked by",
        isOriented: true,
        features: {},
      },
    ],
    objectTypeRelations: [
      ...testModel.objectTypeRelations,
      {
        relationTypeKey: "links",
        fromObjectTypeKey: "domain",
        toObjectTypeKey: "codelist",
        cardinality: "many-to-many" as const,
        attributeTypeKeys: ["active"],
      },
      {
        relationTypeKey: "links",
        fromObjectTypeKey: "domain",
        toObjectTypeKey: "domain",
        cardinality: "many-to-many" as const,
      },
    ],
  };

  it("derives outgoing, incoming and explicit self-relation orientations", () => {
    const outgoing = relationChoices(model, "domain", {
      key: "relations",
      title: "Relations",
      type: "relations",
      region: "main",
      order: 1,
      visible: true,
      config: { relationTypeKeys: ["links"], direction: "both", columns: ["name"] },
    });
    expect(outgoing.map((item) => [item.direction, item.otherObjectTypeKey, item.label])).toEqual([
      ["outgoing", "codelist", "Links"],
      ["outgoing", "domain", "Links"],
      ["incoming", "domain", "Linked by"],
    ]);
    const incoming = relationChoices(model, "codelist", {
      key: "relations",
      title: "Relations",
      type: "relations",
      region: "main",
      order: 1,
      visible: true,
      config: { relationTypeKeys: ["links"], direction: "incoming", columns: ["name"] },
    });
    expect(incoming[0]).toEqual(
      expect.objectContaining({ direction: "incoming", otherObjectTypeKey: "domain", label: "Linked by" }),
    );
  });

  it("recognizes model-maintained containment", () => {
    expect(isManagedRelation(model, model.objectTypeRelations[0])).toBe(true);
    expect(isManagedRelation(model, model.objectTypeRelations[1])).toBe(false);
  });
});

describe("attributeName", () => {
  it("maps built-in column keys to labels", () => {
    expect(attributeName(testModel, "name")).toBe("Name");
    expect(attributeName(testModel, "objectType")).toBe("Type");
  });

  it("resolves attribute type names and falls back to the raw key", () => {
    expect(attributeName(testModel, "code")).toBe("Code");
    expect(attributeName(testModel, "unknown")).toBe("unknown");
  });
});

describe("fieldValue", () => {
  it("reads built-in fields and attached attributes", () => {
    expect(fieldValue(domainObject, "name", testModel)).toBe("Connections");
    expect(fieldValue(domainObject, "objectType", testModel)).toBe("Domain");
    expect(fieldValue(domainObject, "code", testModel)).toBe("CONNECTIONS");
  });

  it("joins path parts into a breadcrumb string", () => {
    expect(fieldValue(codelistObject, "path", testModel)).toBe("Connections / Timetable types");
  });
});

describe("fallbackDetail", () => {
  it("produces the same generic panel shape for two different object types", () => {
    const domain = fallbackDetail(testModel.objectTypes[0], testModel);
    const codelist = fallbackDetail(testModel.objectTypes[1], testModel);
    expect(domain.panels.filter((panel) => panel.region === "side").map((panel) => panel.type)).toEqual(
      codelist.panels.filter((panel) => panel.region === "side").map((panel) => panel.type),
    );
    const children = domain.panels.filter((panel) => panel.type === "children");
    expect(children).toHaveLength(1);
    expect(children[0].config.objectTypeKeys).toEqual(["codelist"]);
    expect(domain.panels.find((panel) => panel.type === "relations")?.config).toMatchObject({ direction: "both" });
    expect(domain.header.titleField).toBe("name");
    expect(codelist.panels[0].type).toBe("attributes");
  });
});
