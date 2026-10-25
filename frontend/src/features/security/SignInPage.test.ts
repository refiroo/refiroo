import { describe, expect, it } from "vitest";
import type { Group } from "@/types";
import { groupsBySource } from "./GroupsPage";
import { providerKeyFrom } from "./SignInPage";

describe("Sign-in providers and their groups (0.12 I3)", () => {
  it("makes a provider's key from its name as the API accepts it", () => {
    expect(providerKeyFrom("Northfield Entra ID")).toBe("northfield-entra-id");
    expect(providerKeyFrom("  2nd Keycloak!  ")).toBe("nd-keycloak");
    expect(providerKeyFrom("Ögöny SSO")).toBe("ogony-sso");
    expect(providerKeyFrom("x".repeat(80))).toHaveLength(63);
  });

  it("lists local groups first, then each provider's under its name", () => {
    const group = (id: string, provider?: string): Group => ({
      id,
      name: id,
      description: null,
      source: provider ? { provider: { key: provider, name: provider.toUpperCase() }, claimValue: id } : null,
      members: 0,
      version: 1,
      createdAt: "",
      updatedAt: "",
    });
    const sections = groupsBySource([group("p1", "entra"), group("l1"), group("k1", "kc"), group("p2", "entra")]);
    expect(sections.map((section) => [section.label, section.groups.map((g) => g.id)])).toEqual([
      ["Local", ["l1"]],
      ["From ENTRA", ["p1", "p2"]],
      ["From KC", ["k1"]],
    ]);
    expect(groupsBySource([group("p1", "entra")]).map((section) => section.label)).toEqual(["From ENTRA"]);
  });
});
