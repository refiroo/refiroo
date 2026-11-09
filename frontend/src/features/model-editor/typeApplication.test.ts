import { describe, expect, it } from "vitest";
import { applicationForType, applicationsHolding } from "@/features/model-editor/typeApplication";

// The shape of the user's draft: country is listed in three applications; only reference-lists has table views for it.
const applications = [
  { key: "system-codes", objectTypeKeys: ["country", "language"], details: [], views: [] },
  {
    key: "reference-lists",
    objectTypeKeys: ["country"],
    details: [],
    views: [
      { type: "table", objectTypeKey: "country", key: "country-list" },
      { type: "table", objectTypeKey: "country", key: "countries" },
    ],
  },
  { key: "translations", objectTypeKeys: ["country"], details: [], views: [] },
];

describe("applicationForType", () => {
  it("uses the application named when it holds the type, with its table views", () => {
    const found = applicationForType(applications, "country", "reference-lists");
    expect(found?.key).toBe("reference-lists");
    expect(found?.views.filter((view) => view.type === "table" && view.objectTypeKey === "country")).toHaveLength(2);
    expect(applicationForType(applications, "country", "translations")?.key).toBe("translations");
  });

  it("falls back to the first application with a table view or detail page for the type", () => {
    expect(applicationForType(applications, "country")?.key).toBe("reference-lists");
    expect(applicationForType(applications, "country", "billing")?.key).toBe("reference-lists");
    const withDetail = [applications[0]!, { ...applications[2]!, details: [{ objectTypeKey: "country" }] }];
    expect(applicationForType(withDetail, "country", "reference-lists")?.key).toBe("translations");
  });

  it("falls back to the first that lists the type, and to none when no application does", () => {
    expect(applicationForType([applications[0]!, applications[2]!], "country")?.key).toBe("system-codes");
    expect(applicationForType(applications, "language", "reference-lists")?.key).toBe("system-codes");
    expect(applicationForType(applications, "missing", "system-codes")).toBeUndefined();
  });

  it("uses the application that owns the workspace's records over the designed fallback, and the named one over both", () => {
    const withDetails = applications.map((item) => ({ ...item, details: [{ objectTypeKey: "country" }] }));
    // All three have a detail page: the first (system-codes) would be the designed fallback.
    expect(applicationForType(withDetails, "country")?.key).toBe("system-codes");
    expect(applicationForType(withDetails, "country", undefined, "reference-lists")?.key).toBe("reference-lists");
    expect(applicationForType(withDetails, "country", "translations", "reference-lists")?.key).toBe("translations");
    // A records' application that does not hold the type is ignored.
    expect(applicationForType(applications, "language", undefined, "reference-lists")?.key).toBe("system-codes");
  });
});

describe("applicationsHolding", () => {
  it("lists the applications that hold the type, in order", () => {
    expect(applicationsHolding(applications, "country").map((item) => item.key)).toEqual([
      "system-codes",
      "reference-lists",
      "translations",
    ]);
    expect(applicationsHolding(applications, "language")).toHaveLength(1);
  });
});
