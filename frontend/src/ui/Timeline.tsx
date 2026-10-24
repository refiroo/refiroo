import type { ReactNode } from "react";
import { formatServerTime } from "@/lib/dates";

export interface TimelineEntry {
  key: string;
  title: string;
  summary?: string;
  /** When it happened, shown relative to now within a week. */
  at: string;
  /** What follows the time on its line, such as " · by Ana Varga · version 4". */
  after?: ReactNode;
}

/** Changes newest first, each with a marker, a title, a summary and when: a record's history and a
 * person's recent activity (0.12 Z4). */
export function Timeline({ entries, label }: { entries: readonly TimelineEntry[]; label?: string }) {
  return (
    <ol className="history-timeline" aria-label={label}>
      {entries.map((entry) => (
        <li key={entry.key}>
          <span className="history-marker" />
          <div>
            <strong>{entry.title}</strong>
            {entry.summary && <p>{entry.summary}</p>}
            <small>
              <time dateTime={entry.at} title={formatServerTime(entry.at)}>
                {relativeTime(entry.at)}
              </time>
              {entry.after}
            </small>
          </div>
        </li>
      ))}
    </ol>
  );
}

const relative = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["day", 86_400_000],
  ["hour", 3_600_000],
  ["minute", 60_000],
];

function relativeTime(iso: string) {
  const elapsed = new Date(iso).getTime() - Date.now();
  if (Number.isNaN(elapsed) || Math.abs(elapsed) > 7 * 86_400_000) return formatServerTime(iso);
  for (const [unit, size] of UNITS) {
    if (Math.abs(elapsed) >= size) return relative.format(Math.round(elapsed / size), unit);
  }
  return "just now";
}
