import { describe, expect, it } from "vitest";
import { formatServerTime } from "@/lib/dates";

describe("server times", () => {
  it("formats an offset timestamp as local time", () => {
    expect(formatServerTime("2026-09-24T18:41:59Z")).toBe(new Date(Date.UTC(2026, 8, 24, 18, 41, 59)).toLocaleString());
  });

  it("returns unparseable input unchanged for display", () => {
    expect(formatServerTime("not a time")).toBe("not a time");
  });
});
