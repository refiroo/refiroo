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
    updateClient: vi.fn(),
  },
}));
vi.mock("@/state/useSystem", () => ({ useCapabilities: () => ({ capabilities: undefined }) }));
vi.mock("@/state/permissions", async (original) => ({
  ...(await original<typeof import("@/state/permissions")>()),
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

function renderClient(onNavigate = vi.fn(), clientId: string | null = "c1") {
  return render(
    <ToastProvider>
      <ClientsPage
        route={{ kind: "settings", page: "clients", clientId: clientId ?? undefined }}
        onNavigate={onNavigate}
      />
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
    fireEvent.click(within(dialog).getByRole("button", { name: "Rotate secret" }));
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

describe("Rename a client where it stands (0.17 UX1)", () => {
  it("saves through the same call, with no dialog, and offers Undo", async () => {
    vi.mocked(security.client).mockResolvedValue(client(true));
    vi.mocked(security.updateClient).mockResolvedValue({ ...client(true), name: "Billing", version: 4 });
    renderClient();
    fireEvent.click(await screen.findByRole("button", { name: /Edit Name:/ }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Billing" } });
    fireEvent.keyDown(screen.getByLabelText("Name"), { key: "Enter" });
    await waitFor(() =>
      expect(security.updateClient).toHaveBeenCalledWith("c1", { expectedVersion: 3, name: "Billing" }),
    );
    expect(await screen.findByText("Renamed.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Undo" }));
    await waitFor(() =>
      expect(security.updateClient).toHaveBeenLastCalledWith("c1", { expectedVersion: 4, name: "Billing sync" }),
    );
  });
});

describe("A client's name left empty where it stands (0.17 UX2)", () => {
  it("says it needs a value under the field and writes nothing, and leaving it as it was closes it", async () => {
    vi.mocked(security.client).mockResolvedValue(client(true));
    renderClient();
    fireEvent.click(await screen.findByRole("button", { name: /Edit Name:/ }));
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "" } });
    fireEvent.keyDown(screen.getByLabelText("Name"), { key: "Enter" });
    expect(await screen.findByText("Name needs a value.")).toBeInTheDocument();
    expect(security.updateClient).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    fireEvent.click(await screen.findByRole("button", { name: /Edit Name:/ }));
    fireEvent.keyDown(screen.getByLabelText("Name"), { key: "Enter" });
    await waitFor(() => expect(screen.queryByLabelText("Name")).not.toBeInTheDocument());
    expect(security.updateClient).not.toHaveBeenCalled();
  });
});

describe("the list and a client's page (0.17 ST1)", () => {
  it("lists clients, and a row opens the client's page", async () => {
    vi.mocked(security.clientPage).mockResolvedValue({
      items: [client(true)],
      nextCursor: null,
      totalCount: 1,
    } as never);
    const onNavigate = vi.fn();
    renderClient(onNavigate, null);
    fireEvent.click(await screen.findByRole("button", { name: /Billing sync/ }));
    expect(onNavigate).toHaveBeenCalledWith({ kind: "settings", page: "clients", clientId: "c1" });
  });

  it("goes back to the list from the page's trail, with Deactivate in the ⋯ menu", async () => {
    vi.mocked(security.client).mockResolvedValue(client(true));
    const onNavigate = vi.fn();
    renderClient(onNavigate);
    expect(await screen.findByRole("button", { name: "Rotate secret…" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Deactivate" })).toBeNull();
    fireEvent.click(screen.getByRole("link", { name: "Clients" }));
    expect(onNavigate).toHaveBeenCalledWith({ kind: "settings", page: "clients" });
  });
});
