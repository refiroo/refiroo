import { describe, expect, it } from "vitest";
import { testModel } from "@/test/fixtures";
import { ALL_WRITES, NO_WRITES, recordWrites } from "./permissions";
import { narrowedRecords, permissionLine } from "./permissionText";
import { permissionsFixture } from "@/test/permissions";

const live = { context: "live" as const, workspaceLabel: "West", proposing: false, publishes: true };

describe("the band's line (0.12 Z5, D322, D329)", () => {
  it("keeps the context's own line while the permissions load, and for someone who may do it all", () => {
    expect(permissionLine(testModel, { ...live, writes: undefined })).toBeUndefined();
    expect(permissionLine(testModel, { ...live, writes: ALL_WRITES })).toBeUndefined();
    expect(permissionLine(testModel, { ...live, context: "changeSet", writes: ALL_WRITES })).toBeUndefined();
  });

  it("tells a reader they can read, live and in a change set", () => {
    expect(permissionLine(testModel, { ...live, writes: NO_WRITES })).toBe(
      "You can read this workspace. To change records, ask a security administrator for a role that allows it.",
    );
    expect(permissionLine(testModel, { ...live, context: "changeSet", writes: NO_WRITES })).toMatch(
      /^You can read this change set\./,
    );
  });

  it("tells a contributor in live data that their changes go into their change set", () => {
    expect(permissionLine(testModel, { ...live, writes: NO_WRITES, proposing: true })).toBe(
      "Changes you make go into your change set, not live. Someone who holds Publish in West publishes it.",
    );
  });

  it("tells someone in a change set who cannot publish who does", () => {
    expect(permissionLine(testModel, { ...live, context: "changeSet", writes: ALL_WRITES, publishes: false })).toBe(
      "Edits stay in this change set until someone who holds Publish in West publishes it.",
    );
  });

  it("names a narrowed writer's records by the model's names", () => {
    const [first, second] = testModel.objectTypes;
    const writes = recordWrites(
      permissionsFixture("w", ["edit-live"], { recordTypes: [first.key, second.key] }),
      "edit-live",
    );
    expect(permissionLine(testModel, { ...live, writes })).toBe(
      `Your role changes ${first.name} and ${second.name} records here; others you can read.`,
    );
    const application = testModel.applications[0];
    expect(narrowedRecords(testModel, { applications: [application.key], recordTypes: [first.key] })).toBe(
      `${first.name} records and the records of ${application.name}`,
    );
    expect(narrowedRecords(testModel, { applications: [], recordTypes: ["gone"] })).toBe("no records of this model");
  });
});
