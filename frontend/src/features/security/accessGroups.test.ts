import { describe, expect, it } from "vitest";
import type { Grant } from "@/types";
import { chipHue, groupByPrincipal, narrowingShort } from "./accessGroups";

const grant = (id: string, principalId: string, roleKey: string | null, extra: Partial<Grant["scope"]> = {}) =>
  ({
    id,
    principal: { kind: "user", id: principalId, name: principalId },
    role: roleKey ? { key: roleKey, name: roleKey } : null,
    consumerApi: roleKey ? null : { key: "api", name: "api" },
    scope: {
      instance: false,
      workspaceKey: "w",
      applications: [],
      recordTypes: [],
      applicationNames: [],
      recordTypeNames: [],
      ...extra,
    },
  }) as unknown as Grant;

describe("groupByPrincipal", () => {
  it("merges adjacent grants of a principal, also across page boundaries", () => {
    const firstPage = [grant("1", "a", "reader"), grant("2", "b", "reader"), grant("3", "b", "steward")];
    const secondPage = [grant("4", "b", "owner"), grant("5", "c", "reader")];
    const rows = groupByPrincipal([...firstPage, ...secondPage]);
    expect(rows.map((row) => [row.principal.id, row.grants.length])).toEqual([
      ["a", 1],
      ["b", 3],
      ["c", 1],
    ]);
  });
  it("keeps a person and a group with the same id apart", () => {
    const group = { ...grant("2", "a", "reader"), principal: { kind: "group", id: "a", name: "a" } } as Grant;
    expect(groupByPrincipal([grant("1", "a", "reader"), group])).toHaveLength(2);
  });
});

describe("chipHue", () => {
  it("colours by the kind of role", () => {
    expect(chipHue(grant("1", "a", "reader"))).toBe(8);
    expect(chipHue(grant("1", "a", "security-admin"))).toBe(3);
    expect(chipHue(grant("1", "a", null))).toBe(2);
    expect(chipHue(grant("1", "a", "custom-role"))).toBe("neutral");
  });
});

describe("narrowingShort", () => {
  it("shortens to two names and a count", () => {
    expect(
      narrowingShort(grant("1", "a", "steward", { applicationNames: ["A", "B"], recordTypeNames: ["C", "D"] })),
    ).toBe("A, B +2");
    expect(narrowingShort(grant("1", "a", "steward"))).toBe("");
  });
});
