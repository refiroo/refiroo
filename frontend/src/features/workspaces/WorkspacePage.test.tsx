import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { foldRepeats, WorkspacePage } from "@/features/workspaces/WorkspacePage";
import { capabilitiesFixture } from "@/test/capabilities";
import { testAvailability, testModel, testWorkspaceModel } from "@/test/fixtures";
import { EVERY_GROUP, heldAnywhereFixture, permissionsFixture } from "@/test/permissions";
import { ToastProvider } from "@/ui/Toast";
import type { ChangeEntry, EngineModel, OwnChangeSet, RouteState } from "@/types";

vi.mock("@/features/inbox/InboxButton", () => ({ InboxButton: () => <span /> }));
vi.mock("@/app/SettingsMenu", () => ({ AccountMenu: () => <span /> }));
vi.mock("@/app/instanceProduct", () => ({ useInstanceProduct: () => ({ name: "refiroo", description: "" }) }));

const workspace = {
  key: "stops",
  label: "Graubünden stops",
  status: "active" as const,
  version: 1,
  createdAt: "2026-09-05T00:00:00Z",
  updatedAt: "2026-09-05T00:00:00Z",
  model: testWorkspaceModel,
  availability: testAvailability,
};

const waiting = (id: string, name: string, extra: Partial<OwnChangeSet> = {}) =>
  ({
    id,
    workspaceKey: "stops",
    workspaceLabel: "Graubünden stops",
    name,
    changeCount: 14,
    updatedAt: "2026-11-12T10:00:00Z",
    submission: null,
    ...extra,
  }) as unknown as OwnChangeSet;

/** The test model with a second list in its application, so a shelf can hold two. */
const twoLists: EngineModel = {
  ...testModel,
  applications: testModel.applications.map((application) => ({
    ...application,
    views: [
      ...application.views,
      { key: "codelists", name: "Codelists", type: "table", objectTypeKey: "codelist", config: { columns: ["name"] } },
    ] as never,
  })),
};

const PINS_KEY = "rdm:workspace-pins:v1:stops";
const shelfOf = (...viewKeys: string[]) =>
  JSON.stringify(viewKeys.map((viewKey) => ({ applicationKey: "test-app", viewKey })));

function setUp(groups: string[], manages = true, model: EngineModel = testModel, changes: ChangeEntry[] = []) {
  vi.spyOn(api, "workspace").mockResolvedValue(workspace as never);
  vi.spyOn(api, "myPermissions").mockImplementation(async (key) => permissionsFixture(key, groups));
  vi.spyOn(api, "myActionGroups").mockResolvedValue(heldAnywhereFixture(groups));
  vi.spyOn(api, "capabilities").mockResolvedValue(
    capabilitiesFixture({ manageWorkspaces: manages, manageModel: true }),
  );
  vi.spyOn(api, "changes").mockResolvedValue({ items: changes, nextCursor: null });
  vi.spyOn(api, "myChangeSets").mockResolvedValue({
    items: [
      waiting("cs1", "Didok sync", { submission: { state: "submitted" } as never }),
      waiting("cs2", "Elsewhere", { workspaceKey: "other" }),
    ],
    nextCursor: null,
  });
  const onNavigate = vi.fn<(route: RouteState) => void>();
  render(
    <ToastProvider>
      <WorkspacePage model={model} workspaceKey="stops" onNavigate={onNavigate} onHome={vi.fn()} />
    </ToastProvider>,
  );
  return onNavigate;
}

describe("WorkspacePage (0.17 SH1)", () => {
  let stored: Map<string, string>;
  beforeEach(() => {
    stored = new Map();
    vi.stubGlobal("localStorage", {
      getItem: (key: string) => stored.get(key) ?? null,
      setItem: (key: string, value: string) => stored.set(key, value),
      removeItem: (key: string) => stored.delete(key),
    });
    vi.spyOn(api, "findRecords").mockResolvedValue({ items: [], nextCursor: null });
    vi.spyOn(api, "countRecords").mockImplementation(async (_workspace, type) => (type === "domain" ? 229 : 7));
  });
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("shows the workspace, its applications, the person's waiting change sets here and opens each", async () => {
    const onNavigate = setUp(EVERY_GROUP);
    expect(await screen.findByRole("heading", { name: "Graubünden stops", level: 1 })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("link", { name: /Test App/ }));
    expect(onNavigate).toHaveBeenCalledWith(
      expect.objectContaining({ kind: "list", applicationKey: "test-app", workspaceKey: "stops" }),
    );
    // Only this workspace's change sets, with how much each changes and its state.
    const rows = await screen.findByRole("region", { name: /Needs you/ });
    expect(within(rows).getByText("Didok sync")).toBeInTheDocument();
    expect(within(rows).getByText(/14 changes · waits for approval/)).toBeInTheDocument();
    expect(within(rows).queryByText("Elsewhere")).not.toBeInTheDocument();
    fireEvent.click(within(rows).getByRole("button", { name: "Review Didok sync" }));
    expect(onNavigate).toHaveBeenLastCalledWith(
      expect.objectContaining({ kind: "changeSetChanges", workspaceKey: "stops", changeSetId: "cs1" }),
    );
  });

  it("offers Edit model and the ⋯ menu's pages to a person who may use them", async () => {
    setUp(EVERY_GROUP);
    expect(await screen.findByRole("button", { name: "Edit model" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Workspace actions" }));
    const menu = within(await screen.findByRole("menu"));
    expect(menu.getAllByRole("menuitem").map((item) => item.textContent)).toEqual([
      "Rename",
      "Access",
      "Approval",
      "Copy or move",
      "Retire",
    ]);
  });

  it("hides what the person may not do, never disabling it", async () => {
    setUp(["browse"], false);
    await screen.findByRole("heading", { name: "Graubünden stops", level: 1 });
    await waitFor(() => expect(api.myActionGroups).toHaveBeenCalled());
    expect(screen.queryByRole("button", { name: "Edit model" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Workspace actions" })).not.toBeInTheDocument();
  });

  it("opens the Settings page a menu item names", async () => {
    const onNavigate = setUp(EVERY_GROUP);
    fireEvent.click(await screen.findByRole("button", { name: "Workspace actions" }));
    fireEvent.click(await screen.findByRole("menuitem", { name: "Access" }));
    expect(onNavigate).toHaveBeenCalledWith({
      kind: "settings",
      page: "workspaces",
      workspaceKey: "stops",
      workspaceTab: "access",
    });
  });
  it("says the shelf is empty and offers to add a list", async () => {
    setUp(EVERY_GROUP);
    expect(await screen.findByText("Nothing on your shelf yet")).toBeInTheDocument();
    expect(screen.getByText("Add a list")).toBeInTheDocument();
  });

  it("draws the stored pins in their order with each list's record count", async () => {
    stored.set(PINS_KEY, shelfOf("codelists", "domains"));
    setUp(EVERY_GROUP, true, twoLists);
    const shelf = within(await screen.findByRole("region", { name: /Your shelf/ }));
    expect(await shelf.findByText("229 · Test App")).toBeInTheDocument();
    expect(shelf.getByText("7 · Test App")).toBeInTheDocument();
    expect(shelf.getAllByRole("listitem").map((tile) => tile.querySelector(".ws-pin-name")?.textContent)).toEqual([
      "Codelists",
      "Domains",
    ]);
    expect(api.countRecords).toHaveBeenCalledWith("stops", "domain");
  });

  it("moves and takes off a pin from the tile's menu, and keeps the order", async () => {
    stored.set(PINS_KEY, shelfOf("codelists", "domains"));
    setUp(EVERY_GROUP, true, twoLists);
    await screen.findByText("229 · Test App");
    fireEvent.click(screen.getByRole("button", { name: "Codelists on your shelf" }));
    // The first tile cannot move earlier.
    expect(
      within(await screen.findByRole("menu"))
        .getAllByRole("menuitem")
        .map((item) => item.textContent),
    ).toEqual(["Move later", "Take off your shelf"]);
    fireEvent.click(screen.getByRole("menuitem", { name: "Move later" }));
    await waitFor(() =>
      expect(JSON.parse(stored.get(PINS_KEY) ?? "[]").map((pin: { viewKey: string }) => pin.viewKey)).toEqual([
        "domains",
        "codelists",
      ]),
    );
    fireEvent.click(screen.getByRole("button", { name: "Codelists on your shelf" }));
    expect(
      within(await screen.findByRole("menu"))
        .getAllByRole("menuitem")
        .map((item) => item.textContent),
    ).toEqual(["Move earlier", "Take off your shelf"]);
    fireEvent.click(screen.getByRole("menuitem", { name: "Move earlier" }));
    await waitFor(() =>
      expect(JSON.parse(stored.get(PINS_KEY) ?? "[]").map((pin: { viewKey: string }) => pin.viewKey)).toEqual([
        "codelists",
        "domains",
      ]),
    );
    fireEvent.click(screen.getByRole("button", { name: "Domains on your shelf" }));
    fireEvent.click(await screen.findByRole("menuitem", { name: "Take off your shelf" }));
    await waitFor(() =>
      expect(JSON.parse(stored.get(PINS_KEY) ?? "[]").map((pin: { viewKey: string }) => pin.viewKey)).toEqual([
        "codelists",
      ]),
    );
    expect(screen.queryByRole("button", { name: "Domains on your shelf" })).not.toBeInTheDocument();
  });

  it("does not draw a pin whose view the model lacks", async () => {
    stored.set(PINS_KEY, shelfOf("gone", "domains"));
    setUp(EVERY_GROUP);
    const shelf = within(await screen.findByRole("region", { name: /Your shelf/ }));
    expect(await shelf.findByText("229 · Test App")).toBeInTheDocument();
    expect(shelf.getAllByRole("listitem")).toHaveLength(1);
    expect(screen.queryByText("gone")).not.toBeInTheDocument();
  });

  it("shows each application's lists as links", async () => {
    const onNavigate = setUp(EVERY_GROUP, true, twoLists);
    const lists = within(await screen.findByRole("list", { name: "Lists of Test App" }));
    expect(lists.getAllByRole("link").map((link) => link.textContent)).toEqual(["Domains", "Codelists"]);
    fireEvent.click(lists.getByRole("link", { name: "Codelists" }));
    expect(onNavigate).toHaveBeenCalledWith(
      expect.objectContaining({
        kind: "list",
        applicationKey: "test-app",
        viewKey: "codelists",
        workspaceKey: "stops",
      }),
    );
  });

  it("folds consecutive changes of one kind by one actor into one line", async () => {
    const entry = (id: string, actor: ChangeEntry["actor"], kind: ChangeEntry["kind"] = "record"): ChangeEntry =>
      ({
        id,
        occurredAt: "2026-11-12T10:00:00Z",
        kind,
        action: "updated",
        workspace: { key: "stops", label: "Graubünden stops" },
        changeSet: null,
        subject: { id, name: `Record ${id}`, applicationKey: "test-app", objectTypeKey: "domain" },
        changedFields: [],
        attributes: [],
        cause: { kind: "api" },
        actor,
      }) as ChangeEntry;
    const ana = { kind: "user" as const, id: "u1", name: "Ana" };
    const ben = { kind: "user" as const, id: "u2", name: "Ben" };
    const items = [entry("1", ana), entry("2", ana), entry("3", ana), entry("4", ana), entry("5", ben)];
    const folded = foldRepeats(items);
    expect(folded.map((line) => line.times)).toEqual([4, 1]);
    expect(foldRepeats([entry("1", ana), entry("2", ben), entry("3", ana)]).map((line) => line.times)).toEqual([
      1, 1, 1,
    ]);
    expect(foldRepeats([entry("1", ana), entry("2", ana, "relationship")]).map((line) => line.times)).toEqual([1, 1]);

    setUp(EVERY_GROUP, true, testModel, items);
    const latest = within(await screen.findByRole("region", { name: /What changed/ }));
    expect(await latest.findByText("4 in a row")).toBeInTheDocument();
    expect(latest.getAllByRole("listitem")).toHaveLength(2);
  });
});
