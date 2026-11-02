import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import type { NoticeMail } from "@/types";
import { NotificationsPage } from "./NotificationsPage";

vi.mock("@/api/client", () => ({
  api: {
    myNoticeMail: vi.fn(),
    setMyNoticeMail: vi.fn(),
    followedWorkspaces: vi.fn(),
    unfollowWorkspace: vi.fn(),
  },
}));

const kinds: NoticeMail["kinds"] = [
  { kind: "change-set.submitted", label: "A change set is waiting for your approval", delivery: "now" },
  { kind: "change-set.approved", label: "A change set you submitted was approved", delivery: "now" },
  { kind: "job.failed", label: "A job you started has failed", delivery: "now" },
];
const available: NoticeMail = {
  enabled: false,
  available: true,
  reason: null,
  email: "ana@example.org",
  kinds,
  digest: null,
};
const label = "Email me when something arrives in my inbox";

describe("Settings › Notifications (0.12 M2 and its follow-up)", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(api.followedWorkspaces).mockResolvedValue([]);
  });

  it("switches it on and off, showing the address", async () => {
    vi.mocked(api.myNoticeMail).mockResolvedValue(available);
    vi.mocked(api.setMyNoticeMail).mockResolvedValueOnce({ ...available, enabled: true });
    render(<NotificationsPage />);
    expect(await screen.findByRole("heading", { name: "Notification email" })).toBeInTheDocument();
    const toggle = await screen.findByRole("switch", { name: label });
    expect(toggle).toHaveAttribute("aria-checked", "false");
    expect(screen.getByText(/Sent to ana@example.org/)).toBeInTheDocument();
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

  it("offers each kind as a three-way choice and saves it at once", async () => {
    vi.mocked(api.myNoticeMail).mockResolvedValue({ ...available, enabled: true });
    const after = kinds.map((item) => (item.kind === "job.failed" ? { ...item, delivery: "off" as const } : item));
    vi.mocked(api.setMyNoticeMail).mockResolvedValueOnce({ ...available, enabled: true, kinds: after });
    render(<NotificationsPage />);
    const group = await screen.findByRole("group", { name: "How each kind reaches me" });
    for (const item of kinds) {
      const choice = within(group).getByRole("radiogroup", { name: item.label });
      expect(
        within(choice)
          .getAllByRole("radio")
          .map((radio) => radio.parentElement?.textContent),
      ).toEqual(["At once", "Digest", "Off"]);
      expect(within(choice).getByRole("radio", { name: "At once" })).toBeChecked();
    }
    const failed = within(group).getByRole("radiogroup", { name: "A job you started has failed" });
    fireEvent.click(within(failed).getByRole("radio", { name: "Off" }));
    await waitFor(() => expect(api.setMyNoticeMail).toHaveBeenCalledWith({ kinds: { "job.failed": "off" } }));
    await waitFor(() => expect(within(failed).getByRole("radio", { name: "Off" })).toBeChecked());
    const approved = within(group).getByRole("radiogroup", { name: "A change set you submitted was approved" });
    expect(within(approved).getByRole("radio", { name: "At once" })).toBeChecked();
  });

  it("starts a daily digest in the browser's time zone with the first kind put in it", async () => {
    vi.spyOn(Intl.DateTimeFormat.prototype, "resolvedOptions").mockReturnValue({
      timeZone: "Europe/Budapest",
    } as Intl.ResolvedDateTimeFormatOptions);
    vi.mocked(api.myNoticeMail).mockResolvedValue({ ...available, enabled: true });
    render(<NotificationsPage />);
    expect(await screen.findByText(/Choose Digest for a kind to start one/)).toBeInTheDocument();
    const approvals = await screen.findByRole("radiogroup", { name: "A change set is waiting for your approval" });
    vi.mocked(api.setMyNoticeMail).mockResolvedValueOnce({
      ...available,
      enabled: true,
      kinds: kinds.map((item) => (item.kind === "change-set.submitted" ? { ...item, delivery: "digest" } : item)),
      digest: { every: "daily", timeZone: "Europe/Budapest", nextAt: "2026-11-03T06:00:00Z" },
    });
    fireEvent.click(within(approvals).getByRole("radio", { name: "Digest" }));
    await waitFor(() =>
      expect(api.setMyNoticeMail).toHaveBeenCalledWith({
        kinds: { "change-set.submitted": "digest" },
        digest: { every: "daily", timeZone: "Europe/Budapest" },
      }),
    );
    expect(await screen.findByText(/In your time zone, Europe\/Budapest\./)).toBeInTheDocument();
    expect(screen.getByText(/Next digest: Tuesday 3 November, 07:00\./)).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Every morning at 07:00" })).toBeChecked();
  });

  it("changes the digest to Mondays, sending the browser's time zone, and shows the next time", async () => {
    vi.spyOn(Intl.DateTimeFormat.prototype, "resolvedOptions").mockReturnValue({
      timeZone: "Europe/Budapest",
    } as Intl.ResolvedDateTimeFormatOptions);
    const daily = { every: "daily" as const, timeZone: "Europe/Budapest", nextAt: "2026-11-03T06:00:00Z" };
    vi.mocked(api.myNoticeMail).mockResolvedValue({ ...available, enabled: true, digest: daily });
    vi.mocked(api.setMyNoticeMail).mockResolvedValueOnce({
      ...available,
      enabled: true,
      digest: { ...daily, every: "weekly", nextAt: "2026-11-09T06:00:00Z" },
    });
    render(<NotificationsPage />);
    fireEvent.click(await screen.findByRole("radio", { name: "Mondays at 07:00" }));
    await waitFor(() =>
      expect(api.setMyNoticeMail).toHaveBeenCalledWith({
        digest: { every: "weekly", timeZone: "Europe/Budapest" },
      }),
    );
    expect(await screen.findByText(/Next digest: Monday 9 November, 07:00\./)).toBeInTheDocument();
  });

  it("lists the followed workspaces with Stop following", async () => {
    vi.mocked(api.myNoticeMail).mockResolvedValue({ ...available, enabled: true });
    vi.mocked(api.followedWorkspaces).mockResolvedValue([
      { workspaceKey: "default", label: "Master data", since: "2026-11-02T10:00:00Z" },
      { workspaceKey: "second", label: "Translations", since: "2026-11-02T10:00:00Z" },
    ]);
    vi.mocked(api.unfollowWorkspace).mockResolvedValue(undefined);
    render(<NotificationsPage />);
    expect(await screen.findByText("Master data")).toBeInTheDocument();
    expect(screen.getAllByText("Following since 2 November")).toHaveLength(2);
    fireEvent.click(screen.getByRole("button", { name: "Stop following Master data" }));
    await waitFor(() => expect(api.unfollowWorkspace).toHaveBeenCalledWith("default"));
    await waitFor(() => expect(screen.queryByText("Master data")).not.toBeInTheDocument());
    expect(screen.getByText("Translations")).toBeInTheDocument();
  });

  it("greys out the kinds while the main switch is off", async () => {
    vi.mocked(api.myNoticeMail).mockResolvedValue(available);
    render(<NotificationsPage />);
    const group = await screen.findByRole("group", { name: "How each kind reaches me" });
    expect(group).toBeDisabled();
    expect(screen.getByRole("switch", { name: label })).toBeEnabled();
  });

  it("shows the engine's refusal for a kind and leaves it as it was", async () => {
    vi.mocked(api.myNoticeMail).mockResolvedValue({ ...available, enabled: true });
    vi.mocked(api.setMyNoticeMail).mockRejectedValueOnce(
      new ApiError(422, "UNKNOWN_NOTICE_KIND", "Not a kind of notice: job.failed"),
    );
    render(<NotificationsPage />);
    const failed = await screen.findByRole("radiogroup", { name: "A job you started has failed" });
    fireEvent.click(within(failed).getByRole("radio", { name: "Off" }));
    expect(await screen.findByText(/Not a kind of notice/)).toBeInTheDocument();
    expect(within(failed).getByRole("radio", { name: "At once" })).toBeChecked();
  });
});
