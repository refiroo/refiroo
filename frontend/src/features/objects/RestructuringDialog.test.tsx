import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "@/api/client";
import { RestructuringDialog, summaryText, type RestructuringSetup } from "@/features/objects/RestructuringDialog";
import { starterModel } from "@/test/placements";
import type { EngineModel, ObjectItem, RestructuringPreview, RestructuringRecord } from "@/types";

afterEach(() => vi.restoreAllMocks());

const model: EngineModel = starterModel;

const system = { id: "s1", name: "Lab system", objectTypeKey: "system" };
const group = { id: "g1", name: "Chemistry", objectTypeKey: "system-group" };
const sodium: ObjectItem = {
  id: "v1",
  applicationKey: "rdm-systems",
  workspaceKey: "default",
  objectTypeKey: "system-value",
  name: "Sodium",
  parentObjectId: group.id,
  path: [system, group, { id: "v1", name: "Sodium", objectTypeKey: "system-value" }],
  attributes: [],
  version: 3,
} as unknown as ObjectItem;

const summary = {
  recordCount: 1,
  typeChangeCount: 1,
  moveCount: 0,
  createdCount: 0,
  removedCount: 0,
  valuesWithoutPlaceCount: 1,
  relationshipsWithoutPlaceCount: 0,
  restoredCount: 0,
  inputsNeededCount: 0,
  refusalCount: 0,
};

function planRecord(overrides: Partial<RestructuringRecord> = {}): RestructuringRecord {
  return {
    objectId: sodium.id,
    name: "Sodium",
    path: [system, group, { id: sodium.id, name: "Sodium", objectTypeKey: "system-group" }],
    before: { objectTypeKey: "system-value", parentObjectId: group.id },
    after: { objectTypeKey: "system-group", parentObjectId: group.id },
    outcomes: ["typeChanged"],
    attributes: [
      { attributeTypeKey: "group-code", from: "value-code", outcome: "mapped", value: "NA" },
      { attributeTypeKey: "active", from: "active", outcome: "kept", value: true },
    ],
    withoutPlace: {
      attributes: [
        { attributeTypeKey: "value-name", value: "Sodium" },
        { attributeTypeKey: "active", value: false },
      ],
      relationships: [],
    },
    restoredRelationships: [],
    inputsNeeded: [],
    refusals: [],
    ...overrides,
  };
}

function plan(overrides: Partial<RestructuringPreview> = {}): RestructuringPreview {
  return {
    changeSetId: "cs-1",
    changeSetVersion: 7,
    planDigest: "digest-1",
    status: "ready",
    summary,
    typeQuestions: [],
    pairs: [
      {
        fromObjectTypeKey: "system-value",
        toObjectTypeKey: "system-group",
        recordCount: 1,
        restore: true,
        attributes: [
          {
            attributeTypeKey: "group-code",
            from: "value-code",
            rule: "uniqueRequired",
            alternatives: ["value-name", "external-id"],
            kept: 0,
            mapped: 1,
            restored: 0,
            inputs: 0,
            empty: 0,
          },
        ],
        withoutPlace: [{ attributeTypeKey: "value-name", count: 1 }],
        relations: [],
      },
    ],
    refusals: [],
    refusalCount: 0,
    refusalsTruncated: false,
    records: [planRecord()],
    nextCursor: null,
    prevCursor: null,
    totalCount: 1,
    startIndex: 0,
    ...overrides,
  };
}

function open(setup: RestructuringSetup) {
  const props = { onClose: vi.fn(), onApplied: vi.fn(), onReview: vi.fn() };
  render(<RestructuringDialog model={model} workspaceKey="default" setup={setup} label={setup.item.name} {...props} />);
  return props;
}

const changeType: RestructuringSetup = { kind: "changeType", item: sodium, options: ["system-group"] };
const lastRequest = (spy: ReturnType<typeof vi.spyOn>) => spy.mock.calls.at(-1)![0];

describe("RestructuringDialog", () => {
  it("previews a type change by record and by type pair, applies the reviewed plan and links to the review", async () => {
    const preview = vi.spyOn(api, "previewRestructuring").mockResolvedValue(plan());
    const apply = vi.spyOn(api, "applyRestructuring").mockResolvedValue({
      operationId: "op",
      changeSetId: "cs-1",
      changeSetVersion: 8,
      summary,
      createdObjectId: null,
    });
    const { onApplied, onReview, onClose } = open(changeType);
    const dialog = screen.getByRole("dialog", { name: "Change the type of Sodium" });
    expect(within(dialog).getByText("New type").nextSibling).toHaveTextContent("System group");

    expect(await within(dialog).findByText("Ready to apply")).toBeInTheDocument();
    expect(lastRequest(preview)).toEqual({
      operation: { kind: "changeType", objectId: sodium.id, objectTypeKey: "system-group" },
      choices: { types: [], mappings: [] },
      inputs: [],
    });
    // By record: the type on both sides, each value's origin and what has no place.
    const record = within(dialog).getByRole("listitem");
    expect(within(record).getByText("System value → System group")).toBeInTheDocument();
    expect(within(record).getByText("from Value code")).toBeInTheDocument();
    // A boolean reads as it does everywhere else, not as `false` (C5).
    expect(
      within(record).getByText(/Without a place, kept in history: Value name “Sodium”, Active “No”$/),
    ).toBeInTheDocument();

    // By type: the pair's mapping, with the rule that suggested it.
    fireEvent.click(within(dialog).getByRole("tab", { name: "By type (1)" }));
    const source = within(dialog).getByRole("combobox", { name: "Group code: value from" });
    expect(source).toHaveValue("value-code");
    expect(
      within(source)
        .getAllByRole("option")
        .map((option) => option.textContent),
    ).toEqual(["Value code", "Value name", "External ID", "No value"]);

    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    await within(dialog).findByText("Applied to the change set");
    expect(apply).toHaveBeenCalledWith({
      ...lastRequest(preview),
      expectedChangeSetVersion: 7,
      planDigest: "digest-1",
    });
    expect(onApplied).toHaveBeenCalledOnce();
    fireEvent.click(within(dialog).getByRole("button", { name: "Review the change set" }));
    expect(onReview).toHaveBeenCalledOnce();
    fireEvent.click(within(dialog).getByRole("button", { name: "Done" }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("changes a mapping in place, which re-plans with the pair's choice", async () => {
    const preview = vi.spyOn(api, "previewRestructuring").mockResolvedValue(plan());
    open(changeType);
    await screen.findByText("Ready to apply");
    fireEvent.click(screen.getByRole("tab", { name: "By type (1)" }));
    fireEvent.change(screen.getByRole("combobox", { name: "Group code: value from" }), { target: { value: "" } });
    await waitFor(() =>
      expect(lastRequest(preview).choices.mappings).toEqual([
        {
          fromObjectTypeKey: "system-value",
          toObjectTypeKey: "system-group",
          attributes: [{ attributeTypeKey: "group-code", from: null }],
          restore: true,
        },
      ]),
    );
  });

  it("asks a type question and the inputs a record needs, re-planning with each answer", async () => {
    const question = {
      objectTypeKey: "system-value",
      parentObjectTypeKey: "system",
      options: ["system-group", "system-value"],
      chosen: null,
      recordCount: 2,
    };
    const needing = plan({
      status: "needsInput",
      summary: { ...summary, inputsNeededCount: 1 },
      typeQuestions: [question],
      records: [
        planRecord({
          attributes: [{ attributeTypeKey: "group-code", from: null, outcome: "empty", value: null }],
          inputsNeeded: [{ kind: "attribute", key: "group-code", reason: "required" }],
        }),
      ],
    });
    const preview = vi.spyOn(api, "previewRestructuring").mockResolvedValue(needing);
    const apply = vi.spyOn(api, "applyRestructuring");
    open({ kind: "move", item: sodium, parent: { ...system, path: [system] } });
    expect(await screen.findByText("Some answers are needed")).toBeInTheDocument();
    // What is asked starts its own sentence (C5).
    expect(screen.getByText("Some answers are needed").closest(".notice")).toHaveTextContent(
      /\. Choose the types asked for below, and give the 1 value the records need \(Show: Needing input\)\.$/,
    );
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
    expect(lastRequest(preview).operation).toEqual({ kind: "move", objectId: sodium.id, parentObjectId: system.id });

    const legend = screen.getByRole("group", { name: "System values under a system (2) become" });
    fireEvent.click(within(legend).getByRole("radio", { name: "System group" }));
    await waitFor(() =>
      expect(lastRequest(preview).choices.types).toEqual([
        { objectTypeKey: "system-value", parentObjectTypeKey: "system", newObjectTypeKey: "system-group" },
      ]),
    );

    const code = screen.getByRole("textbox", { name: "Group code" });
    expect(screen.getByText("Required by the new type")).toBeInTheDocument();
    preview.mockResolvedValue(plan());
    fireEvent.change(code, { target: { value: "NA" } });
    await waitFor(() =>
      expect(lastRequest(preview).inputs).toEqual([
        { objectId: sodium.id, attributes: [{ attributeTypeKey: "group-code", value: "NA" }], relations: [] },
      ]),
    );
    expect(await screen.findByText("Ready to apply")).toBeInTheDocument();
    // The field stays where it was typed in once its value is accepted.
    expect(screen.getByRole("textbox", { name: "Group code" })).toBe(code);
    expect(apply).not.toHaveBeenCalled();
  });

  it("shows why a plan is refused and does not apply it", async () => {
    vi.spyOn(api, "previewRestructuring").mockResolvedValue(
      plan({
        status: "refused",
        summary: { ...summary, refusalCount: 1 },
        refusals: [{ code: "noPossibleType", message: "Records below Chemistry have no type they can take." }],
        refusalCount: 1,
        records: [
          planRecord({
            refusals: [{ code: "uniqueness", message: "Group code NA is taken", conflictingObjectId: "g9" }],
          }),
        ],
      }),
    );
    open({ kind: "removeLevel", item: { ...sodium, objectTypeKey: "system-group", name: "Chemistry" } });
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("This cannot be applied");
    expect(alert).toHaveTextContent("No type can stand here: Records below Chemistry have no type they can take.");
    expect(screen.getByText("A value is already taken: Group code NA is taken")).toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "Records in the plan" })).getByText("Refused"),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
  });

  it("re-plans when the change set moved on since the preview, writing nothing", async () => {
    const preview = vi.spyOn(api, "previewRestructuring").mockResolvedValue(plan());
    vi.spyOn(api, "applyRestructuring").mockRejectedValue(
      new ApiError(409, "RESTRUCTURING_PLAN_CHANGED", "The plan changed."),
    );
    const { onApplied } = open(changeType);
    await screen.findByText("Ready to apply");
    const calls = preview.mock.calls.length;
    preview.mockResolvedValue(plan({ planDigest: "digest-2", changeSetVersion: 8 }));
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("The plan changed")).toBeInTheDocument();
    await waitFor(() => expect(preview.mock.calls.length).toBeGreaterThan(calls));
    expect(onApplied).not.toHaveBeenCalled();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("plans a new level only once it has a name, and reports a request the engine refuses", async () => {
    const preview = vi
      .spyOn(api, "previewRestructuring")
      .mockRejectedValue(new ApiError(422, "RESTRUCTURING_TOO_LARGE", "More than 500 records would change."));
    vi.spyOn(api, "objects").mockResolvedValue({ items: [sodium], nextCursor: null, totalCount: 1, startIndex: 0 });
    open({
      kind: "insertLevel",
      item: sodium,
      options: ["system-group"],
      siblingTypes: ["system-group", "system-value"],
    });
    expect(screen.getByText("Name the new level to see what changes.")).toBeInTheDocument();
    expect(preview).not.toHaveBeenCalled();
    fireEvent.change(screen.getByRole("textbox", { name: "Name of the new level" }), { target: { value: "Salts" } });
    expect(await screen.findByText("More than 500 records would change.")).toBeInTheDocument();
    expect(lastRequest(preview).operation).toEqual({
      kind: "insertLevel",
      parentObjectId: group.id,
      childObjectIds: [sodium.id],
      objectTypeKey: "system-group",
      name: "Salts",
    });
  });

  it("groups siblings chosen from the list under a new level, one type at a time", async () => {
    const potassium = {
      ...sodium,
      id: "v2",
      name: "Potassium",
      path: [system, group, { ...sodium.path[2], id: "v2" }],
    };
    const chloride = { ...sodium, id: "g2", name: "Chloride", objectTypeKey: "system-group" };
    const objects = vi.spyOn(api, "objects").mockImplementation(async (type) => {
      const items = type === "system-value" ? [potassium, sodium] : [chloride];
      return { items, nextCursor: null, totalCount: items.length, startIndex: 0 };
    });
    const preview = vi.spyOn(api, "previewRestructuring").mockResolvedValue(plan());
    open({
      kind: "insertLevel",
      item: sodium,
      options: ["system-group"],
      siblingTypes: ["system-group", "system-value"],
    });
    const siblings = screen.getByRole("group", { name: /Records to move under the new level/ });
    // The record's own type is listed first, with the record chosen.
    expect(await within(siblings).findByRole("checkbox", { name: /^Sodium/ })).toBeChecked();
    expect(objects).toHaveBeenCalledWith(
      "system-value",
      expect.objectContaining({ applicationKey: "rdm-systems", parentObjectId: group.id, workspaceKey: "default" }),
    );
    fireEvent.change(screen.getByRole("textbox", { name: "Name of the new level" }), { target: { value: "Salts" } });
    fireEvent.click(within(siblings).getByRole("checkbox", { name: /^Potassium/ }));
    fireEvent.change(within(siblings).getByRole("combobox", { name: "Type" }), { target: { value: "system-group" } });
    fireEvent.click(await within(siblings).findByRole("checkbox", { name: /^Chloride/ }));
    expect(within(siblings).getByText("(3 chosen)")).toBeInTheDocument();
    await waitFor(() =>
      expect(lastRequest(preview).operation).toMatchObject({
        kind: "insertLevel",
        parentObjectId: group.id,
        childObjectIds: [sodium.id, potassium.id, chloride.id],
      }),
    );

    // With nothing chosen there is nothing to plan.
    fireEvent.click(within(siblings).getByRole("checkbox", { name: /^Chloride/ }));
    fireEvent.change(within(siblings).getByRole("combobox", { name: "Type" }), { target: { value: "system-value" } });
    fireEvent.click(await within(siblings).findByRole("checkbox", { name: /^Sodium/ }));
    fireEvent.click(within(siblings).getByRole("checkbox", { name: /^Potassium/ }));
    expect(await screen.findByText("Choose at least one record to move under the new level.")).toBeInTheDocument();
  });

  it("summarises a plan's counts in words, leaving out zeros", () => {
    expect(summaryText(summary)).toBe("1 type change, 1 value without a place, kept in history");
    expect(summaryText({ ...summary, typeChangeCount: 3, moveCount: 1, createdCount: 1, restoredCount: 2 })).toBe(
      "3 type changes, 1 move, 1 record created, 1 value without a place, kept in history, 2 values or relationships restored from an earlier type change",
    );
    expect(summaryText({ ...summary, typeChangeCount: 0, valuesWithoutPlaceCount: 0 })).toBe("Nothing changes");
  });
});
