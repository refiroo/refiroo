import type { ModelDraftOutline } from "@/types";

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
          groups: [{ key: "lists", label: "Lists", collapsed: false, collections: ["bin"], mark: "new" }],
          ungrouped: ["area", "shelf"],
        },
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
