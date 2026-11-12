import { useEffect, useRef, type CSSProperties, type KeyboardEvent, type ReactNode } from "react";
import { Icon, type IconName } from "@/ui/Icon";
import { InlineError } from "@/ui/InlineError";
import { SearchField } from "@/ui/SearchField";

export interface EntityFact {
  label: string;
  value: ReactNode;
  mono?: boolean;
  /** The column's width in characters, for a value that is not text (chips): text sets its own. */
  width?: number;
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
  /** The glyph on the row's tile; a row with a `lead` has none. */
  icon?: IconName;
  /** The row's own mark in place of the tile: a person's initials, a coloured tile (0.17 ST1). */
  lead?: ReactNode;
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

/** The longest text of a fact's value, in characters; a value that is not text counts as its label. */
const factLength = (fact: EntityFact | undefined) =>
  typeof fact?.value === "string" || typeof fact?.value === "number" ? String(fact.value).length : 0;

/**
 * The width of each fact's column (0.17 SH1): what its longest value and its label need, so a long
 * version is never cut into the column beside it and the name keeps what the facts leave. One set
 * for every group of the list, so the columns line up from group to group.
 */
function factTracks(groups: EntityGroup[]): string | undefined {
  const rows = groups.flatMap((group) => group.rows);
  const labels = rows.find((row) => row.facts?.length)?.facts?.map((fact) => fact.label);
  if (!labels) return undefined;
  return labels
    .map((label, at) => {
      const set = rows.find((row) => row.facts?.[at]?.width)?.facts?.[at]?.width;
      if (set) return `${set}ch`;
      const longest = Math.max(label.length, ...rows.map((row) => factLength(row.facts?.[at])));
      return `${Math.min(Math.max(longest + 2, 6), 28)}ch`;
    })
    .join(" ");
}

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
  statusTrack,
}: {
  /** What is listed, plural: "workspaces" (the search box is "Search workspaces"). */
  label: string;
  groups: EntityGroup[];
  /** Without `onSearch` the list has no search box: the page's tools above it hold the search (0.17 ST1). */
  search?: string;
  onSearch?: (text: string) => void;
  /** The text when nothing is listed. */
  empty: ReactNode;
  /** The width of the last column where rows hold facts; `0` where no row has a pill (0.17 ST1). */
  statusTrack?: string;
}) {
  const body = useRef<HTMLDivElement>(null);
  const settled = groups.every((group) => !group.loading && !group.error);
  const nothing = settled && groups.every((group) => !group.rows.length);
  const tracks = factTracks(groups);
  return (
    <div className="entity-list" ref={body} onKeyDown={(event) => moveBetweenRows(event, body.current)}>
      {onSearch && (
        <SearchField
          className="entity-search"
          type="search"
          label={`Search ${label}`}
          placeholder={`Search ${label}`}
          value={search ?? ""}
          onChange={onSearch}
        />
      )}
      <div className="entity-groups">
        {groups.map((group) => (
          <EntityGroupSection key={group.key} group={group} label={label} tracks={tracks} statusTrack={statusTrack} />
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

function EntityGroupSection({
  group,
  label,
  tracks,
  statusTrack,
}: {
  group: EntityGroup;
  label: string;
  tracks?: string;
  statusTrack?: string;
}) {
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
  const hasFacts = factLabels.length > 0 && tracks !== undefined;
  return (
    <section
      className={`entity-group${hasFacts ? " has-facts" : ""}`}
      aria-label={group.title}
      style={hasFacts ? ({ "--fact-tracks": tracks, "--status-track": statusTrack } as CSSProperties) : undefined}
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
          {row.lead ?? (
            <span className="entity-tile" aria-hidden="true">
              {row.icon && <Icon name={row.icon} size={16} />}
            </span>
          )}
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
                    className={`entity-fact-value${fact.mono ? " mono" : ""}${
                      typeof fact.value === "string" || typeof fact.value === "number" ? "" : " entity-fact-node"
                    }`}
                    title={typeof fact.value === "string" ? fact.value : undefined}
                  >
                    {fact.value}
                  </span>
                </span>
              ))}
            </span>
          ) : null}
          {hasFacts ? <span className="entity-status">{row.pill}</span> : row.pill}
        </button>
      ))}
      {group.error && <InlineError message={group.error} onRetry={group.onRetry ?? noRetry} />}
      {onEnd && <div ref={sentinel} className="entity-sentinel" aria-hidden="true" />}
    </section>
  );
}
