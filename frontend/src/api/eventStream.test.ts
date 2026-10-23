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
});
