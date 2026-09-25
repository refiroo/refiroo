import type { CursorWindow } from "@/lib/hooks/useCursorWindow";

/** A complete, fully loaded window over `items`, for rendering a list component in isolation. */
export function staticWindow<T>(items: T[], overrides: Partial<CursorWindow<T>> = {}): CursorWindow<T> {
  const noop = () => undefined;
  return {
    items,
    startIndex: 0,
    totalCount: items.length,
    hasPrevious: false,
    hasNext: false,
    loading: false,
    error: "",
    before: { loading: false, error: "" },
    after: { loading: false, error: "" },
    landing: undefined,
    loadPrevious: noop,
    loadNext: noop,
    jumpTo: noop,
    jumpToStart: noop,
    jumpToEnd: noop,
    seek: noop,
    retry: noop,
    reload: noop,
    setViewportIndex: noop,
    anchorAt: () => undefined,
    ...overrides,
  };
}
