/**
 * The signed-in person's inbox count, kept live (0.12 A2): one stream of the engine's server-sent
 * events, opened while any inbox button is mounted and closed with the last. The engine sends the
 * unread count at once, each new notice and the count after every change; nothing is polled. The
 * stream reconnects by itself (`api/eventStream`), and the count sent on connecting tells a panel
 * that its list may be stale. The stream is read with `fetch` so it carries the access token (D247).
 * A page showing a job or a change set marks the person's notices about it read (`useSubjectSeen`).
 */

import { useEffect, useSyncExternalStore } from "react";
import { api, notificationEventsUrl } from "@/api/client";
import { openEventStream, type EventStream } from "@/api/eventStream";
import type { Notification } from "@/types";

export interface InboxState {
  unreadCount: number;
  /** Counts the changes that make a shown list stale: a new notice, or a count that moved. */
  arrivals: number;
  /**
   * The newest notice that arrived or was opened, by what it is about: a page that follows the
   * thing the notice names (a change set's page) reads again when `count` moves for its subject.
   */
  touched?: { subjectId: string; count: number };
}

const INITIAL: InboxState = { unreadCount: 0, arrivals: 0 };
let state = INITIAL;
let stream: EventStream | undefined;
let mounted = 0;
const listeners = new Set<() => void>();

function update(change: (current: InboxState) => InboxState) {
  state = change(state);
  listeners.forEach((listener) => listener());
}

/** A notice about `subjectId` arrived, or was opened where the person already is. */
export function touchSubject(subjectId: string) {
  update((current) => ({ ...current, touched: { subjectId, count: (current.touched?.count ?? 0) + 1 } }));
}

/** Take the count a read answered, so the badge is right before the stream says so. */
export function setUnreadCount(unreadCount: number) {
  if (unreadCount !== state.unreadCount) update((current) => ({ ...current, unreadCount }));
}

function open() {
  try {
    stream = openEventStream(notificationEventsUrl());
  } catch {
    return;
  }
  stream.addEventListener("unread", (event) => {
    const { unreadCount } = JSON.parse(event.data) as { unreadCount: number };
    update((current) => ({
      unreadCount,
      arrivals: unreadCount === current.unreadCount ? current.arrivals : current.arrivals + 1,
    }));
  });
  stream.addEventListener("notification", (event) => {
    const notice = JSON.parse(event.data) as Notification;
    update((current) => ({
      unreadCount: notice.read ? current.unreadCount : current.unreadCount + 1,
      arrivals: current.arrivals + 1,
    }));
    touchSubject(notice.subject.id);
  });
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/**
 * The person has `subjectId` (a job or a change set) in front of them, so their unread notices
 * about it are read (0.12 NT1, D464): on opening, and again when a notice about it arrives while it
 * is shown, such as a job finishing on its page. Nothing is asked while nothing is unread.
 */
export function useSubjectSeen(subjectId: string | undefined) {
  const { unreadCount, touched } = useSyncExternalStore(subscribe, () => state);
  const anyUnread = unreadCount > 0;
  const arrived = subjectId && touched?.subjectId === subjectId ? touched.count : 0;
  useEffect(() => {
    if (!subjectId || !anyUnread) return;
    api.markNotificationsRead({ subjectId }).then(
      (result) => setUnreadCount(result.unreadCount),
      () => undefined,
    );
  }, [subjectId, anyUnread, arrived]);
}

/** The inbox's live state; the stream runs while `enabled` and a component uses it. */
export function useInbox(enabled: boolean): InboxState {
  useEffect(() => {
    if (!enabled) return;
    if (mounted++ === 0) open();
    return () => {
      if (--mounted === 0) {
        stream?.close();
        stream = undefined;
        update(() => INITIAL);
      }
    };
  }, [enabled]);
  return useSyncExternalStore(subscribe, () => state);
}
