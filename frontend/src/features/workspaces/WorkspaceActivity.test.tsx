import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ai } from "@/api/aiClient";
import { api } from "@/api/client";
import { WorkspaceActivity } from "@/features/workspaces/WorkspaceActivity";
import { testModel } from "@/test/fixtures";

vi.mock("@/api/client", () => ({ api: { changes: vi.fn(), model: vi.fn() } }));
vi.mock("@/api/aiClient", () => ({ ai: { explainWorkspaceHistory: vi.fn() } }));
const offer = vi.hoisted(() => ({ value: undefined as unknown }));
vi.mock("@/features/settings/useWorkspaceAiOffer", () => ({ useHistoryAccountOffer: () => offer.value }));

describe("WorkspaceActivity with What changed (0.16 AO2)", () => {
  beforeEach(() => {
    vi.mocked(api.changes).mockReset().mockResolvedValue({ items: [], nextCursor: null, prevCursor: null });
    vi.mocked(api.model).mockReset().mockResolvedValue(testModel);
    vi.mocked(ai.explainWorkspaceHistory).mockReset();
    offer.value = { configured: true, provider: "Claude", sendLevel: "structure" };
  });

  it("is the Activity as before without the offer", async () => {
    offer.value = undefined;
    render(<WorkspaceActivity workspaceKey="north" onNavigate={vi.fn()} />);
    expect(await screen.findByText("No activity yet.")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "What changed" })).not.toBeInTheDocument();
  });

  it("narrows the list, in place, to the live changes a fact counted, and the way back widens it", async () => {
    vi.mocked(ai.explainWorkspaceHistory).mockResolvedValue({
      scope: "workspace",
      since: "2026-10-25T00:00:00Z",
      until: "2026-11-01T12:00:00Z",
      timeZone: "UTC",
      facts: [
        {
          id: "rc-1",
          kind: "records",
          text: "Delivery method: 214 records changed",
          count: 214,
          keys: {},
          link: {
            kind: "changes",
            id: null,
            query: { kind: ["record"], objectTypeKey: "delivery", action: "updated", live: true },
          },
        },
      ],
      statements: [{ text: "214 records changed.", factIds: ["rc-1"] }],
      removedStatements: 0,
      failure: null,
      cached: false,
      callId: "c1",
    });
    render(<WorkspaceActivity workspaceKey="north" onNavigate={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Explain this period" }));
    await screen.findByText("214 records changed.");
    fireEvent.click(screen.getByRole("button", { name: "Show them" }));
    await waitFor(() =>
      expect(api.changes).toHaveBeenLastCalledWith(
        expect.objectContaining({
          workspaceKey: "north",
          kinds: ["record"],
          objectTypeKey: "delivery",
          action: "updated",
          live: true,
          since: "2026-10-25T00:00:00Z",
          until: "2026-11-01T12:00:00Z",
        }),
      ),
    );
    expect(screen.getByText(/Narrowed by: Delivery method: 214 records changed/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Records" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(screen.getByRole("button", { name: "Show all activity" }));
    await waitFor(() => expect(vi.mocked(api.changes).mock.calls.at(-1)?.[0].live).toBeUndefined());
    expect(screen.queryByText(/Narrowed by/)).not.toBeInTheDocument();
  });
});
