import { describe, expect, it } from "vitest";
import type { EngineModel, MappingProposal, MappingTypeEntry, ModelMapping } from "@/types";
import { mappingBlocks, stillProposed } from "./mappingRows";

function model(types: { key: string; attributes: string[] }[], unique: string[] = []): EngineModel {
  const attributes = [...new Set(types.flatMap((type) => type.attributes))];
  return {
    schemaVersion: "0.10",
    release: { key: "m", name: "M", version: "1.0.0" },
    product: { name: "M" },
    attributeTypes: attributes.map((key) => ({
      key,
      name: key.toUpperCase(),
      valueType: "text",
      features: unique.includes(key) ? { unique: true } : {},
      validation: {},
      ui: {},
    })),
    objectTypes: types.map((type) => ({
      key: type.key,
      name: type.key,
      pluralName: `${type.key}s`,
      attributes: type.attributes.map((attributeTypeKey, order) => ({
        attributeTypeKey,
        required: attributeTypeKey === "kind",
        readOnly: false,
        order,
        ui: {},
      })),
      features: {},
      behavior: {},
      validation: {},
    })),
    relationTypes: [],
    objectTypeRelations: [],
    applications: [],
  } as unknown as EngineModel;
}

const source = model([{ key: "title", attributes: ["isbn", "year"] }]);
const target = model([{ key: "holding", attributes: ["code", "period", "kind"] }], ["code"]);

const typeProposal = (status: MappingProposal["status"]): MappingProposal => ({
  id: "p1",
  position: 0,
  kind: "type",
  sourceType: "title",
  relation: null,
  target: "holding",
  score: 4,
  summary: "Titles become holdings",
  evidence: [{ kind: "sameName" }],
  operations: [
    { kind: "mapType", sourceType: "title", targetType: "holding" },
    { kind: "mapAttribute", sourceType: "title", attribute: "isbn", target: "code" },
    { kind: "mapAttribute", sourceType: "title", attribute: "year", target: "period" },
    { kind: "setMatch", sourceType: "title", match: { attributeTypeKey: "code" } },
  ],
  alternatives: [],
  requires: [],
  status,
});

const entry = (changes: Partial<MappingTypeEntry> = {}): MappingTypeEntry => ({
  source: "title",
  target: "holding",
  attributes: [
    { source: "isbn", target: "code" },
    { source: "year", target: "period" },
  ],
  relations: [],
  defaults: {},
  match: { attributeTypeKey: "code" },
  ...changes,
});

describe("the Proposed mark on a mapping row (D141)", () => {
  it("marks each row still as an applied proposal set it", () => {
    const proposal = typeProposal("applied");
    expect(stillProposed(entry(), proposal, { kind: "type" })).toBe(proposal);
    expect(stillProposed(entry(), proposal, { kind: "attribute", attribute: "isbn" })).toBe(proposal);
    expect(stillProposed(entry(), proposal, { kind: "match" })).toBe(proposal);
  });

  it("keeps the mark on the other rows of a held proposal, and drops it from the row changed by hand", () => {
    const proposal = typeProposal("held");
    const changed = entry({
      attributes: [
        { source: "isbn", target: "code" },
        { source: "year", target: "kind" },
      ],
    });
    expect(stillProposed(changed, proposal, { kind: "attribute", attribute: "isbn" })).toBe(proposal);
    expect(stillProposed(changed, proposal, { kind: "attribute", attribute: "year" })).toBeUndefined();
    expect(stillProposed(entry({ match: null }), proposal, { kind: "match" })).toBeUndefined();
  });

  it("drops every mark of a type mapped by hand to another target, and of an undone proposal", () => {
    const remapped = entry({ target: "other" });
    expect(stillProposed(remapped, typeProposal("held"), { kind: "attribute", attribute: "isbn" })).toBeUndefined();
    expect(stillProposed(entry(), typeProposal("rejected"), { kind: "type" })).toBeUndefined();
    expect(stillProposed(entry(), typeProposal("open"), { kind: "type" })).toBeUndefined();
  });

  it("marks a value-mapped or ignored attribute as the user's", () => {
    const proposal = typeProposal("held");
    const mapped = entry({ attributes: [{ source: "isbn", target: "code", valueMap: "codes" }] });
    expect(stillProposed(mapped, proposal, { kind: "attribute", attribute: "isbn" })).toBeUndefined();
    const ignored = entry({ attributes: [{ source: "isbn", ignore: true }] });
    expect(stillProposed(ignored, proposal, { kind: "attribute", attribute: "isbn" })).toBeUndefined();
  });
});

describe("a mapping's rows", () => {
  const mapping = (types: MappingTypeEntry[], problems: ModelMapping["problems"] = []): ModelMapping => ({
    key: "a",
    name: "A",
    sourceModelKey: "m",
    targetModelKey: "m",
    sourceReleaseId: "s",
    targetReleaseId: "t",
    version: 3,
    updatedAt: "",
    createdAt: "",
    types,
    valueMaps: {},
    problems,
    coverage: { types: [], attributes: [], relations: [], required: [], requiredRelations: [], parents: [] },
  });

  it("offers each source field, the match by a unique target field, and the target's required field as a default", () => {
    const [block] = mappingBlocks(mapping([entry()]), source, target, [typeProposal("applied")]);
    expect(block.rows.map((row) => row.key)).toEqual([
      "type",
      "attribute:isbn",
      "attribute:year",
      "match",
      "default:kind",
    ]);
    const match = block.rows.find((row) => row.kind === "match")!;
    expect(match.options.map((option) => option.value)).toEqual(["", "name", "attribute:code"]);
    expect(match.value).toBe("attribute:code");
    expect(block.rows.find((row) => row.key === "default:kind")!.value).toBe("");
  });

  it("sends one step per choice, and unmaps only what the mapping holds", () => {
    const [block] = mappingBlocks(
      mapping([entry({ attributes: [{ source: "isbn", target: "code" }] })]),
      source,
      target,
      [],
    );
    const isbn = block.rows.find((row) => row.key === "attribute:isbn")!;
    const year = block.rows.find((row) => row.key === "attribute:year")!;
    expect(isbn.operations("")).toEqual([{ kind: "unmapAttribute", sourceType: "title", attribute: "isbn" }]);
    expect(year.operations("")).toEqual([]);
    expect(year.operations("period")).toEqual([
      { kind: "mapAttribute", sourceType: "title", attribute: "year", target: "period" },
    ]);
  });

  it("puts a problem at the row its pointer names", () => {
    const [block] = mappingBlocks(
      mapping(
        [entry()],
        [{ code: "ATTRIBUTE_FILLED_TWICE", pointer: "/types/0/attributes/1/target", side: "target", message: "Twice" }],
      ),
      source,
      target,
      [],
    );
    expect(block.rows.find((row) => row.key === "attribute:year")!.problems).toHaveLength(1);
    expect(block.rows.find((row) => row.key === "attribute:isbn")!.problems).toHaveLength(0);
  });
});
