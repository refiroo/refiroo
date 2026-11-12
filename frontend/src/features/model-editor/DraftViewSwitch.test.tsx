import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  DRAFT_VIEW_KEY,
  DraftViewSwitch,
  draftOpensOn,
  draftViewRoute,
  lastDraftView,
  rememberDraftView,
} from "@/features/model-editor/DraftViewSwitch";

let stored: Map<string, string>;
beforeEach(() => {
  stored = new Map();
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => stored.get(key) ?? null,
    setItem: (key: string, value: string) => stored.set(key, value),
    removeItem: (key: string) => stored.delete(key),
  });
});

describe("Editor | Canvas (PP-D80)", () => {
  it("presses the current view and goes to the other, remembering it", () => {
    const onChange = vi.fn();
    render(<DraftViewSwitch draftId="d1" view="editor" onChange={onChange} />);
    expect(screen.getByRole("button", { name: "Editor" }).getAttribute("aria-pressed")).toBe("true");
    expect(screen.getByRole("button", { name: "Canvas" }).getAttribute("aria-pressed")).toBe("false");
    fireEvent.click(screen.getByRole("button", { name: "Editor" }));
    expect(onChange).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Canvas" }));
    expect(onChange).toHaveBeenCalledWith("canvas");
    expect(lastDraftView("d1")).toBe("canvas");
  });

  it("counts being on a view as using it, however the page was opened", () => {
    render(<DraftViewSwitch draftId="d2" view="canvas" onChange={vi.fn()} />);
    expect(lastDraftView("d2")).toBe("canvas");
  });

  it("opens a draft on the canvas from a workbook flow, else on the view used last, else the editor", () => {
    expect(draftOpensOn("d1")).toBe("editor");
    rememberDraftView("d1", "canvas");
    expect(draftOpensOn("d1")).toBe("canvas");
    rememberDraftView("d1", "editor");
    expect(draftOpensOn("d1")).toBe("editor");
    expect(draftOpensOn("d1", { fromWorkbook: true })).toBe("canvas");
    // Each draft has its own.
    expect(draftOpensOn("d3")).toBe("editor");
  });

  it("ignores what storage holds that is not a view, and keeps the most recent sixty drafts", () => {
    stored.set(DRAFT_VIEW_KEY, JSON.stringify({ d1: "sideways" }));
    expect(lastDraftView("d1")).toBeUndefined();
    for (let index = 0; index < 70; index += 1) rememberDraftView(`draft-${index}`, "canvas");
    expect(lastDraftView("draft-0")).toBeUndefined();
    expect(lastDraftView("draft-69")).toBe("canvas");
    expect(Object.keys(JSON.parse(stored.get(DRAFT_VIEW_KEY) ?? "{}"))).toHaveLength(60);
  });

  it("addresses each view, keeping the workspace and journey the draft was opened from", () => {
    expect(draftViewRoute("d1", "canvas", { forWorkspace: "ws" })).toEqual({
      kind: "settings",
      page: "model",
      draftId: "d1",
      editor: { show: "canvas" },
      forWorkspace: "ws",
    });
    expect(draftViewRoute("d1", "editor", { journey: { kind: "aiTask", taskId: "t1" } })).toEqual({
      kind: "settings",
      page: "model",
      draftId: "d1",
      editor: {},
      journey: { kind: "aiTask", taskId: "t1" },
    });
  });
});
