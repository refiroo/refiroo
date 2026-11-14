import { describe, expect, it } from "vitest";
import { ApiError, invalidFields, isVersionConflict, isVersionConflictCode, refusalMessage } from "./errors";

// The engine's `422 REQUEST_VALIDATION_ERROR`, as FastAPI words it for a person with a malformed e-mail
// and a name that is too long (0.12 SP1: the dialog said only "Request validation failed").
const refused = new ApiError(422, "REQUEST_VALIDATION_ERROR", "Request validation failed", [
  { type: "string_pattern_mismatch", loc: ["body", "name"], msg: "String should have at most 200 characters" },
  { type: "string_pattern_mismatch", loc: ["body", "email"], msg: "String should match pattern '^[^@\\s]+@[^@\\s]+$'" },
  { type: "missing", loc: ["query", "pageSize"], msg: "Field required" },
]);

describe("invalidFields", () => {
  it("names each body field the engine refused, with its reason", () => {
    expect(invalidFields(refused)).toEqual({
      name: "String should have at most 200 characters",
      email: "String should match pattern '^[^@\\s]+@[^@\\s]+$'",
    });
  });

  it("is empty for any other failure", () => {
    expect(invalidFields(new ApiError(409, "EMAIL_TAKEN", "Taken"))).toEqual({});
    expect(invalidFields(new Error("offline"))).toEqual({});
  });
});

describe("refusalMessage", () => {
  it("names the refused fields by their labels instead of the bare message", () => {
    expect(refusalMessage(refused, { name: "Name", email: "E-mail" })).toBe(
      "Name: String should have at most 200 characters. E-mail: String should match pattern '^[^@\\s]+@[^@\\s]+$'.",
    );
    expect(refusalMessage(new ApiError(409, "ROLE_NAME_TAKEN", "Another role is named 'x'"), {})).toBe(
      "Another role is named 'x'",
    );
  });
});

describe("isVersionConflict", () => {
  it("recognises the three stale-write codes, or only those asked for", () => {
    for (const code of ["VERSION_CONFLICT", "CHANGE_SET_VERSION_CONFLICT", "RELATION_SET_VERSION_CONFLICT"])
      expect(isVersionConflict(new ApiError(409, code, "Changed"))).toBe(true);
    const claim = new ApiError(409, "CHANGE_SET_VERSION_CONFLICT", "Changed");
    expect(isVersionConflict(claim, ["VERSION_CONFLICT"])).toBe(false);
    expect(isVersionConflict(claim, ["CHANGE_SET_VERSION_CONFLICT"])).toBe(true);
  });

  it("is not the mapping targets read's refusal, another code or another failure", () => {
    expect(isVersionConflict(new ApiError(409, "MAPPING_VERSION_CONFLICT", "Read again"))).toBe(false);
    expect(isVersionConflict(new ApiError(409, "ACTIVATION_CONFLICT", "Moved"))).toBe(false);
    expect(isVersionConflict(new Error("offline"))).toBe(false);
    expect(isVersionConflictCode("RELATION_SET_VERSION_CONFLICT")).toBe(true);
    expect(isVersionConflictCode(undefined)).toBe(false);
  });
});
