import { describe, expect, it } from "vitest";
import { formatDuration } from "@/lib/duration";

describe("formatDuration", () => {
  it("says seconds and minutes", () => {
    expect(formatDuration(400)).toBe("0.4 s");
    expect(formatDuration(50_000)).toBe("50 s");
    expect(formatDuration(87_000)).toBe("1 min 27 s");
    expect(formatDuration(120_000)).toBe("2 min");
    expect(formatDuration(7_500_000)).toBe("2 h 5 min");
  });
});
