import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { testModel } from "@/test/fixtures";
import type { Job, MigrationRow, MigrationSummary } from "@/types";
import { MigrationOutcome } from "./MigrationOutcome";

vi.mock("@/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/api/client")>()),
  api: { migrationRows: vi.fn(), modelRelease: vi.fn() },
}));

const summary: MigrationSummary = {
  targetReleaseId: "rel-2",
  currentReleaseId: "rel-1",
  expectedVersion: 1,
  feedPosition: 10,
  counts: { conversion: 4, reclassified: 2, loss: 0, refused: 1 },
};
const job = { id: "m1", kind: "migration", workspaceKey: "west", confirmedAt: null, parameters: {} } as unknown as Job;
const refused: MigrationRow = {
  index: 0,
  outcome: "refused",
  code: "REQUIRED_ATTRIBUTE_MISSING",
  objectId: "o1",
  objectName: "Alpha",
  objectTypeKey: "domain",
  path: "/objects/o1/attributes/code/value",
};

describe("MigrationOutcome (the job page of a migration)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.modelRelease).mockResolvedValue({ model: testModel } as never);
    vi.mocked(api.migrationRows).mockResolvedValue({ items: [refused], nextCursor: null });
  });

  it("counts what it converted, changed and refused, and lists the refused items first", async () => {
    render(<MigrationOutcome job={job} summary={summary} model={testModel} />);
    const cards = screen.getByRole("group", { name: "What the migration did" });
    expect(within(cards).getByText("Must be fixed").previousSibling).toHaveTextContent("1");
    expect(within(cards).getByText("Type changed").previousSibling).toHaveTextContent("2");
    expect(await screen.findByText("Alpha")).toBeInTheDocument();
    expect(api.migrationRows).toHaveBeenCalledWith("m1", expect.objectContaining({ status: "refused" }));
    // Named under the target release once both are read.
    await waitFor(() => expect(screen.getByText(/to release 0\.3\.0/)).toBeInTheDocument());
    expect(screen.getByText("Empty, and required in 0.3.0")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("radio", { name: "Converted (4)" }));
    await waitFor(() =>
      expect(api.migrationRows).toHaveBeenLastCalledWith("m1", expect.objectContaining({ status: "conversion" })),
    );
  });
});
