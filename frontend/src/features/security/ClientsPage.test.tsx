import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { security } from "@/api/securityClient";
import type { Client } from "@/types";
import { ToastProvider } from "@/ui/Toast";
import { ClientsPage } from "./ClientsPage";

vi.mock("@/api/securityClient", () => ({
  security: {
    clientPage: vi.fn(),
    client: vi.fn(),
    rotateSecret: vi.fn(),
  },
}));
vi.mock("@/features/settings/useSystem", () => ({ useCapabilities: () => ({ capabilities: undefined }) }));
vi.mock("./permissions", async (original) => ({
  ...(await original<typeof import("./permissions")>()),
  useHeldAnywhere: () => [],
}));
vi.mock("./GrantsSection", () => ({ GrantsSection: () => null, useWorkspaceLabels: () => ({}) }));
vi.mock("./RecentActivity", () => ({ RecentActivity: () => null }));

const client = (active: boolean): Client =>
  ({
    id: "c1",
    name: "Billing sync",
    kind: "api",
    active,
    version: 3,
    createdAt: "2026-10-01T08:00:00Z",
    updatedAt: "2026-10-01T08:00:00Z",
    lastUsedAt: null,
    secrets: [],
    roles: [],
    consumerApis: [],
    createdBy: null,
  }) as unknown as Client;

function renderClient() {
  return render(
    <ToastProvider>
      <ClientsPage route={{ kind: "settings", page: "clients", clientId: "c1" }} onNavigate={vi.fn()} />
    </ToastProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(security.clientPage).mockResolvedValue({ items: [], nextCursor: null, totalCount: 0 } as never);
});

describe("Rotate a client's secret (0.13 DF2)", () => {
  it("offers it for a deactivated client, says the new secret works once it is restored, and rotates", async () => {
    vi.mocked(security.client).mockResolvedValue(client(false));
    vi.mocked(security.rotateSecret).mockResolvedValue({ ...client(false), secretId: "s2", secret: "rdm_new" });
    renderClient();
    fireEvent.click(await screen.findByRole("button", { name: "Rotate secret…" }));
    const dialog = await screen.findByRole("dialog", { name: "Rotate the secret of Billing sync" });
    expect(within(dialog).getByText(/takes effect when you restore it/)).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("radio", { name: "Stop it now" }));
    fireEvent.click(within(dialog).getByRole("button", { name: "Make a new secret" }));
    await waitFor(() =>
      expect(security.rotateSecret).toHaveBeenCalledWith("c1", { expectedVersion: 3, overlapHours: 0 }),
    );
  });

  it("keeps the usual wording for an active client", async () => {
    vi.mocked(security.client).mockResolvedValue(client(true));
    renderClient();
    fireEvent.click(await screen.findByRole("button", { name: "Rotate secret…" }));
    const dialog = await screen.findByRole("dialog", { name: "Rotate the secret of Billing sync" });
    expect(within(dialog).queryByText(/takes effect when you restore it/)).not.toBeInTheDocument();
  });
});
