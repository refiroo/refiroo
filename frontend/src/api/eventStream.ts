/**
 * A server-sent event stream read with `fetch`, so it carries the access token (0.12 I2, D247):
 * `EventSource` cannot send a header, and a token in a URL is excluded (C-D1). It reads the same
 * `text/event-stream` format and, like `EventSource`, connects again a few seconds after the
 * engine closes the stream, until `close()`.
 */

import { authorizedFetch } from "@/api/session";

const RECONNECT_MS = 3000;

export interface EventStream {
  readonly url: string;
  addEventListener(type: string, listener: (event: MessageEvent<string>) => void): void;
  close(): void;
}

class FetchEventStream implements EventStream {
  private readonly listeners = new Map<string, ((event: MessageEvent<string>) => void)[]>();
  private readonly abort = new AbortController();

  constructor(readonly url: string) {
    void this.run();
  }

  addEventListener(type: string, listener: (event: MessageEvent<string>) => void) {
    this.listeners.set(type, [...(this.listeners.get(type) ?? []), listener]);
  }

  close() {
    this.abort.abort();
  }

  private dispatch(type: string, data: string) {
    const event = new MessageEvent<string>(type, { data });
    for (const listener of this.listeners.get(type) ?? []) listener(event);
  }

  private async run() {
    while (!this.abort.signal.aborted) {
      try {
        const response = await authorizedFetch(this.url, {
          headers: { Accept: "text/event-stream" },
          signal: this.abort.signal,
        });
        if (response.ok && response.body) await this.read(response.body);
      } catch {
        // A dropped connection is retried below, as EventSource retries it.
      }
      if (this.abort.signal.aborted) return;
      await new Promise((done) => setTimeout(done, RECONNECT_MS));
    }
  }

  private async read(body: ReadableStream<Uint8Array>) {
    const reader = body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let type = "message";
    let data: string[] = [];
    for (;;) {
      const { value, done } = await reader.read();
      if (done) return;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split(/\r\n|\r|\n/);
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        if (line === "") {
          if (data.length) this.dispatch(type, data.join("\n"));
          type = "message";
          data = [];
        } else if (!line.startsWith(":")) {
          const colon = line.indexOf(":");
          const field = colon < 0 ? line : line.slice(0, colon);
          const text = colon < 0 ? "" : line.slice(colon + 1).replace(/^ /, "");
          if (field === "event") type = text;
          else if (field === "data") data.push(text);
        }
      }
    }
  }
}

/** Open a stream of the engine's server-sent events at `url`. */
export function openEventStream(url: string): EventStream {
  return new FetchEventStream(url);
}
