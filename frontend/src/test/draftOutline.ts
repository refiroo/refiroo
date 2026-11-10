import type { ConsumerDefinition, ModelDraftOutline } from "@/types";

/** A consumer API definition over the fixture's types, as the draft would hold it (0.10 A4c). */
export function consumerDefinitionFixture(): ConsumerDefinition {
  return {
    key: "shop-feed",
    name: "Shop feed",
    contractVersion: 1,
    exposes: ["shelf", "bin"],
    publicNames: { bin: "StorageBin" },
    object: {
      fields: {
        id: { role: "id" },
        name: { role: "name", from: "name" },
        depth: "depth",
        code: { role: "code", from: ["shelf-code", "bin-code"] },
      },
      related: { bins: { via: "stores", fields: { binName: "name" } } },
    },
    operations: {
      objects: {},
      xref: { matchOn: [{ field: "name", exact: 200 }] },
      lists: { shelves: { of: "shelf" } },
    },
    filters: { kind: { byType: true } },
  };
}

/** A small outline for the editor's tests: a released top-level type with a child, and a new type. */
export function outlineFixture(): ModelDraftOutline {
  return {
    version: 4,
    baseReleaseId: "r1",
    release: { key: "store", name: "Store", version: "1.2.0", schemaVersion: "0.10" },
    baseRelease: { key: "store", name: "Store", version: "1.2.0" },
    applications: [
      {
        key: "shop",
        name: "Shop",
        objectTypeKeys: ["area", "shelf", "bin"],
        tree: [
          { objectType: "area", children: [{ objectType: "shelf", children: [] }] },
          { objectType: "bin", children: [] },
        ],
        navigation: {
          groups: [
            {
              key: "lists",
              label: "Lists",
              collapsed: false,
              collections: ["bin"],
              entries: [{ collection: "bin" }],
              mark: "new",
            },
          ],
          ungrouped: ["area", "shelf"],
          opens: {},
        },
        views: [{ key: "bins", name: "Bins", type: "table", shows: ["bin"], mark: "new" }],
        unlistable: [],
        ownTypes: ["area", "shelf", "bin"],
        ownTree: [
          { objectType: "area", children: [{ objectType: "shelf", children: [] }] },
          { objectType: "bin", children: [] },
        ],
        borrowed: [],
        borrowedTree: [],
        unused: [],
        mark: "changed",
      },
    ],
    objectTypes: [
      {
        key: "area",
        name: "Area",
        pluralName: "Areas",
        rootCreatable: true,
        parents: [],
        attributes: [
          {
            attributeType: "code",
            name: "Code",
            valueType: "text",
            required: true,
            readOnly: false,
            unique: true,
            sharedWith: ["shelf"],
            mark: "released",
          },
        ],
        mark: "changed",
      },
      {
        key: "shelf",
        name: "Shelf",
        pluralName: "Shelves",
        rootCreatable: false,
        parents: ["area"],
        attributes: [
          {
            attributeType: "code",
            name: "Code",
            valueType: "text",
            required: false,
            readOnly: false,
            unique: true,
            sharedWith: ["area"],
            mark: "released",
          },
          {
            attributeType: "depth",
            name: "Depth",
            valueType: "decimal",
            required: false,
            readOnly: false,
            unique: false,
            sharedWith: [],
            mark: "new",
          },
        ],
        mark: "released",
      },
      { key: "bin", name: "Bin", pluralName: "Bins", rootCreatable: true, parents: [], attributes: [], mark: "new" },
    ],
    attributeTypes: [
      {
        key: "code",
        name: "Code",
        valueType: "text",
        features: { unique: true },
        boundBy: ["area", "shelf"],
        mark: "released",
      },
      { key: "depth", name: "Depth", valueType: "decimal", features: {}, boundBy: ["shelf"], mark: "new" },
      { key: "colour", name: "Colour", valueType: "text", features: {}, boundBy: [], mark: "new" },
    ],
    relationTypes: [
      {
        key: "holds",
        reverseKey: "held-by",
        name: "Holds",
        reverseName: "Held by",
        containment: true,
        mark: "released",
      },
      {
        key: "stores",
        reverseKey: "stored-on",
        name: "Stores",
        reverseName: "Stored on",
        containment: false,
        mark: "new",
      },
    ],
    relations: [
      {
        relationType: "holds",
        from: "area",
        to: "shelf",
        cardinality: "one-to-many",
        required: false,
        containment: true,
        mark: "released",
      },
      {
        relationType: "stores",
        from: "shelf",
        to: "bin",
        cardinality: "many-to-one",
        required: false,
        containment: false,
        mark: "new",
      },
    ],
    consumerApis: [
      {
        key: "shop-feed",
        name: "Shop feed",
        contractVersion: 1,
        exposes: [
          { objectType: "shelf", publicName: "Shelf" },
          { objectType: "bin", publicName: "StorageBin" },
        ],
        counts: { fields: 4, related: 1, lists: 1, filters: 1, events: 0 },
        mark: "released",
        contract: null,
      },
    ],
    valid: false,
    diagnostics: [
      {
        severity: "error",
        code: "INVALID_REFERENCE",
        path: "/objectTypes/bin/attributes",
        message: "Bin needs an attribute",
        element: { objectType: "bin" },
      },
    ],
  };
}
