// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";

async function addressWith(value: string) {
  vi.stubEnv("VITE_API_URL", value);
  vi.resetModules();
  return (await import("@/api/address")).API_URL;
}

describe("the engine's address (0.12 DP1, D404)", () => {
  afterEach(() => vi.unstubAllEnvs());

  it("is the address the page was opened at unless VITE_API_URL names another", async () => {
    expect(await addressWith("")).toBe(window.location.origin);
    expect(await addressWith("https://engine.example.org")).toBe("https://engine.example.org");
  });
});
