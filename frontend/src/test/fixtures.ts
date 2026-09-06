import type { EngineModel, ObjectItem } from "@/types";

// A minimal two-object-type model used to exercise the generic renderers and helpers. The point of
// the fixture is to prove the code path is model-driven, not to mirror the starter application.
export const testModel: EngineModel = {
  schemaVersion: "0.5",
  release: { key: "test", name: "Test", version: "0.3.0" },
  product: { name: "Test Engine" },
  attributeTypes: [
    {
      key: "code",
      name: "Code",
      valueType: "text",
      features: { filterable: true, sortable: true },
      validation: {},
      ui: {},
    },
    {
      key: "active",
      name: "Active",
      valueType: "boolean",
      default: true,
      features: { filterable: true },
      validation: {},
      ui: {},
    },
  ],
  objectTypes: [
    {
      key: "domain",
      name: "Domain",
      pluralName: "Domains",
      attributes: [
        { attributeTypeKey: "code", required: true, readOnly: false, order: 10, ui: {} },
        { attributeTypeKey: "active", required: false, readOnly: false, order: 20, ui: {} },
      ],
      features: { rootCreatable: true },
      behavior: {},
      validation: {},
    },
    {
      key: "codelist",
      name: "Codelist",
      pluralName: "Codelists",
      attributes: [
        { attributeTypeKey: "code", required: true, readOnly: false, order: 10, ui: {} },
        { attributeTypeKey: "active", required: false, readOnly: false, order: 20, ui: {} },
      ],
      features: { rootCreatable: false },
      behavior: { parentRelationTypeKeys: ["domain-contains-codelist"] },
      validation: {},
    },
  ],
  relationTypes: [
    {
      key: "domain-contains-codelist",
      reverseKey: "codelist-belongs-to-domain",
      name: "Contains",
      reverseName: "Belongs to",
      isOriented: true,
      features: {},
    },
  ],
  objectTypeRelations: [
    {
      relationTypeKey: "domain-contains-codelist",
      fromObjectTypeKey: "domain",
      toObjectTypeKey: "codelist",
      cardinality: "one-to-many",
    },
  ],
  applications: [
    {
      key: "test-app",
      name: "Test App",
      state: "active",
      objectTypeKeys: ["domain", "codelist"],
      defaultView: "domains",
      views: [
        {
          key: "domains",
          name: "Domains",
          type: "table",
          objectTypeKey: "domain",
          config: {
            columns: ["name", "code"],
            filterFields: ["code", "active"],
            sortFields: ["name", "code"],
            defaultSort: "name",
            pageSize: 20,
          },
        },
      ],
      details: [],
      settings: {},
    },
  ],
};

export const domainObject: ObjectItem = {
  id: "11111111-1111-4111-8111-111111111111",
  workspaceKey: "default",
  applicationKey: "test-app",
  objectTypeKey: "domain",
  parentObjectId: null,
  activeRevisionId: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  lifecycle: "active",
  name: "Connections",
  path: [{ id: "11111111-1111-4111-8111-111111111111", name: "Connections", objectTypeKey: "domain" }],
  attributes: [
    {
      id: "33333333-3333-4333-8333-333333333333",
      attributeTypeKey: "code",
      name: "Code",
      valueType: "text",
      value: "CONNECTIONS",
    },
    {
      id: "44444444-4444-4444-8444-444444444444",
      attributeTypeKey: "active",
      name: "Active",
      valueType: "boolean",
      value: true,
    },
  ],
  version: 1,
  createdAt: "2026-09-02T00:00:00Z",
  updatedAt: "2026-09-02T00:00:00Z",
};

export const codelistObject: ObjectItem = {
  ...domainObject,
  id: "22222222-2222-4222-8222-222222222222",
  objectTypeKey: "codelist",
  name: "Timetable types",
  path: [
    { id: "11111111-1111-4111-8111-111111111111", name: "Connections", objectTypeKey: "domain" },
    { id: "22222222-2222-4222-8222-222222222222", name: "Timetable types", objectTypeKey: "codelist" },
  ],
  attributes: [
    {
      id: "55555555-5555-4555-8555-555555555555",
      attributeTypeKey: "code",
      name: "Code",
      valueType: "text",
      value: "MOT",
    },
    {
      id: "66666666-6666-4666-8666-666666666666",
      attributeTypeKey: "active",
      name: "Active",
      valueType: "boolean",
      value: false,
    },
  ],
};
