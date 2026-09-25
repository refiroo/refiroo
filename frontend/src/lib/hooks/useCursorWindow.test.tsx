import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { PageSelector } from "@/api/client";
import { ApiError } from "@/api/errors";
import { useCursorWindow, WINDOW_PAGES, type WindowedPage } from "@/lib/hooks/useCursorWindow";

/** A server over rows 0..total-1 whose cursors name the row a page continues from. */
function server(total: number, size = 10) {
  const page = (start: number): WindowedPage<number> => {
    const from = Math.max(0, Math.min(start, total));
    const items = Array.from({ length: Math.max(0, Math.min(size, total - from)) }, (_, offset) => from + offset);
    return {
      items,
      prevCursor: from > 0 ? `before:${from}` : null,
      nextCursor: from + size < total ? `from:${from + size}` : null,
      anchor: `from:${from}`,
    };
  };
  return vi.fn(async (selector: PageSelector): Promise<WindowedPage<number>> => {
    let result: WindowedPage<number>;
    if (selector.cursor?.startsWith("before:")) result = page(Math.max(0, Number(selector.cursor.slice(7)) - size));
    else if (selector.cursor) result = page(Number(selector.cursor.slice(5)));
    else if (selector.fromEnd) result = page(Math.max(0, Math.floor((total - 1) / size) * size));
    else if (selector.position !== undefined) result = page(selector.position);
    else result = page(0);
    if (selector.cursor?.startsWith("before:")) {
      const end = Number(selector.cursor.slice(7));
      result = { ...result, items: result.items.filter((row) => row < end) };
    }
    return selector.includeTotal ? { ...result, totalCount: total, startIndex: result.items[0] ?? total } : result;
  });
}

describe("useCursorWindow", () => {
  it("scrolls forward with a bounded window and back through the evicted pages", async () => {
    const fetch = server(100);
    const { result } = renderHook(() => useCursorWindow(fetch, ["list"]));
    await waitFor(() => expect(result.current.items).toHaveLength(10));
    expect(result.current.totalCount).toBe(100);
    expect(result.current.landing?.target).toBe("start");
    for (let page = 1; page < 8; page++) {
      act(() => result.current.loadNext());
      await waitFor(() => expect(result.current.items.at(-1)).toBe(page * 10 + 9));
    }
    expect(result.current.items).toHaveLength(WINDOW_PAGES * 10);
    expect(result.current.startIndex).toBe(30);
    expect(result.current.items[0]).toBe(30);
    expect(result.current.hasPrevious).toBe(true);
    act(() => result.current.loadPrevious());
    await waitFor(() => expect(result.current.items[0]).toBe(20));
    expect(result.current.startIndex).toBe(20);
    expect(result.current.items.at(-1)).toBe(69);
    // Only the first page asked for totals; scrolling uses cursors alone.
    expect(fetch.mock.calls.filter(([selector]) => selector.includeTotal)).toHaveLength(1);
  });

  it("jumps by position with one request, and lands locally when the row is held", async () => {
    const fetch = server(1000);
    const { result } = renderHook(() => useCursorWindow(fetch, ["list"]));
    await waitFor(() => expect(result.current.items).toHaveLength(10));
    act(() => result.current.jumpTo(5));
    expect(result.current.landing?.target).toBe(5);
    expect(fetch).toHaveBeenCalledTimes(1);
    act(() => result.current.jumpTo(730));
    await waitFor(() => expect(result.current.items[0]).toBe(730));
    expect(fetch).toHaveBeenLastCalledWith({ position: 730, includeTotal: true });
    expect(result.current.startIndex).toBe(730);
    expect(result.current.landing?.target).toBe(730);
    act(() => result.current.jumpToEnd(true));
    await waitFor(() => expect(result.current.items.at(-1)).toBe(999));
    expect(result.current.landing).toMatchObject({ target: "end", focus: "last" });
    expect(result.current.hasNext).toBe(false);
  });

  it("reopens at an anchor, and at the start when the anchor is no longer valid", async () => {
    const fetch = server(100);
    const { result } = renderHook(() => useCursorWindow(fetch, ["list"], { anchor: "from:40" }));
    await waitFor(() => expect(result.current.items[0]).toBe(40));
    expect(result.current.startIndex).toBe(40);
    expect(result.current.anchorAt(45)).toBe("from:40");
    expect(result.current.anchorAt(0)).toBeUndefined();

    const stale = vi
      .fn()
      .mockRejectedValueOnce(new ApiError(422, "invalid_cursor", "Invalid cursor"))
      .mockResolvedValueOnce({ items: [1], nextCursor: null, totalCount: 1, startIndex: 0 });
    const reopened = renderHook(() => useCursorWindow(stale, ["list"], { anchor: "old" }));
    await waitFor(() => expect(reopened.result.current.items).toEqual([1]));
    expect(stale.mock.calls.map(([selector]) => selector)).toEqual([
      { cursor: "old", includeTotal: true },
      { includeTotal: true },
    ]);
  });

  it("corrects indexes when rows were deleted before the window", async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce({
        items: ["c"],
        prevCursor: "before-c",
        nextCursor: null,
        anchor: "c",
        totalCount: 3,
        startIndex: 2,
      })
      .mockResolvedValueOnce({ items: ["a"], prevCursor: null, nextCursor: "after-a", anchor: "a" });
    const { result } = renderHook(() => useCursorWindow<string>(fetch, ["list"]));
    await waitFor(() => expect(result.current.items).toEqual(["c"]));
    act(() => result.current.loadPrevious());
    await waitFor(() => expect(result.current.items).toEqual(["a", "c"]));
    expect(result.current.startIndex).toBe(0);
    expect(result.current.totalCount).toBe(2);
  });

  it("keeps the window on an edge failure and retries the same cursor", async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce({ items: [1], nextCursor: "two", totalCount: 2, startIndex: 0 })
      .mockRejectedValueOnce(new Error("Page unavailable"))
      .mockResolvedValueOnce({ items: [2], nextCursor: null, prevCursor: "one" });
    const { result } = renderHook(() => useCursorWindow<number>(fetch, ["list"]));
    await waitFor(() => expect(result.current.items).toEqual([1]));
    act(() => result.current.loadNext());
    await waitFor(() => expect(result.current.after.error).toBe("Page unavailable"));
    expect(result.current.items).toEqual([1]);
    act(() => result.current.retry());
    await waitFor(() => expect(result.current.items).toEqual([1, 2]));
    expect(fetch.mock.calls.map(([selector]) => selector.cursor)).toEqual([undefined, "two", "two"]);
  });

  it("hides the previous query's rows and reloads in place on a refresh", async () => {
    const fetch = server(100);
    const { result, rerender } = renderHook(
      ({ search, token }) => useCursorWindow(fetch, [search], { refreshToken: token }),
      { initialProps: { search: "a", token: 0 } },
    );
    await waitFor(() => expect(result.current.items).toHaveLength(10));
    act(() => result.current.jumpTo(50));
    await waitFor(() => expect(result.current.items[0]).toBe(50));
    act(() => result.current.setViewportIndex(53));
    rerender({ search: "a", token: 1 });
    await waitFor(() => expect(fetch).toHaveBeenLastCalledWith({ cursor: "from:50", includeTotal: true }));
    await waitFor(() => expect(result.current.landing?.target).toBe(53));
    rerender({ search: "b", token: 1 });
    expect(result.current.items).toEqual([]);
    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.items[0]).toBe(0));
  });
});
