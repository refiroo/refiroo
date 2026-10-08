import { act, waitFor } from "@testing-library/react";
import { expect } from "vitest";
import type { Job } from "@/types";

/** A job stream the test pushes jobs into, as the engine pushes them over server-sent events. */
export class PushedEventSource {
  static open: PushedEventSource[] = [];
  private listener?: (event: MessageEvent<string>) => void;
  constructor(public url: string) {
    PushedEventSource.open.push(this);
  }
  addEventListener(_: string, listener: (event: MessageEvent<string>) => void) {
    this.listener = listener;
  }
  close() {
    PushedEventSource.open = PushedEventSource.open.filter((source) => source !== this);
  }
  /** Pushes once the job's stream is open, as the engine answers a connecting stream. */
  static async push(job: Job) {
    await waitFor(() => expect(PushedEventSource.open.some((item) => item.url.includes(job.id))).toBe(true));
    act(() => {
      for (const source of PushedEventSource.open.filter((item) => item.url.includes(job.id)))
        source.listener?.({ data: JSON.stringify(job) } as MessageEvent<string>);
    });
  }
}
