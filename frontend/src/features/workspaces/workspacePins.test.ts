// @vitest-environment jsdom
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { movePin, useWorkspacePins, type WorkspacePin } from "@/features/workspaces/workspacePins";

const a: WorkspacePin = { applicationKey: "app", viewKey: "a" };
const b: WorkspacePin = { applicationKey: "app", viewKey: "b" };
const c: WorkspacePin = { applicationKey: "other", viewKey: "c" };

describe("movePin", () => {
  it("moves a pin to its new place", () => {
    expect(movePin([a, b, c], 0, 2)).toEqual([b, c, a]);
    expect(movePin([a, b, c], 2, 1)).toEqual([a, c, b]);
  });

  it("changes nothing for a bad index or the same place, and never alters its input", () => {
    const pins = [a, b, c];
    for (const [from, to] of [
      [-1, 1],
      [1, 3],
      [3, 0],
      [0, -1],
      [1, 1],
    ]) {
      expect(movePin(pins, from, to)).toEqual([a, b, c]);
    }
    expect(pins).toEqual([a, b, c]);
  });
});

describe("the shelf of a workspace", () => {
  let stored: Map<string, string>;
  beforeEach(() => {
    stored = new Map();
    vi.stubGlobal("localStorage", {
      getItem: (key: string) => stored.get(key) ?? null,
      setItem: (key: string, value: string) => stored.set(key, value),
      removeItem: (key: string) => stored.delete(key),
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  it("reads the stored shelf of its workspace", () => {
    stored.set("rdm:workspace-pins:v1:ws", JSON.stringify([b, a]));
    const { result } = renderHook(() => useWorkspacePins("ws"));
    expect(result.current.pins).toEqual([b, a]);
    expect(result.current.isPinned(a)).toBe(true);
    expect(result.current.isPinned(c)).toBe(false);
  });

  it("adds and takes off a pin with toggle, writing the shelf each time", () => {
    const { result } = renderHook(() => useWorkspacePins("ws"));
    expect(result.current.pins).toEqual([]);
    act(() => result.current.toggle(a));
    act(() => result.current.toggle(b));
    expect(result.current.pins).toEqual([a, b]);
    expect(JSON.parse(stored.get("rdm:workspace-pins:v1:ws") ?? "null")).toEqual([a, b]);
    act(() => result.current.toggle(a));
    expect(result.current.pins).toEqual([b]);
    expect(JSON.parse(stored.get("rdm:workspace-pins:v1:ws") ?? "null")).toEqual([b]);
  });

  it("moves a pin and keeps the new order", () => {
    stored.set("rdm:workspace-pins:v1:ws", JSON.stringify([a, b, c]));
    const { result } = renderHook(() => useWorkspacePins("ws"));
    act(() => result.current.move(2, 0));
    expect(result.current.pins).toEqual([c, a, b]);
    expect(JSON.parse(stored.get("rdm:workspace-pins:v1:ws") ?? "null")).toEqual([c, a, b]);
  });

  it("falls back to an empty shelf when the stored value is corrupt or the wrong shape", () => {
    stored.set("rdm:workspace-pins:v1:ws", "{not json");
    expect(renderHook(() => useWorkspacePins("ws")).result.current.pins).toEqual([]);
    stored.set("rdm:workspace-pins:v1:ws", JSON.stringify([{ applicationKey: "app" }]));
    expect(renderHook(() => useWorkspacePins("ws")).result.current.pins).toEqual([]);
  });

  it("gives another workspace a shelf of its own", () => {
    stored.set("rdm:workspace-pins:v1:one", JSON.stringify([a]));
    stored.set("rdm:workspace-pins:v1:two", JSON.stringify([c]));
    const { result, rerender } = renderHook(({ key }) => useWorkspacePins(key), { initialProps: { key: "one" } });
    expect(result.current.pins).toEqual([a]);
    rerender({ key: "two" });
    expect(result.current.pins).toEqual([c]);
    act(() => result.current.toggle(b));
    expect(JSON.parse(stored.get("rdm:workspace-pins:v1:two") ?? "null")).toEqual([c, b]);
    expect(JSON.parse(stored.get("rdm:workspace-pins:v1:one") ?? "null")).toEqual([a]);
  });
});
