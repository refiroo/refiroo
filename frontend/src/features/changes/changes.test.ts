import { describe, expect, it } from "vitest";
import { testModel } from "@/test/fixtures";
import { parseRoute, routePath } from "@/routing/routes";
import type { ChangeEntry, HeldAnywhere } from "@/types";
import {
  byDay,
  changeSummary,
  changeTarget,
  changeTitle,
  changeWhere,
  changesHeading,
  changesSubtitle,
  draftStepsTitle,
  groupDraftSteps,
  periodSince,
  readsChanges,
} from "./changeText";

function entry(overrides: Partial<ChangeEntry>): ChangeEntry {
  return {
    id: "e",
    occurredAt: "2026-10-25T09:40:00Z",
    kind: "record",
    action: "updated",
    workspace: { key: "main", label: "Main collection" },
    changeSet: null,
    subject: {
      id: "r1",
      name: "Quercus robur",
      applicationKey: "app",
      objectTypeKey: "specimen",
      objectTypeName: "Specimen",
      removed: false,
    },
    changedFields: ["name", "attributes", "version"],
    attributes: [{ key: "det", name: "Determiner" }],
    cause: { kind: "user" },
    actor: { kind: "user", id: "p", name: "Ana Varga" },
    ...overrides,
  };
}

describe("an entry's text", () => {
  it("names each kind of change by what it changed", () => {
    expect(changeTitle(entry({}))).toBe("Updated Quercus robur");
    expect(changeTitle(entry({ action: "created" }))).toBe("Added Quercus robur");
    expect(changeTitle(entry({ action: "deleted", subject: { id: "r1", removed: true } }))).toBe(
      "Deleted a record since removed",
    );
    const link = entry({
      kind: "relationship",
      action: "created",
      subject: {
        id: "l",
        relationTypeName: "is determined as",
        fromObject: { id: "a", name: "NFH-1" },
        toObject: { id: "b", name: null },
      },
    });
    expect(changeTitle(link)).toBe("Linked NFH-1 to a removed record");
    expect(changeTitle({ ...link, action: "deleted" })).toBe("Unlinked NFH-1 from a removed record");
    expect(changeTitle(entry({ kind: "change-set", action: "created", subject: { id: "c", name: "Spring" } }))).toBe(
      "Created change set “Spring”",
    );
    expect(changeTitle(entry({ kind: "publication", action: "withdrawn", subject: { id: "p", number: 14 } }))).toBe(
      "Withdrew publication 14",
    );
    expect(changeTitle(entry({ kind: "model", action: "updated", subject: { id: "d", name: "Next" } }))).toBe(
      "Changed model draft “Next”",
    );
    expect(
      changeTitle(entry({ kind: "model", action: "activated", subject: { id: "r", name: "Catalogue 3.2" } })),
    ).toBe("Activated release Catalogue 3.2");
  });

  it("summarises a record's type and the fields a person recognises, never identifiers", () => {
    expect(changeSummary(entry({}))).toBe("Specimen · changed name, Determiner");
    expect(changeSummary(entry({ action: "created" }))).toBe("Specimen");
    expect(
      changeSummary(
        entry({ kind: "publication", action: "published", changeSet: { id: "c", name: "Loans", open: false } }),
      ),
    ).toBe("From change set “Loans”");
  });

  it("says where and how after the time", () => {
    expect(changeWhere(entry({}))).toEqual(["Main collection"]);
    expect(
      changeWhere(entry({ changeSet: { id: "c", name: "Spring", open: true }, cause: { kind: "job", id: "j" } })),
    ).toEqual(["Main collection", "in change set “Spring”", "in a background job"]);
    expect(changeWhere(entry({ kind: "model", workspace: null }))).toEqual(["Model administration"]);
    expect(changeWhere(entry({ workspace: null, cause: { kind: "publication", id: "p" } }))).toEqual([
      "A deleted workspace",
      "applied by a publication",
    ]);
  });

  it("heads the page by whose changes they are", () => {
    expect(changesHeading(true, "Ana Varga")).toBe("Your changes");
    expect(changesHeading(false, "Ana Varga")).toBe("Ana Varga's changes");
    expect(changesHeading(false, undefined)).toBe("Changes");
    expect(changesSubtitle(false, "client")).toBe("Client · newest first, in the workspaces you can read");
    expect(changesSubtitle(true, "user")).toBe("Newest first, in the workspaces you can read");
  });
});

describe("where an entry leads", () => {
  it("opens a record in its change set while that is open, live otherwise, nowhere once removed", () => {
    const open = changeTarget(entry({ changeSet: { id: "c", name: null, open: true } }), "app");
    expect(open).toMatchObject({ kind: "detail", objectId: "r1", workspaceKey: "main", changeSetId: "c" });
    const published = changeTarget(entry({ changeSet: { id: "c", name: null, open: false } }), "app");
    expect(published).not.toHaveProperty("changeSetId");
    expect(changeTarget(entry({ subject: { id: "r1", removed: true } }), "app")).toBeUndefined();
  });

  it("opens a change set's review only while it is open, and a draft or release in Settings", () => {
    const changeSet = entry({
      kind: "change-set",
      changeSet: { id: "c", name: "S", open: true },
      subject: { id: "c" },
    });
    expect(changeTarget(changeSet, "app")).toMatchObject({ kind: "changeSetChanges", changeSetId: "c" });
    expect(changeTarget({ ...changeSet, changeSet: { id: "c", name: "S", open: false } }, "app")).toBeUndefined();
    expect(changeTarget(entry({ kind: "model", action: "created", subject: { id: "d" } }), undefined)).toEqual({
      kind: "settings",
      page: "model",
      draftId: "d",
    });
  });
});

describe("the period and the days", () => {
  it("starts a period that many days back, none for any time", () => {
    const now = new Date("2026-10-25T12:00:00Z");
    expect(periodSince("week", now)).toBe("2026-10-18T12:00:00.000Z");
    expect(periodSince(undefined, now)).toBeUndefined();
  });

  it("groups entries into runs of one day", () => {
    const now = new Date("2026-10-25T12:00:00");
    const days = byDay(
      [
        { occurredAt: "2026-10-25T09:00:00" },
        { occurredAt: "2026-10-25T08:00:00" },
        { occurredAt: "2026-10-24T16:00:00" },
      ],
      now,
    );
    expect(days.map((day) => [day.day, day.entries.length])).toEqual([
      ["Today", 2],
      ["Yesterday", 1],
    ]);
  });
});

describe("the way to someone's changes", () => {
  it("is offered only to a caller who would see something there", () => {
    const held = (key: string, instance: boolean, workspaces: string[] = []): HeldAnywhere => ({
      key,
      name: key,
      instance,
      workspaces: workspaces.map((item) => ({ key: item, label: item })),
    });
    expect(readsChanges([held("browse", false, ["main"])])).toBe(true);
    expect(readsChanges([held("model-authoring", true)])).toBe(true);
    expect(readsChanges([held("security-admin", true)])).toBe(false);
    expect(readsChanges(undefined)).toBe(false);
  });

  it("is an address of its own outside any workspace, with its filters", () => {
    const route = { kind: "changes", actorId: "p1", inWorkspace: "main", what: "record", period: "week" } as const;
    const path = routePath(route);
    expect(path).toBe("/changes?actorId=p1&workspace=main&kind=record&period=week");
    expect(parseRoute(testModel, "default", new URL(path, "http://x"))).toEqual(route);
    expect(parseRoute(testModel, "default", new URL("/changes?actorId=p1&kind=nothing", "http://x"))).toEqual({
      kind: "changes",
      actorId: "p1",
    });
  });
});

describe("grouping the steps on a model draft", () => {
  const step = (id: string, draft: string, overrides: Partial<ChangeEntry> = {}) =>
    entry({
      id,
      kind: "model",
      action: "updated",
      workspace: null,
      subject: { id: draft, name: draft === "d1" ? "Spring" : "Autumn" },
      ...overrides,
    });

  it("shows consecutive steps on one draft as one line with their count, newest first", () => {
    const items = groupDraftSteps([step("a", "d1"), step("b", "d1"), step("c", "d1", { action: "created" })]);
    expect(items).toHaveLength(1);
    const [group] = items;
    expect(group.kind).toBe("draft");
    if (group.kind !== "draft") return;
    expect(group.entries.map((item) => item.id)).toEqual(["a", "b", "c"]);
    expect(draftStepsTitle(group.entries.length, group.name)).toBe("3 steps on the draft “Spring”");
  });

  it("leaves a single step, other drafts and other changes as they are, in order", () => {
    const record = entry({ id: "r" });
    const items = groupDraftSteps([step("a", "d1"), record, step("b", "d1"), step("c", "d2"), step("d", "d2")]);
    expect(
      items.map((item) => (item.kind === "entry" ? item.entry.id : item.entries.map((e) => e.id).join("+"))),
    ).toEqual(["a", "r", "b", "c+d"]);
  });

  it("does not group releases", () => {
    const installed = (id: string) => step(id, "d1", { action: "installed" });
    expect(groupDraftSteps([installed("a"), installed("b")]).every((item) => item.kind === "entry")).toBe(true);
  });
});
