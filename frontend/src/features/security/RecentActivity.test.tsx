import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { security } from "@/api/securityClient";
import { RecentActivity } from "@/features/security/RecentActivity";
import type { SecurityEvent } from "@/types";

vi.mock("@/api/securityClient", () => ({ security: { securityEvents: vi.fn() } }));
vi.mock("./GrantsSection", () => ({ useWorkspaceLabels: () => new Map() }));

const signIn = (index: number): SecurityEvent =>
  ({
    id: `event-${index}`,
    aggregateType: "sign-in",
    aggregateId: "person",
    action: "succeeded",
    occurredAt: new Date(Date.now() - index * 3_600_000).toISOString(),
    details: {},
    actor: null,
  }) as unknown as SecurityEvent;

describe("a person's recent activity (0.12 RA1)", () => {
  it("shows the 10 newest by day, 20 more on Load more, Show fewer, and asks the API for one kind", async () => {
    vi.mocked(security.securityEvents)
      .mockResolvedValueOnce({ items: Array.from({ length: 10 }, (_, index) => signIn(index)), nextCursor: "older" })
      .mockResolvedValueOnce({ items: Array.from({ length: 4 }, (_, index) => signIn(index + 10)), nextCursor: null })
      .mockResolvedValueOnce({ items: [], nextCursor: null });
    render(<RecentActivity principal={{ id: "person", name: "Anna", version: 1 }} />);
    expect(await screen.findByText("Showing 10 entries")).toBeInTheDocument();
    expect(security.securityEvents).toHaveBeenLastCalledWith("person", undefined, 10, []);
    expect(screen.getAllByRole("heading", { level: 3 }).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Load more" }));
    expect(await screen.findByText("Showing 14 entries")).toBeInTheDocument();
    expect(security.securityEvents).toHaveBeenLastCalledWith("person", "older", 20, []);
    fireEvent.click(screen.getByRole("button", { name: "Show fewer" }));
    expect(screen.getByText("Showing 10 entries")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("radio", { name: "Roles and groups" }));
    await waitFor(() =>
      expect(security.securityEvents).toHaveBeenLastCalledWith("person", undefined, 10, ["grant", "group", "role"]),
    );
    expect(await screen.findByText("No activity of this kind.")).toBeInTheDocument();
  });
});
