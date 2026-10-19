import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useRecordSelection } from "@/lib/hooks/useRecordSelection";

const rows = (count: number) => Array.from({ length: count }, (_, index) => ({ id: `r${index}`, version: 1 }));

describe("useRecordSelection", () => {
  // 0.11 X6: a list reads on in the background, so the loaded rows may be more than one bulk change
  // holds; they are refused as all matching is, with the count to explain.
  it("refuses the loaded rows over the limit, by the header and by Cmd+A, and takes them under it", () => {
    const over = renderHook(() => useRecordSelection("list", rows(150), 100));
    act(() => over.result.current.toggleLoaded());
    expect(over.result.current.count).toBe(0);
    expect(over.result.current.refusedTotal).toBe(150);
    act(() => over.result.current.selectLoaded());
    expect(over.result.current.count).toBe(0);
    expect(over.result.current.refusedTotal).toBe(150);

    const under = renderHook(() => useRecordSelection("list", rows(80), 100));
    act(() => under.result.current.toggleLoaded());
    expect(under.result.current.count).toBe(80);
    expect(under.result.current.refusedTotal).toBeUndefined();
  });
});
