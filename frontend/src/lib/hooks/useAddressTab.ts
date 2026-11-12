import { useCallback, useEffect, useState } from "react";

/**
 * The address the document was loaded with. The router rewrites the address to its own route as the application
 * opens, which drops what it does not know (`?tab=`, and a hash too), so the first page to ask for its tab reads
 * it from the browser's record of the navigation, once.
 */
function openedAddress(): { path: string; search: string } | undefined {
  if (openedSpent) return undefined;
  try {
    const entry = performance.getEntriesByType("navigation")[0];
    if (!entry) return undefined;
    const url = new URL(entry.name);
    return { path: url.pathname, search: url.search };
  } catch {
    return undefined;
  }
}
let openedSpent = false;

/** The tab the address names: `?tab=` when it is one of `ids`, else the first. */
function tabOf(search: string, ids: readonly string[]): string | undefined {
  const wanted = new URLSearchParams(search).get("tab");
  return wanted && ids.includes(wanted) ? wanted : undefined;
}

function tabOfAddress(ids: readonly string[]): string {
  const now = tabOf(window.location.search, ids);
  if (now) return now;
  const opened = openedAddress();
  if (opened && opened.path === window.location.pathname) {
    const first = tabOf(opened.search, ids);
    if (first) return first;
  }
  return ids[0]!;
}

function writeTab(id: string, first: string | undefined) {
  const url = new URL(window.location.href);
  if (id === first) url.searchParams.delete("tab");
  else url.searchParams.set("tab", id);
  window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}${url.hash}`);
}

/**
 * The selected tab of a page, kept in the address as `?tab=` (0.17 ST1, PP-D62): a reload or a pasted link opens
 * on the same tab. The first tab has no parameter. Choosing a tab replaces the history entry (it is a view of the
 * page, not a step back) and keeps the router's state; Back and Forward are followed.
 */
export function useAddressTab(ids: readonly string[]): [string, (id: string) => void] {
  const [tab, setTabState] = useState(() => tabOfAddress(ids));
  const key = ids.join("\u0000");

  // The tab the page was opened on is put back in the address the router has just cleaned.
  useEffect(() => {
    const first = key.split("\u0000")[0];
    const opened = openedAddress();
    if (opened && opened.path === window.location.pathname) {
      openedSpent = true;
      const wanted = tabOf(opened.search, key.split("\u0000"));
      if (wanted && wanted !== first && !tabOf(window.location.search, key.split("\u0000"))) writeTab(wanted, first);
    }
    const follow = () => setTabState(tabOfAddress(key.split("\u0000")));
    window.addEventListener("popstate", follow);
    return () => window.removeEventListener("popstate", follow);
  }, [key]);

  const setTab = useCallback(
    (id: string) => {
      writeTab(id, key.split("\u0000")[0]);
      setTabState(id);
    },
    [key],
  );

  return [tab, setTab];
}
