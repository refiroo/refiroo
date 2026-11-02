import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ai } from "@/api/aiClient";
import { api } from "@/api/client";
import { HistoryPanel } from "@/features/objects/panels/HistoryPanel";
import { domainObject } from "@/test/fixtures";

vi.mock("@/api/client", () => ({ api: { objectHistory: vi.fn() } }));
vi.mock("@/api/aiClient", () => ({ ai: { explainRecordHistory: vi.fn() } }));
const offer = vi.hoisted(() => ({ value: undefined as unknown }));
vi.mock("@/features/settings/useWorkspaceAiOffer", () => ({ useHistoryAccountOffer: () => offer.value }));

describe("HistoryPanel with What changed (0.16 AO2)", () => {
  beforeEach(() => {
    vi.mocked(api.objectHistory).mockReset().mockResolvedValue({ items: [], nextCursor: null });
    vi.mocked(ai.explainRecordHistory).mockReset();
    offer.value = { configured: true, provider: "Claude", sendLevel: "values" };
  });

  it("draws no account without the workspace, or without the offer", () => {
    render(<HistoryPanel objectTypeKey="domain" objectId={domainObject.id} />);
    expect(screen.queryByRole("heading", { name: "What changed" })).not.toBeInTheDocument();
    offer.value = undefined;
    render(<HistoryPanel objectTypeKey="domain" objectId={domainObject.id} workspaceKey="north" />);
    expect(screen.queryByRole("heading", { name: "What changed" })).not.toBeInTheDocument();
  });

  it("asks for the record's account and narrows the timeline to the live changes a fact counted", async () => {
    vi.mocked(ai.explainRecordHistory).mockResolvedValue({
      scope: "record",
      since: "2026-10-02T00:00:00Z",
      until: "2026-11-01T12:00:00Z",
      timeZone: "UTC",
      facts: [
        {
          id: "fl-1",
          kind: "fields",
          text: "Label: changed twice",
          count: 2,
          keys: {},
          link: { kind: "history", id: null, query: { kind: "values", live: true } },
        },
      ],
      statements: [{ text: "The label changed twice.", factIds: ["fl-1"] }],
      removedStatements: 0,
      failure: null,
      cached: false,
      callId: "c1",
    });
    render(<HistoryPanel objectTypeKey="domain" objectId={domainObject.id} workspaceKey="north" />);
    expect(screen.getByRole("combobox", { name: "Period" })).toHaveValue("30");
    fireEvent.click(screen.getByRole("button", { name: "Explain this period" }));
    await screen.findByText("The label changed twice.");
    fireEvent.click(screen.getByRole("button", { name: "Show them" }));
    await waitFor(() =>
      expect(api.objectHistory).toHaveBeenLastCalledWith(
        "domain",
        domainObject.id,
        expect.objectContaining({ kind: "values", live: true }),
      ),
    );
    expect(screen.getByRole("radio", { name: "Values" })).toBeChecked();
    expect(screen.getByText(/Narrowed by: Label: changed twice/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Show all history" }));
    await waitFor(() =>
      expect(vi.mocked(api.objectHistory).mock.calls.at(-1)?.[2]).toEqual(expect.objectContaining({ live: undefined })),
    );
    expect(screen.queryByText(/Narrowed by/)).not.toBeInTheDocument();
  });
});
