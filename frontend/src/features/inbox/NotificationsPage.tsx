/**
 * The person's notices of the last 90 days (0.12 NT1, D460–D465), opened from the account menu and
 * the bell's short list: searched, filtered by kind, workspace and read or unread, newest or oldest
 * first, and loaded as the list scrolls. A notice opens its place and is marked read; ticked
 * notices are marked read or unread, or deleted for good; Delete all read… clears the read ones.
 * Every filter is the engine's, so it covers every notice, not the rows loaded. Outside any
 * workspace, as Home is.
 */

import { useEffect, useMemo, useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { ShellFrame } from "@/app/ShellFrame";
import { TopBar } from "@/app/TopBar";
import { counted } from "@/lib/count";
import { useCursorWindow } from "@/lib/hooks/useCursorWindow";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import { useRecordSelection } from "@/lib/hooks/useRecordSelection";
import { emptyModel } from "@/model/emptyModel";
import { appPath, openIn } from "@/state/openWorkspace";
import { applicationFor } from "@/model/lookup";
import { HOME, routePath, viewRoute } from "@/routing/routes";
import type { EngineModel, Notification, NotificationKind, OwnWorkspace, RouteState } from "@/types";
import { CatalogueWindow } from "@/ui/CatalogueWindow";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { Notice } from "@/ui/Notice";
import { RouteLink } from "@/ui/RouteLink";
import { WorkspaceField } from "@/ui/WorkspaceField";
import { SearchField } from "@/ui/SearchField";
import { SelectionCheckbox } from "@/ui/SelectionCheckbox";
import { NoticeButton } from "./InboxPanel";
import { KIND_LABELS, noticeRoute, noticeText } from "./inboxText";
import { setUnreadCount, touchSubject, useInbox } from "@/state/useInbox";

const PAGE_SIZE = 50;
/** The most notices one mark or delete names (the API's limit). */
const MAX_SELECTED = 500;
const MAIL_SETTINGS: RouteState = { kind: "settings", page: "notifications" };

type Show = "all" | "unread" | "read";
const SHOW: Record<Show, boolean | undefined> = { all: undefined, unread: true, read: false };

export function NotificationsPage({
  model,
  noticeId,
  onNavigate,
}: {
  model: EngineModel;
  /** A notice a digest's link names (`?notice=<id>`, 0.16 AO3): opened once the workspaces are known. */
  noticeId?: string;
  onNavigate: (route: RouteState) => void;
}) {
  const { unreadCount, arrivals } = useInbox(false);
  const [workspaces, setWorkspaces] = useState<OwnWorkspace[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [search, setSearch] = useState("");
  const [kind, setKind] = useState<NotificationKind | "">("");
  const [workspace, setWorkspace] = useState("");
  const [show, setShow] = useState<Show>("all");
  const [sort, setSort] = useState<"newest" | "oldest">("newest");
  const [problem, setProblem] = useState("");
  const [pending, setPending] = useState(false);
  const [clearing, setClearing] = useState(false);
  const q = useDebouncedValue(search.trim());

  useEffect(() => {
    let active = true;
    api.myWorkspaces().then(
      (found) => {
        if (!active) return;
        setWorkspaces(found);
        setLoaded(true);
      },
      () => active && setLoaded(true),
    );
    return () => {
      active = false;
    };
  }, []);

  const list = useCursorWindow<Notification>(
    async (selector) => {
      const page = await api.notifications({
        q: q || undefined,
        kind: kind || undefined,
        workspace: workspace || undefined,
        unread: SHOW[show],
        sort,
        pageSize: PAGE_SIZE,
        ...selector,
      });
      setUnreadCount(page.unreadCount);
      return page;
    },
    [q, kind, workspace, show, sort],
    // A notice arriving, or the count moving elsewhere, re-reads the rows in place.
    { refreshToken: arrivals },
  );
  // The records table's selection (0.9 K1): a tick toggles, Shift extends from the last one ticked,
  // and a changed filter starts with none. A notice has no version; at most one request's worth.
  const rows = useMemo(() => list.items.map((item) => ({ id: item.id, version: 0 })), [list.items]);
  const selection = useRecordSelection(JSON.stringify([q, kind, workspace, show, sort]), rows, MAX_SELECTED);
  const ids = selection.selection.mode === "ids" ? [...selection.selection.ids.keys()] : [];

  const workspaceLabel = new Map(workspaces.map((item) => [item.key, item.label]));
  const firstApplication = new Map(workspaces.map((item) => [item.key, item.applications[0]?.key]));
  const narrowed = Boolean(q || kind || workspace || show !== "all");

  const act = async (action: () => Promise<{ unreadCount: number }>) => {
    setProblem("");
    setPending(true);
    try {
      setUnreadCount((await action()).unreadCount);
      selection.clear();
      list.reload();
      return true;
    } catch (cause) {
      setProblem(errorMessage(cause));
      return false;
    } finally {
      setPending(false);
    }
  };

  /** A click on a notice opens it; with Cmd or Ctrl it ticks it, with Shift it ticks the range to it. */
  const press = (notice: Notification, event: React.MouseEvent) => {
    if (event.shiftKey || event.metaKey || event.ctrlKey) {
      selection.toggle({ id: notice.id, version: 0 }, event.shiftKey);
      return;
    }
    open(notice);
  };

  const open = (notice: Notification) => {
    if (!notice.read) void act(() => api.markNotificationsRead({ ids: [notice.id] }));
    const route = noticeRoute(notice, firstApplication.get(notice.workspaceKey));
    // A followed publication leads to the publication, as the workspace's Publications page opens it: while
    // it is the active one and the person may still browse the workspace; else the workspace's Publications.
    const publicationId = notice.details.publicationId;
    const fallback = () => {
      if (!route) return;
      onNavigate(route);
      touchSubject(notice.subject.id);
    };
    const application = workspaces.find((item) => item.key === notice.workspaceKey)?.applications[0];
    if (notice.kind === "change-set.published" && publicationId && application) {
      api.publication(publicationId).then((found) => {
        if (found.status !== "active") return fallback();
        openIn(notice.workspaceKey, appPath(notice.workspaceKey, application), onNavigate, (model) => {
          const app = applicationFor(model, application.key);
          return app && { ...viewRoute(app, app.defaultView, notice.workspaceKey), publicationId };
        });
      }, fallback);
      return;
    }
    fallback();
  };

  // A digest's link opens the notice's subject, as a click on it in the list does (0.16 AO3, AO-D36).
  // A notice that is gone, or not the person's, leaves the page as it is, with a sentence.
  const [opened, setOpened] = useState("");
  useEffect(() => {
    if (!noticeId || opened === noticeId || !loaded) return;
    setOpened(noticeId);
    let active = true;
    api.notification(noticeId).then(
      (found) => active && open(found),
      () => active && setProblem("That notification is no longer in your inbox."),
    );
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [noticeId, loaded]);

  const bar = { ...emptyModel(), product: model.product };
  const total = list.totalCount;

  return (
    <ShellFrame
      topBar={
        <TopBar
          model={bar}
          onHome={() => onNavigate(HOME)}
          onSelectApplication={() => undefined}
          onNavigate={onNavigate}
        />
      }
      main={{ className: "home" }}
    >
      <div className="home-page notifications-page">
        <header className="notifications-head">
          <div>
            <h1>Notifications</h1>
            <p>
              {unreadCount} unread
              {total !== null && !narrowed && ` · ${total} in the last 90 days`}
              {total !== null && narrowed && ` · ${counted(total, "match", "matches")}`}
            </p>
          </div>
          <RouteLink href={routePath(MAIL_SETTINGS)} onNavigate={() => onNavigate(MAIL_SETTINGS)}>
            Notification email settings
          </RouteLink>
        </header>
        <div className="changes-filters notifications-filters" role="group" aria-label="Filter the notifications">
          <SearchField
            label="Search"
            placeholder="Change set, comment, person, job"
            value={search}
            onChange={setSearch}
            clearOnEscape
          />
          <label className="toolbar-field">
            Kind
            <select value={kind} onChange={(event) => setKind(event.target.value as NotificationKind | "")}>
              <option value="">All kinds</option>
              {Object.entries(KIND_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <WorkspaceField
            toolbar
            items={workspaces}
            allOption="All workspaces"
            value={workspace}
            onChange={setWorkspace}
          />
          <label className="toolbar-field">
            Show
            <select value={show} onChange={(event) => setShow(event.target.value as Show)}>
              <option value="all">All</option>
              <option value="unread">Unread</option>
              <option value="read">Read</option>
            </select>
          </label>
          <label className="toolbar-field">
            Sort
            <select value={sort} onChange={(event) => setSort(event.target.value as "newest" | "oldest")}>
              <option value="newest">Newest first</option>
              <option value="oldest">Oldest first</option>
            </select>
          </label>
        </div>
        {problem && <Notice tone="error">{problem}</Notice>}
        {selection.refusedTotal !== undefined && (
          <Notice tone="warning">At most {MAX_SELECTED} notifications are changed at once.</Notice>
        )}
        {/* One bar of one height above the list: ticking a notice changes its words and buttons,
            never where the list starts (the user, 2026-10-28). */}
        <div
          className="notifications-selection"
          role="toolbar"
          aria-label="The ticked notifications"
          data-active={selection.count > 0 || undefined}
        >
          <label className="notifications-select-all">
            <SelectionCheckbox
              label="Select every loaded notification"
              state={selection.loaded}
              onSelect={() => selection.toggleLoaded()}
            />
            Select all
          </label>
          {selection.count === 0 ? (
            <small>Shift selects a range, Cmd or Ctrl adds one</small>
          ) : (
            <>
              <strong aria-live="polite">{selection.count} selected</strong>
              <button
                type="button"
                className="secondary"
                disabled={pending}
                onClick={() => void act(() => api.markNotificationsRead({ ids }))}
              >
                Mark read
              </button>
              <button
                type="button"
                className="secondary"
                disabled={pending}
                onClick={() => void act(() => api.markNotificationsRead({ ids }, false))}
              >
                Mark unread
              </button>
              <button
                type="button"
                className="danger-outline"
                disabled={pending}
                onClick={() => void act(() => api.removeNotifications({ ids }))}
              >
                Delete
              </button>
            </>
          )}
        </div>
        <CatalogueWindow
          list={list}
          label="Notifications"
          noun={["notification", "notifications"]}
          pageSize={PAGE_SIZE}
          loadingText="Loading notifications…"
          emptyText={narrowed ? "No notification matches." : "No notifications in the last 90 days."}
          entry={(notice) => (
            <div className="notification-row" data-unread={!notice.read || undefined}>
              <SelectionCheckbox
                label={`Select: ${noticeText(notice).title}`}
                state={selection.isSelected(notice.id) ? "all" : "none"}
                onSelect={(extend) => selection.toggle({ id: notice.id, version: 0 }, extend)}
              />
              <NoticeButton notice={notice} onOpen={(event) => press(notice, event)} />
              <span className="notification-workspace">
                {workspaceLabel.get(notice.workspaceKey) ?? notice.workspaceKey}
              </span>
            </div>
          )}
        />
        <footer className="notifications-foot">
          <p>Notices are kept for 90 days.</p>
          <button type="button" className="secondary" onClick={() => setClearing(true)}>
            Delete all read…
          </button>
        </footer>
      </div>
      {clearing && (
        <ConfirmDialog
          title="Delete all read notifications?"
          confirmLabel="Delete read notifications"
          pending={pending}
          error={problem}
          onCancel={() => {
            setClearing(false);
            setProblem("");
          }}
          onConfirm={async () => {
            if (await act(() => api.removeNotifications({ read: true }))) setClearing(false);
          }}
        >
          <p>
            Every notification you have read is deleted for good. Unread ones stay, and the change sets and jobs they
            were about are not touched.
          </p>
        </ConfirmDialog>
      )}
    </ShellFrame>
  );
}
