import { describe, expect, it } from "vitest";
import { newestFirst } from "@/model/newestFirst";

describe("newestFirst", () => {
  it("orders by the date key, newest first, and leaves the caller's list as it was", () => {
    const releases = [
      { id: "a", installedAt: "2026-10-01T08:00:00+00:00" },
      { id: "c", installedAt: "2026-11-02T08:00:00+00:00" },
      { id: "b", installedAt: "2026-10-20T08:00:00+00:00" },
    ];
    expect(newestFirst(releases, "installedAt").map((item) => item.id)).toEqual(["c", "b", "a"]);
    expect(releases.map((item) => item.id)).toEqual(["a", "c", "b"]);
  });
});
