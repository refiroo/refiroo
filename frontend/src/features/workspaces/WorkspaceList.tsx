import { useMemo, useState } from "react";
import { api } from "@/api/client";
import { useCursorFeed, type CursorFeed } from "@/lib/hooks/useCursorFeed";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import { UnavailableBadge, unavailability } from "@/features/workspaces/UnavailableWorkspace";
import type { Workspace } from "@/types";
import { settingsHead } from "@/ui/settingsNavigation";
import { EntityList, type EntityGroup } from "@/ui/EntityList";
import { SearchField } from "@/ui/SearchField";
import { SettingsPanel, SettingsTile, SettingsTools } from "@/ui/SettingsParts";
import { StatusPill } from "@/ui/StatusPill";

const PAGE_SIZE = 100;

/**
 * The first page of each list as last read, per status and search. The page shows it at once when
 * it opens again and reads the list afresh in the background, replacing it in place, so the rows do
 * not appear after placeholders and the Retired group does not pop in.
 */
const firstPages = new Map<string, { items: Workspace[]; hasMore: boolean }>();

export function resetWorkspaceListCacheForTests() {
  firstPages.clear();
}

/** A list's feed with the last known first page standing in while the first read is in flight. */
function useWorkspaceList(status: "active" | "retired", search: string): CursorFeed<Workspace> {
  const feed = useCursorFeed<Workspace>(
    (cursor) =>
      api.workspaces({ status, search, cursor, pageSize: PAGE_SIZE }).then((page) => {
        if (!cursor) firstPages.set(`${status}|${search}`, { items: page.items, hasMore: Boolean(page.nextCursor) });
        return page;
      }),
    [status, search],
  );
  const known = firstPages.get(`${status}|${search}`);
  if (known && !feed.items.length && feed.loading && !feed.error) {
    return { ...feed, items: known.items, hasMore: false, loading: false };
  }
  return feed;
}

/**
 * Settings › Workspaces opens with this list: Active (the default workspace first) and Retired,
 * each read in pages with the search applied by the server; the next page of a list loads when the
 * person scrolls to its end. The lists last read are shown at once and read again in the background.
 */
export function WorkspaceList({ defaultKey, onOpen }: { defaultKey?: string; onOpen: (workspaceKey: string) => void }) {
  const [text, setText] = useState("");
  const search = useDebouncedValue(text.trim());
  const active = useWorkspaceList("active", search);
  const retired = useWorkspaceList("retired", search);

  // The default workspace first among those loaded; the server's order is otherwise kept.
  const activeItems = useMemo(() => {
    const at = active.items.findIndex((item) => item.key === defaultKey);
    if (at <= 0) return active.items;
    return [active.items[at], ...active.items.slice(0, at), ...active.items.slice(at + 1)];
  }, [active.items, defaultKey]);

  const hue = settingsHead("workspaces").hue;
  const group = (key: string, title: string, feed: CursorFeed<Workspace>, items: Workspace[]): EntityGroup => ({
    key,
    title,
    count: feed.hasMore ? `${items.length}+` : items.length,
    loading: feed.loading && !items.length,
    loadingMore: feed.loading && items.length > 0,
    error: feed.error,
    onRetry: feed.retry,
    onEnd: feed.hasMore ? feed.loadMore : undefined,
    rows: items.map((workspace) => ({
      key: workspace.key,
      title: workspace.label,
      subtitle: workspace.key,
      subtitleMono: true,
      facts: [
        { label: "Model", value: workspace.model.releaseName },
        { label: "Release", value: workspace.model.releaseVersion, mono: true },
      ],
      lead: <SettingsTile icon="workspace" hue={hue} />,
      pill: (
        <>
          {workspace.key === defaultKey ? (
            <StatusPill tone="success">Default</StatusPill>
          ) : (
            workspace.status === "retired" && <StatusPill tone="neutral">Retired</StatusPill>
          )}
          {unavailability(workspace) && <UnavailableBadge />}
        </>
      ),
      onOpen: () => onOpen(workspace.key),
    })),
  });

  const shown = activeItems.length + retired.items.length;
  const more = active.hasMore || retired.hasMore;
  const settled = !(active.loading && !activeItems.length) && !(retired.loading && !retired.items.length);

  return (
    <>
      <SettingsTools
        count={settled ? `${shown}${more ? "+" : ""} ${shown === 1 ? "workspace" : "workspaces"}` : undefined}
      >
        <SearchField
          type="search"
          label="Search workspaces"
          placeholder="Name or key"
          value={text}
          onChange={setText}
          clearOnEscape
        />
      </SettingsTools>
      <SettingsPanel>
        <EntityList
          label="workspaces"
          groups={[group("active", "Active", active, activeItems), group("retired", "Retired", retired, retired.items)]}
          empty={search ? `No workspace matches “${search}”` : "There are no workspaces."}
        />
      </SettingsPanel>
    </>
  );
}
