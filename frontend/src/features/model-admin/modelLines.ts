import { newestFirst } from "@/model/newestFirst";
import type { ModelReleaseSummary } from "@/types";

/** One model: its key, its name (its newest release's) and its releases, newest first (0.11 M6). */
export interface ModelLine {
  key: string;
  name: string;
  releases: ModelReleaseSummary[];
}

/** The installed releases by model (`release.key`), each model named by its newest release. */
export function releasesByModel(releases: ModelReleaseSummary[]): ModelLine[] {
  const models = new Map<string, ModelReleaseSummary[]>();
  for (const release of releases) models.set(release.key, [...(models.get(release.key) ?? []), release]);
  return [...models].map(([key, items]) => {
    const ordered = newestFirst(items, "installedAt");
    return { key, name: ordered[0].name, releases: ordered };
  });
}
