import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { openEventStream } from "@/api/eventStream";
import type { Notification, NotificationPage } from "@/types";
import { InboxButton } from "./InboxButton";

vi.mock("@/api/client", () => ({
  notificationEventsUrl: () => "/api/v1/me/notifications/events",
  api: { me: vi.fn(), notifications: vi.fn(), markNotificationsRead: vi.fn(), myWorkspaces: vi.fn(async () => []) },
}));
// The stream is read with fetch (D247); the test drives what the engine would push.
vi.mock("@/api/eventStream", () => ({ openEventStream: vi.fn() }));

class FakeStream {
  static opened: FakeStream[] = [];
  listeners = new Map<string, (event: MessageEvent<string>) => void>();
  closed = false;
  constructor(public url: string) {
    FakeStream.opened.push(this);
  }
  addEventListener(type: string, listener: (event: MessageEvent<string>) => void) {
    this.listeners.set(type, listener);
  }
  close() {
    this.closed = true;
  }
  push(type: string, data: unknown) {
    act(() => this.listeners.get(type)?.({ data: JSON.stringify(data) } as MessageEvent<string>));
  }
}

const notice = (id: string, kind: Notification["kind"], details: Notification["details"], read = false) =>
  ({
    id,
    kind,
    workspaceKey: "default",
    subject: { kind: kind.startsWith("job") ? "job" : "change-set", id: `s-${id}` },
    details,
    read,
    readAt: null,
    createdAt: new Date().toISOString(),
  }) as Notification;

const submitted = notice("n1", "change-set.submitted", {
  changeSetName: "Spring update",
  actor: { kind: "user", id: "u2", name: "Bea Costa" },
});
const sentBack = notice("n2", "change-set.sent-back", { changeSetName: "Autumn fixes", comment: "Check the codes" });
const approved = notice("n3", "change-set.approved", { changeSetName: "Old set" });
const failed = notice("n4", "job.failed", { jobKind: "import" }, true);

const page = (items: Notification[], unreadCount: number, nextCursor: string | null = null): NotificationPage => ({
  items,
  nextCursor,
  unreadCount,
});

/** A pointer press as a browser makes it: focus moves to the button before the click. */
function press(button: HTMLElement) {
  fireEvent.pointerDown(button);
  act(() => button.focus());
  fireEvent.click(button);
}

const onNavigate = vi.fn();
const bell = () => screen.findByRole("button", { name: /^Inbox/ });

function renderBell() {
  return render(<InboxButton applicationKey="herbarium" onNavigate={onNavigate} />);
}

beforeEach(() => {
  vi.clearAllMocks();
  FakeStream.opened = [];
  vi.mocked(openEventStream).mockImplementation((url) => new FakeStream(url) as never);
  vi.mocked(api.me).mockResolvedValue({ id: "u1", kind: "user", name: "Ana" } as never);
  vi.mocked(api.notifications).mockResolvedValue(page([submitted, sentBack, approved, failed], 3));
  vi.mocked(api.markNotificationsRead).mockResolvedValue({ marked: 1, unreadCount: 2 });
});
afterEach(cleanup);

describe("Inbox (0.12 A2)", () => {
  it("shows the live unread count on the bell, named for screen readers, and none at zero", async () => {
    renderBell();
    await bell();
    // The stream opens just after the bell shows; on a loaded runner that can be a moment later.
    await waitFor(() => expect(FakeStream.opened).toHaveLength(1));
    FakeStream.opened[0].push("unread", { unreadCount: 3 });
    expect(await screen.findByRole("button", { name: "Inbox, 3 unread" })).toHaveTextContent("3");
    FakeStream.opened[0].push("unread", { unreadCount: 12 });
    expect(await screen.findByRole("button", { name: "Inbox, 12 unread" })).toHaveTextContent("9+");
    FakeStream.opened[0].push("unread", { unreadCount: 0 });
    const quiet = await screen.findByRole("button", { name: "Inbox" });
    expect(quiet).not.toHaveTextContent(/\d/);
  });

  it("counts a notice that arrives on the stream and closes the stream with the bell", async () => {
    const { unmount } = renderBell();
    await bell();
    await waitFor(() => expect(FakeStream.opened).toHaveLength(1));
    FakeStream.opened[0].push("unread", { unreadCount: 1 });
    FakeStream.opened[0].push("notification", failed);
    FakeStream.opened[0].push("notification", submitted);
    expect(await screen.findByRole("button", { name: "Inbox, 2 unread" })).toBeInTheDocument();
    unmount();
    expect(FakeStream.opened[0].closed).toBe(true);
  });

  it("shows no bell to a client", async () => {
    vi.mocked(api.me).mockResolvedValue({ id: "c1", kind: "client", name: "Integration" } as never);
    // useMe keeps the first answer for the page, so the person is already known: a fresh module.
    vi.resetModules();
    const { InboxButton: Fresh } = await import("./InboxButton");
    render(<Fresh applicationKey="herbarium" onNavigate={onNavigate} />);
    await waitFor(() => expect(api.me).toHaveBeenCalled());
    await act(async () => undefined);
    expect(screen.queryByRole("button", { name: /^Inbox/ })).not.toBeInTheDocument();
    expect(FakeStream.opened).toHaveLength(0);
  });

  it("opens with the keyboard's activation, words each kind, and closes on Escape returning focus", async () => {
    renderBell();
    const button = await bell();
    button.focus();
    fireEvent.click(button);
    const panel = await screen.findByRole("dialog", { name: /^Inbox/ });
    expect(within(panel).getByRole("heading", { name: /^Unread/ })).toBeInTheDocument();
    expect(await within(panel).findByText("Waiting for your approval")).toBeInTheDocument();
    expect(within(panel).getByText(/‘Spring update’ · From Bea Costa/)).toBeInTheDocument();
    expect(within(panel).getByText("Sent back: ‘Autumn fixes’")).toBeInTheDocument();
    expect(within(panel).getByText(/Check the codes/)).toBeInTheDocument();
    expect(within(panel).getByText("Approved: ‘Old set’")).toBeInTheDocument();
    expect(within(panel).getByText("Import failed")).toBeInTheDocument();
    expect(within(panel).getByText(/Started by you/)).toBeInTheDocument();
    // Unread is said in words as well as by the dot.
    expect(within(panel).getAllByText("Unread:")).toHaveLength(3);

    fireEvent.keyDown(panel, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog", { name: /^Inbox/ })).not.toBeInTheDocument());
    await waitFor(() => expect(button).toHaveFocus());
  });

  it("marks a notice read and opens its place when activated", async () => {
    renderBell();
    fireEvent.click(await bell());
    fireEvent.click(await screen.findByRole("button", { name: /Waiting for your approval/ }));
    expect(api.markNotificationsRead).toHaveBeenCalledWith({ ids: ["n1"] });
    expect(onNavigate).toHaveBeenCalledWith(expect.objectContaining({ kind: "changeSetChanges", changeSetId: "s-n1" }));
    expect(await screen.findByRole("button", { name: "Inbox, 2 unread" })).toBeInTheDocument();
  });

  it("opens a change set in its own workspace's application where none is open, as on Home (0.12 NT1)", async () => {
    vi.mocked(api.myWorkspaces).mockResolvedValueOnce([{ key: "default", applications: [{ key: "plants" }] }] as never);
    render(<InboxButton applicationKey={undefined} onNavigate={onNavigate} />);
    fireEvent.click(await bell());
    await waitFor(() => expect(api.myWorkspaces).toHaveBeenCalled());
    await act(async () => undefined);
    fireEvent.click(await screen.findByRole("button", { name: /Waiting for your approval/ }));
    expect(onNavigate).toHaveBeenCalledWith(
      expect.objectContaining({ kind: "changeSetChanges", applicationKey: "plants", changeSetId: "s-n1" }),
    );
  });

  it("opens a job's page, and leads nowhere for an approved change set that is gone", async () => {
    vi.mocked(api.notifications).mockResolvedValue(page([approved, failed], 1));
    renderBell();
    fireEvent.click(await bell());
    fireEvent.click(await screen.findByRole("button", { name: /Approved/ }));
    expect(api.markNotificationsRead).toHaveBeenCalledWith({ ids: ["n3"] });
    expect(onNavigate).not.toHaveBeenCalled();
    fireEvent.click(await screen.findByRole("button", { name: /Import failed/ }));
    expect(onNavigate).toHaveBeenCalledWith({ kind: "settings", page: "jobs", jobId: "s-n4" });
    expect(api.markNotificationsRead).toHaveBeenCalledTimes(1);
  });

  it("marks every notice read, then hides Mark all read", async () => {
    vi.mocked(api.markNotificationsRead).mockResolvedValue({ marked: 3, unreadCount: 0 });
    renderBell();
    await bell();
    await waitFor(() => expect(FakeStream.opened).toHaveLength(1));
    FakeStream.opened[0].push("unread", { unreadCount: 3 });
    fireEvent.click(await screen.findByRole("button", { name: "Inbox, 3 unread" }));
    fireEvent.click(await screen.findByRole("button", { name: "Mark all read" }));
    expect(api.markNotificationsRead).toHaveBeenCalledWith({ all: true });
    await waitFor(() => expect(screen.queryByRole("button", { name: "Mark all read" })).not.toBeInTheDocument());
    expect(screen.queryByText("Unread:")).not.toBeInTheDocument();
  });

  it("lists at most 20 unread notices, counts the rest, and opens every notice's page (0.12 NT1)", async () => {
    vi.mocked(api.notifications).mockResolvedValue(page([submitted, sentBack], 25, "c2"));
    renderBell();
    await bell();
    FakeStream.opened[0].push("unread", { unreadCount: 25 });
    fireEvent.click(await screen.findByRole("button", { name: "Inbox, 25 unread" }));
    await screen.findByText("Waiting for your approval");
    expect(api.notifications).toHaveBeenCalledWith({ unread: true, pageSize: 20 });
    expect(screen.getByText("And 23 more unread.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Show older" })).not.toBeInTheDocument();
    const all = screen.getByRole("link", { name: /See all notifications/ });
    expect(all).toHaveAttribute("href", "/notifications");
    fireEvent.click(all);
    expect(onNavigate).toHaveBeenCalledWith({ kind: "notifications" });
    await waitFor(() => expect(screen.queryByRole("dialog", { name: /^Inbox/ })).not.toBeInTheDocument());
  });

  it("closes on a second press of the bell (the user, 2026-10-28)", async () => {
    renderBell();
    const button = await bell();
    press(button);
    // Opened, the panel holds focus, as in a browser; the second press takes it to the bell.
    const panel = await screen.findByRole("dialog", { name: /^Inbox/ });
    act(() => panel.focus());
    press(button);
    await waitFor(() => expect(screen.queryByRole("dialog", { name: /^Inbox/ })).not.toBeInTheDocument());
    press(button);
    expect(await screen.findByRole("dialog", { name: /^Inbox/ })).toBeInTheDocument();
  });

  it("says all is read when nothing is unread, and shows a failed read with Retry", async () => {
    vi.mocked(api.notifications).mockResolvedValueOnce(page([], 0));
    renderBell();
    fireEvent.click(await bell());
    expect(await screen.findByText("You are all caught up.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /See all notifications/ })).toBeInTheDocument();
    cleanup();

    vi.mocked(api.notifications).mockRejectedValueOnce(new Error("Inbox unavailable"));
    vi.mocked(api.notifications).mockResolvedValueOnce(page([failed], 0));
    renderBell();
    fireEvent.click(await bell());
    expect(await screen.findByText(/Inbox unavailable/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("Import failed")).toBeInTheDocument();
  });

  it("rereads an open list when the stream brings a new notice", async () => {
    renderBell();
    fireEvent.click(await bell());
    await screen.findByText("Waiting for your approval");
    const before = vi.mocked(api.notifications).mock.calls.length;
    FakeStream.opened[0].push("notification", notice("n9", "job.completed", { jobKind: "export" }));
    await waitFor(() => expect(vi.mocked(api.notifications).mock.calls.length).toBeGreaterThan(before));
  });
});
