/**
 * The inbox's notices, newest first (0.12 A2): an unread dot, a title and a second line each; a
 * notice opens its place and is marked read; Show older reads the next page; Mark all read clears
 * the lot. Shown inside the popover the bell opens.
 */

import { useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { formatServerDayTime } from "@/lib/dates";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import type { Notification, RouteState } from "@/types";
import { InlineError } from "@/ui/InlineError";
import { Notice } from "@/ui/Notice";
import { Skeleton } from "@/ui/Skeleton";
import { noticeRoute, noticeText } from "./inboxText";
import { setUnreadCount, useInbox } from "./useInbox";

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
  const feed = useCursorFeed<Notification>(
    async (cursor) => {
      const page = await api.notifications(cursor);
      setUnreadCount(page.unreadCount);
      return page;
    },
    [arrivals],
  );

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
    const route = noticeRoute(notice, applicationKey);
    if (route) {
      close();
      onNavigate(route);
    }
  };

  return (
    <div className="inbox-panel">
      <header>
        <h2>Inbox</h2>
        {unreadCount > 0 && (
          <button type="button" className="ghost" onClick={() => void markRead({ all: true }, "all")}>
            Mark all read
          </button>
        )}
      </header>
      {problem && <Notice tone="error">{problem}</Notice>}
      {feed.error && <InlineError message={feed.error} onRetry={feed.retry} />}
      {feed.loading && !feed.items.length && !feed.error && <Skeleton label="Loading the inbox" lines={3} />}
      {!feed.loading && !feed.error && !feed.items.length && <p className="inbox-empty">Nothing waiting for you.</p>}
      {feed.items.length > 0 && (
        <ul className="inbox-list">
          {feed.items.map((notice) => {
            const { title, detail } = noticeText(notice);
            return (
              <li key={notice.id}>
                <button
                  type="button"
                  className="inbox-item"
                  data-read={notice.read || undefined}
                  onClick={() => open(notice)}
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
              </li>
            );
          })}
        </ul>
      )}
      {feed.hasMore && !feed.loading && (
        <button type="button" className="secondary" onClick={feed.loadMore}>
          Show older
        </button>
      )}
    </div>
  );
}
