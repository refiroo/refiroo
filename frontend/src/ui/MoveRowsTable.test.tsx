import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { testModel } from "@/test/fixtures";
import type { MoveRow } from "@/types";
import { MoveRowsTable } from "./MoveRowsTable";

vi.mock("@/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/api/client")>()),
  api: { moveRows: vi.fn() },
}));

const refused: MoveRow = {
  index: 2236,
  kind: "relationship",
  outcome: "refused",
  reasons: [{ code: "RELATION_CANDIDATE_REFUSED", message: "'Alpha' cannot be chosen at the from end", details: {} }],
  leftBehind: [],
  sourceType: "domain",
  relationTypeKey: "domain-contains-codelist",
  fromId: "a",
  toId: "b",
  fromName: "Alpha",
  toName: "Beta",
};
const record: MoveRow = {
  index: 3,
  kind: "record",
  outcome: "notMoved",
  reasons: [{ code: "TYPE_NOT_MAPPED", message: "Its type is not mapped", action: "mapType" }],
  leftBehind: [],
  sourceType: "codelist",
  sourceId: "c",
  name: "Gamma",
};

describe("MoveRowsTable (0.16)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.moveRows).mockResolvedValue({ items: [refused, record], nextCursor: null });
  });

  it("lists the filtered rows by number, what they are and the engine's reason with its code", async () => {
    render(
      <MoveRowsTable
        jobId="j1"
        filter={{ outcome: "refused", reason: "RELATION_CANDIDATE_REFUSED" }}
        source={testModel}
        target={testModel}
        label="Items"
        emptyMessage="None here."
      />,
    );
    expect(await screen.findByText("2,236")).toBeInTheDocument();
    expect(api.moveRows).toHaveBeenCalledWith(
      "j1",
      expect.objectContaining({ outcome: "refused", reason: "RELATION_CANDIDATE_REFUSED" }),
    );
    expect(screen.getByText(/Alpha → Beta/)).toBeInTheDocument();
    expect(screen.getByText("'Alpha' cannot be chosen at the from end")).toBeInTheDocument();
    expect(screen.getByText("RELATION_CANDIDATE_REFUSED")).toBeInTheDocument();
    // A record is its name and its type; without a link render it is plain text.
    expect(screen.getByText(/Gamma/)).toBeInTheDocument();
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("draws what the caller adds: a link on a name, the criteria and a fix", async () => {
    const onFix = vi.fn();
    render(
      <MoveRowsTable
        jobId="j1"
        filter={{}}
        source={testModel}
        target={testModel}
        label="Items"
        emptyMessage="None here."
        record={(row, end, name) => <a href={`#${row.index}-${end}`}>{name}</a>}
        criteria={(reason) => (reason.details ? <a href="#criteria">The criteria</a> : null)}
        fix={(row) => (
          <button type="button" onClick={() => onFix(row.index)}>
            Fix {row.index}
          </button>
        )}
      />,
    );
    expect(await screen.findByRole("link", { name: "Alpha" })).toHaveAttribute("href", "#2236-from");
    expect(screen.getByRole("link", { name: "Beta" })).toHaveAttribute("href", "#2236-to");
    expect(screen.getByRole("link", { name: "Gamma" })).toHaveAttribute("href", "#3-record");
    expect(screen.getAllByRole("link", { name: "The criteria" })).toHaveLength(1);
    fireEvent.click(screen.getByRole("button", { name: "Fix 3" }));
    expect(onFix).toHaveBeenCalledWith(3);
  });

  it("says so when no row is left", async () => {
    vi.mocked(api.moveRows).mockResolvedValue({ items: [], nextCursor: null });
    render(
      <MoveRowsTable
        jobId="j1"
        filter={{}}
        source={testModel}
        target={testModel}
        label="Items"
        emptyMessage="None here."
      />,
    );
    await waitFor(() => expect(screen.getByText("None here.")).toBeInTheDocument());
  });
});
