import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import { signOut } from "@/api/session";
import { ToastProvider } from "@/ui/Toast";
import { AccountPage } from "./AccountPage";

vi.mock("@/api/client", () => ({
  api: {
    me: vi.fn(),
    mySessions: vi.fn(),
    workspaces: vi.fn(),
    myGrants: vi.fn(),
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

const session = (id: string, current: boolean, userAgent: string) => ({
  id,
  current,
  signedInWith: "password",
  userAgent,
  createdAt: "2026-10-23T08:12:00Z",
  lastUsedAt: "2026-10-23T09:00:00Z",
  endsAt: "2026-10-23T21:00:00Z",
});

function grant(
  id: string,
  key: string,
  name: string,
  scope: { instance?: boolean; workspaceKey?: string; recordTypes?: string[]; recordTypeNames?: string[] },
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
      applicationNames: [],
      recordTypeNames: scope.recordTypeNames ?? [],
    },
    createdAt: "2026-10-23T08:00:00Z",
  };
}

function renderPage() {
  render(
    <ToastProvider>
      <AccountPage />
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
      username: "ana",
      email: "ana@example.org",
      lastSignInAt: "2026-10-23T08:12:00Z",
      signedInWith: "password",
      sessionId: "s1",
    });
    vi.mocked(api.mySessions).mockResolvedValue([session("s1", true, firefox), session("s2", false, iphone)]);
    vi.mocked(api.myGrants).mockResolvedValue([]);
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

  it("signs out everywhere after confirming", async () => {
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Sign out everywhere" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Sign out everywhere?" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Sign out everywhere" }));
    await waitFor(() => expect(signOut).toHaveBeenCalledTimes(1));
    expect(api.endAllMySessions).toHaveBeenCalledTimes(1);
  });

  it("lists the person's roles: where, what they narrow and where they come from (Z1)", async () => {
    vi.mocked(api.myGrants).mockResolvedValue([
      grant("g1", "steward", "Data steward", {
        workspaceKey: "default",
        recordTypes: ["t1"],
        recordTypeNames: ["Specimen"],
      }),
      grant("g2", "reader", "Reader", { workspaceKey: "field-stations" }, { kind: "group", id: "c", name: "Curators" }),
      grant("g3", "security-admin", "Security administrator", { instance: true }),
    ]);
    renderPage();
    const list = await screen.findByRole("list", { name: "What you can do" });
    const rows = within(list).getAllByRole("listitem");
    expect(rows.map((row) => row.textContent)).toEqual([
      "DefaultChanges narrowed to Specimen · directlyData steward",
      "Field stationsThrough the group CuratorsReader",
      "Every workspaceThe whole instance · directlySecurity administrator",
    ]);
    expect(screen.getByText("3 roles")).toBeInTheDocument();
    expect(screen.getByText(/Reading a workspace is never narrowed/)).toBeInTheDocument();
  });

  it("says when the person has no roles yet", async () => {
    vi.mocked(api.myGrants).mockResolvedValue([]);
    renderPage();
    expect(await screen.findByText(/You have no roles yet/)).toBeInTheDocument();
    expect(screen.queryByRole("list", { name: "What you can do" })).not.toBeInTheDocument();
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
    fireEvent.click(screen.getByRole("button", { name: "Save new password" }));
    expect(await screen.findByText("The current password is not right")).toBeInTheDocument();
    expect(current).toHaveAttribute("aria-invalid", "true");

    vi.mocked(api.changePassword).mockRejectedValueOnce(
      new ApiError(422, "PASSWORD_REJECTED", "A password needs at least 15 characters", { reason: "tooShort" }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Save new password" }));
    expect(await screen.findByText("A password needs at least 15 characters")).toBeInTheDocument();
    expect(next).toHaveAttribute("aria-invalid", "true");

    vi.mocked(api.changePassword).mockResolvedValueOnce(undefined);
    fireEvent.click(screen.getByRole("button", { name: "Save new password" }));
    expect(await screen.findByText(/Your password is changed/)).toBeInTheDocument();
    expect(screen.queryByLabelText("Current password")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Change password" })).toBeInTheDocument();
  });
});
