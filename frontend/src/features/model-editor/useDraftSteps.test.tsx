import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "@/api/client";
import { outlineFixture } from "@/test/draftOutline";
import { useDraftEditing } from "@/features/model-editor/useDraftEditing";
import { useDraftSteps } from "@/features/model-editor/useDraftSteps";
import type { ModelDraftOperationEntry } from "@/types";

vi.mock("@/api/client", async (load) => {
  const actual = await load<typeof import("@/api/client")>();
  return { ...actual, api: Object.fromEntries(Object.keys(actual.api).map((key) => [key, vi.fn()])) };
});

const entry = (step: number): ModelDraftOperationEntry => ({
  sequence: step,
  step,
  kind: "setLabel",
  parameters: {},
  inverse: {},
  draftVersion: step,
  author: null,
  at: "2026-10-11T10:00:00Z",
  undone: false,
  origin: { type: "request" },
});
const answer = (version: number) => ({ version, entries: [entry(version)], valid: true, diagnostics: [] });

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(api.modelDraftOutline).mockResolvedValue({ ...outlineFixture(), version: 4 });
  vi.mocked(api.modelDraft).mockResolvedValue({ name: "Draft", baseReleaseId: null } as never);
});

describe("steps of one draft (R17-F2, R17-F4)", () => {
  it("sends two quick steps in order, the second at the version the first answered", async () => {
    let live = 4;
    vi.mocked(api.modelDraftOutline).mockImplementation(async () => ({ ...outlineFixture(), version: live }));
    vi.mocked(api.applyModelDraftOperations).mockImplementation(async (_id, at) => {
      // A step sent at a stale version is refused, as the engine does.
      if (at !== live) throw new ApiError(409, "VERSION_CONFLICT", "moved on", {});
      live += 1;
      return answer(live);
    });
    const { result } = renderHook(() => useDraftSteps("d1"));
    await waitFor(() => expect(result.current.outline).toBeDefined());
    let both: Promise<unknown> | undefined;
    act(() => {
      both = Promise.all([result.current.run([]), result.current.run([])]);
    });
    await act(async () => {
      await both;
    });
    expect(vi.mocked(api.applyModelDraftOperations).mock.calls.map((call) => call[1])).toEqual([4, 5]);
    expect(live).toBe(6);
  });

  it("still says a conflict that someone else caused", async () => {
    vi.mocked(api.applyModelDraftOperations).mockRejectedValueOnce(
      new ApiError(409, "VERSION_CONFLICT", "moved on", { operations: [], more: false }),
    );
    const onStale = vi.fn();
    const { result } = renderHook(() => useDraftSteps("d1", { onStale }));
    await waitFor(() => expect(result.current.outline).toBeDefined());
    await act(async () => {
      expect(await result.current.run([])).toBe("stale");
    });
    expect(onStale).toHaveBeenCalledTimes(1);
  });

  it("names the step it made, so an Undo takes that one back", async () => {
    vi.mocked(api.applyModelDraftOperations).mockResolvedValue(answer(5));
    vi.mocked(api.undoModelDraftStep).mockResolvedValue(answer(6));
    const { result } = renderHook(() => useDraftEditing("d1"));
    await waitFor(() => expect(result.current.outline).toBeDefined());
    vi.mocked(api.modelDraftOutline).mockResolvedValue({ ...outlineFixture(), version: 5 });
    let made: number | undefined;
    await act(async () => {
      made = (await result.current.runAnswered([])).step;
    });
    expect(made).toBe(5);
    await act(async () => {
      await result.current.undo([made!]);
    });
    expect(api.undoModelDraftStep).toHaveBeenCalledWith("d1", 5, [5]);
  });
});
