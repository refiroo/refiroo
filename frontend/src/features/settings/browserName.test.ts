import { describe, expect, it } from "vitest";
import { browserName } from "./browserName";

describe("browserName (0.12 I2)", () => {
  it.each([
    ["Mozilla/5.0 (Macintosh; Intel Mac OS X 14.5; rv:131.0) Gecko/20100101 Firefox/131.0", "Firefox on macOS"],
    [
      "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
      "Safari on iOS",
    ],
    [
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
      "Edge on Windows",
    ],
    [
      "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",
      "Chrome on Android",
    ],
  ])("names %s", (agent, name) => expect(browserName(agent)).toBe(name));

  it("shows what it does not recognise as sent, and nothing as unknown", () => {
    expect(browserName("curl/8.7.1")).toBe("curl/8.7.1");
    expect(browserName(null)).toBe("Unknown browser");
  });
});
