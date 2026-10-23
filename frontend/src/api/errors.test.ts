import { describe, expect, it } from "vitest";
import { ApiError, invalidFields, refusalMessage } from "./errors";

// The engine's `422 REQUEST_VALIDATION_ERROR`, as FastAPI words it for a person with a space in the
// username and a malformed e-mail (0.12 SP1: the dialog said only "Request validation failed").
const refused = new ApiError(422, "REQUEST_VALIDATION_ERROR", "Request validation failed", [
  { type: "string_pattern_mismatch", loc: ["body", "username"], msg: "String should match pattern '^\\S+$'" },
  { type: "string_pattern_mismatch", loc: ["body", "email"], msg: "String should match pattern '^[^@\\s]+@[^@\\s]+$'" },
  { type: "missing", loc: ["query", "pageSize"], msg: "Field required" },
]);

describe("invalidFields", () => {
  it("names each body field the engine refused, with its reason", () => {
    expect(invalidFields(refused)).toEqual({
      username: "String should match pattern '^\\S+$'",
      email: "String should match pattern '^[^@\\s]+@[^@\\s]+$'",
    });
  });

  it("is empty for any other failure", () => {
    expect(invalidFields(new ApiError(409, "USERNAME_TAKEN", "Taken"))).toEqual({});
    expect(invalidFields(new Error("offline"))).toEqual({});
  });
});

describe("refusalMessage", () => {
  it("names the refused fields by their labels instead of the bare message", () => {
    expect(refusalMessage(refused, { username: "Username", email: "E-mail" })).toBe(
      "Username: String should match pattern '^\\S+$'. E-mail: String should match pattern '^[^@\\s]+@[^@\\s]+$'.",
    );
    expect(refusalMessage(new ApiError(409, "ROLE_NAME_TAKEN", "Another role is named 'x'"), {})).toBe(
      "Another role is named 'x'",
    );
  });
});
