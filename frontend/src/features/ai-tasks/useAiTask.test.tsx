import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ai } from "@/api/aiClient";
import { useAiTask } from "./useAiTask";
import { designTask } from "./designFixture";

vi.mock("@/api/aiClient", () => ({ ai: { task: vi.fn() } }));
// No stream is opened: a job's changes are not under test here.
vi.mock("@/api/eventStream", () => ({
  openEventStream: (url: string) => ({ url, addEventListener: () => undefined, close: () => undefined }),
}));

describe("useAiTask", () => {
  it("gives the page and the journey bar one copy: a write's answer reaches both", async () => {
    vi.mocked(ai.task).mockResolvedValue(designTask());
    const { result } = renderHook(() => ({ page: useAiTask("task-1"), bar: useAiTask("task-1") }));
    await waitFor(() => expect(result.current.bar.task?.state).toBe("checked"));
    act(() => result.current.page.set({ ...designTask(), state: "loaded" }));
    expect(result.current.bar.task?.state).toBe("loaded");
  });
});
