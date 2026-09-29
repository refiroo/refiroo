import { describe, expect, it } from "vitest";
import starter from "../../../model/rdm-starter.json";
import { chooseGapBranch, gapBranches, moveRefusal, moveRefusalText, type RowPlace } from "@/model/treeDrop";
import type { ApplicationDefinition, EngineModel, ObjectItem } from "@/types";

const starterModel = starter as unknown as EngineModel;
const application = (model: EngineModel, key: string) =>
  model.applications.find((candidate) => candidate.key === key) as ApplicationDefinition;

type Placed = Pick<ObjectItem, "id" | "objectTypeKey" | "applicationKey" | "parentObjectId" | "path">;

/** A record of `objectTypeKey` under `parent`, in `applicationKey`. */
function placed(id: string, objectTypeKey: string, parent?: Placed, applicationKey = parent?.applicationKey): Placed {
  return {
    id,
    objectTypeKey,
    applicationKey: applicationKey ?? "",
    parentObjectId: parent?.id ?? null,
    path: [...(parent?.path ?? []), { id, name: id, objectTypeKey }],
  };
}

/**
 * The shape of the generated volume model (backend `tests/volume_fixture.py`): groups hold groups,
 * items and nodes; nodes nest to any depth; items hold nothing.
 */
function volumeModel(): EngineModel {
  const relation = (key: string) => ({
    key,
    reverseKey: `${key}-reverse`,
    name: key,
    reverseName: key,
    features: { parentOf: true },
  });
  const type = (key: string, parents: string[], root: boolean) => ({
    key,
    name: key,
    pluralName: `${key}s`,
    attributes: [],
    features: { rootCreatable: root },
    behavior: { parentRelationTypeKeys: parents },
  });
  const binding = (relationTypeKey: string, fromObjectTypeKey: string, toObjectTypeKey: string) => ({
    relationTypeKey,
    fromObjectTypeKey,
    toObjectTypeKey,
    cardinality: "one-to-many",
  });
  return {
    attributeTypes: [],
    objectTypes: [
      type("vol-group", ["vol-group-has-child"], true),
      type("vol-item", ["vol-group-contains-item"], false),
      type("vol-node", ["vol-group-contains-node", "vol-node-has-child"], false),
    ],
    relationTypes: [
      relation("vol-group-has-child"),
      relation("vol-group-contains-item"),
      relation("vol-group-contains-node"),
      relation("vol-node-has-child"),
    ],
    objectTypeRelations: [
      binding("vol-group-has-child", "vol-group", "vol-group"),
      binding("vol-group-contains-item", "vol-group", "vol-item"),
      binding("vol-group-contains-node", "vol-group", "vol-node"),
      binding("vol-node-has-child", "vol-node", "vol-node"),
    ],
    applications: [
      {
        key: "vol-catalogue",
        name: "Volume catalogue",
        objectTypeKeys: ["vol-group", "vol-item", "vol-node"],
        views: [],
      },
    ],
  } as unknown as EngineModel;
}

describe("moveRefusal", () => {
  it("judges the starter system hierarchy by its containment rule and B2's refusals", () => {
    const systems = application(starterModel, "rdm-systems");
    const system = placed("system-00", "system", undefined, "rdm-systems");
    const other = placed("system-01", "system", undefined, "rdm-systems");
    const lab = placed("lab-group", "system-group", system);
    const chemistry = placed("chemistry", "system-group", lab);
    const sodium = placed("sodium", "system-value", chemistry);
    const xray = placed("x-ray", "system-value", system);
    const foreign = placed("master-group", "system-group", undefined, "rdm-master");
    const refusal = (record: Placed, parent: Placed) => moveRefusal(starterModel, systems, record, parent);

    expect(refusal(lab, lab)).toBe("self");
    expect(refusal(lab, chemistry)).toBe("descendant");
    expect(refusal(chemistry, lab)).toBe("currentParent");
    expect(refusal(chemistry, sodium)).toBe("descendant");
    expect(refusal(chemistry, xray)).toBe("type");
    expect(refusal(chemistry, foreign)).toBe("application");
    // A group nests in a system or a group; a value in either too, whichever type the parent is.
    expect(refusal(chemistry, other)).toBeUndefined();
    expect(refusal(sodium, lab)).toBeUndefined();
    expect(refusal(sodium, other)).toBeUndefined();
    expect(moveRefusalText(starterModel, "type", chemistry)).toBe("Can't contain system groups");
    expect(moveRefusalText(starterModel, "application", chemistry)).toBe("In another application");
    expect(moveRefusalText(starterModel, "descendant", chemistry)).toBe("Inside the record");
  });

  it("judges the starter domain hierarchy, where master values nest in codelists and each other", () => {
    const master = application(starterModel, "rdm-master");
    const domain = placed("domain-00", "domain", undefined, "rdm-master");
    const alpha = placed("alpha", "codelist", domain);
    const beta = placed("beta", "codelist", domain);
    const courier = placed("courier", "master-value", alpha);
    const sameDay = placed("same-day", "master-value", courier);
    const pickup = placed("pickup", "master-value", beta);
    const refusal = (record: Placed, parent: Placed) => moveRefusal(starterModel, master, record, parent);

    expect(refusal(courier, beta)).toBeUndefined();
    expect(refusal(sameDay, pickup)).toBeUndefined();
    expect(refusal(courier, sameDay)).toBe("descendant");
    expect(refusal(courier, domain)).toBe("type");
    expect(refusal(alpha, beta)).toBe("type");
    expect(refusal(alpha, domain)).toBe("currentParent");
    expect(moveRefusalText(starterModel, "type", courier)).toBe("Can't contain master values");
  });

  it("judges the generated volume tree, seven levels of nodes under groups beside items", () => {
    const model = volumeModel();
    const catalogue = model.applications[0];
    const group = placed("group-0", "vol-group", undefined, "vol-catalogue");
    const sibling = placed("group-1", "vol-group", undefined, "vol-catalogue");
    const item = placed("item-0", "vol-item", group);
    let node = placed("node-1", "vol-node", group);
    const top = node;
    for (let level = 2; level <= 7; level += 1) node = placed(`node-${level}`, "vol-node", node);
    const refusal = (record: Placed, parent: Placed) => moveRefusal(model, catalogue, record, parent);

    expect(refusal(node, sibling)).toBeUndefined();
    expect(refusal(node, top)).toBeUndefined();
    expect(refusal(top, node)).toBe("descendant");
    expect(refusal(node, item)).toBe("type");
    expect(refusal(item, top)).toBe("type");
    expect(refusal(item, sibling)).toBeUndefined();
    expect(refusal(sibling, group)).toBeUndefined();
  });
});

describe("gapBranches", () => {
  // Rows as drawn: parents are the record rows above, outermost first.
  const [system, lab, chemistry] = ["system", "lab", "chemistry"];
  const row = (...parents: string[]): RowPlace<string> => ({ level: parents.length + 1, parents });
  const indentOf = (level: number) => 26 + (level - 1) * 14;

  it("puts a gap between siblings in their branch", () => {
    expect(gapBranches(row(system, lab), row(system, lab))).toEqual([{ level: 3, parent: lab }]);
  });

  it("puts the gap above a branch's type heading, or its first row, in that branch", () => {
    // An expanded record's row, then its first child type's heading one level deeper.
    expect(gapBranches(row(system), row(system, lab))).toEqual([{ level: 3, parent: lab }]);
    expect(gapBranches(undefined, row(system, lab))).toEqual([{ level: 3, parent: lab }]);
  });

  it("offers each branch that ends at a gap, deepest first, and the pointer picks the level", () => {
    // Chemistry's last value, then Boat back at the second level.
    const branches = gapBranches(row(system, lab, chemistry), row(system));
    expect(branches).toEqual([
      { level: 4, parent: chemistry },
      { level: 3, parent: lab },
      { level: 2, parent: system },
    ]);
    expect(chooseGapBranch(branches, 400, indentOf)?.parent).toBe(chemistry);
    expect(chooseGapBranch(branches, indentOf(3) + 2, indentOf)?.parent).toBe(lab);
    expect(chooseGapBranch(branches, indentOf(2), indentOf)?.parent).toBe(system);
    // Left of every branch, the shallowest one still holds.
    expect(chooseGapBranch(branches, 0, indentOf)?.parent).toBe(system);
  });

  it("never offers the top level, which has no parent to move into", () => {
    expect(gapBranches(row(), row())).toEqual([]);
    expect(gapBranches(row(system), undefined)).toEqual([{ level: 2, parent: system }]);
    expect(gapBranches(row(system, lab), row())).toEqual([
      { level: 3, parent: lab },
      { level: 2, parent: system },
    ]);
    expect(chooseGapBranch([], 100, indentOf)).toBeUndefined();
  });
});
