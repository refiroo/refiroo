import { describe, expect, it } from "vitest";
import { permissionsFixture } from "@/test/permissions";
import { holds, recordWrites } from "./permissions";

const ref = (applicationKey: string, objectTypeKey: string) => ({ applicationKey, objectTypeKey });

describe("recordWrites (0.12 Z5, D329)", () => {
  it("allows every record when the group is held unnarrowed", () => {
    const writes = recordWrites(permissionsFixture("w", ["edit-live"]), "edit-live");
    expect(writes.any).toBe(true);
    expect(writes.permits("any-app", "any-type")).toBe(true);
    expect(writes.narrowing).toBeUndefined();
  });

  it("allows nothing when the group is not held, or nothing was read", () => {
    for (const permissions of [permissionsFixture("w", ["browse", "change-sets"]), undefined]) {
      const writes = recordWrites(permissions, "edit-live");
      expect(writes.any).toBe(false);
      expect(writes.permits("app", "type")).toBe(false);
      expect(writes.permitsRelation(ref("app", "a"), ref("app", "b"))).toBe(false);
    }
  });

  it("narrowed to record types: those types in any application, no other", () => {
    const writes = recordWrites(permissionsFixture("w", ["edit-live"], { recordTypes: ["a"] }), "edit-live");
    expect(writes.any).toBe(true);
    expect(writes.permits("one", "a")).toBe(true);
    expect(writes.permits("two", "a")).toBe(true);
    expect(writes.permits("one", "b")).toBe(false);
    expect(writes.permitsType("a")).toBe(true);
    expect(writes.permitsType("b")).toBe(false);
    expect(writes.narrowing).toEqual({ applications: [], recordTypes: ["a"] });
  });

  it("narrowed to an application: its records of every type, none elsewhere; a type alone does not say", () => {
    const writes = recordWrites(permissionsFixture("w", ["change-sets"], { applications: ["one"] }), "change-sets");
    expect(writes.permits("one", "b")).toBe(true);
    expect(writes.permits("two", "b")).toBe(false);
    expect(writes.permitsType("b")).toBe(false);
  });

  it("a relationship passes when either end is permitted (D291)", () => {
    const writes = recordWrites(permissionsFixture("w", ["edit-live"], { recordTypes: ["a"] }), "edit-live");
    expect(writes.permitsRelation(ref("x", "a"), ref("x", "b"))).toBe(true);
    expect(writes.permitsRelation(ref("x", "b"), ref("x", "a"))).toBe(true);
    expect(writes.permitsRelation(ref("x", "b"), ref("x", "c"))).toBe(false);
  });

  it("each group has its own narrowing: live and change-set writes are told apart (D231, D244)", () => {
    const contributor = permissionsFixture("w", ["browse", "change-sets"]);
    expect(recordWrites(contributor, "edit-live").any).toBe(false);
    expect(recordWrites(contributor, "change-sets").any).toBe(true);
  });
});

describe("holds", () => {
  it("holds only what was read, nothing while unknown", () => {
    const reader = permissionsFixture("w", ["browse"]);
    expect(holds(reader, "browse")).toBe(true);
    expect(holds(reader, "publish")).toBe(false);
    expect(holds(undefined, "browse")).toBe(false);
    expect(holds(undefined, "publish")).toBe(false);
  });
});
