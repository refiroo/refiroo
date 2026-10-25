import { useState } from "react";

/** The newest entries a timeline shows first, and how many more each press shows (0.12 RH1, D393). */
export const TIMELINE_FIRST = 10;
export const TIMELINE_MORE = 20;

/**
 * How many of a timeline's loaded entries are shown: the 10 newest, then 20 more at a time, and back
 * to 10 with Show fewer (a record's history, a person's recent activity). `reset` starts again at
 * 10, for a new filter.
 */
export function useTimelineLimit() {
  const [limit, setLimit] = useState(TIMELINE_FIRST);
  return {
    limit,
    reset: () => setLimit(TIMELINE_FIRST),
    more: () => setLimit((current) => current + TIMELINE_MORE),
  };
}

/** Below a timeline: how many are shown, Show fewer once more are, and the button that shows more. */
export function TimelinePaging({
  limit,
  loaded,
  hasMore,
  loading,
  failed = false,
  moreLabel,
  noun = ["change", "changes"],
  onMore,
  onLoad,
  onFewer,
}: {
  limit: number;
  /** How many entries are loaded. */
  loaded: number;
  /** Whether the server holds more than are loaded. */
  hasMore: boolean;
  loading: boolean;
  failed?: boolean;
  moreLabel: string;
  /** What an entry is called, singular and plural. */
  noun?: readonly [string, string];
  /** Shows more of what is loaded. */
  onMore: () => void;
  /** Reads the next page, when what is loaded is all shown. */
  onLoad: () => void;
  onFewer: () => void;
}) {
  const shown = Math.min(limit, loaded);
  if (!loaded) return null;
  return (
    <div className="history-paging">
      <span className="history-count">
        Showing {shown} {shown === 1 ? noun[0] : noun[1]}
      </span>
      {limit > TIMELINE_FIRST && shown > TIMELINE_FIRST && (
        <button type="button" className="ghost" onClick={onFewer}>
          Show fewer
        </button>
      )}
      {(loaded > limit || hasMore) && !failed && (
        <button
          type="button"
          className="load-more inline history-more"
          disabled={loading}
          onClick={() => {
            if (loaded <= limit) onLoad();
            onMore();
          }}
        >
          {loading ? "Loading…" : moreLabel}
        </button>
      )}
    </div>
  );
}
