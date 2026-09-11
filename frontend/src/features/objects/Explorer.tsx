import { useEffect, useMemo, useRef, useState } from "react";
import { useDataApi } from "@/features/workspaces/WorkspaceDataContext";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import { errorMessage } from "@/api/errors";
import { objectTypeFor } from "@/model/lookup";
import type { ApplicationDefinition, EngineModel, ObjectItem, ObjectPage } from "@/types";
import { InlineError } from "@/ui/InlineError";
import { Icon } from "@/ui/Icon";

interface LoadedPage extends ObjectPage {
  loaded: ObjectItem[];
}

export function Explorer({
  model,
  application,
  workspaceKey,
  activeObjectId,
  refreshToken,
  onOpen,
}: {
  model: EngineModel;
  application: ApplicationDefinition;
  workspaceKey: string;
  activeObjectId?: string;
  refreshToken: number;
  onOpen: (item: ObjectItem) => void;
}) {
  const api = useDataApi();
  const storageKey = `rdm:hierarchy:v1:${JSON.stringify([workspaceKey, application.key])}`;
  const [branchState, setBranchState] = useState(() => ({ key: storageKey, collapsed: readCollapsed(storageKey) }));
  if (branchState.key !== storageKey) {
    setBranchState({ key: storageKey, collapsed: readCollapsed(storageKey) });
  }

  function toggleBranch(id: string) {
    const collapsed = new Set(branchState.collapsed);
    if (collapsed.has(id)) collapsed.delete(id);
    else collapsed.add(id);
    setBranchState({ key: storageKey, collapsed });
    try {
      window.localStorage.setItem(storageKey, JSON.stringify([...collapsed]));
    } catch {
      // Storage may be unavailable; keep this session's navigation usable.
    }
  }

  const [searchInput, setSearchInput] = useState("");
  const search = useDebouncedValue(searchInput.trim());
  const [pages, setPages] = useState<Record<string, LoadedPage>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retryToken, setRetryToken] = useState(0);
  const [loadedSearch, setLoadedSearch] = useState<string>();
  const [failedMore, setFailedMore] = useState(false);
  const generation = useRef(0);

  useEffect(() => {
    let active = true;
    const requestGeneration = ++generation.current;
    setLoading(true);
    setError("");
    setFailedMore(false);
    Promise.all(
      application.objectTypeKeys.map(
        async (key) =>
          [
            key,
            await api.objects(key, { applicationKey: application.key, workspaceKey, search, pageSize: 30 }),
          ] as const,
      ),
    )
      .then((results) => {
        if (!active || generation.current !== requestGeneration) return;
        setLoadedSearch(search);
        setPages(Object.fromEntries(results.map(([key, page]) => [key, { ...page, loaded: page.items }])));
        setError("");
      })
      .catch((cause) => active && setError(errorMessage(cause)))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
      generation.current += 1;
    };
  }, [api, application.key, application.objectTypeKeys.join("|"), refreshToken, retryToken, search, workspaceKey]);

  const objects = useMemo(
    () => (loadedSearch === search ? Object.values(pages).flatMap((page) => page.loaded) : []),
    [pages, loadedSearch, search],
  );
  const objectIds = new Set(objects.map((item) => item.id));
  const roots = objects
    .filter((item) => !item.parentObjectId || !objectIds.has(item.parentObjectId))
    .sort(comparePaths);
  const children = new Map<string, ObjectItem[]>();
  for (const item of objects) {
    if (!item.parentObjectId || !objectIds.has(item.parentObjectId)) continue;
    children.set(item.parentObjectId, [...(children.get(item.parentObjectId) ?? []), item]);
  }
  for (const values of children.values()) values.sort(comparePaths);
  const canLoadMore = loadedSearch === search && Object.values(pages).some((page) => page.nextCursor);

  async function loadMore() {
    if (loading || !canLoadMore) return;
    const requestGeneration = generation.current;
    setLoading(true);
    setError("");
    try {
      const entries = await Promise.all(
        Object.entries(pages).map(async ([key, page]) => {
          if (!page.nextCursor) return [key, page] as const;
          const next = await api.objects(key, {
            applicationKey: application.key,
            workspaceKey,
            search,
            cursor: page.nextCursor,
            pageSize: 30,
          });
          return [key, { ...next, loaded: [...page.loaded, ...next.items] }] as [string, LoadedPage];
        }),
      );
      if (generation.current !== requestGeneration) return;
      setPages(Object.fromEntries(entries));
    } catch (cause) {
      if (generation.current !== requestGeneration) return;
      setFailedMore(true);
      setError(errorMessage(cause));
    } finally {
      if (generation.current === requestGeneration) setLoading(false);
    }
  }

  function node(item: ObjectItem, depth: number): React.ReactNode {
    const hasChildren = Boolean(children.get(item.id)?.length);
    const expanded = !branchState.collapsed.has(item.id);
    return (
      <li key={item.id}>
        <div className="tree-row" style={{ paddingLeft: `${12 + depth * 17}px` }}>
          {hasChildren ? (
            <button
              className="tree-toggle"
              aria-label={`${expanded ? "Collapse" : "Expand"} ${item.name}`}
              aria-expanded={expanded}
              onClick={() => toggleBranch(item.id)}
            >
              <Icon name={expanded ? "chevron-down" : "chevron-right"} size={14} />
            </button>
          ) : (
            <span className="tree-branch" />
          )}
          <button
            className={item.id === activeObjectId ? "active" : ""}
            aria-current={item.id === activeObjectId ? "page" : undefined}
            onClick={() => onOpen(item)}
          >
            <span className="tree-name">{item.name}</span>
            <span className="type-tag">{objectTypeFor(model, item.objectTypeKey)?.name}</span>
          </button>
        </div>
        {hasChildren && expanded ? <ul>{children.get(item.id)!.map((child) => node(child, depth + 1))}</ul> : null}
      </li>
    );
  }

  return (
    <section className="explorer" aria-label={`${application.name} explorer`}>
      <label className="search-box compact">
        <Icon name="search" />
        <input
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
          aria-label="Search this explorer"
          placeholder="Search this explorer"
        />
      </label>
      {error && (
        <InlineError message={error} onRetry={failedMore ? loadMore : () => setRetryToken((value) => value + 1)} />
      )}
      {roots.length ? (
        <ul className="tree">{roots.map((item) => node(item, search ? Math.max(0, item.path.length - 1) : 0))}</ul>
      ) : loading ? (
        <div className="explorer-empty">Loading objects…</div>
      ) : !error ? (
        <div className="explorer-empty">{search ? "No matching objects." : "No objects in this application yet."}</div>
      ) : null}
      {canLoadMore && !error && (
        <button className="load-more" disabled={loading} onClick={loadMore}>
          {loading ? "Loading…" : "Load more objects"}
        </button>
      )}
    </section>
  );
}

function comparePaths(left: ObjectItem, right: ObjectItem) {
  return left.path
    .map((part) => part.name)
    .join("/")
    .localeCompare(right.path.map((part) => part.name).join("/"));
}

function readCollapsed(key: string): Set<string> {
  try {
    const value: unknown = JSON.parse(window.localStorage.getItem(key) ?? "[]");
    if (Array.isArray(value) && value.every((id) => typeof id === "string")) return new Set(value);
  } catch {
    // Invalid or unavailable storage falls back to the initial expanded hierarchy.
  }
  return new Set();
}
