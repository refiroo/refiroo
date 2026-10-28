import { useEffect, useRef, type CSSProperties, type KeyboardEvent, type ReactNode } from "react";
import { Icon, type IconName } from "@/ui/Icon";
import { InlineError } from "@/ui/InlineError";

export interface EntityFact {
  label: string;
  value: ReactNode;
  mono?: boolean;
}

/** One line of a list: an item with a tile, a title, a pill and a second line. */
export interface EntityRow {
  /** Unique across the groups. */
  key: string;
  title: string;
  subtitle: string;
  /** The subtitle is a code (a key): shown in the mono face. */
  subtitleMono?: boolean;
  /** Labelled facts shown as aligned columns at the row's end (under the text on a narrow screen). */
  facts?: EntityFact[];
  icon: IconName;
  pill?: ReactNode;
  /** The row of the item shown elsewhere on the page. */
  current?: boolean;
  onOpen: () => void;
}

export interface EntityGroup {
  key: string;
  title: string;
  /** Shown after the title, "Active · 3"; "3+" while more can be read. */
  count: number | string;
  rows: EntityRow[];
  /** The group's first read is in flight: placeholders stand in for the rows. */
  loading?: boolean;
  error?: string;
  onRetry?: () => void;
  /** Present while more rows can be read: called when the person scrolls to the group's end. */
  onEnd?: () => void;
  /** A read for further rows is in flight (no further call is made meanwhile). */
  loadingMore?: boolean;
}

const noRetry = () => undefined;

/** Arrow keys step through the search box and the rows of a list. */
export function moveBetweenRows(event: KeyboardEvent, container: HTMLElement | null) {
  if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
  const stops = Array.from(container?.querySelectorAll<HTMLElement>("input, button.entity-row") ?? []);
  const at = stops.indexOf(document.activeElement as HTMLElement);
  if (at < 0) return;
  const next = stops[at + (event.key === "ArrowDown" ? 1 : -1)];
  if (!next) return;
  event.preventDefault();
  next.focus();
}

/**
 * The list an administration page opens with (Settings › Workspaces, Settings › Model): a search
 * box and groups of rows, each group with its own heading and count. A group fed from a server
 * pages: it names `onEnd`, called when the person scrolls to the end of its rows. A group fed from
 * what the page holds simply lists. Empty groups are left out; with every group settled and empty
 * the `empty` text is shown.
 */
export function EntityList({
  label,
  groups,
  search,
  onSearch,
  empty,
}: {
  /** What is listed, plural: "workspaces" (the search box is "Search workspaces"). */
  label: string;
  groups: EntityGroup[];
  search: string;
  onSearch: (text: string) => void;
  /** The text when nothing is listed. */
  empty: ReactNode;
}) {
  const body = useRef<HTMLDivElement>(null);
  const settled = groups.every((group) => !group.loading && !group.error);
  const nothing = settled && groups.every((group) => !group.rows.length);
  return (
    <div className="entity-list" ref={body} onKeyDown={(event) => moveBetweenRows(event, body.current)}>
      <label className="search-box entity-search">
        <Icon name="search" size={16} />
        <input
          type="search"
          aria-label={`Search ${label}`}
          placeholder={`Search ${label}`}
          value={search}
          onChange={(event) => onSearch(event.target.value)}
        />
      </label>
      <div className="entity-groups">
        {groups.map((group) => (
          <EntityGroupSection key={group.key} group={group} label={label} />
        ))}
        {nothing && (
          <p className="explorer-empty" role="status">
            {empty}
          </p>
        )}
      </div>
    </div>
  );
}

function EntityGroupSection({ group, label }: { group: EntityGroup; label: string }) {
  const sentinel = useRef<HTMLDivElement>(null);
  const { onEnd, loadingMore } = group;
  const rowCount = group.rows.length;

  // Reaching the end of the rows asks for the next page. A new observer is made after each page,
  // so an end still in view after it asks for the one after.
  useEffect(() => {
    const node = sentinel.current;
    if (!node || !onEnd || loadingMore || typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) onEnd();
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, [onEnd, loadingMore, rowCount]);

  if (group.error && !rowCount) {
    return (
      <section className="entity-group" aria-label={group.title}>
        <h2 className="nav-label">{group.title}</h2>
        <InlineError message={group.error} onRetry={group.onRetry ?? noRetry} />
      </section>
    );
  }
  if (group.loading && !rowCount) {
    return (
      <section className="entity-group" aria-label={group.title}>
        <h2 className="nav-label">{group.title}</h2>
        <div
          className="entity-skeleton"
          role="status"
          aria-busy="true"
          aria-label={`Loading ${group.title.toLowerCase()} ${label}`}
        >
          <span className="entity-row entity-row-skeleton" aria-hidden="true" />
          <span className="entity-row entity-row-skeleton" aria-hidden="true" />
        </div>
      </section>
    );
  }
  if (!rowCount) return null;
  // Labels once per group, in the heading, above the same columns the rows use. A row keeps its
  // labels for a screen reader and for a narrow screen, where the columns give way to a stack.
  const factLabels = group.rows.find((row) => row.facts?.length)?.facts?.map((fact) => fact.label) ?? [];
  const tracks = factLabels.length
    ? `minmax(12rem, 18rem)${factLabels.length > 1 ? ` repeat(${factLabels.length - 1}, 7rem)` : ""}`
    : undefined;
  return (
    <section
      className={`entity-group${tracks ? " has-facts" : ""}`}
      aria-label={group.title}
      style={tracks ? ({ "--fact-tracks": tracks } as CSSProperties) : undefined}
    >
      <h2 className="nav-label">
        <span className="entity-group-title">
          {group.title} · {group.count}
        </span>
        {factLabels.map((label) => (
          <span key={label} className="entity-group-fact" aria-hidden="true">
            {label}
          </span>
        ))}
      </h2>
      {group.rows.map((row) => (
        <button
          key={row.key}
          type="button"
          className={`entity-row${row.current ? " active" : ""}`}
          aria-current={row.current ? "true" : undefined}
          onClick={row.onOpen}
        >
          <span className="entity-tile" aria-hidden="true">
            <Icon name={row.icon} size={16} />
          </span>
          <span className="catalogue-text">
            <strong>{row.title}</strong>
            <small className={row.subtitleMono ? "mono" : undefined}>{row.subtitle}</small>
          </span>
          {row.facts?.length ? (
            // Spans, not a dl: a button may hold phrasing content only. The hidden colon and comma
            // make a screen reader say "Model: Starter model, Release: 0.3.0".
            <span className="entity-facts">
              {row.facts.map((fact, at) => (
                <span key={fact.label} className="entity-fact">
                  {at > 0 && (
                    <>
                      <span className="visually-hidden">,</span>{" "}
                    </>
                  )}
                  <span className="entity-fact-label">
                    {fact.label}
                    <span className="visually-hidden">: </span>
                  </span>{" "}
                  <span
                    className={fact.mono ? "entity-fact-value mono" : "entity-fact-value"}
                    title={typeof fact.value === "string" ? fact.value : undefined}
                  >
                    {fact.value}
                  </span>
                </span>
              ))}
            </span>
          ) : null}
          {tracks ? <span className="entity-status">{row.pill}</span> : row.pill}
        </button>
      ))}
      {group.error && <InlineError message={group.error} onRetry={group.onRetry ?? noRetry} />}
      {onEnd && <div ref={sentinel} className="entity-sentinel" aria-hidden="true" />}
    </section>
  );
}
