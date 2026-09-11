import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useCursorPages } from "@/lib/hooks/useCursorPages";

describe("useCursorPages", () => {
  it("retains a later page when a mutation refresh fails and retries it without losing the cursor", async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce({ items: ["saved row"], nextCursor: null })
      .mockRejectedValueOnce(new Error("Refresh unavailable"))
      .mockResolvedValueOnce({ items: ["updated row"], nextCursor: null });
    const { result, rerender } = renderHook(
      ({ token }) => useCursorPages(fetch, ["west"], { cursors: ["second"], onChange: vi.fn() }, token),
      { initialProps: { token: 0 } },
    );
    await waitFor(() => expect(result.current.items).toEqual(["saved row"]));
    rerender({ token: 1 });
    await waitFor(() => expect(result.current.error).toBe("Refresh unavailable"));
    expect(result.current.items).toEqual(["saved row"]);
    expect(result.current.pageNumber).toBe(2);
    act(() => result.current.retry());
    await waitFor(() => expect(result.current.items).toEqual(["updated row"]));
    expect(fetch.mock.calls.map(([cursor]) => cursor)).toEqual(["second", "second", "second"]);
  });
  it("retains the displayed page on failure and retries the same requested cursor", async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce({ items: ["first"], nextCursor: "second" })
      .mockRejectedValueOnce(new Error("Page unavailable"))
      .mockResolvedValueOnce({ items: ["second"], nextCursor: null });
    const { result } = renderHook(() => useCursorPages(fetch, ["west"]));
    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => result.current.next());
    await waitFor(() => expect(result.current.error).toBe("Page unavailable"));
    expect(result.current.items).toEqual(["first"]);
    expect(result.current.pageNumber).toBe(1);
    act(() => result.current.retry());
    await waitFor(() => expect(result.current.items).toEqual(["second"]));
    expect(fetch.mock.calls.map(([cursor]) => cursor)).toEqual([undefined, "second", "second"]);
    expect(result.current.pageNumber).toBe(2);
  });

  it("hides old workspace rows and cursors while the new workspace is unavailable", async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce({ items: ["west"], nextCursor: "west-next" })
      .mockRejectedValueOnce(new Error("East unavailable"));
    const { result, rerender } = renderHook(({ workspace }) => useCursorPages(fetch, [workspace]), {
      initialProps: { workspace: "west" },
    });
    await waitFor(() => expect(result.current.items).toEqual(["west"]));
    rerender({ workspace: "east" });
    expect(result.current.items).toEqual([]);
    await waitFor(() => expect(result.current.error).toBe("East unavailable"));
    expect(result.current.hasNext).toBe(false);
    expect(result.current.pageNumber).toBe(1);
    expect(fetch).toHaveBeenLastCalledWith(undefined);
  });
});
