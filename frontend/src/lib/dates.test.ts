import { describe, expect, it } from "vitest";
import { formatServerAgo, formatServerDayTime, formatServerTime, timeOfDay } from "@/lib/dates";

describe("server times", () => {
  it("formats an offset timestamp as local time", () => {
    expect(formatServerTime("2026-09-24T18:41:59Z")).toBe(new Date(Date.UTC(2026, 8, 24, 18, 41, 59)).toLocaleString());
  });

  it("returns unparseable input unchanged for display", () => {
    expect(formatServerTime("not a time")).toBe("not a time");
  });
});

describe("day and time at a glance (0.12 I2 Account)", () => {
  const now = new Date(2026, 9, 23, 14, 0);
  const at = (day: number, hour: number, minute = 0) => new Date(2026, 9, day, hour, minute).toISOString();
  const time = (day: number, hour: number, minute = 0) =>
    new Date(2026, 9, day, hour, minute).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });

  it("names today and yesterday, then the date", () => {
    expect(formatServerDayTime(at(23, 8, 12), now)).toBe(`today, ${time(23, 8, 12)}`);
    expect(formatServerDayTime(at(22, 17, 40), now)).toBe(`yesterday, ${time(22, 17, 40)}`);
    expect(formatServerDayTime(at(20, 17, 40), now)).toContain(time(20, 17, 40));
  });

  it("says how long ago, falling back to the day", () => {
    expect(formatServerAgo(at(23, 13, 59), now)).toBe("1 minute ago");
    expect(formatServerAgo(new Date(now.valueOf() - 20_000).toISOString(), now)).toBe("just now");
    expect(formatServerAgo(at(23, 12, 0), now)).toBe("2 hours ago");
    expect(formatServerAgo(at(22, 17, 40), now)).toBe(`yesterday, ${time(22, 17, 40)}`);
  });
});

describe("time of day", () => {
  it("reads in the browser's locale and returns what it cannot read", () => {
    const at = new Date(2026, 9, 23, 8, 12).toISOString();
    expect(timeOfDay(at)).toBe(new Date(at).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" }));
    expect(timeOfDay("not a time")).toBe("not a time");
  });
});
