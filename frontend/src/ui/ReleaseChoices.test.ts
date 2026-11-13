import { describe, expect, it } from "vitest";
import { releaseChoices } from "@/ui/ReleaseChoices";
import type { ModelReleaseSummary } from "@/types";

function release(id: string, key: string, installedAt: string): ModelReleaseSummary {
  return {
    id,
    key,
    name: key,
    version: id,
    schemaVersion: "0.10",
    modelHash: id,
    installedAt,
    assigned: false,
    workspaces: [],
    status: "active",
    statusVersion: 1,
    deletable: true,
  };
}

const a1 = release("a1", "a", "2026-10-01T00:00:00Z");
const a2 = release("a2", "a", "2026-10-03T00:00:00Z");
const b1 = release("b1", "b", "2026-10-02T00:00:00Z");

describe("releaseChoices", () => {
  it("lists the newest release of each model, newest first, and counts the older ones", () => {
    expect(releaseChoices([a1, b1, a2], false)).toEqual({ shown: [a2, b1], olderCount: 1 });
  });

  it("adds the older releases after the newest ones when asked", () => {
    expect(releaseChoices([a1, b1, a2], true).shown).toEqual([a2, b1, a1]);
  });

  it("lists nothing for no releases", () => {
    expect(releaseChoices([], false)).toEqual({ shown: [], olderCount: 0 });
  });
});
