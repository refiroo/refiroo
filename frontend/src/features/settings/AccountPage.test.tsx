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
    endMySession: vi.fn(async () => undefined),
    endAllMySessions: vi.fn(async () => undefined),
    changePassword: vi.fn(),
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

  it("says what the person can do in each workspace until roles arrive", async () => {
    renderPage();
    const list = await screen.findByRole("list", { name: "What you can do" });
    expect(within(list).getAllByText("Everything")).toHaveLength(2);
    expect(within(list).getByText("Field stations")).toBeInTheDocument();
    expect(screen.getByText(/Roles come in a later update/)).toBeInTheDocument();
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
