import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { emptyModel } from "@/model/emptyModel";
import type { Notification } from "@/types";
import { NotificationsPage } from "./NotificationsPage";

vi.mock("@/api/client", () => ({
  notificationEventsUrl: () => "/api/v1/me/notifications/events",
  api: {
    notifications: vi.fn(),
    markNotificationsRead: vi.fn(),
    removeNotifications: vi.fn(),
    myWorkspaces: vi.fn(),
    notification: vi.fn(),
    publication: vi.fn(),
  },
}));
// The top bar is the one every page shows (its own tests); here only the page's content.
vi.mock("@/state/openWorkspace", () => ({
  appPath: () => "/apps/plants",
  openIn: (_key: string, _path: string, go: (route: unknown) => void, route: (model: unknown) => unknown) =>
    go(route({ applications: [{ key: "plants", defaultView: "all", views: [] }] })),
}));
vi.mock("@/model/lookup", () => ({ applicationFor: (model: { applications: unknown[] }) => model.applications[0] }));
vi.mock("@/app/TopBar", () => ({ TopBar: () => null }));

const notice = (id: string, kind: Notification["kind"], details: Notification["details"], read = false) =>
  ({
    id,
    kind,
    workspaceKey: "herbarium",
    subject: { kind: kind.startsWith("job") ? "job" : "change-set", id: `s-${id}` },
    details,
    read,
    readAt: null,
    createdAt: new Date().toISOString(),
  }) as Notification;

const waiting = notice("n1", "change-set.submitted", { changeSetName: "Spring update" });
const finished = notice("n2", "job.completed", { jobKind: "export" }, true);
const onNavigate = vi.fn();

function renderPage(noticeId?: string) {
  return render(<NotificationsPage model={emptyModel()} noticeId={noticeId} onNavigate={onNavigate} />);
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.notifications).mockResolvedValue({
    items: [waiting, finished],
    nextCursor: null,
    totalCount: 2,
    startIndex: 0,
    unreadCount: 1,
  });
  vi.mocked(api.myWorkspaces).mockResolvedValue([
    { key: "herbarium", label: "Herbarium", applications: [{ key: "plants" }] },
  ] as never);
  vi.mocked(api.markNotificationsRead).mockResolvedValue({ marked: 1, unreadCount: 0 });
  vi.mocked(api.removeNotifications).mockResolvedValue({ removed: 1, unreadCount: 1 });
});

describe("The Notifications page (0.12 NT1)", () => {
  it("lists every notice with its workspace, the unread one tinted as a whole row", async () => {
    renderPage();
    expect(await screen.findByRole("heading", { name: "Notifications" })).toBeInTheDocument();
    const list = await screen.findByRole("list", { name: "Notifications" });
    expect(await within(list).findByText("Waiting for your approval")).toBeInTheDocument();
    expect(within(list).getByText("Export finished")).toBeInTheDocument();
    expect(await within(list).findAllByText("Herbarium")).toHaveLength(2);
    const rows = list.querySelectorAll(".notification-row");
    expect(rows[0]).toHaveAttribute("data-unread", "true");
    expect(rows[1]).not.toHaveAttribute("data-unread");
    expect(screen.getByText(/2 in the last 90 days/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Notification email settings" })).toHaveAttribute(
      "href",
      "/settings/notifications",
    );
  });

  it("asks the engine for each filter and the order, so they cover every notice", async () => {
    renderPage();
    await screen.findByText("Waiting for your approval");
    fireEvent.change(screen.getByLabelText("Kind"), { target: { value: "job.failed" } });
    fireEvent.change(screen.getByLabelText("Show"), { target: { value: "unread" } });
    fireEvent.change(screen.getByLabelText("Sort"), { target: { value: "oldest" } });
    await waitFor(() =>
      expect(api.notifications).toHaveBeenLastCalledWith(
        expect.objectContaining({ kind: "job.failed", unread: true, sort: "oldest", pageSize: 50 }),
      ),
    );
  });

  it("marks ticked notices unread, deletes them, and clears every read one after a confirmation", async () => {
    renderPage();
    const list = await screen.findByRole("list", { name: "Notifications" });
    fireEvent.click(await within(list).findByRole("checkbox", { name: "Select: Export finished" }));
    const bar = screen.getByRole("toolbar", { name: "The ticked notifications" });
    expect(within(bar).getByText("1 selected")).toBeInTheDocument();
    fireEvent.click(within(bar).getByRole("button", { name: "Mark unread" }));
    await waitFor(() => expect(api.markNotificationsRead).toHaveBeenCalledWith({ ids: ["n2"] }, false));
    await waitFor(() => expect(screen.queryByRole("button", { name: "Mark read" })).not.toBeInTheDocument());

    fireEvent.click(within(list).getByRole("checkbox", { name: "Select: Waiting for your approval" }));
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    await waitFor(() => expect(api.removeNotifications).toHaveBeenCalledWith({ ids: ["n1"] }));

    fireEvent.click(screen.getByRole("button", { name: "Delete all read…" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Delete all read notifications?" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Delete read notifications" }));
    await waitFor(() => expect(api.removeNotifications).toHaveBeenLastCalledWith({ read: true }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument());
  });

  it("shows a ticked notice read, then unread again, as the engine answers it (the user, 2026-10-28)", async () => {
    renderPage();
    const list = await screen.findByRole("list", { name: "Notifications" });
    await within(list).findByText("Waiting for your approval");
    const row = () => within(list).getByText("Waiting for your approval").closest(".notification-row");
    expect(row()).toHaveAttribute("data-unread", "true");

    vi.mocked(api.notifications).mockResolvedValue({
      items: [{ ...waiting, read: true }, finished],
      nextCursor: null,
      totalCount: 2,
      startIndex: 0,
      unreadCount: 0,
    });
    fireEvent.click(within(list).getByRole("checkbox", { name: "Select: Waiting for your approval" }));
    fireEvent.click(screen.getByRole("button", { name: "Mark read" }));
    await waitFor(() => expect(row()).not.toHaveAttribute("data-unread"));

    vi.mocked(api.notifications).mockResolvedValue({
      items: [waiting, finished],
      nextCursor: null,
      totalCount: 2,
      startIndex: 0,
      unreadCount: 1,
    });
    fireEvent.click(within(list).getByRole("checkbox", { name: "Select: Waiting for your approval" }));
    fireEvent.click(screen.getByRole("button", { name: "Mark unread" }));
    await waitFor(() => expect(row()).toHaveAttribute("data-unread", "true"));
  });

  it("selects with Cmd or Ctrl one at a time, a range with Shift, and all loaded at once (the user, 2026-10-28)", async () => {
    const third = notice("n3", "job.failed", { jobKind: "import" });
    vi.mocked(api.notifications).mockResolvedValue({
      items: [waiting, finished, third],
      nextCursor: null,
      totalCount: 3,
      startIndex: 0,
      unreadCount: 2,
    });
    renderPage();
    const list = await screen.findByRole("list", { name: "Notifications" });
    const count = () => screen.getByRole("toolbar", { name: "The ticked notifications" });

    fireEvent.click(await within(list).findByRole("button", { name: /Waiting for your approval/ }), { metaKey: true });
    expect(onNavigate).not.toHaveBeenCalled();
    expect(within(count()).getByText("1 selected")).toBeInTheDocument();
    fireEvent.click(within(list).getByRole("button", { name: /Import failed/ }), { shiftKey: true });
    expect(within(count()).getByText("3 selected")).toBeInTheDocument();
    fireEvent.click(within(list).getByRole("button", { name: /Export finished/ }), { ctrlKey: true });
    expect(within(count()).getByText("2 selected")).toBeInTheDocument();
    fireEvent.click(within(count()).getByRole("button", { name: "Mark read" }));
    await waitFor(() => expect(api.markNotificationsRead).toHaveBeenCalledWith({ ids: ["n1", "n3"] }));
    await waitFor(() => expect(screen.queryByRole("button", { name: "Mark read" })).not.toBeInTheDocument());

    fireEvent.click(screen.getByRole("checkbox", { name: "Select every loaded notification" }));
    expect(within(count()).getByText("3 selected")).toBeInTheDocument();
    // Unticking one, then Shift on another, sets the range between them as the clicked row goes: off.
    fireEvent.click(within(list).getByRole("checkbox", { name: "Select: Waiting for your approval" }));
    expect(within(count()).getByText("2 selected")).toBeInTheDocument();
    fireEvent.click(within(list).getByRole("checkbox", { name: "Select: Import failed" }), { shiftKey: true });
    expect(screen.queryByRole("button", { name: "Mark read" })).not.toBeInTheDocument();
  });

  it("opens a notice's place and marks it read", async () => {
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: /Waiting for your approval/ }));
    expect(api.markNotificationsRead).toHaveBeenCalledWith({ ids: ["n1"] });
    expect(onNavigate).toHaveBeenCalledWith(
      expect.objectContaining({ kind: "changeSetChanges", applicationKey: "plants", changeSetId: "s-n1" }),
    );
  });
});

describe("Opening a notice from a digest's link (0.16 AO3, AO-D36)", () => {
  it("opens the notice named in the address: marks it read and goes to its subject", async () => {
    vi.mocked(api.notification).mockResolvedValue(waiting);
    renderPage("n1");
    await waitFor(() => expect(api.notification).toHaveBeenCalledWith("n1"));
    await waitFor(() => expect(api.markNotificationsRead).toHaveBeenCalledWith({ ids: ["n1"] }));
    expect(onNavigate).toHaveBeenCalledWith(
      expect.objectContaining({ kind: "changeSetChanges", changeSetId: "s-n1", workspaceKey: "herbarium" }),
    );
  });

  it("says so when the notice is gone, and stays on the list", async () => {
    vi.mocked(api.notification).mockRejectedValue(new Error("There is no such notification"));
    renderPage("gone");
    expect(await screen.findByText(/no longer in your inbox/)).toBeInTheDocument();
    expect(onNavigate).not.toHaveBeenCalled();
    expect(api.markNotificationsRead).not.toHaveBeenCalled();
  });

  it("words a followed publication and opens the publication while it is the active one", async () => {
    const published = notice("n3", "change-set.published", {
      changeSetName: "Spring update",
      publicationId: "p-1",
      actor: { kind: "user", id: "u", name: "Ana" },
    });
    vi.mocked(api.notification).mockResolvedValue(published);
    vi.mocked(api.publication).mockResolvedValue({ id: "p-1", status: "active" } as never);
    vi.mocked(api.notifications).mockResolvedValue({
      items: [published],
      nextCursor: null,
      totalCount: 1,
      startIndex: 0,
      unreadCount: 1,
    });
    renderPage("n3");
    expect(await screen.findByText("Published: ‘Spring update’")).toBeInTheDocument();
    await waitFor(() => expect(api.markNotificationsRead).toHaveBeenCalledWith({ ids: ["n3"] }));
    await waitFor(() =>
      expect(onNavigate).toHaveBeenCalledWith(
        expect.objectContaining({
          kind: "list",
          applicationKey: "plants",
          workspaceKey: "herbarium",
          publicationId: "p-1",
        }),
      ),
    );
  });

  it("leads a withdrawn followed publication to the workspace's Publications", async () => {
    const published = notice("n4", "change-set.published", { changeSetName: "Old", publicationId: "p-0" });
    vi.mocked(api.notification).mockResolvedValue(published);
    vi.mocked(api.publication).mockResolvedValue({ id: "p-0", status: "withdrawn" } as never);
    renderPage("n4");
    await waitFor(() => expect(api.markNotificationsRead).toHaveBeenCalledWith({ ids: ["n4"] }));
    await waitFor(() => expect(api.publication).toHaveBeenCalledWith("p-0"));
    await waitFor(() =>
      expect(onNavigate).toHaveBeenCalledWith({
        kind: "publications",
        applicationKey: "plants",
        workspaceKey: "herbarium",
      }),
    );
  });
});
