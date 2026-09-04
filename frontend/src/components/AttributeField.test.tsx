import { describe, expect, it } from "vitest";
import type { AttributeTypeDefinition } from "../types";
import { parseAttributeValue } from "./AttributeField";

function attribute(valueType: AttributeTypeDefinition["valueType"]): AttributeTypeDefinition {
  return { key: "value", name: "Value", valueType, features: {}, validation: {}, ui: {} };
}

describe("typed attribute conversion", () => {
  it("preserves false and numeric zero", () => {
    expect(parseAttributeValue(attribute("boolean"), null, false)).toBe(false);
    expect(parseAttributeValue(attribute("integer"), "0")).toBe(0);
    expect(parseAttributeValue(attribute("decimal"), "0.0")).toBe(0);
  });

  it("parses JSON and rejects malformed JSON", () => {
    expect(parseAttributeValue(attribute("json"), '{"enabled":false}')).toEqual({ enabled: false });
    expect(() => parseAttributeValue(attribute("json"), "{")).toThrow();
  });

  it("keeps date and datetime strings intact", () => {
    expect(parseAttributeValue(attribute("date"), "2026-09-03")).toBe("2026-09-03");
    expect(parseAttributeValue(attribute("dateTime"), "2026-09-03T10:15")).toBe("2026-09-03T10:15");
  });
});
