import { describe, expect, it } from "vitest";
import { codelistObject, domainObject, testModel } from "../test/fixtures";
import {
  attributeName,
  defaultRoute,
  fallbackDetail,
  fieldValue,
  objectTypeFor,
  parseRoute,
  routePath,
  relationChoices,
  isManagedRelation,
} from "./model";

describe("objectTypeFor", () => {
  it("resolves a known object type and returns undefined for an unknown key", () => {
    expect(objectTypeFor(testModel, "domain")?.name).toBe("Domain");
    expect(objectTypeFor(testModel, "missing")).toBeUndefined();
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
    expect(attributeName(testModel, "state")).toBe("State");
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
    const domain = fallbackDetail(testModel.objectTypes[0]);
    const codelist = fallbackDetail(testModel.objectTypes[1]);
    expect(domain.panels.map((panel) => panel.type)).toEqual(codelist.panels.map((panel) => panel.type));
    expect(domain.header.titleField).toBe("name");
    expect(codelist.panels[0].type).toBe("attributes");
  });
});

describe("routes", () => {
  it("round-trips the global Models route outside application navigation", () => {
    const models = { kind: "models", releaseId: "release/id" } as const;
    window.history.pushState({}, "", routePath(models));
    expect(routePath(models)).toBe("/models?releaseId=release%2Fid");
    expect(parseRoute(testModel)).toEqual(models);
    window.history.pushState({}, "", "/");
  });

  it("normalizes an ambiguous Models URL to the editable draft", () => {
    window.history.pushState({}, "", "/models?releaseId=r1&draftId=d1");
    expect(parseRoute(testModel)).toEqual({ kind: "models", draftId: "d1" });
    window.history.pushState({}, "", "/");
  });

  it("points the default route at the first application's default view", () => {
    expect(defaultRoute(testModel)).toEqual({
      kind: "list",
      applicationKey: "test-app",
      viewKey: "domains",
      workspaceKey: "default",
      search: "",
      states: [],
      sort: "name",
      pageSize: 20,
    });
  });

  it("round-trips a detail route through routePath and parseRoute", () => {
    const detail = {
      kind: "detail",
      applicationKey: "test-app",
      objectTypeKey: "domain",
      objectId: domainObject.id,
      workspaceKey: "west",
    } as const;
    window.history.pushState({}, "", routePath(detail));
    expect(parseRoute(testModel)).toEqual(detail);
    window.history.pushState({}, "", "/");
  });

  it("restores workspace and collection controls from repeatable URL state", () => {
    window.history.pushState(
      {},
      "",
      "/apps/test-app/views/domains?workspaceKey=west&search=A%26B&state=active&state=draft&sort=-updatedAt&pageSize=50",
    );
    const route = parseRoute(testModel);
    expect(route).toEqual({
      kind: "list",
      applicationKey: "test-app",
      viewKey: "domains",
      workspaceKey: "west",
      search: "A&B",
      states: ["active", "draft"],
      sort: "-updatedAt",
      pageSize: 50,
    });
    expect(routePath(route)).toBe(
      "/apps/test-app/views/domains?workspaceKey=west&search=A%26B&state=active&state=draft&sort=-updatedAt&pageSize=50",
    );
    window.history.pushState({}, "", "/");
  });
});
