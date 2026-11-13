import { describe, expect, it } from "vitest";
import { consumerDefinitionFixture, outlineFixture } from "@/test/draftOutline";
import {
  fieldOptions,
  initialValues,
  missingField,
  needsMigration,
  OPERATIONS,
  operationById,
  operationTargetKinds,
  operationsFor,
  visibleFields,
  type FieldValues,
  type OperationField,
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
  "setCollectionOpening",
  "addView",
  "removeView",
  "setViewProperty",
  "listObjectType",
  "unlistObjectType",
  // The settings a model holds (0.13 ED).
  "setObjectTypeProperty",
  "setAttributeTypeProperty",
  "setRelationTypeProperty",
  "setApplicationProperty",
  // The consumer API kinds (0.10 A4c, D51).
  "addConsumerApi",
  "removeConsumerApi",
  "setConsumerApiPart",
  "insertConsumerApiPart",
  "moveConsumerApiPart",
  "removeConsumerApiPart",
  "raiseConsumerApiVersion",
  "removeConsumerApiVersion",
  "setConsumerApiSunset",
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
  view: { on: "view", applicationKey: "shop", view: "bins" },
  group: { on: "group", applicationKey: "shop", group: "lists" },
  groupEntry: { on: "groupEntry", applicationKey: "shop", group: "lists", collection: "bin" },
  consumerApis: { on: "consumerApis" },
  consumerApi: { on: "consumerApi", consumerApi: "shop-feed", definition: consumerDefinitionFixture() },
  consumerItem: {
    on: "consumerItem",
    consumerApi: "shop-feed",
    pointer: "/object/fields/depth",
    label: "field depth",
    index: 2,
    count: 4,
    value: "depth",
  },
};

/** Descriptors that send only what a person changed, and are tried on their own below. */
const SENDS_WHAT_CHANGED = new Set(["attribute-type-limits", "view-tree-change", "view-grid-change"]);

/** The form as a user completes it: the descriptor's starting values, every empty required field filled. */
function completed(id: string, target: OperationTarget): FieldValues {
  const operation = operationById(id)!;
  const values = initialValues(operation, target, outline);
  for (let guard = 0; guard < 10; guard += 1) {
    const missing = missingField(operation, target, outline, values);
    if (!missing) break;
    values[missing.name] =
      missing.type === "select"
        ? (fieldOptions(missing, values)[0]?.value ?? "x")
        : missing.type === "choices" || missing.type === "pairs" || missing.type === "checkboxes"
          ? [fieldOptions(missing, values)[0]?.value ?? "x"]
          : `Filled ${missing.name}`;
  }
  return values;
}

describe("the editor's operation descriptors (D38)", () => {
  it.each(
    OPERATIONS.filter((item) => !item.move && !SENDS_WHAT_CHANGED.has(item.id)).map(
      (item) => [item.id, item.on] as const,
    ),
  )("%s builds requests of known kinds with no empty parameter", (id, on) => {
    const operation = operationById(id)!;
    const target = TARGETS[on];
    const operations = operation.build(completed(id, target), target as never, outline);
    expect(operations.length).toBeGreaterThan(0);
    for (const item of operations) {
      expect(KINDS).toContain(item.kind);
      for (const [name, value] of Object.entries(item)) {
        if (value === null) continue; // a `parent` or `group` of null means the top level.
        if (item.kind === "setConsumerApiPart" && name === "pointer") continue; // "" is the whole definition (D51).
        expect(value, `${item.kind}.${name}`).not.toBe("");
      }
    }
  });

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

  it("sets a type's display attribute, effective period, at-least-one rule and parent relationships", () => {
    const type: OperationTarget = { on: "objectType", objectType: "shelf" };
    const build = (id: string, values: FieldValues) => operationById(id)!.build(values, type as never, outline);
    expect(build("type-display-attribute", { attribute: "code" })).toEqual([
      { kind: "setObjectTypeProperty", objectType: "shelf", property: "displayAttributeTypeKey", value: "code" },
    ]);
    expect(build("type-display-attribute", { attribute: "" })[0].value).toBeNull();
    expect(build("type-at-least-one", { attributes: ["code", "depth"] })[0]).toMatchObject({
      property: "atLeastOneOf",
      value: ["code", "depth"],
    });
    expect(build("type-at-least-one", { attributes: [] })[0].value).toBeNull();
    expect(build("type-effective-period", { start: "code", end: "depth" })[0].value).toEqual({
      startAttributeTypeKey: "code",
      endAttributeTypeKey: "depth",
    });
    expect(build("type-effective-period", { start: "", end: "depth" })[0].value).toBeNull();
    expect(build("type-parent-relations", { relations: ["holds"] })[0]).toMatchObject({
      property: "parentRelationTypeKeys",
      value: ["holds"],
    });
    // The relationships allowed to the type are what it offers as parents.
    const field = operationById("type-parent-relations")!.fields!(type as never, outline)[0];
    expect(fieldOptions(field as never, {}).map((item) => item.value)).toEqual(["holds"]);
    expect(needsMigration(operationById("type-parent-relations")!, type, outline)).toBe(true);
  });

  it("sets a number type's bounds, sending only what changed and the looser bound first", () => {
    const target: OperationTarget = { on: "attributeType", attributeType: "depth" };
    const limits = operationById("attribute-type-limits")!;
    expect(operationsFor(target, outline).includes(limits)).toBe(true);
    expect(operationsFor({ on: "attributeType", attributeType: "colour" }, outline)).not.toContain(limits);
    expect(limits.build({ minimum: "2", maximum: "" }, target as never, outline)).toEqual([
      { kind: "setAttributeTypeProperty", attributeType: "depth", property: "minimum", value: 2 },
    ]);
    expect(limits.build({ minimum: "", maximum: "" }, target as never, outline)).toEqual([]);
    const bounded = {
      ...outline,
      attributeTypes: outline.attributeTypes.map((item) =>
        item.key === "depth" ? { ...item, minimum: 1, maximum: 5 } : item,
      ),
    };
    // Both raised above the old maximum: the maximum goes first, or the new minimum would be refused.
    expect(limits.build({ minimum: "8", maximum: "9" }, target as never, bounded).map((item) => item.property)).toEqual(
      ["maximum", "minimum"],
    );
    expect(limits.build({ minimum: "0", maximum: "3" }, target as never, bounded).map((item) => item.property)).toEqual(
      ["minimum", "maximum"],
    );
  });

  it("chooses the attributes a relationship carries", () => {
    const [step] = operationById("relation-attributes")!.build(
      { attributes: ["colour"] },
      TARGETS.relation as never,
      outline,
    );
    expect(step).toEqual({
      kind: "setRelationRule",
      relationType: "stores",
      from: "shelf",
      to: "bin",
      attributeTypeKeys: ["colour"],
    });
  });

  it("starts every view form with its name, for each kind and when the view is changed", () => {
    const add = operationById("application-add-view")!;
    const target = TARGETS.application as never;
    for (const kind of ["table", "tree", "mappingGrid", "relationMatrix", "relationTable"]) {
      const shown = visibleFields(add, TARGETS.application, outline, { kind });
      expect(shown.filter((field) => field.name === "name")).toHaveLength(1);
      expect(shown[0]).toMatchObject({ name: "name", markEmpty: true });
    }
    for (const id of ["view-matrix-change", "view-tree-change", "view-grid-change"]) {
      expect(
        operationById(id)!.fields!({ on: "view", applicationKey: "shop", view: "v" } as never, outline)[0]?.name,
      ).toBe("name");
    }
    expect(add.fields!(target, outline)).toBeTruthy();
  });

  it("adds a table, a tree and a mapping grid to an application, listing the types they need", () => {
    const add = operationById("application-add-view")!;
    const target = TARGETS.application;
    const offered = fieldOptions(
      add.fields!(target as never, outline).find((field) => field.name === "kind") as never,
      {},
    ).map((item) => item.value);
    expect(offered).toEqual(expect.arrayContaining(["table", "tree", "mappingGrid"]));
    expect(add.build({ kind: "table", type: "bin", name: "All bins" }, target as never, outline)).toEqual([
      {
        kind: "addView",
        applicationKey: "shop",
        view: { key: "all-bins", name: "All bins", type: "table", objectTypeKey: "bin" },
      },
    ]);
    const [tree] = add.build(
      { kind: "tree", name: "Shelves", roots: ["area"], label: "name", secondary: "", order: "name", availability: "" },
      target as never,
      outline,
    );
    expect(tree).toMatchObject({
      kind: "addView",
      view: {
        type: "tree",
        config: {
          rootObjectTypeKeys: ["area"],
          objectTypeKeys: ["area", "shelf"],
          labelField: "name",
          childSort: { shelf: "name" },
          actions: [],
          availabilityField: null,
        },
      },
    });
    const [grid] = add.build(
      {
        kind: "mappingGrid",
        name: "Bin matching",
        binding: "stores|shelf|bin",
        rows: "from",
        sourceColumns: ["name"],
        targetColumns: ["name"],
        search: ["name"],
      },
      target as never,
      outline,
    );
    expect(grid).toMatchObject({
      view: {
        type: "mappingGrid",
        config: {
          relationTypeKey: "stores",
          fromObjectTypeKey: "shelf",
          toObjectTypeKey: "bin",
          direction: "outgoing",
        },
      },
    });
    // A grid's row columns offer the types above the rows, as a matrix's do.
    const columns = add.fields!(target as never, outline).find((field) => field.name === "sourceColumns")!;
    expect(
      fieldOptions(columns as never, { binding: "stores|shelf|bin", rows: "from" }).filter((item) =>
        String(item.value).startsWith("ancestor:"),
      ),
    ).toEqual([expect.objectContaining({ value: "ancestor:area", label: "Area" })]);
    // The matrix is still one of the kinds, with the preview beside it; the others have none.
    expect(add.preview!({ kind: "tree" }, target as never, outline)).toBeUndefined();
  });

  it("Layout… opens on the current layout of a relationships table", () => {
    const withTable = (layout: string | undefined) => ({
      ...outline,
      applications: [
        {
          ...outline.applications[0],
          views: [
            {
              key: "links",
              name: "Links",
              type: "relationTable",
              shows: ["area", "shelf"],
              config: { fromObjectTypeKey: "area", toObjectTypeKey: "shelf", ...(layout ? { layout } : {}) },
              mark: "new" as const,
            },
          ],
        },
      ],
    });
    const target: OperationTarget = { on: "view", applicationKey: "shop", view: "links" };
    const layout = operationById("view-table-layout")!;
    expect(initialValues(layout, target, withTable("grid"))).toMatchObject({ layout: "grid" });
    expect(initialValues(layout, target, withTable(undefined))).toMatchObject({ layout: "rows" });
  });

  it("changes a tree or a mapping grid property by property", () => {
    const withTree = {
      ...outline,
      applications: [
        {
          ...outline.applications[0],
          views: [
            {
              key: "shelves",
              name: "Shelves",
              type: "tree",
              shows: ["area", "shelf"],
              config: {
                rootObjectTypeKeys: ["area"],
                objectTypeKeys: ["area", "shelf"],
                labelField: "name",
                secondaryField: null,
                childSort: { shelf: "name" },
                pageSize: 50,
                actions: [],
                availabilityField: null,
              },
              mark: "new" as const,
            },
          ],
        },
      ],
    };
    const target: OperationTarget = { on: "view", applicationKey: "shop", view: "shelves" };
    const change = operationById("view-tree-change")!;
    // A tree needs a top: with none ticked the dialog cannot be applied (found in the ED try).
    expect(
      missingField(change, target, withTree, { name: "Shelves", roots: [], label: "code", order: "name" })?.name,
    ).toBe("roots");
    expect(operationsFor(target, withTree)).toContain(change);
    expect(
      change
        .build(
          { name: "Shelves", roots: ["area"], label: "code", secondary: "", order: "name", availability: "" },
          target as never,
          withTree,
        )
        .map((item) => [item.property, item.value]),
    ).toEqual([["labelField", "code"]]);
  });

  it("changing a tree keeps its declared actions and per-type orders", () => {
    const tree = (config: Record<string, unknown>) => ({
      ...outline,
      applications: [
        {
          ...outline.applications[0],
          views: [
            {
              key: "shelves",
              name: "Shelves",
              type: "tree",
              shows: ["area", "shelf"],
              config: {
                rootObjectTypeKeys: ["area"],
                objectTypeKeys: ["area", "shelf"],
                labelField: "name",
                secondaryField: null,
                childSort: { shelf: "-code" },
                pageSize: 50,
                actions: ["createChild", "rename", "move"],
                availabilityField: null,
                ...config,
              },
              mark: "new" as const,
            },
          ],
        },
      ],
    });
    const target: OperationTarget = { on: "view", applicationKey: "shop", view: "shelves" };
    const change = operationById("view-tree-change")!;
    const values = { name: "Shelves", roots: ["area"], label: "name", secondary: "", order: "code", availability: "" };
    const model = tree({});
    // Nothing changed in the form: nothing is sent, so the descending order and the actions stay.
    expect(change.build(values, target as never, model)).toEqual([]);
    // A new label moves only the label.
    expect(
      change.build({ ...values, label: "code" }, target as never, model).map((item) => [item.property, item.value]),
    ).toEqual([["labelField", "code"]]);
    // An availability field adds its action to the declared ones and removes it again.
    const withField = tree({ actions: ["createChild", "setAvailability"], availabilityField: "open" });
    expect(
      change
        .build({ ...values, availability: "open" }, target as never, tree({ availabilityField: "open" }))
        .map((item) => [item.property, item.value]),
    ).toEqual([["actions", ["createChild", "rename", "move", "setAvailability"]]]);
    expect(
      change
        .build({ ...values, availability: "" }, target as never, withField)
        .map((item) => [item.property, item.value]),
    ).toEqual([
      ["actions", ["createChild"]],
      ["availabilityField", null],
    ]);
    // A new order replaces the sort of the types but keeps a type's descending direction.
    expect(
      change.build({ ...values, order: "name" }, target as never, model).map((item) => [item.property, item.value]),
    ).toEqual([["childSort", { shelf: "-name" }]]);
  });

  it("tells apart types and relation types that share a name, with what each is for", () => {
    const named: typeof outline = {
      ...outline,
      applications: [
        { ...outline.applications[0], key: "a", name: "Sales", objectTypeKeys: ["lang", "text"] },
        { ...outline.applications[0], key: "b", name: "Stock", objectTypeKeys: ["lang-2", "text"] },
      ],
      objectTypes: [
        { ...outline.objectTypes[0], key: "lang", name: "Language" },
        { ...outline.objectTypes[0], key: "lang-2", name: "language" },
        { ...outline.objectTypes[0], key: "text", name: "Text" },
        { ...outline.objectTypes[0], key: "item", name: "Item" },
      ],
      relationTypes: [
        { key: "has-text", name: "Has text", reverseName: "Text of", containment: false, mark: "released" },
        { key: "has-text-2", name: "Has text", reverseName: "Text of", containment: false, mark: "new" },
        { key: "other", name: "Other", containment: false, mark: "new" },
      ],
      relations: [
        {
          relationType: "has-text",
          from: "item",
          to: "text",
          required: true,
          uniquePer: "lang",
          containment: false,
          mark: "released",
        },
        { relationType: "has-text-2", from: "item", to: "lang-2", required: false, containment: false, mark: "new" },
      ],
    };
    const fields = operationById("type-allow")!.fields!({ on: "objectType", objectType: "item" } as never, named);
    const to = fields.find((field) => field.name === "to") as Extract<OperationField, { type: "select" }>;
    const relation = fields.find((field) => field.name === "relationType") as Extract<
      OperationField,
      { type: "select" }
    >;

    expect(fieldOptions(to, {}).map((option) => option.label)).toEqual([
      "Language · Sales",
      "language · Stock",
      "Text",
      "Item",
    ]);
    expect(fieldOptions(relation, { to: "text" }).slice(0, 2)).toEqual([
      { value: "__new__", label: "A new relation type" },
      { value: "has-text", label: "Has text: Item → Text", group: "Already reaching Text" },
    ]);
    const hint = relation.hint as (values: FieldValues) => string;
    expect(hint({ to: "text", relationType: "has-text" })).toContain("Item → Text (required, one per Language)");
    expect(hint({ to: "text", relationType: "__new__" })).toContain("stands apart");
    expect((to.hint as (values: FieldValues) => string)({ to: "lang-2" })).toContain("key is lang-2");
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

  it("says what Remove group does to views only when the group holds some", () => {
    const confirm = operationById("group-remove")!.confirm!;
    const target = { on: "group", applicationKey: "shop", group: "lists" } as never;
    expect(confirm(target, outline)).toMatch(/top of the sidebar\.$/);
    const withMatrix = structuredClone(outline);
    withMatrix.applications[0].navigation.groups[0].entries.push({ view: "bins-by-shelf" });
    expect(confirm(target, withMatrix)).toContain("views go back inside their source type's entry");
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

describe("the consumer API descriptors (0.10 A4c, D51)", () => {
  const api = TARGETS.consumerApi as never;

  it("adds a field at the end of the fields, written in its shortest form", () => {
    const [insert] = operationById("consumer-add-field")!.build(
      { output: "label", sources: "name, shelf-code", role: "" },
      api,
      outline,
    );
    expect(insert).toEqual({
      kind: "insertConsumerApiPart",
      consumerApi: "shop-feed",
      pointer: "/object/fields",
      key: "label",
      value: ["name", "shelf-code"],
    });
  });

  it("raises the contract version by one, and adds a related block over a relation of an exposed type", () => {
    expect(operationById("consumer-raise")!.label(api, outline)).toBe("Raise contract version to 2");
    // The previous version stays served beside the new one unless the author stops it (DF3).
    expect(operationById("consumer-raise")!.build({}, api, outline)).toEqual([
      { kind: "raiseConsumerApiVersion", consumerApi: "shop-feed" },
    ]);
    expect(operationById("consumer-raise-drop")!.build({}, api, outline)).toEqual([
      { kind: "raiseConsumerApiVersion", consumerApi: "shop-feed", keep: false },
    ]);
    const via = visibleFields(operationById("consumer-add-related")!, TARGETS.consumerApi, outline, {}).find(
      (field) => field.name === "via",
    );
    // Shelf is reached by its containment's reverse, and starts and ends Stores.
    expect(via?.type === "select" && fieldOptions(via, {}).map((option) => option.value)).toEqual([
      "held-by",
      "stores",
      "stored-on",
    ]);
  });

  it("sets the sunset day of an earlier version and stops serving it, offered on that version's row only", () => {
    const row = (pointer: string) =>
      ({
        on: "consumerItem",
        consumerApi: "shop-feed",
        pointer,
        label: "version 1",
        index: 0,
        count: 1,
        value: { contractVersion: 1, sunset: "2027-06-30" },
      }) as never;
    const offered = (pointer: string) => operationsFor(row(pointer), outline).map((item) => item.id);
    expect(offered("/earlierVersions/0")).toEqual(
      expect.arrayContaining(["consumer-version-sunset", "consumer-version-stop"]),
    );
    expect(offered("/object/fields/code")).not.toContain("consumer-version-stop");
    expect(
      operationById("consumer-version-sunset")!.build({ sunset: "2027-12-31" }, row("/earlierVersions/0"), outline),
    ).toEqual([{ kind: "setConsumerApiSunset", consumerApi: "shop-feed", version: 1, sunset: "2027-12-31" }]);
    expect(operationById("consumer-version-sunset")!.build({ sunset: "" }, row("/earlierVersions/0"), outline)).toEqual(
      [{ kind: "setConsumerApiSunset", consumerApi: "shop-feed", version: 1, sunset: null }],
    );
    expect(operationById("consumer-version-stop")!.build({}, row("/earlierVersions/0"), outline)).toEqual([
      { kind: "removeConsumerApiVersion", consumerApi: "shop-feed", version: 1 },
    ]);
  });

  it("starts the events with a custom event when the definition declares none", () => {
    const build = operationById("consumer-add-event")!.build;
    const values = { key: "depth-changed", objectTypes: ["shelf"], changes: ["updated"], watch: "depth, bins" };
    expect(build(values, api, outline)).toEqual([
      {
        kind: "setConsumerApiPart",
        consumerApi: "shop-feed",
        pointer: "/operations/events",
        value: {
          custom: [
            {
              key: "depth-changed",
              objectTypes: ["shelf"],
              changes: ["updated"],
              watch: { fields: ["depth"], related: ["bins"] },
            },
          ],
        },
      },
    ]);
  });

  it("builds a filter from its verb with only the parts that verb takes", () => {
    const build = operationById("consumer-add-filter")!.build;
    expect(
      build({ name: "where", verb: "under", types: ["shelf"], matchOn: "", through: "itself" }, api, outline),
    ).toEqual([
      {
        kind: "insertConsumerApiPart",
        consumerApi: "shop-feed",
        pointer: "/filters",
        key: "where",
        value: { under: ["shelf"] },
      },
    ]);
    expect(
      build(
        { name: "bin", verb: "onRelated", related: "bins", matchOn: "binName", options: ["crosswalk"] },
        api,
        outline,
      )[0],
    ).toMatchObject({ value: { onRelated: "bins", matchOn: ["binName"], crosswalk: true } });
  });

  it("offers a field's sources from what the exposed types and the types above them hold, in order", () => {
    const options = visibleFields(operationById("consumer-add-field")!, TARGETS.consumerApi, outline, {}).find(
      (field) => field.name === "sources",
    );
    expect(options?.type).toBe("choices");
    const values = options?.type === "choices" ? fieldOptions(options, {}).map((option) => option.value) : [];
    // Name first, then the exposed types' attributes, then what a type above them holds.
    expect(values[0]).toBe("name");
    expect(values).toContain("depth");
    expect(values).toContain("ancestor:area.name");
    const [insert] = operationById("consumer-add-field")!.build(
      { output: "label", sources: ["depth", "name"], role: "" },
      api,
      outline,
    );
    expect(insert).toMatchObject({ key: "label", value: ["depth", "name"] });
  });

  it("changes a field's sources in their chosen order, keeping its role and default", () => {
    const code = {
      ...(TARGETS.consumerItem as object),
      pointer: "/object/fields/code",
      label: "field code",
      value: { role: "code", from: ["shelf-code", "bin-code"] },
    } as OperationTarget;
    const sources = operationById("consumer-field-sources")!;
    expect(operationsFor(code, outline)).toContain(sources);
    expect(initialValues(sources, code, outline)).toEqual({ sources: ["shelf-code", "bin-code"] });
    expect(sources.build({ sources: ["bin-code", "shelf-code"] }, code as never, outline)).toEqual([
      {
        kind: "setConsumerApiPart",
        consumerApi: "shop-feed",
        pointer: "/object/fields/code",
        value: { from: ["bin-code", "shelf-code"], role: "code" },
      },
    ]);
    const id = { ...(code as object), pointer: "/object/fields/id", value: { role: "id" } } as OperationTarget;
    expect(operationsFor(id, outline)).not.toContain(sources);
  });

  it("offers field names from lists wherever a dialog asks for one (the user, A4c)", () => {
    const typed = OPERATIONS.filter((item) => item.id.startsWith("consumer-"))
      .flatMap((item) => {
        const target = TARGETS[item.on];
        return (item.fields?.(target as never, outline) ?? []).map((field) => ({ id: item.id, field }));
      })
      .filter(({ field }) => field.type === "text")
      .map(({ id, field }) => `${id}.${field.name}`);
    // What is still typed is a name the author gives or a number, never a field name.
    expect(typed.sort()).toEqual(
      [
        "consumer-add.key",
        "consumer-add.name",
        "consumer-add-event.key",
        "consumer-add-field.output",
        "consumer-add-filter.name",
        "consumer-add-list.key",
        "consumer-add-parent-related.output",
        "consumer-add-related.output",
        "consumer-add-rule.contains",
        "consumer-add-rule.exact",
        "consumer-add-through.contains",
        "consumer-add-through.exact",
        "consumer-describe.description",
        "consumer-key.key",
        "consumer-rename.name",
        "consumer-version-sunset.sunset",
      ].sort(),
    );
  });

  it("offers an XREF rule the exposed types' id, name, code and searchable or unique attributes", () => {
    const field = visibleFields(operationById("consumer-add-rule")!, TARGETS.consumerApi, outline, {}).find(
      (item) => item.name === "field",
    )!;
    const values = field.type === "select" ? fieldOptions(field, {}).map((option) => option.value) : [];
    expect(values.slice(0, 3)).toEqual(["id", "name", "code"]);
  });

  it("offers a related block the fields of the records it reaches, and writes them as output and source", () => {
    const operation = operationById("consumer-add-related")!;
    const fields = visibleFields(operation, TARGETS.consumerApi, outline, {}).find((item) => item.name === "fields")!;
    const offered =
      fields.type === "pairs" ? fieldOptions(fields, { via: "stores" }).map((option) => option.value) : [];
    expect(offered).toEqual(expect.arrayContaining(["id", "objectType", "name"]));
    expect(
      operation.build({ output: "bins", via: "stores", fields: ["binName=name", "binId=id"] }, api, outline),
    ).toEqual([
      {
        kind: "insertConsumerApiPart",
        consumerApi: "shop-feed",
        pointer: "/object/related",
        key: "bins",
        value: { via: "stores", fields: { binName: "name", binId: "id" } },
      },
    ]);
  });

  it("adds a block to the parent, written out in full first when the parent is the short form, and offers it to filters (CA1)", () => {
    const withParent = (parent: unknown) =>
      ({
        ...TARGETS.consumerApi,
        definition: {
          ...consumerDefinitionFixture(),
          object: { ...(consumerDefinitionFixture().object as object), parent },
        },
      }) as never;
    const operation = operationById("consumer-add-parent-related")!;
    expect(operationsFor(TARGETS.consumerApi, outline)).not.toContain(operation);
    expect(operationsFor(withParent(["objectType", "id", "code", "name"]), outline)).toContain(operation);
    const [written, insert] = operation.build(
      { output: "areaBins", via: "stores", fields: ["binName=name"], served: "onRequest" },
      withParent(["objectType", "id", "code", "name"]),
      outline,
    );
    expect(written).toEqual({
      kind: "setConsumerApiPart",
      consumerApi: "shop-feed",
      pointer: "/object/parent",
      value: {
        output: "parent",
        fields: { objectType: "objectType", id: "id", code: "code", name: "name" },
      },
    });
    expect(insert).toEqual({
      kind: "insertConsumerApiPart",
      consumerApi: "shop-feed",
      pointer: "/object/parent/related",
      key: "areaBins",
      value: { via: "stores", fields: { binName: "name" }, served: "onRequest" },
    });
    // An object parent needs no rewriting, and a block served always writes no `served`.
    expect(
      operation.build(
        { output: "areaBins", via: "stores", fields: ["binName=name"], served: "always" },
        withParent({ output: "category", fields: { id: "id" } }),
        outline,
      ),
    ).toHaveLength(1);
    const withBlock = withParent({
      output: "parent",
      fields: { id: "id" },
      related: { areaBins: { via: "stores", fields: { binName: "name" } } },
    });
    const filter = visibleFields(operationById("consumer-add-filter")!, withBlock, outline, { verb: "onRelated" }).find(
      (field) => field.name === "related",
    );
    expect(filter?.type === "select" && fieldOptions(filter, {}).map((option) => option.value)).toEqual([
      "bins",
      "parent.areaBins",
    ]);
  });

  it("chooses the parent's fields as output names, proposing none from a dashed source itself, and keeps a written form (CA1)", () => {
    const target = {
      ...TARGETS.consumerApi,
      definition: {
        ...consumerDefinitionFixture(),
        object: {
          ...(consumerDefinitionFixture().object as object),
          parent: { output: "parent", fields: { masterId: { from: ["master-id"], default: "x" }, kind: "objectType" } },
        },
      },
    } as never;
    const operation = operationById("consumer-parent-fields")!;
    expect(initialValues(operation, target, outline)).toEqual({ fields: ["masterId=master-id", "kind=objectType"] });
    expect(operation.build({ fields: ["masterId=master-id", "fsoNumber=fso-number"] }, target, outline)).toEqual([
      {
        kind: "setConsumerApiPart",
        consumerApi: "shop-feed",
        pointer: "/object/parent",
        value: {
          output: "parent",
          fields: { masterId: { from: ["master-id"], default: "x" }, fsoNumber: "fso-number" },
        },
      },
    ]);
  });

  it("chooses what a filter matches on, and takes it out to fall back to the defaults", () => {
    const filter = {
      ...(TARGETS.consumerItem as object),
      pointer: "/filters/where",
      label: "filter where",
      value: { under: ["area"], matchOn: ["name"] },
      definition: consumerDefinitionFixture(),
    } as OperationTarget;
    const match = operationById("consumer-filter-match")!;
    expect(initialValues(match, filter, outline)).toEqual({ matchOn: ["name"] });
    expect(match.build({ matchOn: [] }, filter as never, outline)).toEqual([
      { kind: "setConsumerApiPart", consumerApi: "shop-feed", pointer: "/filters/where/matchOn", value: null },
    ]);
    const byType = { ...(filter as object), value: { byType: true } } as OperationTarget;
    expect(operationsFor(byType, outline)).not.toContain(match);
  });

  it("refuses JSON it cannot read before anything is sent", () => {
    expect(() => operationById("consumer-json")!.build({ json: "{ nope" }, api, outline)).toThrow(
      /JSON cannot be read/,
    );
  });

  it("moves an item by one place and offers no move past either end", () => {
    const item = TARGETS.consumerItem as never;
    expect(operationById("consumer-item-up")!.build({}, item, outline)).toEqual([
      { kind: "moveConsumerApiPart", consumerApi: "shop-feed", pointer: "/object/fields/depth", position: 1 },
    ]);
    const last = { ...TARGETS.consumerItem, index: 3 } as OperationTarget;
    expect(operationsFor(last, outline).map((op) => op.id)).not.toContain("consumer-item-down");
  });
});

describe("the table of operations as another page reads it (0.17 CE1)", () => {
  it("lists every operation once with the kind of target it acts on", () => {
    const listed = operationTargetKinds();
    expect(listed).toHaveLength(OPERATIONS.length);
    expect(new Set(listed.map((item) => item.id)).size).toBe(OPERATIONS.length);
    expect(listed.find((item) => item.id === "relation-remove")?.on).toBe("relation");
  });

  it("offers a target the operations of its kind that are available, and nothing of another kind", () => {
    const outline = outlineFixture();
    const offered = operationsFor({ on: "objectType", objectType: outline.objectTypes[0]!.key }, outline);
    expect(offered.length).toBeGreaterThan(0);
    expect(offered.every((item) => item.on === "objectType")).toBe(true);
  });
});
