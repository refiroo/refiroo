import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SHARED_WORKSPACE_STORAGE_KEY, useRememberedWorkspace } from "./sharedWorkspace";

describe("the remembered workspace", () => {
  const held = new Map<string, string>();
  beforeEach(() => {
    held.clear();
    vi.stubGlobal("localStorage", {
      getItem: (key: string) => held.get(key) ?? null,
      setItem: (key: string, value: string) => held.set(key, value),
      removeItem: (key: string) => held.delete(key),
    });
  });

  it("is written as the workspace changes, the default one included", () => {
    const { rerender } = renderHook(({ key }) => useRememberedWorkspace(key), { initialProps: { key: "stops" } });
    expect(held.get(SHARED_WORKSPACE_STORAGE_KEY)).toBe('"stops"');
    rerender({ key: "default" });
    expect(held.get(SHARED_WORKSPACE_STORAGE_KEY)).toBe('"default"');
  });
});
