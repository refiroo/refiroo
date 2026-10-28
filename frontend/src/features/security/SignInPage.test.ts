import { describe, expect, it } from "vitest";
import { providerKeyFrom } from "./SignInPage";

describe("Sign-in providers and their groups (0.12 I3)", () => {
  it("makes a provider's key from its name as the API accepts it", () => {
    expect(providerKeyFrom("Northfield Entra ID")).toBe("northfield-entra-id");
    expect(providerKeyFrom("  2nd Keycloak!  ")).toBe("nd-keycloak");
    expect(providerKeyFrom("Ögöny SSO")).toBe("ogony-sso");
    expect(providerKeyFrom("x".repeat(80))).toHaveLength(63);
  });
});
