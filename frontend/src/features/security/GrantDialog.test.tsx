import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { security } from "@/api/securityClient";
import type { Grant } from "@/types";
import { GrantDialog } from "./GrantDialog";

vi.mock("@/api/client", () => ({ api: { workspaces: vi.fn() } }));
vi.mock("@/api/securityClient", () => ({
  security: {
    roles: vi.fn(),
    actionGroups: vi.fn(),
    grantsOf: vi.fn(),
    grantOptions: vi.fn(),
    createGrant: vi.fn(),
  },
}));

// The picker is replaced by buttons, so a test chooses the holder without a search.
vi.mock("./PrincipalPicker", () => ({
  PrincipalPicker: ({
    onPick,
  }: {
    onPick: (principal: { kind: string; id: string; name: string } | undefined) => void;
  }) => (
    <div>
      <button type="button" onClick={() => onPick({ kind: "user", id: "u1", name: "Anna" })}>
        pick person
      </button>
      <button type="button" onClick={() => onPick({ kind: "group", id: "g1", name: "Editors" })}>
        pick group
      </button>
      <button type="button" onClick={() => onPick({ kind: "client", id: "c1", name: "Test client" })}>
        pick client
      </button>
    </div>
  ),
}));

const client = { kind: "client" as const, id: "c1", name: "Test client" };
const created = (consumerApi: string, workspaceKey: string) =>
  ({
    id: `${consumerApi}-${workspaceKey}`,
    principal: client,
    role: null,
    consumerApi: { key: consumerApi, name: consumerApi },
    scope: { instance: false, workspaceKey, applications: [], recordTypes: [] },
  }) as unknown as Grant;

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(security.roles).mockResolvedValue({ items: [], nextCursor: null } as never);
  vi.mocked(security.actionGroups).mockResolvedValue([]);
  vi.mocked(security.grantsOf).mockResolvedValue({ items: [], nextCursor: null } as never);
  vi.mocked(api.workspaces).mockResolvedValue({
    items: [
      { key: "default", label: "Default" },
      { key: "pilot", label: "Pilot" },
    ],
    nextCursor: null,
  } as never);
  vi.mocked(security.grantOptions).mockImplementation(async (key: string) => ({
    applications: [],
    recordTypes: [],
    // The pilot's model does not declare the translations API.
    consumerApis: [
      { key: "rdm", name: "RDM" },
      ...(key === "default" ? [{ key: "rdm-translation", name: "Translations" }] : []),
    ],
  }));
});

describe("granting consumer APIs by ticking a grid (0.12 U9)", () => {
  it("ticks a whole row with its heading and makes one grant per cell", async () => {
    vi.mocked(security.createGrant).mockImplementation(async (body) =>
      created(body.consumerApi ?? "", "workspaceKey" in body.scope ? body.scope.workspaceKey : ""),
    );
    const onGranted = vi.fn();
    render(<GrantDialog who={client} onClose={vi.fn()} onGranted={onGranted} />);
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(await within(dialog).findByLabelText("RDM in all workspaces"));
    expect(
      within(dialog).getByText(/2 grants will be made: Test client reads RDM in Default and Pilot/),
    ).toBeInTheDocument();
    expect(within(dialog).getByText("not in this model")).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "Grant 2" }));
    await waitFor(() => expect(onGranted).toHaveBeenCalled());
    expect(security.createGrant).toHaveBeenCalledTimes(2);
    expect(onGranted.mock.calls[0]?.[0]).toHaveLength(2);
  });

  it("shows what is already granted locked, and does not send it again", async () => {
    vi.mocked(security.grantsOf).mockResolvedValue({ items: [created("rdm", "default")], nextCursor: null } as never);
    render(<GrantDialog who={client} onClose={vi.fn()} onGranted={vi.fn()} />);
    const dialog = await screen.findByRole("dialog");
    const held = await within(dialog).findByLabelText("RDM in Default: already granted");
    expect(held).toBeDisabled();
    fireEvent.click(within(dialog).getByLabelText("RDM in all workspaces"));
    expect(within(dialog).getByRole("button", { name: "Grant" })).toBeEnabled();
    expect(within(dialog).getByText(/^1 grant will be made: Test client reads RDM in Pilot/)).toBeInTheDocument();
  });

  it("keeps a refused grant ticked with its reason while the others are made", async () => {
    vi.mocked(security.createGrant).mockImplementation(async (body) => {
      if ("workspaceKey" in body.scope && body.scope.workspaceKey === "pilot")
        throw new Error("The model no longer declares it");
      return created(body.consumerApi ?? "", "default");
    });
    const onGranted = vi.fn();
    const onClose = vi.fn();
    render(<GrantDialog who={client} onClose={onClose} onGranted={onGranted} />);
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(await within(dialog).findByLabelText("RDM in all workspaces"));
    fireEvent.click(within(dialog).getByRole("button", { name: "Grant 2" }));
    expect(await within(dialog).findByText("1 could not be granted")).toBeInTheDocument();
    expect(within(dialog).getByText(/RDM in Pilot: The model no longer declares it/)).toBeInTheDocument();
    expect(onGranted).not.toHaveBeenCalled();
    fireEvent.click(within(dialog).getAllByRole("button", { name: "Close" }).at(-1)!);
    expect(onGranted).toHaveBeenCalledTimes(1);
    expect(onClose).not.toHaveBeenCalled();
  });
});

describe("consumer APIs are a client's alone", () => {
  const workspace = { key: "default", label: "Default" };

  it("offers roles only until a client is chosen, and not for a person or a group", async () => {
    render(<GrantDialog workspace={workspace} onClose={vi.fn()} onGranted={vi.fn()} />);
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).queryByText("Consumer APIs")).not.toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "pick person" }));
    expect(within(dialog).queryByText("Consumer APIs")).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText(/RDM in/)).not.toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "pick group" }));
    expect(within(dialog).queryByText("Consumer APIs")).not.toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "pick client" }));
    expect(await within(dialog).findByText("Consumer APIs")).toBeInTheDocument();
  });

  it("clears ticked consumer APIs when the holder changes from a client to a person", async () => {
    render(<GrantDialog workspace={workspace} onClose={vi.fn()} onGranted={vi.fn()} />);
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "pick client" }));
    fireEvent.click(await within(dialog).findByLabelText("Consumer APIs"));
    fireEvent.click(await within(dialog).findByLabelText("RDM in Default"));
    expect(within(dialog).getByText(/1 grant will be made: Test client reads RDM/)).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "pick person" }));
    expect(within(dialog).queryByText(/reads RDM/)).not.toBeInTheDocument();
    expect(within(dialog).queryByText("Consumer APIs")).not.toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "pick client" }));
    expect(within(dialog).queryByText(/reads RDM/)).not.toBeInTheDocument();
  });
});
