import { describe, expect, it } from "vitest";
import type { EngineModel, Job, ModelMapping, MoveCounts, MoveSummary } from "@/types";
import { difference, figuresOf, jobRunKey, reasonCards, runKey, selectionFor, VALUES_NOT_CARRIED } from "./moveRun";

const source = {
  attributeTypes: [{ key: "year", name: "Year", valueType: "integer", features: {}, validation: {}, ui: {} }],
  objectTypes: [],
  relationTypes: [],
  objectTypeRelations: [],
} as unknown as EngineModel;

const mapping = (sources: string[]) => ({ types: sources.map((key) => ({ source: key })) }) as unknown as ModelMapping;

const counts = (values: Partial<MoveCounts>): MoveCounts => ({
  create: 0,
  update: 0,
  updateOriginal: 0,
  refused: 0,
  notMoved: 0,
  ...values,
});

describe("what a dry run is asked to move (D142)", () => {
  it("selects every mapped type by default, and the whole workspace when none is mapped", () => {
    expect(selectionFor(mapping(["a", "b"]), undefined, source)).toEqual({
      types: [
        { objectTypeKey: "a", where: [] },
        { objectTypeKey: "b", where: [] },
      ],
    });
    expect(selectionFor(mapping([]), undefined, source)).toEqual({});
  });

  it("sends chosen types with their filters as criteria, a subtree by its record, and the whole workspace", () => {
    expect(
      selectionFor(
        mapping(["a"]),
        { kind: "types", types: [{ objectTypeKey: "a", filters: [{ field: "year", operator: "lt", value: "1960" }] }] },
        source,
      ),
    ).toEqual({ types: [{ objectTypeKey: "a", where: [{ field: "year", op: "lt", value: 1960 }] }] });
    expect(selectionFor(mapping(["a"]), { kind: "subtree", objectId: "r1", objectTypeKey: "a" }, source)).toEqual({
      parentObjectId: "r1",
    });
    expect(selectionFor(mapping(["a"]), { kind: "all" }, source)).toEqual({});
  });

  it("recognises the run a job was started for from what the job stored", () => {
    const selection = { types: [{ objectTypeKey: "a", where: [{ field: "year", op: "lt", value: 1960 }] }] };
    const job = {
      parameters: {
        mapping: { key: "m", version: 4 },
        mode: "copy",
        // As the engine stores it: criteria with their defaults.
        selection: { types: [{ objectTypeKey: "a", where: [{ field: "year", op: "lt", value: 1960, not: false }] }] },
      },
    } as unknown as Job;
    expect(jobRunKey(job)).toBe(runKey(4, selection, "copy"));
    expect(jobRunKey(job)).not.toBe(runKey(5, selection, "copy"));
    expect(jobRunKey(job)).not.toBe(runKey(4, selection, "move"));
  });
});

describe("the dry run's figures (D140) and the report's cards (D143)", () => {
  const summary = {
    counts: counts({ create: 5 }),
    types: [
      { sourceType: "a", counts: counts({ create: 3, update: 1, updateOriginal: 1, refused: 2 }) },
      { sourceType: "b", counts: counts({ notMoved: 4 }) },
    ],
    relationships: [{ relationTypeKey: "r", counts: counts({ create: 6, notMoved: 1 }) }],
    reasons: [
      { code: "TYPE_NOT_MAPPED", count: 4 },
      { code: "SOME_TARGET_RULE", count: 2 },
    ],
    attributesNotCarried: [
      { sourceType: "a", attributeTypeKey: "x", code: "ATTRIBUTE_NOT_MAPPED", count: 3 },
      { sourceType: "a", attributeTypeKey: "y", code: "VALUE_NOT_CONVERTIBLE", count: 1 },
    ],
  } as unknown as MoveSummary;

  it("counts records by type and relationships apart", () => {
    expect(figuresOf(summary)).toEqual({ create: 3, update: 2, cannot: 6, carried: 6, dropped: 1 });
  });

  it("says how a figure changed since the last step, and nothing when it did not", () => {
    expect(difference(6, 3)).toBe("+3 since the last step");
    expect(difference(1200, 2400)).toBe("−1,200 since the last step");
    expect(difference(3, 3)).toBe("");
    expect(difference(3, undefined)).toBe("");
  });

  it("lists each reason with its count, an unknown code in words, then the values not carried", () => {
    const cards = reasonCards(summary);
    expect(cards.map((card) => [card.code, card.count])).toEqual([
      ["TYPE_NOT_MAPPED", 4],
      ["SOME_TARGET_RULE", 2],
      [VALUES_NOT_CARRIED, 4],
    ]);
    expect(cards[0].label).toBe("Type not mapped");
    expect(cards[1].label).toBe("Some target rule");
  });
});
