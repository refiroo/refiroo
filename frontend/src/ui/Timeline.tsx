import { useState, type ReactNode } from "react";
import { byDay, formatServerAgo, formatServerTime, timeOfDay } from "@/lib/dates";
import type { Hue } from "@/model/hues";

export interface TimelineEntry {
  key: string;
  /** What happened; a link where the change's subject can be opened (0.12 Z6). */
  title: ReactNode;
  summary?: string;
  /** When it happened, shown relative to now within a week. */
  at: string;
  /** What follows the time on its line, such as " · by Ana Varga · version 4". */
  after?: ReactNode;
  /** What an opened entry shows below its line, such as each value with the one before (0.12 RH1). */
  details?: ReactNode;
  /** The marker's colour, where entries of different kinds stand together. */
  tone?: string;
  /** The marker in a hue of the type palette: the colour of the entry's kind (0.17 ST1, PP-D67). */
  hue?: Hue;
}

/**
 * Changes newest first, each with a marker, a title, a summary and when: a record's history, a
 * person's recent activity (0.12 Z4) and a person's changes across workspaces (0.12 Z6).
 *
 * `byDay` (0.12 RH1, D393) puts the entries under a heading for each day, each on one line with its
 * time of day; an entry with `details` opens to show them.
 */
export function Timeline({
  entries,
  label,
  byDay: grouped = false,
}: {
  entries: readonly TimelineEntry[];
  label?: string;
  byDay?: boolean;
}) {
  const [open, setOpen] = useState<ReadonlySet<string>>(new Set());
  const toggle = (key: string) =>
    setOpen((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  if (!grouped)
    return (
      <ol className="history-timeline" aria-label={label}>
        {entries.map((entry) => (
          <li key={entry.key}>
            <span className="history-marker" data-hue={entry.hue} />
            <div>
              <strong>{entry.title}</strong>
              {entry.summary && <p>{entry.summary}</p>}
              <small>
                <time dateTime={entry.at} title={formatServerTime(entry.at)}>
                  {formatServerAgo(entry.at)}
                </time>
                {entry.after}
              </small>
              {entry.details && (
                <>
                  <button
                    type="button"
                    className="plain-fold-toggle"
                    aria-expanded={open.has(entry.key)}
                    onClick={() => toggle(entry.key)}
                  >
                    {open.has(entry.key) ? "Hide the steps" : "Show the steps"}
                  </button>
                  {open.has(entry.key) && <div className="history-line-details">{entry.details}</div>}
                </>
              )}
            </div>
          </li>
        ))}
      </ol>
    );
  return (
    <div className="history-days" aria-label={label} role="group">
      {byDay(entries.map((entry) => ({ ...entry, occurredAt: entry.at }))).map((day) => (
        <section key={day.day} aria-label={day.day}>
          <h3 className="history-day">{day.day}</h3>
          <ol className="history-lines">
            {day.entries.map((entry) => {
              const expanded = open.has(entry.key);
              const line = (
                <>
                  <span
                    className="history-line-marker"
                    data-tone={entry.tone}
                    data-hue={entry.hue}
                    aria-hidden="true"
                  />
                  <span className="history-line-text">
                    <strong>{entry.title}</strong>
                    {entry.summary && <span className="history-line-summary"> · {entry.summary}</span>}
                    {entry.after && <span className="history-line-after">{entry.after}</span>}
                  </span>
                  <time dateTime={entry.at} title={formatServerTime(entry.at)}>
                    {timeOfDay(entry.at)}
                  </time>
                </>
              );
              return (
                <li key={entry.key}>
                  {entry.details ? (
                    <button
                      type="button"
                      className="history-line"
                      aria-expanded={expanded}
                      onClick={() => toggle(entry.key)}
                    >
                      {line}
                      <span className="history-line-chevron" aria-hidden="true">
                        {expanded ? "▾" : "▸"}
                      </span>
                    </button>
                  ) : (
                    <div className="history-line">{line}</div>
                  )}
                  {expanded && entry.details && <div className="history-line-details">{entry.details}</div>}
                </li>
              );
            })}
          </ol>
        </section>
      ))}
    </div>
  );
}
