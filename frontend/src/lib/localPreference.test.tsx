import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { readLocalPreference, useLocalNumberPreference, writeLocalPreference } from "@/lib/localPreference";
import { useTableDisplay } from "@/ui/TableDisplay";

describe("local display preferences", () => {
  let stored: Map<string, string>;
  beforeEach(() => {
    stored = new Map();
    vi.stubGlobal("localStorage", {
      getItem: (key: string) => stored.get(key) ?? null,
      setItem: vi.fn((key: string, value: string) => stored.set(key, value)),
      removeItem: vi.fn((key: string) => stored.delete(key)),
    });
  });

  it("falls back for corrupt or unavailable storage", () => {
    window.localStorage.setItem("broken", "{");
    expect(readLocalPreference("broken", 12, (value): value is number => typeof value === "number")).toBe(12);
    vi.mocked(window.localStorage.setItem).mockImplementationOnce(() => {
      throw new Error("blocked");
    });
    expect(() => writeLocalPreference("blocked", { safe: true })).not.toThrow();
  });

  it("scopes, clamps, reloads and resets widths", () => {
    const hook = renderHook(({ scope }) => useLocalNumberPreference(`layout:${scope}`, 240, 200, 380), {
      initialProps: { scope: "first" },
    });
    act(() => hook.result.current.change(999));
    expect(hook.result.current.value).toBe(380);
    expect(window.localStorage.getItem("layout:first")).toBe("380");
    hook.rerender({ scope: "second" });
    expect(hook.result.current.value).toBe(240);
    act(() => hook.result.current.reset());
    expect(window.localStorage.getItem("layout:second")).toBeNull();
  });

  it("remembers table visibility, density and valid widths while ignoring removed columns", () => {
    const first = renderHook(() => useTableDisplay(["name", "code", "active"], "domains"));
    act(() => {
      first.result.current.toggle("active");
    });
    act(() => {
      first.result.current.setCompact(true);
    });
    act(() => {
      first.result.current.setWidth("code", 260);
    });
    first.unmount();

    const restored = renderHook(() => useTableDisplay(["name", "code"], "domains"));
    expect(restored.result.current.columns).toEqual(["name", "code"]);
    expect(restored.result.current.compact).toBe(true);
    expect(restored.result.current.widths).toEqual({ code: 260 });
    act(() => restored.result.current.toggle("name"));
    expect(restored.result.current.columns).toContain("name");
  });
});
