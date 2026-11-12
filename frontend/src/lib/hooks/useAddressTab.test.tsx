import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useAddressTab } from "./useAddressTab";

const IDS = ["server", "messages"] as const;

afterEach(() => {
  vi.restoreAllMocks();
  window.history.replaceState(null, "", "/");
});

describe("useAddressTab", () => {
  it("opens on the first tab without a parameter, and on the one the address names", () => {
    window.history.replaceState(null, "", "/settings/mail");
    expect(renderHook(() => useAddressTab(IDS)).result.current[0]).toBe("server");
    window.history.replaceState(null, "", "/settings/mail?tab=messages");
    expect(renderHook(() => useAddressTab(IDS)).result.current[0]).toBe("messages");
    window.history.replaceState(null, "", "/settings/mail?tab=nonsense");
    expect(renderHook(() => useAddressTab(IDS)).result.current[0]).toBe("server");
  });

  it("writes the tab into the address, none for the first, and follows Back", () => {
    window.history.replaceState({ keep: 1 }, "", "/settings/mail?x=1");
    const { result } = renderHook(() => useAddressTab(IDS));
    act(() => result.current[1]("messages"));
    expect(window.location.search).toBe("?x=1&tab=messages");
    expect(window.history.state).toEqual({ keep: 1 });
    expect(result.current[0]).toBe("messages");
    act(() => result.current[1]("server"));
    expect(window.location.search).toBe("?x=1");
    window.history.replaceState(null, "", "/settings/mail?tab=messages");
    act(() => {
      window.dispatchEvent(new PopStateEvent("popstate"));
    });
    expect(result.current[0]).toBe("messages");
  });

  it("reads the tab from the address the document was loaded with after the router has cleaned it", async () => {
    vi.spyOn(performance, "getEntriesByType").mockReturnValue([
      { name: "https://localhost/settings/mail?tab=messages" } as PerformanceEntry,
    ]);
    vi.resetModules();
    const fresh = await import("./useAddressTab");
    // The router rewrites the address to its own route as the application opens.
    window.history.replaceState(null, "", "/settings/mail");
    const { result } = renderHook(() => fresh.useAddressTab(IDS));
    expect(result.current[0]).toBe("messages");
    expect(window.location.search).toBe("?tab=messages");
  });
});
