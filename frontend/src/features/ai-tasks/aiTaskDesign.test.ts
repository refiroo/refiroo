import { describe, expect, it } from "vitest";
import type { EngineModel } from "@/types";
import { columnTargets, modelChanges, modelNames } from "./aiTaskDesign";
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

describe("modelChanges", () => {
  it("reads a changed type and an other change from the draft's result", () => {
    const rows = modelChanges(
      [
        { kind: "addObjectType", key: "line", name: "Line", applicationKey: "a", parent: null },
        { kind: "changeObjectType", objectType: "station", fields: ["name"] },
        { kind: "changeAttachment", objectType: "station", attributeType: "code", required: false },
        { kind: "removeObjectType", objectType: "driver" },
      ],
      names,
    );
    expect(rows.map((row) => [row.change, row.name])).toEqual([
      ["New type", "Line"],
      ["Other change", "Station"],
      ["Other change", "Station"],
      ["Removed", "Driver"],
    ]);
  });
});
