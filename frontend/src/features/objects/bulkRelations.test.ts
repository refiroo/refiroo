import { describe, expect, it } from "vitest";
import type { SelectableRow } from "@/lib/recordSelection";
import { bulkRelationChoices, type RelationActions } from "@/model/lookup";
import { testModel } from "@/test/fixtures";
import type { EngineModel, ObjectTypeRelationDefinition } from "@/types";
import { claimedByPreview, itemCount, pairRef, relationItems } from "./bulkRelations";

type Cardinality = ObjectTypeRelationDefinition["cardinality"];

/** The test model with one more binding, `domain` → `codelist`, named Cites and Cited by. */
function withBinding(binding: Partial<ObjectTypeRelationDefinition>): EngineModel {
  return {
    ...testModel,
    relationTypes: [
      ...testModel.relationTypes,
      { key: "cites", name: "Cites", reverseName: "Cited by", features: {} } as EngineModel["relationTypes"][number],
    ],
    objectTypeRelations: [
      ...testModel.objectTypeRelations,
      {
        relationTypeKey: "cites",
        fromObjectTypeKey: "domain",
        toObjectTypeKey: "codelist",
        cardinality: "many-to-many",
        ...binding,
      },
    ],
  };
}

const NONE: RelationActions = { add: false, remove: false, replace: false, set: false, clear: false };

/**
 * D128 written out, seen from the selected type's end: `undefined` where the binding is not offered
 * (required ownership, D127).
 */
function expected(cardinality: Cardinality, end: "from" | "to", required: boolean): RelationActions | undefined {
  if (required && cardinality !== "many-to-many") return undefined;
  if (cardinality === "many-to-many")
    return required
      ? { ...NONE, add: true, replace: true }
      : { add: true, remove: true, replace: true, set: false, clear: true };
  if (cardinality === "one-to-many" && end === "to") return { ...NONE, set: true, clear: true };
  return { ...NONE, remove: true, clear: true };
}

const rows: SelectableRow[] = [
  { id: "a", version: 3, name: "Alpha" },
  { id: "b", version: 5, name: "Beta" },
];
const x = { id: "x", name: "Ex" };
const y = { id: "y", name: "Why" };

describe("the relationships a bulk change offers (0.9 K3, D127, D128)", () => {
  it("offers each binding's actions by cardinality, end and required, for every combination", () => {
    for (const cardinality of ["one-to-one", "one-to-many", "many-to-many"] as const)
      for (const required of [false, true]) {
        const model = withBinding({ cardinality, required });
        for (const [end, type, direction, label] of [
          ["from", "domain", "outgoing", "Cites"],
          ["to", "codelist", "incoming", "Cited by"],
        ] as const) {
          const offered = bulkRelationChoices(model, type).filter((item) => item.relation.relationTypeKey === "cites");
          const actions = expected(cardinality, end, required);
          const name = `${cardinality} ${required ? "required" : "optional"} at ${end}`;
          if (!actions) expect(offered, name).toEqual([]);
          else {
            expect(
              offered.map((item) => [item.direction, item.label, item.otherObjectTypeKey]),
              name,
            ).toEqual([[direction, label, type === "domain" ? "codelist" : "domain"]]);
            expect(offered[0].actions, name).toEqual(actions);
          }
        }
      }
  });

  it("never offers containment", () => {
    expect(bulkRelationChoices(testModel, "domain")).toEqual([]);
    expect(bulkRelationChoices(testModel, "codelist")).toEqual([]);
  });
});

describe("the items a relationship change sends (0.9 K3, D129, D130)", () => {
  const model = withBinding({});
  const [outgoing] = bulkRelationChoices(model, "domain");
  const [incoming] = bulkRelationChoices(model, "codelist");

  it("adds and removes by the two records, one item per selected record and chosen record", () => {
    const sent = relationItems(rows, outgoing, { mode: "change", add: [x], remove: [y] });
    expect(sent.items).toEqual([
      { op: "ensureRelation", ref: "Alpha → Ex", relationTypeKey: "cites", from: { id: "a" }, to: { id: "x" } },
      { op: "ensureNoRelation", ref: "Alpha → Why", relationTypeKey: "cites", from: { id: "a" }, to: { id: "y" } },
      { op: "ensureRelation", ref: "Beta → Ex", relationTypeKey: "cites", from: { id: "b" }, to: { id: "x" } },
      { op: "ensureNoRelation", ref: "Beta → Why", relationTypeKey: "cites", from: { id: "b" }, to: { id: "y" } },
    ]);
    expect(sent.rowOf).toEqual([0, 0, 1, 1]);
    // Seen from the other end, the selected records are the relationships' `to`.
    const reverse = relationItems(rows, incoming, { mode: "change", add: [x], remove: [] });
    expect(reverse.items.map((item) => "from" in item && [item.from.id, item.to.id])).toEqual([
      ["x", "a"],
      ["x", "b"],
    ]);
  });

  it("replaces, sets and clears each selected record's set without a claim", () => {
    const replaced = relationItems(rows, incoming, { mode: "replace", targets: [x, y] });
    expect(replaced.items[0]).toEqual({
      op: "replaceRelationSet",
      ref: "Alpha",
      relationTypeKey: "cites",
      fromObjectTypeKey: "domain",
      toObjectTypeKey: "codelist",
      direction: "incoming",
      anchor: { id: "a" },
      targets: [{ object: { id: "x" } }, { object: { id: "y" } }],
    });
    expect(replaced.rowOf).toEqual([0, 1]);
    expect(relationItems(rows, outgoing, { mode: "set", targets: [x] }).items[1]).toMatchObject({
      anchor: { id: "b" },
      targets: [{ object: { id: "x" } }],
    });
    expect(
      relationItems(rows, outgoing, { mode: "clear" }).items.map((item) => "targets" in item && item.targets),
    ).toEqual([[], []]);
    expect(replaced.items.some((item) => "expectedRelationSetVersion" in item)).toBe(false);
  });

  it("counts the items the limits count, and which ones the preview's claim needs (D131, D134)", () => {
    expect(itemCount(4000, { mode: "change", add: [x, y], remove: [x] })).toBe(12000);
    expect(itemCount(4000, { mode: "replace", targets: [x, y] })).toBe(4000);
    expect(itemCount(4000, { mode: "clear" })).toBe(4000);
    expect([
      claimedByPreview("change"),
      claimedByPreview("replace"),
      claimedByPreview("set"),
      claimedByPreview("clear"),
    ]).toEqual([false, true, true, true]);
  });

  it("cuts long names so a pair's ref fits what an item holds", () => {
    const long = { id: "l", version: 1, name: "N".repeat(300) };
    const ref = pairRef(long, { id: "o", name: "O".repeat(300) });
    expect(ref.length).toBeLessThanOrEqual(200);
    expect(ref).toContain(" → ");
  });
});
