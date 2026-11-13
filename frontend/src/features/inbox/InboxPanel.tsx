/**
 * The inbox's short list (0.12 A2; NT1, D460): the unread notices only, newest first, at most
 * `SHORT_LIST` of them and how many more. A notice opens its place and is marked read; it is gone
 * the next time the panel opens. Mark all read clears the lot. Every notice of the last 90 days is
 * on the Notifications page, which the panel's foot opens. Shown inside the popover the bell opens.
 */

import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { formatServerDayTime } from "@/lib/dates";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { NOTIFICATIONS, routePath } from "@/routing/routes";
import type { Notification, RouteState } from "@/types";
import { Icon } from "@/ui/Icon";
import { InlineError } from "@/ui/InlineError";
import { Notice } from "@/ui/Notice";
import { RouteLink } from "@/ui/RouteLink";
import { Skeleton } from "@/ui/Skeleton";
import { noticeRoute, noticeText } from "./inboxText";
import { setUnreadCount, touchSubject, useInbox } from "@/state/useInbox";

/** Unread notices the panel lists at most; the rest are counted. */
const SHORT_LIST = 20;

export function InboxPanel({
  applicationKey,
  onNavigate,
  close,
}: {
  /** The application open now, whose page a change set's review opens in. */
  applicationKey: string | undefined;
  onNavigate: (route: RouteState) => void;
  close: () => void;
}) {
  const { unreadCount, arrivals } = useInbox(false);
  const [problem, setProblem] = useState("");
  // A change set's review opens in its own workspace's first application: Home and the
  // Notifications page have no application open, and another workspace may run another model.
  const [firstApplication, setFirstApplication] = useState<Map<string, string | undefined>>(new Map());
  useEffect(() => {
    let active = true;
    api.myWorkspaces().then(
      (loaded) => active && setFirstApplication(new Map(loaded.map((item) => [item.key, item.applications[0]?.key]))),
      () => undefined,
    );
    return () => {
      active = false;
    };
  }, []);
  const feed = useCursorFeed<Notification>(async () => {
    const page = await api.notifications({ unread: true, pageSize: SHORT_LIST });
    setUnreadCount(page.unreadCount);
    // One page only: the rest are counted, and listed on the Notifications page.
    return { ...page, nextCursor: null };
  }, [arrivals]);
  const shownUnread = feed.items.filter((item) => !item.read).length;
  const more = Math.max(0, unreadCount - shownUnread);

  const markRead = async (selection: { ids: string[] } | { all: true }, ids: string[] | "all") => {
    setProblem("");
    feed.setItems((items) =>
      items.map((item) => (ids === "all" || ids.includes(item.id) ? { ...item, read: true } : item)),
    );
    try {
      setUnreadCount((await api.markNotificationsRead(selection)).unreadCount);
    } catch (cause) {
      setProblem(errorMessage(cause));
      feed.reload();
    }
  };

  const open = (notice: Notification) => {
    if (!notice.read) void markRead({ ids: [notice.id] }, [notice.id]);
    const route = noticeRoute(notice, firstApplication.get(notice.workspaceKey) ?? applicationKey);
    if (route) {
      close();
      onNavigate(route);
      // The address may be the one the person is on: the page there reads its subject again.
      touchSubject(notice.subject.id);
    }
  };

  return (
    <div className="inbox-panel">
      <header>
        <h2>Unread{unreadCount > 0 && <span className="inbox-count">{unreadCount}</span>}</h2>
        {unreadCount > 0 && (
          <button type="button" className="ghost" onClick={() => void markRead({ all: true }, "all")}>
            Mark all read
          </button>
        )}
      </header>
      {problem && <Notice tone="error">{problem}</Notice>}
      {feed.error && <InlineError message={feed.error} onRetry={feed.retry} />}
      {feed.loading && !feed.items.length && !feed.error && <Skeleton label="Loading the inbox" lines={3} />}
      {!feed.loading && !feed.error && !feed.items.length && <p className="inbox-empty">You are all caught up.</p>}
      {feed.items.length > 0 && (
        <ul className="inbox-list">
          {feed.items.map((notice) => (
            <li key={notice.id}>
              <NoticeButton notice={notice} onOpen={() => open(notice)} />
            </li>
          ))}
        </ul>
      )}
      {more > 0 && <p className="inbox-more">And {more} more unread.</p>}
      <RouteLink
        className="inbox-all"
        href={routePath(NOTIFICATIONS)}
        onNavigate={() => {
          close();
          onNavigate(NOTIFICATIONS);
        }}
      >
        See all notifications <Icon name="chevron-right" size={14} />
      </RouteLink>
    </div>
  );
}

/** One notice as a button: the unread dot, its title and second line, and when (`inboxText`). */
export function NoticeButton({
  notice,
  onOpen,
}: {
  notice: Notification;
  onOpen: (event: React.MouseEvent<HTMLButtonElement>) => void;
}) {
  const { title, detail } = noticeText(notice);
  return (
    <button
      type="button"
      className="inbox-item"
      data-read={notice.read || undefined}
      onMouseDown={(event) => {
        // Shift+click would otherwise select the page's text between two notices.
        if (event.shiftKey) event.preventDefault();
      }}
      onClick={onOpen}
    >
      <span className="inbox-dot" data-unread={!notice.read || undefined} aria-hidden="true" />
      <span className="inbox-text">
        <strong>
          {!notice.read && <span className="visually-hidden">Unread: </span>}
          {title}
        </strong>
        {detail.length > 0 && <small>{detail.join(" · ")}</small>}
      </span>
      <time className="inbox-time" dateTime={notice.createdAt}>
        {formatServerDayTime(notice.createdAt)}
      </time>
    </button>
  );
}
