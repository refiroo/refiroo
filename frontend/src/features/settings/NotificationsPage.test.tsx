import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import type { NoticeMail } from "@/types";
import { NotificationsPage } from "./NotificationsPage";

vi.mock("@/api/client", () => ({
  api: { myNoticeMail: vi.fn(), setMyNoticeMail: vi.fn() },
}));

const kinds = [
  { kind: "change-set.submitted", label: "A change set is waiting for your approval", enabled: true },
  { kind: "change-set.approved", label: "A change set you submitted was approved", enabled: true },
  { kind: "job.failed", label: "A job you started has failed", enabled: true },
];
const available: NoticeMail = { enabled: false, available: true, reason: null, email: "ana@example.org", kinds };
const label = "Email me when something arrives in my inbox";

describe("Settings › Notifications (0.12 M2 and its follow-up)", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("switches it on and off, showing the address", async () => {
    vi.mocked(api.myNoticeMail).mockResolvedValue(available);
    vi.mocked(api.setMyNoticeMail).mockResolvedValueOnce({ ...available, enabled: true });
    render(<NotificationsPage />);
    expect(await screen.findByRole("heading", { name: "Notification email" })).toBeInTheDocument();
    const toggle = await screen.findByRole("switch", { name: label });
    expect(toggle).toHaveAttribute("aria-checked", "false");
    expect(screen.getByText(/sent to ana@example.org/)).toBeInTheDocument();
    fireEvent.click(toggle);
    await waitFor(() => expect(api.setMyNoticeMail).toHaveBeenCalledWith({ enabled: true }));
    await waitFor(() => expect(toggle).toHaveAttribute("aria-checked", "true"));

    vi.mocked(api.setMyNoticeMail).mockResolvedValueOnce(available);
    fireEvent.click(toggle);
    await waitFor(() => expect(api.setMyNoticeMail).toHaveBeenLastCalledWith({ enabled: false }));
    await waitFor(() => expect(toggle).toHaveAttribute("aria-checked", "false"));
  });

  it.each(["mail-not-set-up", "no-email", "not-a-person"] as const)(
    "offers nothing and says so in a sentence when it cannot work: %s",
    async (reason) => {
      vi.mocked(api.myNoticeMail).mockResolvedValue({ ...available, available: false, reason, email: null });
      render(<NotificationsPage />);
      expect(await screen.findByText(/there is nothing to choose here/)).toBeInTheDocument();
      expect(screen.queryByRole("switch")).not.toBeInTheDocument();
      expect(screen.queryByText(label)).not.toBeInTheDocument();
    },
  );

  it("stays shown while on, so it can be switched off after mail was removed", async () => {
    vi.mocked(api.myNoticeMail).mockResolvedValue({
      ...available,
      enabled: true,
      available: false,
      reason: "mail-not-set-up",
    });
    render(<NotificationsPage />);
    expect(await screen.findByRole("switch", { name: label })).toHaveAttribute("aria-checked", "true");
  });

  it("shows the engine's refusal and leaves the switch as it was", async () => {
    vi.mocked(api.myNoticeMail).mockResolvedValue(available);
    vi.mocked(api.setMyNoticeMail).mockRejectedValueOnce(
      new ApiError(409, "MAIL_NOT_SET_UP", "Mail is not set up: an administrator saves the SMTP settings first"),
    );
    render(<NotificationsPage />);
    const toggle = await screen.findByRole("switch", { name: label });
    fireEvent.click(toggle);
    expect(await screen.findByText(/Mail is not set up/)).toBeInTheDocument();
    expect(toggle).toHaveAttribute("aria-checked", "false");
    expect(toggle).toBeEnabled();
  });

  it("lists the engine's kinds in a labelled group and saves each at once", async () => {
    vi.mocked(api.myNoticeMail).mockResolvedValue({ ...available, enabled: true });
    const after = kinds.map((item) => (item.kind === "job.failed" ? { ...item, enabled: false } : item));
    vi.mocked(api.setMyNoticeMail).mockResolvedValueOnce({ ...available, enabled: true, kinds: after });
    render(<NotificationsPage />);
    const group = await screen.findByRole("group", { name: "Send me an email for" });
    const switches = within(group).getAllByRole("switch");
    expect(switches.map((item) => item.getAttribute("aria-label"))).toEqual(kinds.map((item) => item.label));
    expect(switches.every((item) => item.getAttribute("aria-checked") === "true")).toBe(true);

    fireEvent.click(within(group).getByRole("switch", { name: "A job you started has failed" }));
    await waitFor(() => expect(api.setMyNoticeMail).toHaveBeenCalledWith({ kinds: { "job.failed": false } }));
    await waitFor(() =>
      expect(within(group).getByRole("switch", { name: "A job you started has failed" })).toHaveAttribute(
        "aria-checked",
        "false",
      ),
    );
    expect(within(group).getByRole("switch", { name: "A change set you submitted was approved" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
  });

  it("greys out the kinds while the main switch is off", async () => {
    vi.mocked(api.myNoticeMail).mockResolvedValue(available);
    render(<NotificationsPage />);
    const kind = await screen.findByRole("switch", { name: "A job you started has failed" });
    expect(kind).toBeDisabled();
    expect(screen.getByRole("switch", { name: label })).toBeEnabled();
  });

  it("shows the engine's refusal for a kind and leaves it as it was", async () => {
    vi.mocked(api.myNoticeMail).mockResolvedValue({ ...available, enabled: true });
    vi.mocked(api.setMyNoticeMail).mockRejectedValueOnce(
      new ApiError(422, "UNKNOWN_NOTICE_KIND", "Not a kind of notice: job.failed"),
    );
    render(<NotificationsPage />);
    const toggle = await screen.findByRole("switch", { name: "A job you started has failed" });
    fireEvent.click(toggle);
    expect(await screen.findByText(/Not a kind of notice/)).toBeInTheDocument();
    expect(toggle).toHaveAttribute("aria-checked", "true");
  });
});
