import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { objectTypeFor } from "../utils/model";
import type { ApplicationDefinition, EngineModel, ObjectItem, ObjectPage } from "../types";
import { InlineError } from "./AsyncState";

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
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [pages, setPages] = useState<Record<string, LoadedPage>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retryToken, setRetryToken] = useState(0);

  useEffect(() => {
    const timer = window.setTimeout(() => setSearch(searchInput.trim()), 250);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    let active = true;
    setLoading(true);
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
        if (!active) return;
        setPages(Object.fromEntries(results.map(([key, page]) => [key, { ...page, loaded: page.items }])));
        setError("");
      })
      .catch((cause) => active && setError(cause instanceof Error ? cause.message : String(cause)))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [application.key, application.objectTypeKeys.join("|"), refreshToken, retryToken, search, workspaceKey]);

  const objects = useMemo(() => Object.values(pages).flatMap((page) => page.loaded), [pages]);
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
  const canLoadMore = Object.values(pages).some((page) => page.nextCursor);

  async function loadMore() {
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
      setPages(Object.fromEntries(entries));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setLoading(false);
    }
  }

  function node(item: ObjectItem, depth: number): React.ReactNode {
    return (
      <li key={item.id}>
        <button
          className={item.id === activeObjectId ? "active" : ""}
          style={{ paddingLeft: `${12 + depth * 17}px` }}
          onClick={() => onOpen(item)}
        >
          <span className="tree-branch">{children.has(item.id) ? "⌄" : "·"}</span>
          <span className="tree-name">{item.name}</span>
          <span className="type-tag">{objectTypeFor(model, item.objectTypeKey)?.name}</span>
        </button>
        {children.get(item.id)?.length ? (
          <ul>{children.get(item.id)!.map((child) => node(child, depth + 1))}</ul>
        ) : null}
      </li>
    );
  }

  return (
    <section className="explorer" aria-label={`${application.name} explorer`}>
      <div className="explorer-heading">
        <div>
          <p className="eyebrow">Current application</p>
          <h2>{application.name}</h2>
        </div>
        <span className="app-badge" style={{ backgroundColor: application.color }} />
      </div>
      <label className="search-box compact">
        <span>⌕</span>
        <input
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
          placeholder="Search this explorer"
        />
      </label>
      <div className="explorer-types">
        {application.objectTypeKeys.map((key) => (
          <span key={key}>{objectTypeFor(model, key)?.pluralName ?? key}</span>
        ))}
      </div>
      {error ? (
        <InlineError message={error} onRetry={() => setRetryToken((value) => value + 1)} />
      ) : loading ? (
        <div className="explorer-empty">Loading objects…</div>
      ) : roots.length ? (
        <ul className="tree">{roots.map((item) => node(item, search ? Math.max(0, item.path.length - 1) : 0))}</ul>
      ) : (
        <div className="explorer-empty">{search ? "No matching objects." : "No objects in this application yet."}</div>
      )}
      {canLoadMore && (
        <button className="load-more" onClick={loadMore}>
          Load more objects
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
