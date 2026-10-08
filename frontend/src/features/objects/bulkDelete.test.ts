import { describe, expect, it } from "vitest";
import { emptySelection, selectMatching, toggle, withoutDeleted } from "@/lib/recordSelection";
import type { Job, JobItemOutcome } from "@/types";
import { recordsToChange } from "./bulkChange";
import { deletedIds, deleteItems, deleteLabel, deletionWords } from "./bulkDelete";

const alpha = { id: "a", version: 3, name: "Alpha" };
const beta = { id: "b", version: 5, name: "Beta" };
const gamma = { id: "c", version: 1, name: "Gamma" };
const picked = toggle(toggle(toggle(emptySelection, alpha), beta), gamma);
const named = (key: string, records: number) => `${records} ${key}${records === 1 ? "" : "s"}`;

const previewed = (extra: Partial<NonNullable<Job["preview"]>>): Job =>
  ({
    preview: {
      coverage: "complete",
      items: { total: 3, previewed: 3 },
      counts: { created: 0, updated: 0, unchanged: 1, deleted: 2, rejected: 0 },
      result: "applied",
      previewedAt: "2026-10-09T09:00:00Z",
      ...extra,
    },
  }) as Job;

describe("bulk delete (0.9 K2b)", () => {
  it("sends one cascading delete per record, from a hand selection or the records read for all matching", () => {
    expect(deleteItems(recordsToChange(picked))).toEqual([
      { op: "delete", ref: "Alpha", target: { id: "a" }, expectedVersion: 3, cascade: true },
      { op: "delete", ref: "Beta", target: { id: "b" }, expectedVersion: 5, cascade: true },
      { op: "delete", ref: "Gamma", target: { id: "c" }, expectedVersion: 1, cascade: true },
    ]);
    const matching = toggle(selectMatching(3), beta);
    expect(deleteItems(recordsToChange(matching, [alpha, beta, gamma])).map((item) => item.target.id)).toEqual([
      "a",
      "c",
    ]);
  });

  it("says the selected records apart from those going with them, the relationships and those deleted together", () => {
    const job = previewed({
      deletion: {
        objectCount: 9,
        objectsByType: { domain: 2, codelist: 6, code: 1 },
        relationshipCount: 7,
        retainedAssociationCount: 1,
      },
    });
    const words = deletionWords(job, "domain", named)!;
    expect(words.total).toBe(9);
    expect(words.selected).toBe("Deletes 2 domains");
    expect(words.withThem).toBe("and 7 records inside or owned by them: 1 code, 6 codelists");
    expect(words.relationships).toBe("Removes 7 relationships; 1 of them links to records that stay, which are kept.");
    expect(words.together).toBe("1 record selected goes with another selected record.");
    expect(deleteLabel(words.total)).toBe("Delete 9 records");

    const alone = deletionWords(
      previewed({
        counts: { created: 0, updated: 0, unchanged: 0, deleted: 1, rejected: 0 },
        deletion: { objectCount: 1, objectsByType: { domain: 1 }, relationshipCount: 0, retainedAssociationCount: 0 },
      }),
      "domain",
      named,
    )!;
    expect([alone.withThem, alone.together, alone.relationships]).toEqual([
      undefined,
      undefined,
      "Removes no relationships.",
    ]);
    expect(deletionWords(previewed({}), "domain", named)).toBeUndefined();
  });

  it("leaves in the selection only what the delete did not remove; all matching is cleared", () => {
    const outcomes: JobItemOutcome[] = [
      { index: 0, ref: "Alpha", status: "applied", action: "deleted", id: "a" },
      {
        index: 1,
        ref: "Beta",
        status: "rejected",
        error: { code: "DELETION_PREVIEW_CHANGED", message: "Changed" },
      },
      { index: 2, ref: "Gamma", status: "applied", action: "unchanged", id: "c", deletedWithItem: 0 },
    ];
    const deleted = deletedIds(outcomes);
    expect([...deleted].sort()).toEqual(["a", "c"]);
    const left = withoutDeleted(picked, deleted);
    expect(left.mode === "ids" && [...left.ids.keys()]).toEqual(["b"]);
    expect(withoutDeleted(selectMatching(10), deleted)).toEqual(emptySelection);
    expect(withoutDeleted(picked, new Set())).toBe(picked);
  });
});
