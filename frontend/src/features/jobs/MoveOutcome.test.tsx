import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { testModel } from "@/test/fixtures";
import type { Job, MoveCounts, MoveRow, MoveSummary } from "@/types";
import { MoveOutcome } from "./MoveOutcome";

vi.mock("@/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/api/client")>()),
  api: { moveRows: vi.fn() },
}));
// Each workspace is read under the model shown; a person who authors models.
vi.mock("@/model/workspaceModels", () => ({ useWorkspaceModel: (_: unknown, fallback: unknown) => fallback }));
const holds = vi.hoisted(() => ({ model: true }));
vi.mock("@/state/useMe", () => ({ useHoldsGroup: (key: string) => holds.model && key === "model-authoring" }));

const counts = (part: Partial<MoveCounts>): MoveCounts => ({
  create: 0,
  update: 0,
  updateOriginal: 0,
  refused: 0,
  notMoved: 0,
  ...part,
});

/** A copy of 3 records and 2 relationships made, one relationship refused by the target's criteria. */
const summary: MoveSummary = {
  coverage: "complete",
  rows: 6,
  counts: counts({ create: 5, refused: 1 }),
  types: [{ sourceType: "domain", targetType: "domain", counts: counts({ create: 3 }) }],
  relationships: [
    {
      relationTypeKey: "domain-contains-codelist",
      targetRelationTypeKey: "domain-contains-codelist",
      counts: counts({ create: 2, refused: 1 }),
    },
  ],
  reasons: [{ code: "RELATION_CANDIDATE_REFUSED", count: 1 }],
  attributesNotCarried: [],
  possibleDuplicates: 0,
  mapping: { key: "map", version: 3 },
  sourceWorkspaceKey: "default",
  targetWorkspaceKey: "copy-2",
  targetReleaseId: "rel-2",
  mode: "copy",
  targetChangeSetId: "cs1",
  sourceChangeSetId: null,
};

const job = (move: MoveSummary, confirmedAt: string | null = "2026-11-02T12:00:00Z"): Job =>
  ({ id: "j1", kind: "move", workspaceKey: "copy-2", confirmedAt, parameters: {}, move }) as unknown as Job;

const refusedRow: MoveRow = {
  index: 4,
  kind: "relationship",
  outcome: "refused",
  reasons: [
    {
      code: "RELATION_CANDIDATE_REFUSED",
      message: "'Alpha' cannot be chosen at the from end of 'contains'",
      details: { criteria: "/objectTypeRelations/domain-contains-codelist/domain/codelist/candidates/from" },
    },
  ],
  leftBehind: [],
  sourceType: "domain",
  relationTypeKey: "domain-contains-codelist",
  direction: "outgoing",
  fromId: "a",
  toId: "b",
  fromName: "Alpha",
  toName: "Beta",
};

function show(move: MoveSummary, onNavigate = vi.fn()) {
  render(<MoveOutcome job={job(move)} summary={move} model={testModel} onNavigate={onNavigate} />);
  return onNavigate;
}

describe("MoveOutcome (the job page of a move)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    holds.model = true;
    vi.mocked(api.moveRows).mockResolvedValue({ items: [refusedRow], nextCursor: null });
  });

  it("says what happened, counts by type and lists the refused items first, linked to the source records", async () => {
    const onNavigate = show(summary);
    expect(
      screen.getByText(/5 of 6 items were made in copy-2\. 1 were refused and are not there\./),
    ).toBeInTheDocument();
    expect(screen.getByText(/Nothing changed in default\./)).toBeInTheDocument();
    const cards = screen.getByRole("group", { name: "What the move did" });
    expect(within(cards).getByText("records made").previousSibling).toHaveTextContent("3");
    expect(within(cards).getByText("relationships made").previousSibling).toHaveTextContent("2");
    expect(within(cards).getByText("refused").previousSibling).toHaveTextContent("1");

    const byType = screen.getByRole("group", { name: "The move by type" });
    expect(within(byType).getByText(/^Relationships: /)).toBeInTheDocument();

    // Refused is shown first, as the rows of that outcome.
    const link = await screen.findByRole("link", { name: "Alpha" });
    expect(api.moveRows).toHaveBeenCalledWith("j1", expect.objectContaining({ outcome: "refused" }));
    fireEvent.click(link);
    expect(onNavigate).toHaveBeenCalledWith(
      expect.objectContaining({ kind: "detail", objectTypeKey: "domain", objectId: "a", workspaceKey: "default" }),
    );
    // The other end's type comes from the criteria path the refusal names.
    fireEvent.click(screen.getByRole("link", { name: "Beta" }));
    expect(onNavigate).toHaveBeenLastCalledWith(expect.objectContaining({ objectTypeKey: "codelist", objectId: "b" }));
    // The refusal leads to the target model's release for a person who authors models.
    fireEvent.click(screen.getByRole("link", { name: "The criteria" }));
    expect(onNavigate).toHaveBeenLastCalledWith({ kind: "settings", page: "model", releaseId: "rel-2" });
  });

  it("filters by outcome and by reason", async () => {
    show(summary);
    await screen.findByRole("link", { name: "Alpha" });
    fireEvent.click(screen.getByRole("radio", { name: "Made (5)" }));
    await waitFor(() =>
      expect(api.moveRows).toHaveBeenLastCalledWith("j1", expect.objectContaining({ outcome: "create" })),
    );
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "RELATION_CANDIDATE_REFUSED" } });
    await waitFor(() =>
      expect(api.moveRows).toHaveBeenLastCalledWith(
        "j1",
        expect.objectContaining({ outcome: "create", reason: "RELATION_CANDIDATE_REFUSED" }),
      ),
    );
  });

  it("offers no link to the criteria to a person who cannot open the model", async () => {
    holds.model = false;
    show(summary);
    await screen.findByRole("link", { name: "Alpha" });
    expect(screen.queryByRole("link", { name: "The criteria" })).toBeNull();
  });

  it("shows a job whose stored summary has no relationship types: the rest is as it was", async () => {
    show({ ...summary, relationships: undefined } as unknown as MoveSummary);
    const cards = screen.getByRole("group", { name: "What the move did" });
    // Relationships made are the made items the record types do not hold.
    expect(within(cards).getByText("relationships made").previousSibling).toHaveTextContent("2");
    expect(within(screen.getByRole("group", { name: "The move by type" })).queryByText(/Relationships:/)).toBeNull();
    await screen.findByRole("link", { name: "Alpha" });
  });

  it("says what a dry run would do when nothing is loaded", () => {
    render(<MoveOutcome job={job(summary, null)} summary={summary} model={testModel} />);
    expect(screen.getByText(/5 of 6 items would be made in copy-2/)).toBeInTheDocument();
  });
});
