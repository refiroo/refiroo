// @vitest-environment jsdom
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { applyScheme, resetSchemePreference, SCHEME_STORAGE_KEY, useSchemePreference } from "@/lib/scheme";

describe("the colour theme preference", () => {
  let stored: Map<string, string>;
  beforeEach(() => {
    stored = new Map();
    vi.stubGlobal("localStorage", {
      getItem: (key: string) => stored.get(key) ?? null,
      setItem: (key: string, value: string) => stored.set(key, value),
      removeItem: (key: string) => stored.delete(key),
    });
    document.head.innerHTML =
      '<meta name="theme-color" content="#f5f7f6" media="(prefers-color-scheme: light)">' +
      '<meta name="theme-color" content="#101614" media="(prefers-color-scheme: dark)">';
    resetSchemePreference();
  });
  afterEach(() => {
    delete document.documentElement.dataset.scheme;
    vi.unstubAllGlobals();
  });

  const colours = () =>
    [...document.querySelectorAll('meta[name="theme-color"]')].map((meta) => meta.getAttribute("content"));

  it("sets data-scheme for Website purple only, and moves the browser colour with it", () => {
    applyScheme("purple");
    expect(document.documentElement.dataset.scheme).toBe("purple");
    expect(colours()).toEqual(["#fbf8f1", "#0e1130"]);
    applyScheme("normal");
    expect(document.documentElement.dataset.scheme).toBeUndefined();
    expect(colours()).toEqual(["#f5f7f6", "#101614"]);
  });

  it("falls back to Normal for an unknown or corrupt stored value, and follows the storage event", () => {
    stored.set(SCHEME_STORAGE_KEY, '"mauve"');
    const hook = renderHook(() => useSchemePreference());
    expect(hook.result.current.scheme).toBe("normal");
    stored.set(SCHEME_STORAGE_KEY, "{");
    resetSchemePreference();
    hook.rerender();
    expect(hook.result.current.scheme).toBe("normal");

    stored.set(SCHEME_STORAGE_KEY, '"purple"');
    act(() => {
      window.dispatchEvent(new StorageEvent("storage", { key: SCHEME_STORAGE_KEY }));
    });
    expect(hook.result.current.scheme).toBe("purple");
    expect(document.documentElement.dataset.scheme).toBe("purple");
    act(() => hook.result.current.setScheme("normal"));
    expect(stored.get(SCHEME_STORAGE_KEY)).toBe('"normal"');
    expect(document.documentElement.dataset.scheme).toBeUndefined();
  });
});
