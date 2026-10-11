import { describe, expect, it } from "vitest";
import { outlineFixture } from "@/test/draftOutline";
import {
  initialValues,
  missingField,
  needsMigration,
  OPERATIONS,
  operationById,
  operationsFor,
  visibleFields,
  type FieldValues,
  type OperationTarget,
} from "@/features/model-editor/operations";
import { keyFromLabel, suggestedVersion } from "@/features/model-editor/outline";

/** Every model-side kind A4a may send (API.md § Kinds, without the view verbs, A4b's). */
const KINDS = new Set([
  "setLabel",
  "setKey",
  "setRelease",
  "addApplication",
  "removeApplication",
  "addObjectType",
  "removeObjectType",
  "splitObjectType",
  "mergeObjectTypes",
  "convertAttributeToListType",
  "addAttributeType",
  "removeAttributeType",
  "setAttributeTypeFeatures",
  "setValueType",
  "attachAttribute",
  "detachAttribute",
  "moveAttribute",
  "setAttributeBinding",
  "setContainment",
  "addRelationType",
  "removeRelationType",
  "allowRelation",
  "disallowRelation",
  "setRelationRule",
  "addNavigationGroup",
  "removeNavigationGroup",
  "setNavigationGroup",
  "placeCollection",
]);

const outline = outlineFixture();
const TARGETS: Record<OperationTarget["on"], OperationTarget> = {
  draft: { on: "draft" },
  application: { on: "application", applicationKey: "shop" },
  objectType: { on: "objectType", objectType: "shelf" },
  attribute: { on: "attribute", objectType: "shelf", attributeType: "depth" },
  attributeType: { on: "attributeType", attributeType: "colour" },
  relationType: { on: "relationType", relationType: "stores" },
  relation: { on: "relation", relationType: "stores", from: "shelf", to: "bin" },
  group: { on: "group", applicationKey: "shop", group: "lists" },
};

/** The form as a user completes it: the descriptor's starting values, every empty required field filled. */
function completed(id: string, target: OperationTarget): FieldValues {
  const operation = operationById(id)!;
  const values = initialValues(operation, target, outline);
  for (let guard = 0; guard < 10; guard += 1) {
    const missing = missingField(operation, target, outline, values);
    if (!missing) break;
    values[missing.name] = missing.type === "select" ? (missing.options[0]?.value ?? "x") : `Filled ${missing.name}`;
  }
  return values;
}

describe("the editor's operation descriptors (D38)", () => {
  it.each(OPERATIONS.filter((item) => !item.move).map((item) => [item.id, item.on] as const))(
    "%s builds requests of known kinds with no empty parameter",
    (id, on) => {
      const operation = operationById(id)!;
      const target = TARGETS[on];
      const operations = operation.build(completed(id, target), target as never, outline);
      expect(operations.length).toBeGreaterThan(0);
      for (const item of operations) {
        expect(KINDS).toContain(item.kind);
        for (const [name, value] of Object.entries(item)) {
          if (value === null) continue; // a `parent` or `group` of null means the top level.
          expect(value, `${item.kind}.${name}`).not.toBe("");
        }
      }
    },
  );

  it("adds a new attribute and attaches it in one step, under the key it names", () => {
    const [add, attach] = operationById("type-new-attribute")!.build(
      { name: "Depth", valueType: "decimal", features: ["sortable"], required: true },
      { on: "objectType", objectType: "bin" } as never,
      outline,
    );
    // "depth" is taken, so the key the server would generate (A-D6) is the next free one.
    expect(add).toEqual({
      kind: "addAttributeType",
      key: "depth-2",
      name: "Depth",
      valueType: "decimal",
      features: { sortable: true },
    });
    expect(attach).toEqual({ kind: "attachAttribute", objectType: "bin", attributeType: "depth-2", required: true });
  });

  it("allows a relation of a new relation type in the same step, or of an existing one", () => {
    const build = operationById("type-allow")!.build;
    const target = { on: "objectType", objectType: "bin" } as never;
    const created = build(
      { relationType: "__new__", name: "Stores", reverseName: "Stored on", to: "area", cardinality: "many-to-one" },
      target,
      outline,
    );
    expect(created.map((item) => item.kind)).toEqual(["addRelationType", "allowRelation"]);
    expect(created[0]).toMatchObject({ key: "stores-2", reverseKey: "stored-on-2" });
    expect(created[1]).toMatchObject({
      relationType: "stores-2",
      from: "bin",
      to: "area",
      cardinality: "many-to-one",
      required: false,
    });
    expect(build({ relationType: "stores", to: "area", cardinality: "one-to-one" }, target, outline)).toEqual([
      {
        kind: "allowRelation",
        relationType: "stores",
        from: "bin",
        to: "area",
        cardinality: "one-to-one",
        required: false,
      },
    ]);
  });

  it("turns an attribute into a list type with which of its records may be chosen, in one step", () => {
    const [convert, rule] = operationById("attribute-list")!.build(
      {
        name: "Colour",
        relationName: "Has colour",
        reverseName: "Colour of",
        candidates: { to: [{ field: "name", op: "startsWith", value: "R" }] },
      },
      { on: "attribute", objectType: "shelf", attributeType: "depth" } as never,
      outline,
    );
    expect(convert).toMatchObject({
      kind: "convertAttributeToListType",
      key: "colour-2",
      relationType: { key: "has-colour", reverseKey: "colour-of", name: "Has colour", reverseName: "Colour of" },
    });
    expect(rule).toEqual({
      kind: "setRelationRule",
      relationType: "has-colour",
      from: "shelf",
      to: "colour-2",
      candidates: { to: [{ field: "name", op: "startsWith", value: "R" }] },
    });
  });

  it("removes a parent link too, saying where the child type is left", () => {
    const remove = operationById("relation-remove")!;
    const target = { on: "relation", relationType: "holds", from: "area", to: "shelf" } as never;
    expect(remove.build({}, target, outline)).toEqual([
      { kind: "disallowRelation", relationType: "holds", from: "area", to: "shelf" },
    ]);
    expect(remove.confirm!(target, outline)).toBe(
      "Stop placing Shelf under Area (Holds)? Shelf then has no place to stand, and the draft shows an issue until you place it with Move to….",
    );
  });

  it("removes a relation type in use with the pairs that allow it, in one step", () => {
    const remove = operationById("relation-type-remove")!;
    const target = { on: "relationType", relationType: "stores" } as never;
    expect(remove.build({}, target, outline)).toEqual([
      { kind: "disallowRelation", relationType: "stores", from: "shelf", to: "bin" },
      { kind: "removeRelationType", relationType: "stores" },
    ]);
    expect(remove.confirm!(target, outline)).toBe("Remove Stores, and stop allowing it between Shelf → Bin?");
  });

  it("removes a relationship's criteria when none is left", () => {
    expect(
      operationById("relation-candidates")!.build(
        { candidates: {} },
        { on: "relation", relationType: "stores", from: "shelf", to: "bin" } as never,
        outline,
      ),
    ).toEqual([{ kind: "setRelationRule", relationType: "stores", from: "shelf", to: "bin", candidates: null }]);
  });

  it("places a type under a parent with a new containment relation, or at the top level", () => {
    const build = operationById("add-type")!.build;
    expect(
      build(
        { applicationKey: "shop", name: "Box", parent: "", relationType: "__new__" },
        { on: "draft" } as never,
        outline,
      ),
    ).toEqual([{ kind: "addObjectType", applicationKey: "shop", name: "Box", parent: null }]);
    expect(
      build(
        {
          applicationKey: "shop",
          name: "Box",
          parent: "shelf",
          relationType: "__new__",
          relationName: "Has box",
          reverseName: "In shelf",
        },
        { on: "draft" } as never,
        outline,
      )[0],
    ).toMatchObject({ parent: { objectTypes: ["shelf"], relationType: { name: "Has box", reverseName: "In shelf" } } });
  });

  it("asks for the containment relation only once a parent is chosen", () => {
    const operation = operationById("add-type")!;
    const names = (values: FieldValues) =>
      visibleFields(operation, { on: "draft" }, outline, values).map((field) => field.name);
    expect(names({ parent: "" })).not.toContain("relationName");
    expect(names({ parent: "area", relationType: "__new__" })).toEqual(
      expect.arrayContaining(["relationName", "reverseName"]),
    );
    expect(names({ parent: "area", relationType: "holds" })).not.toContain("relationName");
  });

  it("places a collection in a group of its application, or back at the top of the sidebar", () => {
    const build = operationById("type-group")!.build;
    const target = { on: "objectType", objectType: "area" } as never;
    expect(build({ group: "shop\u0000lists", applicationKey: "shop" }, target, outline)).toEqual([
      { kind: "placeCollection", applicationKey: "shop", collection: "area", group: "lists" },
    ]);
    expect(build({ group: "", applicationKey: "shop" }, target, outline)).toEqual([
      { kind: "placeCollection", applicationKey: "shop", collection: "area", group: null },
    ]);
  });

  it("marks a draft-only operation as needing a migration only on a released element (D39)", () => {
    const rename = operationById("type-rename")!;
    const key = operationById("type-key")!;
    expect(needsMigration(key, { on: "objectType", objectType: "shelf" }, outline)).toBe(true);
    expect(needsMigration(key, { on: "objectType", objectType: "bin" }, outline)).toBe(false);
    expect(needsMigration(rename, { on: "objectType", objectType: "shelf" }, outline)).toBe(false);
    const detach = operationById("attribute-detach")!;
    expect(needsMigration(detach, { on: "attribute", objectType: "shelf", attributeType: "code" }, outline)).toBe(true);
    expect(needsMigration(detach, { on: "attribute", objectType: "shelf", attributeType: "depth" }, outline)).toBe(
      false,
    );
  });

  it("offers only what applies to the element", () => {
    const ids = (target: OperationTarget) => operationsFor(target, outline).map((item) => item.id);
    expect(ids({ on: "attribute", objectType: "shelf", attributeType: "code" })).not.toContain("attribute-up");
    expect(ids({ on: "attribute", objectType: "shelf", attributeType: "depth" })).not.toContain("attribute-down");
    expect(ids({ on: "attributeType", attributeType: "code" })).not.toContain("attribute-type-remove");
    expect(ids({ on: "attributeType", attributeType: "colour" })).toContain("attribute-type-remove");
    expect(ids({ on: "relation", relationType: "holds", from: "area", to: "shelf" })).toContain("relation-remove");
    expect(ids({ on: "relationType", relationType: "stores" })).toContain("relation-type-remove");
  });
});

describe("keys and versions", () => {
  it.each([
    ["Café Größe", new Set<string>(), "cafe-groe"],
    ["  Shelf code ", new Set(["shelf-code"]), "shelf-code-2"],
    ["Shelf code", new Set(["shelf-code", "shelf-code-2"]), "shelf-code-3"],
    ["!!!", new Set<string>(), "element"],
  ])("makes the key of %j (A-D6)", (label, taken, key) => {
    expect(keyFromLabel(label, taken)).toBe(key);
  });

  it("proposes the base version with its last number raised, or the draft's own (D18)", () => {
    expect(suggestedVersion(outline)).toBe("1.2.1");
    expect(suggestedVersion({ ...outline, release: { ...outline.release, version: "2.0.0" } })).toBe("2.0.0");
    expect(
      suggestedVersion({ ...outline, release: { version: "2026.10-rc3" }, baseRelease: { version: "2026.10-rc3" } }),
    ).toBe("2026.10-rc4");
    expect(suggestedVersion({ ...outline, baseRelease: null, release: { version: "1.0.0" } })).toBe("1.0.0");
  });
});
