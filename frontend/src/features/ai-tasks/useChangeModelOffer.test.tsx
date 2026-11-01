import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { MyPermissions } from "@/types";
import { useChangeModelOffer } from "./useChangeModelOffer";

const state = vi.hoisted(() => ({ authors: true, held: ["model-release"], assistant: true }));

vi.mock("@/app/useMe", () => ({ useHoldsGroup: () => state.authors }));
vi.mock("@/features/security/permissions", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/security/permissions")>()),
  useWorkspacePermissions: () => ({ actionGroups: state.held.map((key) => ({ key })) }) as unknown as MyPermissions,
}));
vi.mock("@/features/settings/useWorkspaceAiOffer", () => ({
  useAssistantOfferIn: () => (state.assistant ? { assistant: true } : undefined),
}));

describe("Change this model… on the workspace menu (0.16 AP12, AP-D51)", () => {
  beforeEach(() => {
    state.authors = true;
    state.held = ["model-release"];
    state.assistant = true;
  });

  it("is offered where the assistant is on and the person authors and releases models in an active workspace", () => {
    expect(renderHook(() => useChangeModelOffer("west", "active")).result.current).toBe(true);
  });

  it.each([
    ["the assistant is off", () => (state.assistant = false)],
    ["the person does not author models", () => (state.authors = false)],
    ["the person does not hold Model release in the workspace", () => (state.held = [])],
  ])("is hidden when %s", (_name, change) => {
    change();
    expect(renderHook(() => useChangeModelOffer("west", "active")).result.current).toBe(false);
  });

  it("is hidden for a retired workspace, or one not read yet", () => {
    expect(renderHook(() => useChangeModelOffer("west", "retired")).result.current).toBe(false);
    expect(renderHook(() => useChangeModelOffer("west", undefined)).result.current).toBe(false);
  });
});
