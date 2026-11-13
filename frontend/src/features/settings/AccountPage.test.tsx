import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import { signOut } from "@/api/session";
import { workspaceHue } from "@/model/workspaceTile";
import { ToastProvider } from "@/ui/Toast";
import { AccountPage } from "./AccountPage";

vi.mock("@/api/client", () => ({
  api: {
    me: vi.fn(),
    mySessions: vi.fn(),
    workspaces: vi.fn(),
    myGrants: vi.fn(),
    myPermissions: vi.fn(),
    model: vi.fn(),
    endMySession: vi.fn(async () => undefined),
    endAllMySessions: vi.fn(async () => undefined),
    changePassword: vi.fn(),
    // Their own panels are tested in SecondFactorPanel.test and PasskeysPanel.test.
    myPasskeys: vi.fn(async () => []),
    mySecondFactor: vi.fn(async () => ({
      enabled: false,
      confirmedAt: null,
      recoveryCodesLeft: 0,
      passkeys: 0,
      required: false,
    })),
  },
}));
vi.mock("@/api/session", () => ({ signOut: vi.fn(async () => undefined) }));

const firefox = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.5; rv:131.0) Gecko/20100101 Firefox/131.0";
const iphone =
  "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1";

const session = (id: string, current: boolean, userAgent: string, application: string | null = null) => ({
  id,
  current,
  signedInWith: "password",
  application,
  userAgent,
  createdAt: "2026-10-23T08:12:00Z",
  lastUsedAt: "2026-10-23T09:00:00Z",
  endsAt: "2026-10-23T21:00:00Z",
});

function grant(
  id: string,
  key: string,
  name: string,
  scope: {
    instance?: boolean;
    workspaceKey?: string;
    recordTypes?: string[];
    recordTypeNames?: string[];
    applicationNames?: string[];
  },
  principal: { kind: "user" | "group"; id: string; name: string } = { kind: "user", id: "u1", name: "Ana Ferreira" },
) {
  return {
    id,
    principal,
    role: { key, name },
    scope: {
      instance: scope.instance ?? false,
      workspaceKey: scope.workspaceKey ?? null,
      applications: [],
      recordTypes: scope.recordTypes ?? [],
      applicationNames: scope.applicationNames ?? [],
      recordTypeNames: scope.recordTypeNames ?? [],
    },
    createdAt: "2026-10-23T08:00:00Z",
  };
}

/** Serve /me/permissions from a map of grant id to the action groups it gives. */
function permissions(held: Record<string, string[]>) {
  vi.mocked(api.myPermissions).mockResolvedValue({
    workspaceKey: "default",
    workspaceLabel: "Default",
    roles: [],
    actionGroups: Object.entries(held).flatMap(([grantId, keys]) =>
      keys.map((key) => ({
        key,
        name: key,
        applications: [],
        recordTypes: [],
        sources: [{ grantId, role: { key: "r", name: "R" }, scope: "workspace" as const, group: null }],
      })),
    ),
  });
}

const onNavigate = vi.fn();

function renderPage() {
  render(
    <ToastProvider>
      <AccountPage onNavigate={onNavigate} />
    </ToastProvider>,
  );
}

describe("Settings › Account (0.12 I2)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.me).mockResolvedValue({
      id: "u1",
      kind: "user",
      name: "Ana Ferreira",
      email: "ana@example.org",
      lastSignInAt: "2026-10-23T08:12:00Z",
      signedInWith: "password",
      sessionId: "s1",
      signInManaged: false,
    });
    vi.mocked(api.mySessions).mockResolvedValue([session("s1", true, firefox), session("s2", false, iphone)]);
    vi.mocked(api.myGrants).mockResolvedValue([]);
    vi.mocked(api.model).mockResolvedValue({
      applications: [
        { key: "operators", name: "Operators", defaultView: "all", objectTypeKeys: ["operator", "depot"] },
        { key: "timetables", name: "Timetables", defaultView: "all", objectTypeKeys: ["timetable", "codelist"] },
      ],
      objectTypes: [
        { key: "operator", name: "Operator" },
        { key: "depot", name: "Depot" },
        { key: "timetable", name: "Timetable" },
        { key: "codelist", name: "Codelist" },
      ],
    } as never);
    vi.mocked(api.workspaces).mockResolvedValue({
      items: [
        { key: "default", label: "Default" },
        { key: "field-stations", label: "Field stations" },
      ] as never,
      nextCursor: null,
    });
  });

  it("shows the person and where they are signed in, and signs out another browser", async () => {
    renderPage();
    const you = await screen.findByRole("region", { name: "You" });
    expect(within(you).getByText("Ana Ferreira")).toBeInTheDocument();
    expect(within(you).getByText("Signed in with your password")).toBeInTheDocument();
    const table = await screen.findByRole("list", { name: "Where you’re signed in" });
    expect(within(table).getByText("This browser")).toBeInTheDocument();
    fireEvent.click(within(table).getByRole("button", { name: "Sign out Safari on iOS" }));
    await waitFor(() => expect(api.endMySession).toHaveBeenCalledWith("s2"));
    await waitFor(() => expect(api.mySessions).toHaveBeenCalledTimes(2));
    await waitFor(() =>
      expect(within(table).getByRole("button", { name: "Sign out Firefox on macOS, this browser" })).toBeEnabled(),
    );
    fireEvent.click(within(table).getByRole("button", { name: "Sign out Firefox on macOS, this browser" }));
    expect(signOut).toHaveBeenCalledTimes(1);
  });

  it("hides the password, passkeys, second factor and other browsers when an administrator manages the sign-in", async () => {
    vi.mocked(api.me).mockResolvedValue({
      id: "u1",
      kind: "user",
      name: "Ana Ferreira",
      email: "ana@example.org",
      lastSignInAt: null,
      signedInWith: "password",
      sessionId: "s1",
      signInManaged: true,
    });
    renderPage();
    expect(await screen.findByText("An administrator manages the sign-in of this account.")).toBeInTheDocument();
    for (const name of ["Change password", "Sign out everywhere", "Set up an authenticator app", "Add a passkey"])
      expect(screen.queryByRole("button", { name })).toBeNull();
    expect(screen.queryByRole("list", { name: "Where you’re signed in" })).toBeNull();
    expect(api.mySessions).not.toHaveBeenCalled();
    expect(api.myPasskeys).not.toHaveBeenCalled();
    expect(api.mySecondFactor).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Sign out" })).toBeEnabled();
  });

  it("names the assistant a session was opened for", async () => {
    vi.mocked(api.mySessions).mockResolvedValue([
      session("s1", true, firefox),
      session("s3", false, "", "Claude Code"),
    ]);
    renderPage();
    const list = await screen.findByRole("list", { name: "Where you’re signed in" });
    expect(within(list).getByText("Claude Code (assistant)")).toBeInTheDocument();
  });

  it("signs out everywhere after confirming", async () => {
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Sign out everywhere" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Sign out everywhere?" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Sign out everywhere" }));
    await waitFor(() => expect(signOut).toHaveBeenCalledTimes(1));
    expect(api.endAllMySessions).toHaveBeenCalledTimes(1);
  });

  /** The card of a workspace under "What you can do". */
  const rowOf = (name: string) => screen.getByRole("region", { name });
  /** The text of a card's cells, each starting with its visually hidden column label. */
  const cellsOf = (card: HTMLElement) =>
    Array.from(card.querySelectorAll(".account-grid-row > .account-cell")) as HTMLElement[];

  it("shows a row per workspace: everything where unlimited, the group a role comes through, the instance roles (Z1)", async () => {
    vi.mocked(api.myGrants).mockResolvedValue([
      grant("g1", "steward", "Data steward", { workspaceKey: "default" }),
      grant("g4", "reader", "Reader", { workspaceKey: "default" }, { kind: "group", id: "c", name: "Curators" }),
      grant("g5", "security-admin", "Security administrator", { instance: true }),
    ]);
    permissions({ g1: ["browse", "edit-live", "change-sets", "publish"], g4: ["browse"] });
    renderPage();
    expect(await screen.findByText("1 workspace · 3 roles")).toBeInTheDocument();
    // The column labels stand once above the cards; each cell carries its own hidden label.
    expect(document.querySelector(".account-columns")).toHaveAttribute("aria-hidden", "true");
    const row = rowOf("Default");
    expect(within(row).getByRole("link", { name: "Default" })).toHaveAttribute(
      "href",
      "/workspace?workspaceKey=default",
    );
    expect(within(row).getByText("Data steward").closest(".access-chip")).toBeInTheDocument();
    expect(within(row).getByText("Reader through the group Curators")).toBeInTheDocument();
    expect(cellsOf(row).map((cell) => cell.textContent)).toEqual([
      "Workspace: DEDefault",
      "Your roles: Data stewardReaderReader through the group Curators",
      "Read: ✓Yes",
      "Propose changes: Everything",
      "Change live: Everything",
      "Publish: ✓Yes",
      "Approve: –No",
    ]);
    // The workspace's tile carries its initials.
    expect(within(row).getByText("DE")).toHaveAttribute("data-hue", String(workspaceHue("default")));
    // No limited cell, so nothing to open.
    expect(screen.queryByRole("button", { name: /application|record type/ })).not.toBeInTheDocument();
    // A workspace's name has the hue of its Home tile.
    expect(within(row).getByRole("link", { name: "Default" }).closest("[data-hue]")).toHaveAttribute(
      "data-hue",
      String(workspaceHue("default")),
    );
    const instance = screen.getByRole("region", { name: "Across the instance" });
    expect(within(instance).getByText("Security administrator")).toBeInTheDocument();
    expect(within(instance).getByText("Manage people, groups, roles and clients")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Reading is never limited. A count opens what each of your roles covers in that workspace. A security administrator gives and removes roles.",
      ),
    ).toBeInTheDocument();
  });

  it("counts a limited cell and names applications as links and types plain in its panel, a role of another set on its own row", async () => {
    vi.mocked(api.myGrants).mockResolvedValue([
      grant("g2", "contributor", "Contributor", { workspaceKey: "field-stations", recordTypeNames: ["Codelist"] }),
      grant("g3", "owner", "Data owner", { workspaceKey: "field-stations", applicationNames: ["Timetables"] }),
      grant("g6", "reader", "Reader", { instance: true }),
    ]);
    permissions({
      g2: ["browse", "change-sets"],
      g3: ["browse", "edit-live", "change-sets", "publish", "approve"],
      g6: ["browse"],
    });
    renderPage();
    expect(await screen.findByText("1 workspace · 3 roles")).toBeInTheDocument();
    // Roles held for every workspace are a row of their own.
    const every = rowOf("Every workspace");
    expect(within(every).getByText("Reader")).toBeInTheDocument();
    expect(within(every).getAllByText("No")).toHaveLength(4);
    expect(within(every).queryByRole("link")).not.toBeInTheDocument();
    const row = rowOf("Field stations");
    const [, , , propose, change] = cellsOf(row);
    // A limited cell is only a count; no name stands in it.
    // The type Codelist is inside the held application, so the count folds it in as the panel does.
    expect(propose).toHaveTextContent("1 application");
    expect(propose).not.toHaveTextContent("record type");
    expect(within(propose).queryByRole("link")).not.toBeInTheDocument();
    expect(propose).not.toHaveTextContent("Timetables");
    expect(propose).not.toHaveTextContent("Codelist");
    expect(change).toHaveTextContent("1 application");
    expect(change).not.toHaveTextContent("record type");
    expect(change).not.toHaveTextContent("Timetables");
    // The panel names them: the application as a link in its hue, the type plain.
    fireEvent.click(within(propose).getByRole("button", { name: "1 application" }));
    const panel = within(row).getByRole("region", { name: "What you may propose in Field stations" });
    const application = within(panel).getByRole("link", { name: "Timetables" });
    expect(application).toHaveAttribute("href", expect.stringContaining("/apps/timetables/views/"));
    expect(application).toHaveAttribute("data-hue", "2");
    // The type Codelist is inside the held application, so its line says all of them.
    expect(within(panel).getByRole("rowheader", { name: "Timetables" }).closest("tr")).toHaveTextContent(
      "All record types",
    );
    expect(within(panel).queryByRole("link", { name: /Codelist/ })).not.toBeInTheDocument();
    // The workspace's name opens it.
    expect(within(row).getByRole("link", { name: "Field stations" })).toHaveAttribute(
      "href",
      "/workspace?workspaceKey=field-stations",
    );
  });

  it("still counts a record type outside the application held whole", async () => {
    vi.mocked(api.myGrants).mockResolvedValue([
      grant("k1", "contributor", "Contributor", {
        workspaceKey: "default",
        applicationNames: ["Timetables"],
        recordTypeNames: ["Codelist", "Operator"],
      }),
    ]);
    permissions({ k1: ["browse", "change-sets"] });
    renderPage();
    expect(await screen.findByText("1 workspace · 1 role")).toBeInTheDocument();
    const [, , , propose] = cellsOf(rowOf("Default"));
    expect(propose).toHaveTextContent("1 application, 1 record type");
  });

  it("counts three or more, and opens a line per application with where each comes from", async () => {
    vi.mocked(api.myGrants).mockResolvedValue([
      grant("h1", "contributor", "Contributor", { workspaceKey: "default" }),
      grant(
        "h2",
        "owner",
        "Data owner",
        { workspaceKey: "default", applicationNames: ["Operators"], recordTypeNames: ["Timetable", "Codelist"] },
        { kind: "group", id: "g", name: "Owners" },
      ),
    ]);
    permissions({ h1: ["browse", "change-sets"], h2: ["browse", "edit-live", "change-sets"] });
    renderPage();
    expect(await screen.findByText("1 workspace · 2 roles")).toBeInTheDocument();
    const row = rowOf("Default");
    const cells = cellsOf(row);
    // A role held for the whole workspace takes in nothing narrower of another role.
    expect(cells[3]).toHaveTextContent("Everything");
    expect(cells[4]).toHaveTextContent("1 application, 2 record types");
    expect(screen.getByText("Data owner through the group Owners")).toBeInTheDocument();

    const count = within(row).getByRole("button", { name: "1 application, 2 record types" });
    expect(count).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("columnheader", { name: "Record types" })).not.toBeInTheDocument();
    fireEvent.click(count);
    expect(count).toHaveAttribute("aria-expanded", "true");
    expect(document.getElementById(count.getAttribute("aria-controls") ?? "")).toContainElement(
      within(row).getByRole("region", { name: "What you may change live in Default" }),
    );
    // The panel sits inside the card and names the workspace.
    const panel = within(row).getByRole("region", { name: "What you may change live in Default" });
    expect(row).toHaveAttribute("data-open");
    const lines = within(panel).getByRole("columnheader", { name: "Record types" }).closest("table") as HTMLElement;
    const operators = within(lines).getByRole("rowheader", { name: "Operators" }).closest("tr") as HTMLElement;
    expect(within(operators).getByRole("link", { name: "Operators" })).toHaveAttribute("data-hue", "1");
    expect(operators).toHaveTextContent("All record types");
    expect(operators).toHaveTextContent("Data owner");
    // Timetables is there through two of its record types, not as a whole.
    const timetables = within(lines).getByRole("rowheader", { name: "Timetables" }).closest("tr") as HTMLElement;
    expect(timetables).toHaveTextContent("Timetable, Codelist");
    // From names only the roles giving Change live there.
    expect(timetables).toHaveTextContent("Data owner");
    expect(timetables).not.toHaveTextContent("Contributor");
    fireEvent.click(count);
    expect(count).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("columnheader", { name: "Record types" })).not.toBeInTheDocument();
  });

  it("opens one view at a time: Propose or Change live, each with its own lines", async () => {
    vi.mocked(api.myGrants).mockResolvedValue([
      grant("v1", "owner", "Data owner", { workspaceKey: "default", applicationNames: ["Timetables"] }),
      grant("v2", "editor", "Editor", { workspaceKey: "default", applicationNames: ["Operators"] }),
    ]);
    permissions({ v1: ["browse", "change-sets", "edit-live"], v2: ["browse", "edit-live"] });
    renderPage();
    expect(await screen.findByText("1 workspace · 2 roles")).toBeInTheDocument();
    const row = rowOf("Default");
    const [, , , proposeCell, changeCell] = cellsOf(row);
    const propose = within(proposeCell).getByRole("button");
    const change = within(changeCell).getByRole("button");
    expect(propose).toHaveAttribute("aria-expanded", "false");
    expect(change).toHaveAttribute("aria-expanded", "false");

    fireEvent.click(propose);
    expect(propose).toHaveAttribute("aria-expanded", "true");
    expect(change).toHaveAttribute("aria-expanded", "false");
    const proposed = within(row).getByRole("region", { name: "What you may propose in Default" });
    expect(within(proposed).getByRole("rowheader", { name: "Timetables" })).toBeInTheDocument();
    expect(within(proposed).queryByRole("rowheader", { name: "Operators" })).not.toBeInTheDocument();
    expect(within(proposed).queryByRole("columnheader", { name: "Propose" })).not.toBeInTheDocument();

    fireEvent.click(change);
    expect(propose).toHaveAttribute("aria-expanded", "false");
    expect(change).toHaveAttribute("aria-expanded", "true");
    expect(within(row).queryByRole("region", { name: "What you may propose in Default" })).not.toBeInTheDocument();
    const changed = within(row).getByRole("region", { name: "What you may change live in Default" });
    expect(within(changed).getByRole("rowheader", { name: "Timetables" })).toBeInTheDocument();
    expect(within(changed).getByRole("rowheader", { name: "Operators" })).toBeInTheDocument();

    fireEvent.click(change);
    expect(change).toHaveAttribute("aria-expanded", "false");
    expect(within(row).queryByRole("region")).not.toBeInTheDocument();
  });

  it("says when the person has no roles yet", async () => {
    vi.mocked(api.myGrants).mockResolvedValue([]);
    renderPage();
    expect(await screen.findByText(/You have no roles yet/)).toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "Workspace" })).not.toBeInTheDocument();
  });

  it("changes the password in place, telling which field was refused", async () => {
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Change password" }));
    const current = await screen.findByLabelText("Current password");
    const next = screen.getByLabelText("New password");
    vi.mocked(api.changePassword).mockRejectedValueOnce(
      new ApiError(422, "PASSWORD_INCORRECT", "The current password is not right"),
    );
    fireEvent.change(current, { target: { value: "not mine at all" } });
    fireEvent.change(next, { target: { value: "a new long passphrase" } });
    fireEvent.click(screen.getByRole("button", { name: "Show current password", pressed: false }));
    expect(current).toHaveAttribute("type", "text");
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("The current password is not right")).toBeInTheDocument();
    expect(current).toHaveAttribute("aria-invalid", "true");

    vi.mocked(api.changePassword).mockRejectedValueOnce(
      new ApiError(422, "PASSWORD_REJECTED", "A password needs at least 15 characters", { reason: "tooShort" }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("A password needs at least 15 characters")).toBeInTheDocument();
    expect(next).toHaveAttribute("aria-invalid", "true");

    vi.mocked(api.changePassword).mockResolvedValueOnce(undefined);
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText(/Your password is changed/)).toBeInTheDocument();
    expect(screen.queryByLabelText("Current password")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Change password" })).toBeInTheDocument();
  });

  it("shows each role once, merging the narrowings of its grants and listing every group it comes through", async () => {
    vi.mocked(api.myGrants).mockResolvedValue([
      grant(
        "m1",
        "owner",
        "Data owner",
        { workspaceKey: "default", applicationNames: ["Operators"] },
        { kind: "group", id: "a", name: "Alpha" },
      ),
      grant(
        "m2",
        "owner",
        "Data owner",
        { workspaceKey: "default", recordTypeNames: ["Codelist"] },
        { kind: "group", id: "b", name: "Beta" },
      ),
    ]);
    permissions({ m1: ["edit-live"], m2: ["edit-live"] });
    renderPage();
    expect(await screen.findByText("Data owner through the groups Alpha and Beta")).toBeInTheDocument();
    const row = rowOf("Default");
    expect(within(row).getAllByText("Data owner", { selector: ".access-chip-name" })).toHaveLength(1);
    // The two grants narrow differently; the cell counts both, the panel names them.
    expect(cellsOf(row)[4]).toHaveTextContent("1 application, 1 record type");
    expect(cellsOf(row)[4]).not.toHaveTextContent("Operators");
    fireEvent.click(within(row).getByRole("button", { name: "1 application, 1 record type" }));
    const panel = within(row).getByRole("region", { name: "What you may change live in Default" });
    expect(within(panel).getByRole("link", { name: "Operators" })).toBeInTheDocument();
    expect(panel).toHaveTextContent("Codelist");
    expect(within(panel).getAllByText("Data owner")).toHaveLength(2);
    // The role is shown as the Access tab's chip.
    expect(
      within(row).getByText("Data owner", { selector: ".access-chip-name" }).closest(".access-chip"),
    ).toHaveAttribute("data-hue", "4");
  });

  it("becomes a list on a phone, with Read, Propose, Change live and Also per workspace", async () => {
    const original = window.matchMedia;
    window.matchMedia = ((query: string) => ({
      matches: query.includes("480"),
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
    })) as never;
    try {
      vi.mocked(api.myGrants).mockResolvedValue([
        grant("p1", "owner", "Data owner", { workspaceKey: "default", applicationNames: ["Operators"] }),
      ]);
      permissions({ p1: ["browse", "edit-live", "change-sets", "publish", "approve"] });
      renderPage();
      expect(await screen.findByText("Data owner")).toBeInTheDocument();
      expect(screen.queryByRole("columnheader", { name: "Workspace" })).not.toBeInTheDocument();
      const place = screen.getByRole("region", { name: "Default" });
      expect(Array.from(place.querySelectorAll("dt")).map((term) => term.textContent)).toEqual([
        "Read",
        "Propose",
        "Change live",
        "Also",
      ]);
      expect(place.querySelector("dl")).toHaveTextContent("Publish · Approve");
      // Limited cells are counts here too; the names are in the panel.
      const dl = place.querySelector("dl") as HTMLElement;
      expect(within(dl).queryByRole("link", { name: "Operators" })).not.toBeInTheDocument();
      const counts = within(place).getAllByRole("button", { name: "1 application" });
      expect(counts).toHaveLength(2);
      fireEvent.click(counts[0]);
      const panel = within(place).getByRole("region", { name: "What you may propose in Default" });
      expect(within(panel).getByRole("link", { name: "Operators" })).toBeInTheDocument();
      expect(panel).toHaveTextContent("All record types · from Data owner");
    } finally {
      window.matchMedia = original;
    }
  });
});
