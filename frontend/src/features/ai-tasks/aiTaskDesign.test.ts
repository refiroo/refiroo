import { describe, expect, it } from "vitest";
import type { EngineModel } from "@/types";
import { columnTargets, describeCriteria, describeLink, modelNames } from "./aiTaskDesign";
import { notLoadedEntries } from "./aiTaskText";
import { designTask } from "./designFixture";

const model = {
  objectTypes: [
    { key: "station", name: "Station", pluralName: "Stations" },
    { key: "driver", name: "Driver", pluralName: "Drivers" },
    { key: "domain", name: "Domain", pluralName: "Domains" },
    { key: "duration", name: "Duration", pluralName: "Durations" },
  ],
  attributeTypes: [{ key: "domain-code", name: "Domain code" }],
  relationTypes: [
    { key: "assigned", reverseKey: "assigned-to", name: "Assigned", reverseName: "Assigned to" },
    { key: "has-duration", reverseKey: "of", name: "Has duration", reverseName: "Duration of" },
  ],
} as unknown as EngineModel;
const names = modelNames(model, []);

describe("describeCriteria", () => {
  it("reads a field criterion in the model's names", () => {
    expect(describeCriteria([{ field: "domain-code", op: "eq", value: "A1" }], names)).toBe(
      "whose Domain code is “A1”",
    );
    expect(describeCriteria([{ field: "name", op: "contains", value: "North" }], names)).toBe(
      "whose Name contains “North”",
    );
  });

  it("reads an ancestor criterion as the ancestor type's field", () => {
    expect(describeCriteria([{ field: "ancestor:domain.name", op: "eq", value: "Care" }], names)).toBe(
      "whose Domain's Name is “Care”",
    );
  });

  it("reads a relationship hop, its direction, its own criteria and not", () => {
    const hop = { related: { relationTypeKey: "assigned", direction: "outgoing" as const } };
    expect(describeCriteria([hop], names)).toBe("that has the relationship “Assigned”");
    expect(
      describeCriteria(
        [
          { related: { ...hop.related, direction: "incoming", where: [{ field: "name", op: "eq", value: "Dr X" }] } },
          { ...hop, not: true },
          { field: "name", op: "eq", value: "Old", not: true },
        ],
        names,
      ),
    ).toBe(
      "that has the relationship “Assigned to” to a record whose Name is “Dr X” and that has no relationship “Assigned” and excluding those whose Name is “Old”",
    );
  });

  it("reads no criteria as nothing", () => {
    expect(describeCriteria(undefined, names)).toBe("");
  });
});

describe("describeLink", () => {
  it("is one sentence with the pairs the engine found", () => {
    const rule = {
      relationTypeKey: "has-duration",
      from: { objectTypeKey: "station", where: [{ related: { relationTypeKey: "assigned" } }] },
      to: { objectTypeKey: "duration" },
    };
    expect(describeLink(rule, names, { rule, from: 4, to: 46, pairs: 100 })).toBe(
      "Has duration: every Station that has the relationship “Assigned”, with every Duration (100 pairs).",
    );
    expect(describeLink(rule, names)).toBe(
      "Has duration: every Station that has the relationship “Assigned”, with every Duration.",
    );
  });
});

describe("columnTargets", () => {
  it("reads a column that is its own attribute or the record's name by what it is", () => {
    const source = {
      objectTypeKey: "domain",
      columns: [
        { column: "Domain code", attributeTypeKey: "domain-code" },
        { column: "Name", field: "name" },
        { column: "Title", field: "name" },
      ],
    };
    expect(columnTargets(source, names).map((item) => item.line)).toEqual([
      "Domain code → its attribute",
      "Name → the record's name",
      "Title → Name",
    ]);
  });
});

describe("notLoadedEntries of a design", () => {
  it("names the sheets the design leaves out and its ignored columns, not the rules' first reading", () => {
    const task = designTask();
    const design = task.design!;
    const withOutcome = {
      ...task,
      reading: {
        tables: [{ table: "t1", sheet: "Sponsors", as: "newData", range: "A1:K74" }],
      } as unknown as typeof task.reading,
      design: {
        ...design,
        outcome: { sheetsNotLoaded: ["source"] },
        leftOut: [
          { sheet: "Sponsors", column: "COUNTRY_ID", reason: "The country name already carries it." },
          { sheet: "Sponsors", column: "#", reason: null },
        ],
      },
    };
    expect(notLoadedEntries(withOutcome, true)).toEqual([
      { sheet: "source", text: "Sheet “source”: the design does not load it" },
      { sheet: "Sponsors", text: "Column “COUNTRY_ID” is left out: The country name already carries it." },
      { sheet: "Sponsors", text: "Column “#” is left out (no reason given)" },
    ]);
  });
});
