import { describe, expect, it } from "vitest";
import { consumerDefinitionFixture, outlineFixture } from "@/test/draftOutline";
import {
  menuItems,
  operationTargetKinds,
  operationsFor,
  type OperationTarget,
} from "@/features/model-editor/operations";
import type { ModelDraftOutline } from "@/types/modelAdmin";
import { CANVAS_SURFACES } from "./canvasSurfaces";

const outline = outlineFixture();

/** Every element of the fixture, as the target its canvas surface gives the editor's menu. */
function targetsOf(model: ModelDraftOutline): OperationTarget[] {
  const targets: OperationTarget[] = [{ on: "draft" }, { on: "consumerApis" }];
  for (const application of model.applications) {
    targets.push({ on: "application", applicationKey: application.key });
    for (const view of application.views) targets.push({ on: "view", applicationKey: application.key, view: view.key });
    for (const group of application.navigation.groups) {
      targets.push({ on: "group", applicationKey: application.key, group: group.key });
      for (const entry of group.entries)
        targets.push({ on: "groupEntry", applicationKey: application.key, group: group.key, ...entry });
    }
  }
  for (const type of model.objectTypes) {
    targets.push({ on: "objectType", objectType: type.key });
    for (const attribute of type.attributes)
      targets.push({ on: "attribute", objectType: type.key, attributeType: attribute.attributeType });
  }
  for (const attributeType of model.attributeTypes)
    targets.push({ on: "attributeType", attributeType: attributeType.key });
  for (const relationType of model.relationTypes) targets.push({ on: "relationType", relationType: relationType.key });
  for (const relation of model.relations)
    targets.push({ on: "relation", relationType: relation.relationType, from: relation.from, to: relation.to });
  const definition = consumerDefinitionFixture();
  targets.push({ on: "consumerApi", consumerApi: "shop-feed", definition });
  targets.push({
    on: "consumerItem",
    consumerApi: "shop-feed",
    pointer: "/object/fields/depth",
    label: "depth",
    index: 0,
    count: 1,
    value: "depth",
    definition,
  });
  return targets;
}

describe("the canvas reaches every operation of the editor's table (0.17 CE1, PP-D89)", () => {
  const all = operationTargetKinds();

  it("has a surface for every kind of target the table acts on", () => {
    for (const kind of new Set(all.map((item) => item.on)))
      expect(CANVAS_SURFACES[kind], `a canvas surface for ${kind}`).toBeDefined();
    // And no surface for a kind the table no longer has.
    for (const kind of Object.keys(CANVAS_SURFACES))
      expect(
        all.some((item) => item.on === kind),
        `${kind} is a kind of the table`,
      ).toBe(true);
  });

  it("offers each operation in the menu of a target of its kind, where the fixture has one that allows it", () => {
    const targets = targetsOf(outline);
    const missing = all
      .filter(
        (item) =>
          !targets.some(
            (target) =>
              target.on === item.on &&
              menuItems(target, outline, () => undefined).some((entry) => entry.id === item.id),
          ),
      )
      .map((item) => item.id);
    expect(missing).toEqual(EXPECTED_UNOFFERED);
  });

  it("lists every operation of the table once", () => {
    expect(new Set(all.map((item) => item.id)).size).toBe(all.length);
    expect(operationsFor({ on: "draft" }, outline).length).toBeGreaterThan(0);
  });
});

/**
 * Operations no element of the small fixture allows: each needs a state the fixture lacks (a second view of a kind, a
 * type nothing lists, a group with a neighbour, a consumer API with a related block or a second version). They are
 * reached by the same menu as the rest of their kind; the list is explicit so that a new operation shows up here.
 */
const EXPECTED_UNOFFERED: string[] = [
  "application-list-type",
  "view-matrix-change",
  "view-tree-change",
  "view-grid-change",
  "view-table-layout",
  "view-table-remove",
  "view-matrix-remove",
  "type-unlist",
  "type-effective-period",
  "entry-up",
  "entry-down",
  "entry-move",
  "group-up",
  "group-down",
  "consumer-add-parent-related",
  "consumer-parent-fields",
  "consumer-item-up",
  "consumer-item-down",
  "consumer-through-prefer",
  "consumer-filter-match",
  "consumer-related-fields",
  "consumer-version-sunset",
  "consumer-version-stop",
];
