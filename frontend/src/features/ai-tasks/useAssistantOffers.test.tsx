import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { MyPermissions } from "@/types";
import { useAssistantOffers } from "./useAssistantOffers";

const state = vi.hoisted(() => ({
  authors: true,
  held: ["model-release", "change-sets", "bulk"],
  assistant: true,
  jobs: true,
}));

vi.mock("@/app/useMe", () => ({ useHoldsGroup: () => state.authors }));
vi.mock("@/features/security/permissions", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/security/permissions")>()),
  useWorkspacePermissions: () => ({ actionGroups: state.held.map((key) => ({ key })) }) as unknown as MyPermissions,
}));
vi.mock("@/features/settings/useSystem", () => ({
  useCapabilities: () => ({ capabilities: { integrationJobs: { createJobs: state.jobs } } }),
}));
vi.mock("@/features/settings/useWorkspaceAiOffer", () => ({
  useAssistantOfferIn: () => (state.assistant ? { assistant: true } : undefined),
}));

const offers = (status?: string) => renderHook(() => useAssistantOffers("west", status)).result.current;

describe("Change this model… and Ask about these records… (0.16 AP12, AP13, AP-D59)", () => {
  beforeEach(() => {
    state.authors = true;
    state.held = ["model-release", "change-sets", "bulk"];
    state.assistant = true;
    state.jobs = true;
  });

  it("offers both where the assistant is on and the person holds every group the steps need in an active workspace", () => {
    expect(offers("active")).toEqual({ changeModel: true, askRecords: true });
  });

  it.each([
    ["the assistant is off", () => (state.assistant = false), { changeModel: false, askRecords: false }],
    [
      "the person does not hold Work in change sets",
      () => (state.held = ["model-release", "bulk"]),
      { changeModel: false, askRecords: false },
    ],
    ["jobs cannot be created", () => (state.jobs = false), { changeModel: false, askRecords: false }],
    ["the person does not author models", () => (state.authors = false), { changeModel: false, askRecords: true }],
    [
      "the person does not hold Model release",
      () => (state.held = ["change-sets", "bulk"]),
      { changeModel: false, askRecords: true },
    ],
    [
      "the person does not hold Bulk and import",
      () => (state.held = ["model-release", "change-sets"]),
      { changeModel: false, askRecords: false },
    ],
  ])("is hidden for what cannot finish when %s", (_name, change, expected) => {
    change();
    expect(offers("active")).toEqual(expected);
  });

  it("offers neither for a retired workspace, or one not read yet", () => {
    expect(offers("retired")).toEqual({ changeModel: false, askRecords: false });
    expect(offers(undefined)).toEqual({ changeModel: false, askRecords: false });
  });
});
