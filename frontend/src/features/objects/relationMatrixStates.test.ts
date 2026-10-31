import { describe, expect, it } from "vitest";
import { cellRecordLabel } from "@/features/objects/relationMatrixStates";

describe("what a matrix cell shows of a record", () => {
  const record = (fields: Record<string, unknown>) => ({ name: "CODE · en", fields });

  it("reads the first cell field holding text or a number, in the view's order", () => {
    expect(cellRecordLabel(record({ text: "Hello", other: "Later" }), ["text", "other"])).toBe("Hello");
    expect(cellRecordLabel(record({ text: " ", other: "Later" }), ["text", "other"])).toBe("Later");
    expect(cellRecordLabel(record({ size: 0 }), ["size"])).toBe("0");
  });

  it("falls back to the name when a yes or no or nothing is all it has", () => {
    expect(cellRecordLabel(record({ active: true, text: null }), ["active", "text"])).toBe("CODE · en");
    expect(cellRecordLabel(record({}), [])).toBe("CODE · en");
  });
});
