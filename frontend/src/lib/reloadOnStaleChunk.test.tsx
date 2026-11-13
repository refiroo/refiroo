import { afterEach, describe, expect, it, vi } from "vitest";
import { reloadOnStaleChunk } from "@/lib/reloadOnStaleChunk";

function stubSessionStorage() {
  const held = new Map<string, string>();
  vi.stubGlobal("sessionStorage", {
    getItem: (key: string) => held.get(key) ?? null,
    setItem: (key: string, value: string) => held.set(key, value),
    removeItem: (key: string) => held.delete(key),
  });
}

afterEach(() => vi.unstubAllGlobals());

describe("reloadOnStaleChunk", () => {
  it("reloads once for a chunk that is gone, and leaves the second failure to the error boundary", () => {
    stubSessionStorage();
    const reload = vi.fn();
    const stop = reloadOnStaleChunk(reload);
    const first = new Event("vite:preloadError", { cancelable: true });
    window.dispatchEvent(first);
    expect(reload).toHaveBeenCalledTimes(1);
    expect(first.defaultPrevented).toBe(true);
    const second = new Event("vite:preloadError", { cancelable: true });
    window.dispatchEvent(second);
    expect(reload).toHaveBeenCalledTimes(1);
    expect(second.defaultPrevented).toBe(false);
    stop();
  });

  it("does not reload where storage cannot guard against a loop", () => {
    vi.stubGlobal("sessionStorage", {
      getItem: () => {
        throw new Error("blocked");
      },
    });
    const reload = vi.fn();
    const stop = reloadOnStaleChunk(reload);
    window.dispatchEvent(new Event("vite:preloadError", { cancelable: true }));
    expect(reload).not.toHaveBeenCalled();
    stop();
  });
});
