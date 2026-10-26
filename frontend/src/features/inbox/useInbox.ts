/**
 * The signed-in person's inbox count, kept live (0.12 A2): one stream of the engine's server-sent
 * events, opened while any inbox button is mounted and closed with the last. The engine sends the
 * unread count at once, each new notice and the count after every change; nothing is polled. The
 * stream reconnects by itself (`api/eventStream`), and the count sent on connecting tells a panel
 * that its list may be stale. The stream is read with `fetch` so it carries the access token (D247).
 */

import { useEffect, useSyncExternalStore } from "react";
import { notificationEventsUrl } from "@/api/client";
import { openEventStream, type EventStream } from "@/api/eventStream";
import type { Notification } from "@/types";

export interface InboxState {
  unreadCount: number;
  /** Counts the changes that make a shown list stale: a new notice, or a count that moved. */
  arrivals: number;
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
  });
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
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
