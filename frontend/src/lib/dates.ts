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

function sameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

/** A server timestamp as a day and time a person reads at a glance: "today, 08:12", "yesterday, 17:40", "20 Oct, 17:40". */
export function formatServerDayTime(value: string, now: Date = new Date()): string {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;
  const time = date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (sameDay(date, now)) return `today, ${time}`;
  if (sameDay(date, yesterday)) return `yesterday, ${time}`;
  return `${date.toLocaleDateString(undefined, { day: "numeric", month: "short" })}, ${time}`;
}

/** How long ago a server timestamp was: "just now", "5 minutes ago", "2 hours ago", then the day. */
export function formatServerAgo(value: string, now: Date = new Date()): string {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;
  const minutes = Math.floor((now.valueOf() - date.valueOf()) / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? "" : "s"} ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24 && sameDay(date, now)) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
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
