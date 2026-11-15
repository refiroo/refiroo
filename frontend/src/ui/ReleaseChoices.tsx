/**
 * The releases a picker offers (0.12 MR1, D458): only those that may be chosen (the caller loads
 * them with `usable`), the newest of each model first, and a model's older releases only after
 * "Show older versions". Used by every picker of a release: a new workspace's model and a change
 * set's model version.
 */

import { useState } from "react";
import { newestFirst } from "@/model/newestFirst";
import type { ModelReleaseSummary } from "@/types";

/** The releases to list, newest of each model first; the older ones only when `older` is on. */
export function releaseChoices(releases: readonly ModelReleaseSummary[], older: boolean) {
  const ordered = newestFirst(releases, "installedAt");
  const seen = new Set<string>();
  const newest: ModelReleaseSummary[] = [];
  const rest: ModelReleaseSummary[] = [];
  for (const release of ordered) {
    (seen.has(release.key) ? rest : newest).push(release);
    seen.add(release.key);
  }
  return { shown: older ? [...newest, ...rest] : newest, olderCount: rest.length };
}

/** `releaseChoices` with its switch; `keep` stays listed even when it is an older release. */
export function useReleaseChoices(releases: readonly ModelReleaseSummary[], keep?: string) {
  const [older, setOlder] = useState(false);
  const { shown, olderCount } = releaseChoices(releases, older);
  const kept = keep && !shown.some((item) => item.id === keep) ? releases.find((item) => item.id === keep) : undefined;
  return { shown: kept ? [...shown, kept] : shown, olderCount, older, setOlder };
}

export function OlderVersionsToggle({
  count,
  older,
  onChange,
}: {
  count: number;
  older: boolean;
  onChange: (older: boolean) => void;
}) {
  if (!count) return null;
  return (
    <label className="checkbox">
      <input type="checkbox" checked={older} onChange={(event) => onChange(event.target.checked)} />
      <span>
        Show older versions <span className="muted">({count})</span>
      </span>
    </label>
  );
}
