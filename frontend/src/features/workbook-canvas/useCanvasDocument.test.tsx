// @vitest-environment jsdom
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { useCanvasDocument } from "./useCanvasDocument";

vi.mock("@/api/client", () => ({
  api: { modelDraftCanvas: vi.fn(), moveCanvasCards: vi.fn(), arrangeCanvas: vi.fn() },
}));

describe("the canvas document's writes", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(api.modelDraftCanvas).mockResolvedValue({ positions: {}, folded: [], scope: null } as never);
  });

  it("sends a later save only after the earlier one has answered, and goes on after a refused one", async () => {
    const sent: string[] = [];
    const settle: Array<(refuse?: boolean) => void> = [];
    const write = (what: string) => () => {
      sent.push(what);
      return new Promise<never>((resolve, reject) =>
        settle.push((refuse) => (refuse ? reject(new Error("x")) : resolve(undefined as never))),
      );
    };
    vi.mocked(api.moveCanvasCards).mockImplementation(write("move") as never);
    vi.mocked(api.arrangeCanvas).mockImplementation(write("arrange") as never);
    const { result } = renderHook(() => useCanvasDocument("draft"));
    await waitFor(() => expect(result.current.ready).toBe(true));
    act(() => {
      result.current.savePositions({ a: { x: 1, y: 2 } });
      result.current.fold("a", true);
      result.current.savePositions({ a: { x: 3, y: 4 } });
    });
    await waitFor(() => expect(sent).toEqual(["move"]));
    settle[0](true);
    await waitFor(() => expect(sent).toEqual(["move", "arrange"]));
    settle[1]();
    await waitFor(() => expect(sent).toEqual(["move", "arrange", "move"]));
    expect(vi.mocked(api.moveCanvasCards).mock.calls[1][1]).toEqual({ a: { x: 3, y: 4 } });
  });
});
