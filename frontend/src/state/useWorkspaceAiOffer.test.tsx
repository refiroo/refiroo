import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AiSystemInfo, MyPermissions } from "@/types";
import {
  historyAccountOffer,
  impactSummaryOffer,
  useAssistantOfferIn,
  useWorkspaceAiOffer,
  useWorkspaceAssistantOffer,
} from "./useWorkspaceAiOffer";

const state = vi.hoisted(() => ({ ai: undefined as unknown, permissions: undefined as unknown }));
vi.mock("@/state/useSystem", () => ({ useSystem: () => ({ system: { ai: state.ai } }) }));
vi.mock("@/state/WorkspaceDataContext", () => ({
  useWorkspaceData: () => ({ permissions: state.permissions }),
}));

const info = (extra: Partial<AiSystemInfo>): AiSystemInfo => ({
  configured: false,
  provider: null,
  sendLevel: "values",
  assistant: false,
  ...extra,
});
const holding = (...keys: string[]) => ({ actionGroups: keys.map((key) => ({ key })) }) as unknown as MyPermissions;

describe("the AI offers in a workspace (AP-D38)", () => {
  beforeEach(() => {
    state.permissions = holding("ai-proposals");
  });

  it("offers the assistant with only the command set, whatever the provider", () => {
    state.ai = info({ assistant: true });
    expect(renderHook(() => useWorkspaceAssistantOffer()).result.current?.assistant).toBe(true);
    expect(renderHook(() => useAssistantOfferIn("west", holding("ai-proposals"))).result.current).toBeDefined();
    // The provider's offer still needs a provider.
    expect(renderHook(() => useWorkspaceAiOffer()).result.current).toBeUndefined();
  });

  it("offers the provider's features only with a provider, not for the assistant alone", () => {
    state.ai = info({ configured: true, provider: "anthropic" });
    expect(renderHook(() => useWorkspaceAiOffer()).result.current?.configured).toBe(true);
    expect(renderHook(() => useWorkspaceAssistantOffer()).result.current).toBeUndefined();
  });

  it("offers nothing without Use AI proposals or below the values send level", () => {
    state.ai = info({ assistant: true, configured: true });
    state.permissions = holding();
    expect(renderHook(() => useWorkspaceAssistantOffer()).result.current).toBeUndefined();
    expect(renderHook(() => useWorkspaceAiOffer()).result.current).toBeUndefined();
    state.permissions = holding("ai-proposals");
    state.ai = info({ assistant: true, configured: true, sendLevel: "samples" });
    expect(renderHook(() => useWorkspaceAssistantOffer()).result.current).toBeUndefined();
  });

  it("offers the account of a model change at any send level to those who use AI proposals and may activate (AO1)", () => {
    const set = info({ configured: true, provider: "claude", sendLevel: "structure" });
    expect(impactSummaryOffer(set, holding("ai-proposals", "model-release"))).toBe(set);
    expect(impactSummaryOffer(set, holding("ai-proposals"))).toBeUndefined();
    expect(impactSummaryOffer(set, holding("model-release"))).toBeUndefined();
    expect(
      impactSummaryOffer(info({ sendLevel: "structure" }), holding("ai-proposals", "model-release")),
    ).toBeUndefined();
    expect(impactSummaryOffer(undefined, holding("ai-proposals", "model-release"))).toBeUndefined();
  });

  it("offers the account of what changed at any send level to those who browse and use AI proposals (AO2)", () => {
    const set = info({ configured: true, provider: "claude", sendLevel: "structure" });
    expect(historyAccountOffer(set, holding("ai-proposals", "browse"))).toBe(set);
    expect(historyAccountOffer(set, holding("ai-proposals"))).toBeUndefined();
    expect(historyAccountOffer(set, holding("browse"))).toBeUndefined();
    expect(historyAccountOffer(info({ sendLevel: "values" }), holding("ai-proposals", "browse"))).toBeUndefined();
  });
});
