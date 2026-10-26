import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { mail } from "@/api/mailClient";
import { ApiError } from "@/api/errors";
import { MailPage } from "@/features/settings/MailPage";
import type { MailSettings } from "@/types";
import { ToastProvider } from "@/ui/Toast";

vi.mock("@/api/mailClient", () => ({
  mail: { settings: vi.fn(), saveSettings: vi.fn(), removeSettings: vi.fn(), sendTest: vi.fn(), messages: vi.fn() },
}));

const empty: MailSettings = {
  configured: false,
  host: null,
  port: null,
  security: null,
  username: null,
  passwordSet: false,
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
  beforeEach(() => vi.resetAllMocks());

  it("says mail is not set up, and the first save sends no version or password without a login", async () => {
    vi.mocked(mail.saveSettings).mockResolvedValue(saved);
    open(empty);
    expect(await screen.findByText("Mail is not set up")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send test message" })).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Server"), { target: { value: "smtp.example.org" } });
    fireEvent.change(screen.getByLabelText("From address"), { target: { value: "refiroo@example.org" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(mail.saveSettings).toHaveBeenCalled());
    expect(mail.saveSettings).toHaveBeenCalledWith({
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
    expect(await screen.findByText("ada@example.org")).toBeInTheDocument();
    expect(screen.getByText("Password reset")).toBeInTheDocument();
    expect(screen.getByText("Failed")).toBeInTheDocument();
    expect(screen.getByText(/550 no such user/)).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Failed (1)" })).toBeInTheDocument();
  });
});
