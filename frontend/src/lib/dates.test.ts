import { describe, expect, it } from "vitest";
import { formatServerTime, parseServerTime } from "@/lib/dates";

describe("server times", () => {
  it("reads a zone-less timestamp as UTC and keeps explicit offsets", () => {
    expect(parseServerTime("2026-09-24T18:41:59.123").toISOString()).toBe("2026-09-24T18:41:59.123Z");
    expect(parseServerTime("2026-09-24T18:41:59Z").toISOString()).toBe("2026-09-24T18:41:59.000Z");
    expect(parseServerTime("2026-09-24T20:41:59+02:00").toISOString()).toBe("2026-09-24T18:41:59.000Z");
  });

  it("returns unparseable input unchanged for display", () => {
    expect(formatServerTime("not a time")).toBe("not a time");
  });
});
