import { describe, expect, it } from "vitest";
import { outlineFixture } from "@/test/draftOutline";
import { ancestorTypeKeys } from "@/model/outline";
import type { ModelDraftOutline } from "@/types";

/** Types `a` -> `b` -> `c` -> `a`, each with the parents given. */
function cycle(): ModelDraftOutline {
  const outline = outlineFixture();
  const type = (key: string, parents: string[]) => ({
    key,
    name: key,
    pluralName: `${key}s`,
    rootCreatable: false,
    parents,
    attributes: [],
    mark: "released" as const,
  });
  return { ...outline, objectTypes: [type("a", ["b"]), type("b", ["c"]), type("c", ["a"])] };
}

describe("ancestorTypeKeys", () => {
  it("leaves the start type out of its ancestors in a cycle, in either order", () => {
    expect(ancestorTypeKeys(cycle(), "a")).toEqual(["b", "c"]);
    expect(ancestorTypeKeys(cycle(), "a", { depthFirst: true })).toEqual(["b", "c"]);
  });

  it("lists the start type when asked, as a type in a cycle is its own ancestor", () => {
    expect(ancestorTypeKeys(cycle(), "a", { startInCycle: true })).toEqual(["b", "c", "a"]);
    expect(ancestorTypeKeys(cycle(), "a", { startInCycle: true, depthFirst: true })).toEqual(["b", "c", "a"]);
  });
});
