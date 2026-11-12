import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { capabilitiesFixture } from "@/test/capabilities";
import { EVERY_GROUP, heldAnywhereFixture } from "@/test/permissions";
import type { DryRun } from "@/types";
import { findings, lookAtWorkbook, startsFromWorkbook, waitFor, workspaceNameOfFile } from "./fromWorkbook";

const ALL = capabilitiesFixture({ manageModel: true });

const run = (sources: object[], total: number): DryRun =>
  ({
    state: "completed",
    summary: {
      coverage: "complete",
      rows: { total, run: total },
      sources,
      difference: null,
      previousJobId: null,
      ranAt: "",
    },
  }) as unknown as DryRun;

describe("startsFromWorkbook", () => {
  it("is offered to a person who holds every step's group at the instance", () => {
    expect(startsFromWorkbook(heldAnywhereFixture(EVERY_GROUP).items, ALL)).toBe(true);
  });

  it("is left out, not disabled, when one group is missing", () => {
    for (const missing of ["workspace-admin", "model-authoring", "model-release", "bulk"]) {
      const groups = EVERY_GROUP.filter((group) => group !== missing);
      expect(startsFromWorkbook(heldAnywhereFixture(groups).items, ALL), missing).toBe(false);
    }
  });

  it("takes Install a model in place of Model release", () => {
    const groups = [...EVERY_GROUP.filter((group) => group !== "model-release"), "model-install"];
    expect(startsFromWorkbook(heldAnywhereFixture(groups).items, ALL)).toBe(true);
  });

  it("needs a group held at the instance, since the new workspace has no grants yet", () => {
    const held = heldAnywhereFixture(EVERY_GROUP).items.map((item) =>
      item.key === "bulk" ? { ...item, instance: false, workspaces: [{ key: "a", label: "A" }] } : item,
    );
    expect(startsFromWorkbook(held, ALL)).toBe(false);
  });

  it("is left out while the deployment switches a step off or nothing is read yet", () => {
    const held = heldAnywhereFixture(EVERY_GROUP).items;
    expect(startsFromWorkbook(held, capabilitiesFixture({ manageModel: false }))).toBe(false);
    expect(startsFromWorkbook(held, capabilitiesFixture({ manageModel: true, manageWorkspaces: false }))).toBe(false);
    expect(startsFromWorkbook(undefined, ALL)).toBe(false);
    expect(startsFromWorkbook(held, undefined)).toBe(false);
  });
});

describe("findings", () => {
  it("counts every list's rows, what loads and what does not, with the reason", () => {
    const answer = findings(
      run(
        [
          {
            source: 0,
            sheet: "Items",
            objectTypeKey: "item",
            rows: 40,
            skippedRows: 2,
            rejections: [{ code: "MISSING_RECORD_KEY", rows: 3 }],
          },
          { source: 1, sheet: "Colours", objectTypeKey: "colour", rows: 6, rejections: [] },
        ],
        46,
      ),
      { item: "Item" },
      { MISSING_RECORD_KEY: "The row has no key" },
    );
    expect(answer.rows).toBe(46);
    expect(answer.refused).toBe(3);
    expect(answer.lists.map((list) => [list.list, list.rows, list.loads])).toEqual([
      ["Item", 40, 35],
      ["colour", 6, 6],
    ]);
    expect(answer.lists[0].refused).toEqual([{ code: "MISSING_RECORD_KEY", rows: 3, reason: "The row has no key" }]);
  });

  it("finds nothing in a run without a summary", () => {
    expect(findings({ state: "failed", summary: null } as unknown as DryRun, {})).toEqual({
      lists: [],
      rows: 0,
      loads: 0,
      refused: 0,
    });
  });
});

describe("workspaceNameOfFile", () => {
  it("names the workspace for the file", () => {
    expect(workspaceNameOfFile("office-supplies.xlsx")).toBe("Office supplies");
  });
});

describe("waitFor", () => {
  it("reads again until the answer is the one wanted", async () => {
    let calls = 0;
    const value = await waitFor(
      async () => ++calls,
      (n) => n === 3,
      { every: 1 },
    );
    expect(value).toBe(3);
  });

  it("gives up with a sentence, not a trace", async () => {
    await expect(
      waitFor(
        async () => 0,
        () => false,
        { every: 1, limitMs: 5 },
      ),
    ).rejects.toThrow("took too long");
  });
});

describe("lookAtWorkbook", () => {
  const made = { id: "d1", version: 3, model: { objectTypes: [] } };
  const book = new File(["x"], "office-supplies.xlsx");

  function readsAWorkbook(open: number) {
    vi.spyOn(api, "system").mockResolvedValue({ schemaLanguages: ["1.0"] } as never);
    vi.spyOn(api, "createModelDraft").mockResolvedValue(made as never);
    vi.spyOn(api, "uploadSourceFile").mockResolvedValue({ id: "f1" } as never);
    vi.spyOn(api, "sourceFile").mockResolvedValue({ profile: { state: "completed" } } as never);
    vi.spyOn(api, "proposeFromWorkbook").mockResolvedValue(undefined as never);
    vi.spyOn(api, "modelDraftInference").mockResolvedValue({ state: "completed", counts: { open } } as never);
    vi.spyOn(api, "modelDraft").mockResolvedValue(made as never);
  }

  afterEach(() => vi.restoreAllMocks());

  it("returns the draft without a dry run when the inference has no open proposal", async () => {
    readsAWorkbook(0);
    const apply = vi.spyOn(api, "applyProposals");
    const dry = vi.spyOn(api, "modelDraftDryRun");
    const looked = await lookAtWorkbook(book, "Office supplies", () => undefined);
    expect(looked.draft).toBe(made);
    expect(looked.dryRun).toBeUndefined();
    expect(apply).not.toHaveBeenCalled();
    expect(dry).not.toHaveBeenCalled();
  });

  it("removes the draft it made when the reading fails", async () => {
    readsAWorkbook(0);
    vi.spyOn(api, "sourceFile").mockResolvedValue({
      profile: { state: "failed", error: { message: "The workbook could not be opened." } },
    } as never);
    const removed = vi.spyOn(api, "deleteModelDraft").mockResolvedValue(undefined as never);
    await expect(lookAtWorkbook(book, "Office supplies", () => undefined)).rejects.toThrow("could not be opened");
    expect(removed).toHaveBeenCalledWith("d1", 3);
  });
});
