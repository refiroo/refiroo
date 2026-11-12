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
    deleteGrant: vi.fn(),
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

const roleGrant = (role: string, workspaceKey: string, applications: string[] = []) =>
  ({
    id: `${role}-${workspaceKey}-${applications.join("")}`,
    principal: client,
    role: { key: role, name: role },
    scope: { instance: false, workspaceKey, applications, recordTypes: [] },
  }) as unknown as Grant;

describe("setting a client's consumer APIs by ticking a grid (0.12 U9, 0.17)", () => {
  it("is the client's access, with a Save that stays off until something changes", async () => {
    render(<GrantDialog who={client} onClose={vi.fn()} onChanged={vi.fn()} />);
    const dialog = await screen.findByRole("dialog", { name: "Test client's access" });
    expect(await within(dialog).findByLabelText("RDM in all workspaces")).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Save" })).toBeDisabled();
    expect(within(dialog).queryByText(/Ticked and grey/)).not.toBeInTheDocument();
  });

  it("ticks a whole row with its heading and makes one grant per cell", async () => {
    vi.mocked(security.createGrant).mockImplementation(async (body) =>
      created(body.consumerApi ?? "", "workspaceKey" in body.scope ? body.scope.workspaceKey : ""),
    );
    const onChanged = vi.fn();
    render(<GrantDialog who={client} onClose={vi.fn()} onChanged={onChanged} />);
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(await within(dialog).findByLabelText("RDM in all workspaces"));
    expect(within(dialog).getByText(/Test client will read RDM in Default and Pilot\./)).toBeInTheDocument();
    expect(within(dialog).getByText("not in this model")).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    await waitFor(() => expect(onChanged).toHaveBeenCalled());
    expect(security.createGrant).toHaveBeenCalledTimes(2);
    expect(onChanged.mock.calls[0]?.[0].added).toHaveLength(2);
    expect(onChanged.mock.calls[0]?.[0].removed).toHaveLength(0);
  });

  it("shows what is held as a normal tick; unticking removes it on Save, ticking adds, and the sentence says both", async () => {
    vi.mocked(security.grantsOf).mockResolvedValue({
      items: [created("rdm", "default"), created("rdm-translation", "default")],
      nextCursor: null,
    } as never);
    vi.mocked(security.createGrant).mockImplementation(async (body) =>
      created(body.consumerApi ?? "", "workspaceKey" in body.scope ? body.scope.workspaceKey : ""),
    );
    vi.mocked(security.deleteGrant).mockResolvedValue(undefined as never);
    const onChanged = vi.fn();
    render(<GrantDialog who={client} onClose={vi.fn()} onChanged={onChanged} />);
    const dialog = await screen.findByRole("dialog");
    const held = await within(dialog).findByLabelText("RDM in Default");
    expect(held).toBeChecked();
    expect(held).toBeEnabled();
    expect(within(dialog).getByRole("button", { name: "Save" })).toBeDisabled();
    fireEvent.click(within(dialog).getByLabelText("Translations in Default"));
    fireEvent.click(within(dialog).getByLabelText("RDM in Pilot"));
    expect(
      within(dialog).getByText("Test client will read RDM in Pilot; Translations in Default is removed."),
    ).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    await waitFor(() => expect(onChanged).toHaveBeenCalled());
    expect(security.deleteGrant).toHaveBeenCalledTimes(1);
    expect(security.deleteGrant).toHaveBeenCalledWith("rdm-translation-default");
    expect(security.createGrant).toHaveBeenCalledTimes(1);
    const change = onChanged.mock.calls[0]?.[0];
    expect(change.removed.map((grant: Grant) => grant.id)).toEqual(["rdm-translation-default"]);
    expect(change.added.map((grant: Grant) => grant.id)).toEqual(["rdm-pilot"]);
  });

  it("is Save-disabled again after unticking and re-ticking the same cell", async () => {
    vi.mocked(security.grantsOf).mockResolvedValue({ items: [created("rdm", "default")], nextCursor: null } as never);
    render(<GrantDialog who={client} onClose={vi.fn()} onChanged={vi.fn()} />);
    const dialog = await screen.findByRole("dialog");
    const held = await within(dialog).findByLabelText("RDM in Default");
    fireEvent.click(held);
    expect(within(dialog).getByRole("button", { name: "Save" })).toBeEnabled();
    expect(within(dialog).getByText("Test client will no longer read RDM in Default.")).toBeInTheDocument();
    fireEvent.click(held);
    expect(within(dialog).getByRole("button", { name: "Save" })).toBeDisabled();
  });

  it("keeps a refused change as it was while the others are made, and reports it", async () => {
    vi.mocked(security.grantsOf).mockResolvedValue({ items: [created("rdm", "default")], nextCursor: null } as never);
    vi.mocked(security.deleteGrant).mockRejectedValue(new Error("The grant is protected"));
    vi.mocked(security.createGrant).mockImplementation(async (body) =>
      created(body.consumerApi ?? "", "workspaceKey" in body.scope ? body.scope.workspaceKey : ""),
    );
    const onChanged = vi.fn();
    const onClose = vi.fn();
    render(<GrantDialog who={client} onClose={onClose} onChanged={onChanged} />);
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(await within(dialog).findByLabelText("RDM in Default"));
    fireEvent.click(within(dialog).getByLabelText("RDM in Pilot"));
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    expect(await within(dialog).findByText("1 could not be saved")).toBeInTheDocument();
    expect(within(dialog).getByText(/Removing RDM in Default: The grant is protected/)).toBeInTheDocument();
    expect(within(dialog).getByText("The others were saved.")).toBeInTheDocument();
    expect(onChanged).not.toHaveBeenCalled();
    // The refused removal is still a pending change; the made grant is not.
    expect(within(dialog).getByLabelText("RDM in Pilot")).toBeChecked();
    expect(within(dialog).getByLabelText("RDM in Default")).not.toBeChecked();
    expect(within(dialog).getByRole("button", { name: "Save" })).toBeEnabled();
    fireEvent.click(within(dialog).getAllByRole("button", { name: "Close" }).at(-1)!);
    expect(onChanged).toHaveBeenCalledTimes(1);
    expect(onChanged.mock.calls[0]?.[0].added).toHaveLength(1);
    expect(onClose).not.toHaveBeenCalled();
  });

  it("says what is already granted in words when it only grants (from a workspace's Access)", async () => {
    vi.mocked(security.grantsOf).mockResolvedValue({ items: [created("rdm", "default")], nextCursor: null } as never);
    render(<GrantDialog workspace={{ key: "default", label: "Default" }} onClose={vi.fn()} onChanged={vi.fn()} />);
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "pick client" }));
    fireEvent.click(await within(dialog).findByLabelText("Consumer APIs"));
    expect(await within(dialog).findByText("already granted")).toBeInTheDocument();
    expect(within(dialog).queryByLabelText("RDM in Default")).not.toBeInTheDocument();
    fireEvent.click(await within(dialog).findByLabelText("Translations in Default"));
    expect(within(dialog).getByRole("button", { name: "Add grant" })).toBeEnabled();
  });
});

describe("setting roles in a workspace (0.17)", () => {
  const workspace = { key: "default", label: "Default" };
  beforeEach(() => {
    vi.mocked(security.roles).mockResolvedValue({
      items: [
        { key: "reader", name: "Reader", actionGroups: [] },
        { key: "editor", name: "Editor", actionGroups: [] },
      ],
      nextCursor: null,
    } as never);
  });

  it("starts the held roles ticked, removes an unticked one and leaves a narrowed grant alone", async () => {
    vi.mocked(security.grantsOf).mockResolvedValue({
      items: [roleGrant("reader", "default"), roleGrant("editor", "default", ["a"])],
      nextCursor: null,
    } as never);
    vi.mocked(security.deleteGrant).mockResolvedValue(undefined as never);
    const onChanged = vi.fn();
    render(<GrantDialog who={client} workspace={workspace} onClose={vi.fn()} onChanged={onChanged} />);
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(await within(dialog).findByLabelText("Roles"));
    expect(await within(dialog).findByLabelText("Reader")).toBeChecked();
    expect(within(dialog).getByLabelText("Editor")).not.toBeChecked();
    fireEvent.click(within(dialog).getByLabelText("Reader"));
    expect(within(dialog).getByText("Test client will no longer hold Reader in Default.")).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    await waitFor(() => expect(onChanged).toHaveBeenCalled());
    expect(security.deleteGrant).toHaveBeenCalledTimes(1);
    expect(security.deleteGrant).toHaveBeenCalledWith("reader-default-");
  });
});

describe("consumer APIs are a client's alone", () => {
  const workspace = { key: "default", label: "Default" };

  it("offers roles only until a client is chosen, and not for a person or a group", async () => {
    render(<GrantDialog workspace={workspace} onClose={vi.fn()} onChanged={vi.fn()} />);
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
    render(<GrantDialog workspace={workspace} onClose={vi.fn()} onChanged={vi.fn()} />);
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
