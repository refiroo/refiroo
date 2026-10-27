import { describe, expect, it } from "vitest";
import { groupActivity, groupSummary } from "@/features/workspaces/activityGroups";
import type { ChangeEntry } from "@/types";

function entry(id: string, over: Partial<ChangeEntry> & { actorId?: string; type?: string } = {}): ChangeEntry {
  return {
    id,
    occurredAt: "2026-10-26T10:00:00",
    kind: "record",
    action: "updated",
    workspace: { key: "w", label: "W" },
    changeSet: { id: "cs1", name: "Spring", open: true },
    subject: { id, name: id, objectTypeKey: over.type ?? "brand", objectTypeName: over.type ?? "Brand" },
    changedFields: [],
    attributes: [],
    cause: { kind: "user" },
    actor: { kind: "user", id: over.actorId ?? "ana", name: "Ana" },
    ...over,
  } as ChangeEntry;
}

describe("groupActivity", () => {
  it("merges consecutive changes of one change set, actor and day", () => {
    const items = groupActivity([entry("a"), entry("b"), entry("c")], false);
    expect(items).toHaveLength(1);
    expect(items[0]).toMatchObject({ type: "group", changeSetName: "Spring", mayContinue: false });
  });

  it("splits on another actor or day and keeps live edits and lone changes single", () => {
    const items = groupActivity(
      [
        entry("a"),
        entry("b", { actorId: "bo" }),
        entry("c", { actorId: "bo" }),
        entry("d", { actorId: "bo", occurredAt: "2026-10-25T10:00:00" }),
        entry("e", { changeSet: null }),
        entry("f", { changeSet: null }),
      ],
      false,
    );
    expect(items.map((item) => item.type)).toEqual(["single", "group", "single", "single", "single"]);
  });

  it("marks a trailing group as possibly continuing while more pages exist", () => {
    const items = groupActivity([entry("a", { changeSet: null }), entry("b"), entry("c")], true);
    expect(items[1]).toMatchObject({ type: "group", mayContinue: true });
    expect(groupActivity([entry("b"), entry("c"), entry("x", { changeSet: null })], true)[0]).toMatchObject({
      mayContinue: false,
    });
  });

  it("describes a group by outcome and type", () => {
    const text = groupSummary(
      [entry("a"), entry("b", { action: "created", type: "slot" }), entry("c", { action: "deleted" })],
      (e) => e.subject.objectTypeName ?? "",
    );
    expect(text).toBe("1 changed · 1 created · 1 removed · Brand ×2, slot ×1");
  });
});
