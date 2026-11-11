// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { openEventStream } from "./eventStream";

vi.mock("@/api/session", () => ({
  authorizedFetch: vi.fn(),
}));

const { authorizedFetch } = await import("@/api/session");

/** A response whose body arrives in the given pieces, as a stream does. */
function streamed(pieces: string[]) {
  const encoder = new TextEncoder();
  return new Response(
    new ReadableStream({
      start(controller) {
        for (const piece of pieces) controller.enqueue(encoder.encode(piece));
        controller.close();
      },
    }),
    { status: 200, headers: { "Content-Type": "text/event-stream" } },
  );
}

describe("openEventStream (0.12 I2, D247)", () => {
  afterEach(() => vi.clearAllMocks());

  it("reads named events split across chunks, with the access token's fetch", async () => {
    vi.mocked(authorizedFetch).mockResolvedValueOnce(
      streamed([': keep-alive\n\nevent: job\ndata: {"id":', '"j1"}\n\nevent: job\r\ndata: {"id":"j2"}\r\n\r\n']),
    );
    const stream = openEventStream("http://engine/api/v1/jobs/j1/events");
    const received: string[] = [];
    stream.addEventListener("job", (event) => received.push(event.data));
    await vi.waitFor(() => expect(received).toEqual(['{"id":"j1"}', '{"id":"j2"}']));
    stream.close();
    expect(vi.mocked(authorizedFetch).mock.calls[0][0]).toBe("http://engine/api/v1/jobs/j1/events");
  });

  it("connects again after the engine closes the stream, until closed", async () => {
    vi.useFakeTimers();
    vi.mocked(authorizedFetch).mockImplementation(async () => streamed(["event: job\ndata: {}\n\n"]));
    const stream = openEventStream("http://engine/events");
    await vi.advanceTimersByTimeAsync(3100);
    expect(vi.mocked(authorizedFetch).mock.calls.length).toBe(2);
    stream.close();
    await vi.advanceTimersByTimeAsync(10_000);
    expect(vi.mocked(authorizedFetch).mock.calls.length).toBe(2);
    vi.useRealTimers();
  });

  it("waits longer after each refusal, up to a minute, and starts short again once it connects", async () => {
    vi.useFakeTimers();
    const calls = () => vi.mocked(authorizedFetch).mock.calls.length;
    vi.mocked(authorizedFetch).mockImplementation(async () => new Response("busy", { status: 503 }));
    const stream = openEventStream("http://engine/events");
    await vi.advanceTimersByTimeAsync(0);
    expect(calls()).toBe(1);
    await vi.advanceTimersByTimeAsync(3100);
    expect(calls()).toBe(2);
    // The second wait is six seconds, the third twelve.
    await vi.advanceTimersByTimeAsync(3100);
    expect(calls()).toBe(2);
    await vi.advanceTimersByTimeAsync(3000);
    expect(calls()).toBe(3);
    await vi.advanceTimersByTimeAsync(6000);
    expect(calls()).toBe(3);
    vi.mocked(authorizedFetch).mockImplementation(async () => streamed(["event: job\ndata: {}\n\n"]));
    await vi.advanceTimersByTimeAsync(6100);
    expect(calls()).toBe(4);
    // Connected: the next retry is three seconds away again.
    await vi.advanceTimersByTimeAsync(3100);
    expect(calls()).toBe(5);
    stream.close();
    vi.useRealTimers();
  });

  it("resumes from the last id it saw and says when a connection follows an earlier one (0.17 RF3)", async () => {
    vi.useFakeTimers();
    vi.mocked(authorizedFetch)
      .mockResolvedValueOnce(streamed(["id: 7\nevent: job\ndata: {}\n\n"]))
      .mockImplementation(async () => streamed([": hello\n\n"]));
    const stream = openEventStream("http://engine/events");
    const reconnected = vi.fn();
    stream.addEventListener("reconnected", reconnected);
    await vi.advanceTimersByTimeAsync(0);
    expect(reconnected).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(3100);
    expect(reconnected).toHaveBeenCalledTimes(1);
    const first = vi.mocked(authorizedFetch).mock.calls[0][1]?.headers as Record<string, string>;
    const second = vi.mocked(authorizedFetch).mock.calls[1][1]?.headers as Record<string, string>;
    expect(first["Last-Event-ID"]).toBeUndefined();
    expect(second["Last-Event-ID"]).toBe("7");
    stream.close();
    vi.useRealTimers();
  });
});
