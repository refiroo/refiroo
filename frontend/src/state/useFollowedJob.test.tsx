import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api, jobEventsUrl } from "@/api/client";
import { isFinal, useFollowedJob } from "@/state/useFollowedJob";
import type { Job } from "@/types";

vi.mock("@/api/client", async (load) => ({
  ...(await load<typeof import("@/api/client")>()),
  api: { job: vi.fn() },
}));

const streams = vi.hoisted(() => ({
  opened: [] as string[],
  closed: [] as string[],
  listeners: new Map<string, (event: { data: string }) => void>(),
}));
vi.mock("@/api/eventStream", () => ({
  openEventStream: (url: string) => {
    streams.opened.push(url);
    return {
      url,
      addEventListener: (_type: string, listener: (event: { data: string }) => void) =>
        streams.listeners.set(url, listener),
      close: () => streams.closed.push(url),
    };
  },
}));

const job = (state: Job["state"], more: Partial<Job> = {}) => ({ id: "j1", state, ...more }) as Job;
const send = (next: Job) => act(() => streams.listeners.get(jobEventsUrl(next.id))?.({ data: JSON.stringify(next) }));

describe("useFollowedJob", () => {
  beforeEach(() => {
    streams.opened.length = 0;
    streams.closed.length = 0;
    streams.listeners.clear();
    vi.clearAllMocks();
  });

  it("calls back for streamed changes only, never for the first read", async () => {
    vi.mocked(api.job).mockResolvedValue(job("running"));
    const onChange = vi.fn();
    const { result } = renderHook(() => useFollowedJob("j1", { onChange }));
    await waitFor(() => expect(result.current.job?.state).toBe("running"));
    expect(onChange).not.toHaveBeenCalled();
    send(job("completed"));
    expect(onChange).toHaveBeenCalledTimes(1);
    expect(result.current.job?.state).toBe("completed");
    expect(streams.closed).toContain(jobEventsUrl("j1"));
  });

  it("opens no stream for a finished job, nor for a preview waiting to be confirmed", async () => {
    vi.mocked(api.job).mockResolvedValue(job("awaiting_confirmation"));
    const { result } = renderHook(() => useFollowedJob("j1"));
    await waitFor(() => expect(result.current.done).toBe(true));
    expect(streams.opened).toEqual([]);
  });

  it("reopens the stream after a confirm sets the running answer (bulk, move, migration)", async () => {
    vi.mocked(api.job).mockResolvedValue(job("awaiting_confirmation"));
    const { result } = renderHook(() => useFollowedJob("j1"));
    await waitFor(() => expect(result.current.job?.state).toBe("awaiting_confirmation"));
    expect(streams.opened).toEqual([]);
    act(() => result.current.setJob(job("queued", { confirmedAt: "2026-11-14T10:00:00Z" })));
    await waitFor(() => expect(streams.opened).toEqual([jobEventsUrl("j1")]));
    send(job("completed", { confirmedAt: "2026-11-14T10:00:00Z" }));
    expect(streams.closed).toContain(jobEventsUrl("j1"));
  });

  it("follows a job without keeping it, passes only what the filter lets through, and ends on done", async () => {
    const onFinal = vi.fn();
    renderHook(() => useFollowedJob("j1", { keep: false, filter: (next) => next.state !== "queued", onFinal }));
    expect(streams.opened).toEqual([jobEventsUrl("j1")]);
    send(job("queued"));
    send(job("failed"));
    expect(onFinal).toHaveBeenCalledTimes(1);
    expect(api.job).not.toHaveBeenCalled();
  });

  it("follows a seeded job on a rule of its own without reading it", async () => {
    const { result } = renderHook(() => useFollowedJob("j1", { seed: job("awaiting_confirmation"), done: isFinal }));
    expect(streams.opened).toEqual([jobEventsUrl("j1")]);
    expect(api.job).not.toHaveBeenCalled();
    expect(result.current.done).toBe(false);
  });

  it("clears the error of the previous job when the id changes", async () => {
    vi.mocked(api.job)
      .mockRejectedValueOnce(new Error("Not found"))
      .mockResolvedValueOnce(job("running", { id: "j2" }));
    const { result, rerender } = renderHook(({ id }) => useFollowedJob(id), { initialProps: { id: "j1" } });
    await waitFor(() => expect(result.current.error).toBe("Not found"));
    rerender({ id: "j2" });
    await waitFor(() => expect(result.current.job?.id).toBe("j2"));
    expect(result.current.error).toBe("");
  });
});
