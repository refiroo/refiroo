import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/api/errors";
import { mail } from "@/api/mailClient";
import { security } from "@/api/securityClient";
import { ToastProvider } from "@/ui/Toast";
import { PeoplePage } from "./PeoplePage";

vi.mock("@/api/securityClient", () => ({
  security: {
    users: vi.fn(async () => ({ items: [], nextCursor: null, totalCount: 0 })),
    user: vi.fn(),
    groups: vi.fn(async () => ({ items: [], nextCursor: null, totalCount: 0 })),
    updateUser: vi.fn(),
    createUser: vi.fn(),
    passwordLink: vi.fn(),
    localSignIn: vi.fn(async () => ({ enabled: true, keptPeople: 1, version: 1, updatedAt: "" })),
  },
}));

vi.mock("./GrantsSection", () => ({ GrantsSection: () => null, useWorkspaceLabels: () => ({}) }));
vi.mock("./RecentActivity", () => ({ RecentActivity: () => null }));
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
  it("asks for the e-mail address, the name a person signs in with, and sends nothing without it", () => {
    const dialog = openNewPerson();
    fireEvent.change(within(dialog).getByLabelText("Name"), { target: { value: "User One" } });
    expect(within(dialog).getByLabelText("E-mail")).toBeRequired();
    expect(within(dialog).getByRole("button", { name: "Add person" })).toBeDisabled();
    expect(security.createUser).not.toHaveBeenCalled();
  });

  it("shows the engine's refusal under the field it names", async () => {
    vi.mocked(security.createUser).mockRejectedValue(
      new ApiError(422, "REQUEST_VALIDATION_ERROR", "Request validation failed", [
        { loc: ["body", "email"], msg: "String should match pattern '^[^@\\s]+@[^@\\s]+$'" },
      ]),
    );
    const dialog = openNewPerson();
    fireEvent.change(within(dialog).getByLabelText("Name"), { target: { value: "User One" } });
    fireEvent.change(within(dialog).getByLabelText("E-mail"), { target: { value: "not an e-mail" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Add person" }));
    expect(await within(dialog).findByText("An e-mail address looks like name@example.org.")).toBeInTheDocument();
    expect(within(dialog).getByLabelText("E-mail")).toHaveAttribute("aria-invalid", "true");
    expect(within(dialog).queryByText("Request validation failed")).toBeNull();
  });
});

describe("A person whose sign-in an administrator manages (0.17 SA1)", () => {
  it("is one checkbox on the form, sent only when ticked", async () => {
    vi.mocked(security.createUser).mockResolvedValue({
      id: "u9",
      name: "Kiosk",
      email: "k@example.org",
      roles: [],
    } as never);
    vi.mocked(security.passwordLink).mockResolvedValue({
      url: "https://x/oauth/password?token=t",
      expiresAt: "2026-11-01T00:00:00Z",
    });
    const dialog = openNewPerson();
    fireEvent.change(within(dialog).getByLabelText("Name"), { target: { value: "Kiosk" } });
    fireEvent.change(within(dialog).getByLabelText("E-mail"), { target: { value: "k@example.org" } });
    const box = within(dialog).getByRole("checkbox", { name: /An administrator manages this person’s sign-in/ });
    expect(box).not.toBeChecked();
    fireEvent.click(box);
    fireEvent.click(within(dialog).getByRole("button", { name: "Add person" }));
    await screen.findByText(/sets a password with this link/);
    expect(security.createUser).toHaveBeenCalledWith({ name: "Kiosk", email: "k@example.org", signInManaged: true });
  });
});

describe("A new person's link by mail (0.12 SP3)", () => {
  const user = { id: "u1", name: "Ada", email: "ada@example.org", roles: [] };
  const link = { url: "https://x/oauth/password?token=t", expiresAt: "2026-11-01T00:00:00Z" };

  async function createAda() {
    const dialog = openNewPerson();
    fireEvent.change(within(dialog).getByLabelText("Name"), { target: { value: "Ada" } });
    fireEvent.change(within(dialog).getByLabelText("E-mail"), { target: { value: "ada@example.org" } });
    return dialog;
  }

  it("shows the link, and the Mail it button sends a newer one to the address", async () => {
    vi.mocked(mail.settings).mockResolvedValue({ configured: true } as never);
    vi.mocked(security.createUser).mockResolvedValue(user as never);
    vi.mocked(security.passwordLink)
      .mockResolvedValueOnce(link)
      .mockResolvedValueOnce({ ...link, sentTo: "ada@example.org" });
    const dialog = await createAda();
    fireEvent.click(within(dialog).getByRole("button", { name: "Add person" }));
    expect(await screen.findByText(/sets a password with this link/)).toBeInTheDocument();
    expect(security.passwordLink).toHaveBeenCalledWith("u1");
    fireEvent.click(await screen.findByRole("button", { name: "Mail it to ada@example.org" }));
    expect(await screen.findByText(/The link was mailed to ada@example.org/)).toBeInTheDocument();
    expect(security.passwordLink).toHaveBeenLastCalledWith("u1", true);
    expect(screen.queryByRole("button", { name: /Mail it to/ })).toBeNull();
    expect(screen.getByRole("button", { name: "I have copied it" })).toBeInTheDocument();
  });

  it("says why the mail failed and keeps the link that was shown", async () => {
    vi.mocked(mail.settings).mockResolvedValue({ configured: true } as never);
    vi.mocked(security.createUser).mockResolvedValue(user as never);
    vi.mocked(security.passwordLink)
      .mockResolvedValueOnce(link)
      .mockRejectedValueOnce(new ApiError(409, "MAIL_NOT_SET_UP", "Mail is not set up"));
    const dialog = await createAda();
    fireEvent.click(within(dialog).getByRole("button", { name: "Add person" }));
    fireEvent.click(await screen.findByRole("button", { name: "Mail it to ada@example.org" }));
    expect(await screen.findByText(/Mail is not set up/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Mail it to ada@example.org" })).toBeEnabled();
  });

  it("makes only a link to pass on when mail is not set up", async () => {
    vi.mocked(mail.settings).mockResolvedValue({ configured: false } as never);
    vi.mocked(security.createUser).mockResolvedValue(user as never);
    vi.mocked(security.passwordLink).mockResolvedValue(link);
    const dialog = await createAda();
    fireEvent.click(within(dialog).getByRole("button", { name: "Add person" }));
    expect(await screen.findByText(/sets a password with this link/)).toBeInTheDocument();
    expect(security.passwordLink).toHaveBeenCalledWith("u1");
  });
});

describe("Keeping local sign-in (0.17 UX1)", () => {
  const person = (localKept: boolean, version: number) => ({
    id: "u2",
    name: "Grace",
    email: "grace@example.org",
    active: true,
    version,
    localKept,
    hasPassword: true,
    identities: [],
    passkeys: 0,
    secondFactor: null,
    signInManaged: false,
    roles: [],
  });

  function openGrace() {
    render(
      <ToastProvider>
        <PeoplePage route={{ kind: "settings", page: "people", userId: "u2" }} onNavigate={vi.fn()} />
      </ToastProvider>,
    );
  }

  it("turning it on saves at once with a toast, with no confirmation, and Undo turns it off", async () => {
    vi.mocked(security.user).mockResolvedValue(person(false, 4) as never);
    vi.mocked(security.updateUser)
      .mockResolvedValueOnce(person(true, 5) as never)
      .mockResolvedValueOnce(person(false, 6) as never);
    openGrace();
    fireEvent.click(await screen.findByRole("switch", { name: "Keeps local sign-in" }));
    expect(await screen.findByText("Grace keeps local sign-in.")).toBeInTheDocument();
    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(security.updateUser).toHaveBeenCalledWith("u2", { expectedVersion: 4, localKept: true });
    fireEvent.click(screen.getByRole("button", { name: "Undo" }));
    await waitFor(() =>
      expect(security.updateUser).toHaveBeenLastCalledWith("u2", { expectedVersion: 5, localKept: false }),
    );
  });

  it("turning it off asks first, naming what is lost", async () => {
    vi.mocked(security.user).mockResolvedValue(person(true, 4) as never);
    openGrace();
    fireEvent.click(await screen.findByRole("switch", { name: "Keeps local sign-in" }));
    const dialog = await screen.findByRole("alertdialog");
    expect(within(dialog).getByRole("button", { name: "Stop keeping local sign-in" })).toBeInTheDocument();
    expect(security.updateUser).not.toHaveBeenCalled();
  });
});

describe("the list and a person's page (0.17 ST1)", () => {
  const grace = {
    id: "u2",
    name: "Grace",
    email: "grace@example.org",
    active: true,
    version: 1,
    localKept: false,
    hasPassword: true,
    identities: [],
    passkeys: 0,
    secondFactor: null,
    signInManaged: false,
    lastSignInAt: null,
    roles: [{ key: "steward", name: "Data steward", instance: true, workspaces: [] }],
  };

  it("lists people with their roles as chips, and a row opens the person's page", async () => {
    vi.mocked(security.users).mockResolvedValue({ items: [grace], nextCursor: null, totalCount: 1 } as never);
    const onNavigate = vi.fn();
    render(
      <ToastProvider>
        <PeoplePage route={{ kind: "settings", page: "people" }} onNavigate={onNavigate} />
      </ToastProvider>,
    );
    const row = await screen.findByRole("button", { name: /Grace/ });
    expect(within(row).getByText("Data steward")).toBeInTheDocument();
    fireEvent.click(row);
    expect(onNavigate).toHaveBeenCalledWith({ kind: "settings", page: "people", userId: "u2" });
  });

  it("goes back to the list from the page's trail, and keeps See changes in the ⋯ menu", async () => {
    vi.mocked(security.user).mockResolvedValue(grace as never);
    const onNavigate = vi.fn();
    render(
      <ToastProvider>
        <PeoplePage route={{ kind: "settings", page: "people", userId: "u2" }} onNavigate={onNavigate} />
      </ToastProvider>,
    );
    expect(await screen.findByRole("heading", { level: 1, name: "Grace" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reset password" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Deactivate" })).toBeNull();
    fireEvent.click(screen.getByRole("link", { name: "People" }));
    expect(onNavigate).toHaveBeenCalledWith({ kind: "settings", page: "people" });
  });
});
