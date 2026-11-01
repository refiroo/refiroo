import { describe, expect, it } from "vitest";
import { queryTranslationOffer } from "@/features/settings/useWorkspaceAiOffer";
import type { AiSystemInfo, MyPermissions } from "@/types";

const provider = (more: Partial<AiSystemInfo> = {}): AiSystemInfo => ({
  configured: true,
  provider: "fake",
  sendLevel: "structure",
  ...more,
});

// What the person holds in the workspace shown: the action groups of their roles there.
const holding = (...keys: string[]) => ({ actionGroups: keys.map((key) => ({ key })) }) as unknown as MyPermissions;

describe("when a question in words is offered (0.16 AG4)", () => {
  it("needs a provider and ai-proposals, at any send level", () => {
    for (const level of ["structure", "samples", "values"] as const) {
      expect(queryTranslationOffer(provider({ sendLevel: level }), holding("browse", "ai-proposals"))).toBeDefined();
    }
  });

  it("is hidden, not disabled, without a provider, without the group, or before they are known", () => {
    expect(queryTranslationOffer(provider({ configured: false }), holding("ai-proposals"))).toBeUndefined();
    expect(queryTranslationOffer(provider(), holding("browse"))).toBeUndefined();
    expect(queryTranslationOffer(undefined, holding("ai-proposals"))).toBeUndefined();
    expect(queryTranslationOffer(provider(), undefined)).toBeUndefined();
  });

  it("is not offered by the assistant alone: the question is a provider call", () => {
    expect(
      queryTranslationOffer(provider({ configured: false, assistant: true }), holding("ai-proposals")),
    ).toBeUndefined();
  });
});
