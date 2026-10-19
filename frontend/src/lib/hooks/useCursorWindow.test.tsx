import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { PageSelector } from "@/api/client";
import { ApiError } from "@/api/errors";
import { useCursorWindow, WINDOW_PAGES, WINDOW_ROWS, type WindowedPage } from "@/lib/hooks/useCursorWindow";

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
    const fetch = server(1000, 100);
    const { result } = renderHook(() => useCursorWindow(fetch, ["list"]));
    await waitFor(() => expect(result.current.items).toHaveLength(100));
    expect(result.current.totalCount).toBe(1000);
    expect(result.current.landing?.target).toBe("start");
    for (let page = 1; page < 8; page++) {
      act(() => result.current.loadNext());
      await waitFor(() => expect(result.current.items.at(-1)).toBe(page * 100 + 99));
    }
    // It keeps its row minimum (and at least its minimum of pages), evicting from the far edge.
    expect(result.current.items).toHaveLength(Math.max(WINDOW_ROWS, WINDOW_PAGES * 100));
    expect(result.current.startIndex).toBe(800 - WINDOW_ROWS);
    expect(result.current.items[0]).toBe(800 - WINDOW_ROWS);
    expect(result.current.hasPrevious).toBe(true);
    act(() => result.current.loadPrevious());
    await waitFor(() => expect(result.current.items[0]).toBe(700 - WINDOW_ROWS));
    expect(result.current.startIndex).toBe(700 - WINDOW_ROWS);
    expect(result.current.items.at(-1)).toBe(699);
    // Only the first page asked for totals; scrolling uses cursors alone.
    expect(fetch.mock.calls.filter(([selector]) => selector.includeTotal)).toHaveLength(1);
  });

  // Reported by the user (2026-10-19): with 20-row pages every page scrolled evicted one.
  it("keeps at least its row minimum when pages are small", async () => {
    const fetch = server(1000, 20);
    const { result } = renderHook(() => useCursorWindow(fetch, ["list"]));
    await waitFor(() => expect(result.current.items).toHaveLength(20));
    for (let page = 1; page <= 30; page++) {
      act(() => result.current.loadNext());
      await waitFor(() => expect(result.current.items.at(-1)).toBe(page * 20 + 19));
    }
    expect(result.current.items).toHaveLength(WINDOW_ROWS);
    expect(result.current.startIndex).toBe(620 - WINDOW_ROWS);
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
      .mockRejectedValueOnce(new ApiError(422, "INVALID_CURSOR", "Invalid cursor"))
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
    act(() => result.current.loadNext());
    await waitFor(() => expect(result.current.items).toHaveLength(20));
    act(() => result.current.setViewportIndex(53));
    rerender({ search: "a", token: 1 });
    await waitFor(() => expect(fetch).toHaveBeenLastCalledWith({ cursor: "from:50", includeTotal: true }));
    // The rows keep their places (0.11 X6): nothing scrolls, and the rows held before stay drawn
    // where no fresh row is held yet.
    await waitFor(() => expect(result.current.landing?.target).toBe("keep"));
    expect(result.current.items).toEqual([50, 51, 52, 53, 54, 55, 56, 57, 58, 59]);
    expect(result.current.itemAt(65)).toBe(65);
    rerender({ search: "b", token: 1 });
    expect(result.current.items).toEqual([]);
    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.items[0]).toBe(0));
  });

  describe("a list drawn by row number (0.11 X6, D156)", () => {
    it("reads ahead toward the view one page at a time, and fills itself until nearly full", async () => {
      const fetch = server(1000, 20);
      const { result } = renderHook(() => useCursorWindow(fetch, ["list"]));
      await waitFor(() => expect(result.current.items).toHaveLength(20));
      // The view shows rows 0–14 and needs two screens (30 rows) beyond it held.
      act(() => {
        result.current.show(0, 14, 30);
        result.current.show(0, 14, 30);
      });
      // One request per direction at a time, however often the view asks.
      expect(fetch).toHaveBeenCalledTimes(2);
      await waitFor(() => expect(result.current.items).toHaveLength(40));
      // The view keeps asking as it draws; the window goes on until it holds about as much as it
      // keeps, with room for a page either side, and then stops.
      for (let round = 0; round < 20; round++) {
        act(() => result.current.show(0, 14, 30));
        await waitFor(() => expect(result.current.after.loading).toBe(false));
      }
      expect(result.current.items).toHaveLength(280);
      expect(result.current.items.length).toBeLessThan(WINDOW_ROWS);
      expect(fetch.mock.calls.slice(1).every(([selector]) => selector.cursor?.startsWith("from:"))).toBe(true);
      // A list shorter than the window is held whole.
      const short = server(220, 20);
      const { result: whole } = renderHook(() => useCursorWindow(short, ["short"]));
      await waitFor(() => expect(whole.current.items).toHaveLength(20));
      for (let round = 0; round < 12; round++) {
        act(() => whole.current.show(0, 14, 30));
        await waitFor(() => expect(whole.current.after.loading).toBe(false));
      }
      expect(whole.current.items).toHaveLength(220);
      expect(whole.current.hasNext).toBe(false);
    });

    it("reads nothing while a far move is under way, then one position read where it rests", async () => {
      const fetch = server(1000, 20);
      const { result } = renderHook(() => useCursorWindow(fetch, ["list"]));
      await waitFor(() => expect(result.current.items).toHaveLength(20));
      act(() => {
        for (const first of [200, 400, 700]) result.current.show(first, first + 14, 30);
      });
      expect(fetch).toHaveBeenCalledTimes(1);
      act(() => result.current.rest(700, 714, 30));
      await waitFor(() => expect(result.current.startIndex).toBe(700));
      expect(fetch).toHaveBeenCalledTimes(2);
      expect(fetch).toHaveBeenLastCalledWith({ position: 700, includeTotal: true });
      expect(result.current.landing?.target).toBe("keep");
      expect(result.current.itemAt(705)).toBe(705);
      expect(result.current.itemAt(5)).toBeUndefined();
      // A view at rest near the held rows reads on with cursors, not positions.
      act(() => result.current.rest(705, 719, 30));
      act(() => result.current.show(705, 719, 30));
      await waitFor(() => expect(result.current.itemAt(680)).toBe(680));
      await waitFor(() => expect(result.current.itemAt(739)).toBe(739));
      expect(fetch.mock.calls.slice(2).every(([selector]) => selector.cursor !== undefined)).toBe(true);
    });

    it("forgets the rows furthest from the view without moving any other row", async () => {
      const fetch = server(2000, 20);
      const { result } = renderHook(() => useCursorWindow(fetch, ["list"]));
      await waitFor(() => expect(result.current.items).toHaveLength(20));
      for (let page = 1; page < 40; page++) {
        act(() => result.current.loadNext());
        await waitFor(() => expect(result.current.items.at(-1)).toBe(page * 20 + 19));
        // Every held row stays at its own row number.
        const { startIndex, items } = result.current;
        expect(items.every((row, offset) => row === startIndex + offset)).toBe(true);
      }
      expect(result.current.items.length).toBeLessThanOrEqual(WINDOW_ROWS + 20);
      expect(result.current.itemAt(0)).toBeUndefined();
      expect(result.current.itemAt(799)).toBe(799);
    });
  });

  it("lands a jump to held rows over a jump still being read (0.11 X6)", async () => {
    let answer: (page: WindowedPage<number>) => void = () => undefined;
    const pages = server(1000, 20);
    const fetch = vi.fn((selector: PageSelector) =>
      selector.fromEnd ? new Promise<WindowedPage<number>>((resolve) => (answer = resolve)) : pages(selector),
    );
    const { result } = renderHook(() => useCursorWindow(fetch, ["list"]));
    await waitFor(() => expect(result.current.items).toHaveLength(20));
    act(() => result.current.jumpToEnd(true));
    act(() => result.current.jumpToStart(true));
    expect(result.current.landing?.target).toBe("start");
    act(() =>
      answer({ items: [980, 999], prevCursor: "before:980", nextCursor: null, totalCount: 1000, startIndex: 980 }),
    );
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(result.current.landing?.target).toBe("start");
    expect(result.current.startIndex).toBe(0);
  });
});
