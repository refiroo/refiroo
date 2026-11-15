/**
 * Every date and time a person reads (SR4, SR-D1): in the browser's locale, so 12 or 24 hours and the order of
 * day and month follow the browser; nothing is fixed to one language. The one exception is `NoticeMailPanel`'s
 * digest time, which is the subscription's own zone in 24 hours.
 */

import { counted } from "@/lib/count";

/** Server timestamps carry an explicit UTC offset; display them in the viewer's local time. */
export function formatServerTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleString();
}

/** A server timestamp's day in the viewer's local time, for lists where the time adds nothing. */
export function formatServerDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.valueOf())
    ? value
    : date.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

/** A server timestamp's time of day ("08:12", or "8:12 AM" where the browser reads 12 hours). */
export function timeOfDay(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.valueOf())
    ? value
    : date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

/** The time of a moment held as a date, with seconds, for a "refreshed at" line. */
export function formatClock(date: Date): string {
  return date.toLocaleTimeString();
}

/** A day without its year: "20 Oct". */
export function formatShortDay(value: string | number): string {
  return new Date(value).toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

/** A day with its month in full and no year: "20 October". */
export function formatLongDay(value: string): string {
  return new Date(value).toLocaleDateString(undefined, { day: "numeric", month: "long" });
}

function sameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

/** A server timestamp as a day and time a person reads at a glance: "today, 08:12", "yesterday, 17:40", "20 Oct, 17:40". */
export function formatServerDayTime(value: string, now: Date = new Date()): string {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;
  const time = timeOfDay(value);
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (sameDay(date, now)) return `today, ${time}`;
  if (sameDay(date, yesterday)) return `yesterday, ${time}`;
  return `${formatShortDay(value)}, ${time}`;
}

/** How long ago a server timestamp was: "just now", "5 minutes ago", "2 hours ago", then the day. */
export function formatServerAgo(value: string, now: Date = new Date()): string {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;
  const minutes = Math.floor((now.valueOf() - date.valueOf()) / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${counted(minutes, "minute")} ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24 && sameDay(date, now)) return `${counted(hours, "hour")} ago`;
  return formatServerDayTime(value, now);
}

/** The day an entry falls on, as its group's heading: "Today", "Yesterday", then the date. */
export function dayLabel(iso: string, now: Date = new Date()): string {
  const date = new Date(iso);
  if (Number.isNaN(date.valueOf())) return iso;
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (sameDay(date, now)) return "Today";
  if (sameDay(date, yesterday)) return "Yesterday";
  return date.toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long", year: "numeric" });
}

/** Entries in runs of the same day, newest first as they come. */
export function byDay<T extends { occurredAt: string }>(entries: readonly T[], now: Date = new Date()) {
  const days: { day: string; entries: T[] }[] = [];
  for (const entry of entries) {
    const day = dayLabel(entry.occurredAt, now);
    const last = days[days.length - 1];
    if (last?.day === day) last.entries.push(entry);
    else days.push({ day, entries: [entry] });
  }
  return days;
}
