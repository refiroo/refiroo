import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { mail } from "@/api/mailClient";
import { ApiError } from "@/api/errors";
import { MailPage } from "@/features/settings/MailPage";
import type { MailSettings } from "@/types";
import { ToastProvider } from "@/ui/Toast";

vi.mock("@/api/mailClient", () => ({
  mail: {
    settings: vi.fn(),
    saveSettings: vi.fn(),
    removeSettings: vi.fn(),
    sendTest: vi.fn(),
    messages: vi.fn(),
    stopMessage: vi.fn(),
  },
}));

const empty: MailSettings = {
  configured: false,
  method: null,
  host: null,
  port: null,
  security: null,
  username: null,
  passwordSet: false,
  credential: null,
  identityMode: null,
  identityClientId: null,
  tenantId: null,
  clientId: null,
  clientSecretSet: false,
  certificateThumbprint: null,
  certificateExpiresAt: null,
  authorityUrl: null,
  graphUrl: null,
  fromAddress: null,
  applicationUrl: "https://refiroo.example.org",
  applicationUrlIsDefault: true,
  outbox: { pending: 0, sent: 0, failed: 0 },
  version: null,
  updatedAt: null,
};
const saved: MailSettings = {
  ...empty,
  configured: true,
  method: "smtp",
  host: "smtp.example.org",
  port: 587,
  security: "starttls",
  username: "mailer",
  passwordSet: true,
  fromAddress: "refiroo@example.org",
  version: 3,
  updatedAt: "2026-10-26T10:00:00Z",
};

function open(settings: MailSettings) {
  vi.mocked(mail.settings).mockResolvedValue(settings);
  vi.mocked(mail.messages).mockResolvedValue({ items: [], nextCursor: null } as never);
  render(
    <ToastProvider>
      <MailPage />
    </ToastProvider>,
  );
}

describe("Settings › Mail (0.12 M1)", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    window.history.replaceState(null, "", "/");
  });

  it("says mail is not set up, and the first save sends no version or password without a login", async () => {
    vi.mocked(mail.saveSettings).mockResolvedValue(saved);
    open(empty);
    expect(await screen.findByText("Mail is not set up")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send test message" })).toBeDisabled();

    fireEvent.change(screen.getByRole("textbox", { name: "Server" }), { target: { value: "smtp.example.org" } });
    fireEvent.change(screen.getByLabelText("From address"), { target: { value: "refiroo@example.org" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(mail.saveSettings).toHaveBeenCalled());
    expect(mail.saveSettings).toHaveBeenCalledWith({
      method: "smtp",
      host: "smtp.example.org",
      port: 587,
      security: "starttls",
      username: null,
      fromAddress: "refiroo@example.org",
      applicationUrl: null,
    });
  });

  it("follows the port with the connection, refuses a login without encryption and keeps a saved password", async () => {
    vi.mocked(mail.saveSettings).mockResolvedValue({ ...saved, version: 4 });
    open(saved);
    const connection = await screen.findByLabelText("Connection");
    expect(screen.getByLabelText("Password")).toHaveAttribute("placeholder", "Saved · type a new one to replace it");

    fireEvent.change(connection, { target: { value: "tls" } });
    expect(screen.getByLabelText("Port")).toHaveValue("465");
    fireEvent.change(connection, { target: { value: "none" } });
    expect(screen.getByText(/A login is not sent over an unencrypted connection/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();

    fireEvent.change(connection, { target: { value: "starttls" } });
    fireEvent.change(screen.getByLabelText("From address"), { target: { value: "mail@example.org" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(mail.saveSettings).toHaveBeenCalled());
    expect(mail.saveSettings).toHaveBeenCalledWith(
      expect.objectContaining({ expectedVersion: 3, username: "mailer", fromAddress: "mail@example.org" }),
    );
    expect(vi.mocked(mail.saveSettings).mock.calls[0][0]).not.toHaveProperty("password");
  });

  it("chooses Microsoft 365, shows what to set up in Entra, and saves its fields only (0.13 MS)", async () => {
    vi.mocked(mail.saveSettings).mockResolvedValue({
      ...empty,
      configured: true,
      method: "microsoft365",
      credential: "secret",
      tenantId: "t-1",
      clientId: "c-1",
      clientSecretSet: true,
      authorityUrl: "https://login.microsoftonline.com",
      graphUrl: "https://graph.microsoft.com",
      fromAddress: "refiroo@example.org",
      version: 1,
    });
    open(empty);
    fireEvent.change(await screen.findByLabelText("Send mail through"), { target: { value: "microsoft365" } });
    expect(screen.getByText("What to set up in Microsoft Entra")).toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: "Server" })).toBeNull();
    fireEvent.change(screen.getByLabelText("Tenant ID"), { target: { value: "t-1" } });
    fireEvent.change(screen.getByLabelText("Application (client) ID"), { target: { value: "c-1" } });
    fireEvent.change(screen.getByLabelText("Sending mailbox"), { target: { value: "refiroo@example.org" } });
    // No credential yet: not savable.
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Client secret"), { target: { value: "s3cret" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(mail.saveSettings).toHaveBeenCalled());
    expect(mail.saveSettings).toHaveBeenCalledWith({
      method: "microsoft365",
      tenantId: "t-1",
      clientId: "c-1",
      clientSecret: "s3cret",
      fromAddress: "refiroo@example.org",
      applicationUrl: null,
    });
  });

  it("shows a saved certificate's thumbprint and expiry, keeps it, and needs a new credential for another application", async () => {
    vi.mocked(mail.saveSettings).mockResolvedValue(saved);
    open({
      ...saved,
      method: "microsoft365",
      credential: "certificate",
      host: null,
      port: null,
      security: null,
      username: null,
      passwordSet: false,
      tenantId: "t-1",
      clientId: "c-1",
      certificateThumbprint: "AB12CD34",
      certificateExpiresAt: "2027-03-01T10:00:00Z",
      authorityUrl: "https://login.microsoftonline.com",
      graphUrl: "https://graph.microsoft.com",
    });
    expect(await screen.findByText("AB12CD34")).toBeInTheDocument();
    expect(screen.getByText(/Saved: thumbprint/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Sending mailbox"), { target: { value: "other@example.org" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(mail.saveSettings).toHaveBeenCalled());
    const body = vi.mocked(mail.saveSettings).mock.calls[0][0];
    expect(body).toMatchObject({ method: "microsoft365", expectedVersion: 3 });
    expect(body).not.toHaveProperty("certificate");
    expect(body).not.toHaveProperty("clientSecret");

    fireEvent.change(screen.getByLabelText("Application (client) ID"), { target: { value: "c-2" } });
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
  });

  it("offers a managed identity as a third credential, direct without tenant or application, federated with them (0.13 MS-D5)", async () => {
    vi.mocked(mail.saveSettings).mockResolvedValue({
      ...empty,
      configured: true,
      method: "microsoft365",
      credential: "managedIdentity",
      identityMode: "direct",
      identityClientId: "uai-1",
      authorityUrl: "https://login.microsoftonline.com",
      graphUrl: "https://graph.microsoft.com",
      fromAddress: "refiroo@example.org",
      version: 1,
    });
    open(empty);
    fireEvent.change(await screen.findByLabelText("Send mail through"), { target: { value: "microsoft365" } });
    fireEvent.change(screen.getByLabelText("Sign in with"), { target: { value: "direct" } });
    // Direct: no tenant or application, no secret; the checklist names the app role.
    expect(screen.queryByLabelText("Tenant ID")).toBeNull();
    expect(screen.queryByLabelText("Client secret")).toBeNull();
    expect(screen.getByText(/only when refiroo runs in Azure/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Sending mailbox"), { target: { value: "refiroo@example.org" } });
    fireEvent.change(screen.getByLabelText("Identity client ID"), { target: { value: "uai-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(mail.saveSettings).toHaveBeenCalledTimes(1));
    expect(mail.saveSettings).toHaveBeenLastCalledWith({
      method: "microsoft365",
      identityMode: "direct",
      identityClientId: "uai-1",
      fromAddress: "refiroo@example.org",
      applicationUrl: null,
    });

    // Saved: the form shows the saved identity. Federated: the identity's client ID is required, with the app's client ID and the tenant.
    fireEvent.change(screen.getByLabelText("Sign in with"), { target: { value: "federated" } });
    fireEvent.change(screen.getByLabelText("Identity client ID"), { target: { value: "" } });
    fireEvent.change(screen.getByLabelText("Tenant ID"), { target: { value: "t-1" } });
    fireEvent.change(screen.getByLabelText("Application (client) ID"), { target: { value: "c-1" } });
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Identity client ID"), { target: { value: "uai-2" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(mail.saveSettings).toHaveBeenCalledTimes(2));
    expect(mail.saveSettings).toHaveBeenLastCalledWith({
      expectedVersion: 1,
      method: "microsoft365",
      authorityUrl: "https://login.microsoftonline.com",
      graphUrl: "https://graph.microsoft.com",
      tenantId: "t-1",
      clientId: "c-1",
      identityMode: "federated",
      identityClientId: "uai-2",
      fromAddress: "refiroo@example.org",
      applicationUrl: null,
    });
  });

  it("shows only the fields of the entry chosen in Sign in with, and its steps in a folded section", async () => {
    open({
      ...empty,
      configured: true,
      method: "microsoft365",
      credential: "secret",
      tenantId: "t",
      clientId: "c",
      clientSecretSet: true,
      authorityUrl: "https://login.microsoftonline.com",
      graphUrl: "https://graph.microsoft.com",
      fromAddress: "a@example.org",
      version: 2,
    });
    const menu = await screen.findByLabelText("Sign in with");
    const options = within(menu)
      .getAllByRole("option")
      .map((o) => o.textContent);
    expect(options).toEqual([
      "Client secret",
      "Certificate",
      "Managed identity – this tenant",
      "Managed identity – hosted in another tenant",
    ]);
    const fields = () =>
      ["Tenant ID", "Application (client) ID", "Client secret", "Certificate", "Identity client ID"].filter((label) =>
        screen.queryByLabelText(label),
      );
    const steps = () => screen.getByText("What to set up in Microsoft Entra").closest("details")!;

    expect(fields()).toEqual(["Tenant ID", "Application (client) ID", "Client secret"]);
    expect(screen.getByText(/The simplest/)).toBeInTheDocument();
    expect(steps()).not.toHaveAttribute("open");
    expect(within(steps()).getByText(/Register an application/)).toBeInTheDocument();

    fireEvent.change(menu, { target: { value: "certificate" } });
    expect(fields()).toEqual(["Tenant ID", "Application (client) ID", "Certificate"]);
    expect(screen.getByText(/No shared secret is sent/)).toBeInTheDocument();

    fireEvent.change(menu, { target: { value: "direct" } });
    expect(fields()).toEqual(["Identity client ID"]);
    expect(screen.getByLabelText("Identity client ID")).not.toBeRequired();
    expect(screen.getByText(/only when refiroo runs in Azure/)).toBeInTheDocument();
    expect(within(steps()).getByText(/app role/)).toBeInTheDocument();

    fireEvent.change(menu, { target: { value: "federated" } });
    expect(fields()).toEqual(["Tenant ID", "Application (client) ID", "Identity client ID"]);
    expect(screen.getByLabelText("Identity client ID")).toBeRequired();
    expect(within(steps()).getByText(/federated credential/)).toBeInTheDocument();
  });

  it("folds the token and Graph addresses away, and opens them when a saved address is not the default", async () => {
    const microsoft = {
      ...empty,
      configured: true,
      method: "microsoft365" as const,
      credential: "secret" as const,
      tenantId: "t",
      clientId: "c",
      clientSecretSet: true,
      fromAddress: "a@example.org",
      version: 2,
    };
    open({ ...microsoft, authorityUrl: "https://login.microsoftonline.com", graphUrl: "https://graph.microsoft.com" });
    const folded = (await screen.findByText(/Other Microsoft clouds/)).closest("details")!;
    expect(folded).not.toHaveAttribute("open");
    cleanup();
    open({ ...microsoft, authorityUrl: "https://login.microsoftonline.us", graphUrl: "https://graph.microsoft.us" });
    const opened = (await screen.findByText(/Other Microsoft clouds/)).closest("details")!;
    expect(opened).toHaveAttribute("open");
    expect(screen.getByLabelText("Token address")).toHaveValue("https://login.microsoftonline.us");
  });

  it("names what failed when a test message is refused", async () => {
    vi.mocked(mail.sendTest).mockRejectedValue(
      new ApiError(422, "MAIL_SEND_FAILED", "smtp.example.org:587 refused the login of mailer: 535 denied", {
        kind: "login",
      }),
    );
    open(saved);
    fireEvent.change(await screen.findByLabelText("Send to"), { target: { value: "ada@example.org" } });
    fireEvent.click(screen.getByRole("button", { name: "Send test message" }));
    expect(await screen.findByText("The login was refused")).toBeInTheDocument();
    expect(screen.getByText(/535 denied/)).toBeInTheDocument();
  });

  it("lists a failed message with the reason", async () => {
    vi.mocked(mail.settings).mockResolvedValue({ ...saved, outbox: { pending: 0, sent: 0, failed: 1 } });
    vi.mocked(mail.messages).mockResolvedValue({
      items: [
        {
          id: "m1",
          kind: "password-reset",
          to: "ada@example.org",
          subject: "Choose a new password",
          status: "failed",
          attempts: 1,
          lastError: "smtp.example.org:587 refused the address: 550 no such user",
          lastErrorKind: "recipient",
          createdAt: "2026-10-26T10:00:00Z",
          nextAttemptAt: null,
          finishedAt: "2026-10-26T10:00:01Z",
        },
      ],
      nextCursor: null,
    } as never);
    render(
      <ToastProvider>
        <MailPage />
      </ToastProvider>,
    );
    fireEvent.click(await screen.findByRole("tab", { name: "Messages" }));
    const table = await screen.findByRole("group", { name: "Messages" });
    expect(within(table).getByText("ada@example.org")).toBeInTheDocument();
    expect(within(table).getByText("Password reset")).toBeInTheDocument();
    expect(within(table).getByText("Failed")).toBeInTheDocument();
    expect(within(table).getByText(/550 no such user/)).toBeInTheDocument();
    expect(within(screen.getByLabelText("Outbox")).getByText("failed").previousSibling).toHaveTextContent("1");
    expect(screen.getByRole("button", { name: "Failed" })).toHaveAttribute("aria-pressed", "false");
  });

  describe("stopping a message that is still being tried", () => {
    const waiting = {
      id: "m2",
      kind: "activation",
      to: "bea@example.org",
      subject: "Your account",
      status: "pending",
      attempts: 2,
      lastError: "The server could not be reached",
      lastErrorKind: "connection",
      createdAt: "2026-10-26T10:00:00Z",
      nextAttemptAt: "2026-10-26T10:05:00Z",
      finishedAt: null,
    };

    function openWaiting() {
      vi.mocked(mail.settings).mockResolvedValue({ ...saved, outbox: { pending: 1, sent: 0, failed: 0 } });
      vi.mocked(mail.messages).mockResolvedValue({ items: [waiting], nextCursor: null } as never);
      render(
        <ToastProvider>
          <MailPage />
        </ToastProvider>,
      );
    }

    it("asks first, then shows the message as failed and says why", async () => {
      openWaiting();
      const stopped = {
        ...waiting,
        status: "failed",
        lastError: "Stopped by an administrator",
        lastErrorKind: "stopped",
        nextAttemptAt: null,
        finishedAt: "2026-10-26T10:03:00Z",
      };
      vi.mocked(mail.stopMessage).mockImplementation(async () => {
        // The list read again afterwards holds the message as the engine now has it.
        vi.mocked(mail.messages).mockResolvedValue({ items: [stopped], nextCursor: null } as never);
        return stopped as never;
      });
      fireEvent.click(await screen.findByRole("tab", { name: "Messages" }));
      fireEvent.click(await screen.findByRole("button", { name: "Stop sending" }));
      expect(mail.stopMessage).not.toHaveBeenCalled();
      const dialog = screen.getByRole("alertdialog");
      expect(within(dialog).getByText(/will not be sent, now or on a later try/)).toBeInTheDocument();
      fireEvent.click(within(dialog).getByRole("button", { name: "Stop sending" }));
      expect(await screen.findByText("Stopped by an administrator")).toBeInTheDocument();
      expect(mail.stopMessage).toHaveBeenCalledWith("m2");
      expect(screen.queryByRole("button", { name: "Stop sending" })).toBeNull();
    });

    it("keeps trying when the dialog is dismissed, and offers no stop for a finished message", async () => {
      openWaiting();
      fireEvent.click(await screen.findByRole("tab", { name: "Messages" }));
      fireEvent.click(await screen.findByRole("button", { name: "Stop sending" }));
      fireEvent.click(screen.getByRole("button", { name: "Keep trying" }));
      expect(mail.stopMessage).not.toHaveBeenCalled();
      expect(screen.queryByText(/will not be sent/)).toBeNull();
    });
  });
});
