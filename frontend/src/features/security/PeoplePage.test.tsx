import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/api/errors";
import { mail } from "@/api/mailClient";
import { security } from "@/api/securityClient";
import { ToastProvider } from "@/ui/Toast";
import { PeoplePage } from "./PeoplePage";

vi.mock("@/api/securityClient", () => ({
  security: {
    users: vi.fn(async () => ({ items: [], nextCursor: null, totalCount: 0 })),
    createUser: vi.fn(),
    passwordLink: vi.fn(),
    localSignIn: vi.fn(async () => ({ enabled: true, keptPeople: 1, version: 1, updatedAt: "" })),
  },
}));

vi.mock("@/api/mailClient", () => ({ mail: { settings: vi.fn(async () => ({ configured: false })) } }));

function openNewPerson() {
  render(
    <ToastProvider>
      <PeoplePage route={{ kind: "settings", page: "people" }} onNavigate={vi.fn()} />
    </ToastProvider>,
  );
  fireEvent.click(screen.getByRole("button", { name: "New person" }));
  return screen.getByRole("dialog", { name: "New person" });
}

beforeEach(() => vi.clearAllMocks());

describe("New person (0.12 SP1: a refusal said only 'Request validation failed')", () => {
  it("says a username has no spaces as it is typed, and sends nothing", () => {
    const dialog = openNewPerson();
    fireEvent.change(within(dialog).getByLabelText("Username"), { target: { value: "user 1" } });
    fireEvent.change(within(dialog).getByLabelText("Name"), { target: { value: "User One" } });
    const username = within(dialog).getByLabelText("Username");
    expect(username).toHaveAttribute("aria-invalid", "true");
    expect(within(dialog).getByText(/A username has no spaces/)).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Create and make a password link" })).toBeDisabled();
    expect(security.createUser).not.toHaveBeenCalled();
  });

  it("shows the engine's refusal under the field it names", async () => {
    vi.mocked(security.createUser).mockRejectedValue(
      new ApiError(422, "REQUEST_VALIDATION_ERROR", "Request validation failed", [
        { loc: ["body", "email"], msg: "String should match pattern '^[^@\\s]+@[^@\\s]+$'" },
      ]),
    );
    const dialog = openNewPerson();
    fireEvent.change(within(dialog).getByLabelText("Username"), { target: { value: "user1" } });
    fireEvent.change(within(dialog).getByLabelText("Name"), { target: { value: "User One" } });
    fireEvent.change(within(dialog).getByLabelText("E-mail (optional)"), { target: { value: "not an e-mail" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Create and make a password link" }));
    expect(await within(dialog).findByText("An e-mail address looks like name@example.org.")).toBeInTheDocument();
    expect(within(dialog).getByLabelText("E-mail (optional)")).toHaveAttribute("aria-invalid", "true");
    expect(within(dialog).queryByText("Request validation failed")).toBeNull();
  });
});

describe("A new person's link by mail (0.12 SP3)", () => {
  const user = { id: "u1", name: "Ada", username: "ada", email: "ada@example.org", roles: [] };
  const link = { url: "https://x/oauth/password?token=t", expiresAt: "2026-11-01T00:00:00Z" };

  async function createAda() {
    const dialog = openNewPerson();
    fireEvent.change(within(dialog).getByLabelText("Username"), { target: { value: "ada" } });
    fireEvent.change(within(dialog).getByLabelText("Name"), { target: { value: "Ada" } });
    fireEvent.change(within(dialog).getByLabelText("E-mail (optional)"), { target: { value: "ada@example.org" } });
    return dialog;
  }

  it("asks for the link to be mailed when mail is set up and says where it went", async () => {
    vi.mocked(mail.settings).mockResolvedValue({ configured: true } as never);
    vi.mocked(security.createUser).mockResolvedValue(user as never);
    vi.mocked(security.passwordLink).mockResolvedValue({ ...link, sentTo: "ada@example.org" });
    const dialog = await createAda();
    fireEvent.click(await within(dialog).findByRole("button", { name: "Create and mail a password link" }));
    expect(await screen.findByText(/The link was mailed to ada@example.org/)).toBeInTheDocument();
    expect(security.passwordLink).toHaveBeenCalledWith("u1", true);
  });

  it("falls back to the link to pass on when the engine says mail cannot be sent", async () => {
    vi.mocked(mail.settings).mockResolvedValue({ configured: true } as never);
    vi.mocked(security.createUser).mockResolvedValue(user as never);
    vi.mocked(security.passwordLink)
      .mockRejectedValueOnce(new ApiError(409, "MAIL_NOT_SET_UP", "Mail is not set up"))
      .mockResolvedValueOnce(link);
    const dialog = await createAda();
    fireEvent.click(await within(dialog).findByRole("button", { name: "Create and mail a password link" }));
    expect(await screen.findByText(/sets a password with this link/)).toBeInTheDocument();
    expect(security.passwordLink).toHaveBeenLastCalledWith("u1");
  });

  it("makes only a link to pass on when mail is not set up", async () => {
    vi.mocked(mail.settings).mockResolvedValue({ configured: false } as never);
    vi.mocked(security.createUser).mockResolvedValue(user as never);
    vi.mocked(security.passwordLink).mockResolvedValue(link);
    const dialog = await createAda();
    fireEvent.click(within(dialog).getByRole("button", { name: "Create and make a password link" }));
    expect(await screen.findByText(/sets a password with this link/)).toBeInTheDocument();
    expect(security.passwordLink).toHaveBeenCalledWith("u1");
  });
});
