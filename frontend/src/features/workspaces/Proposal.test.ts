import { describe, expect, it } from "vitest";
import type { ChangeSet } from "@/types";
import { ownChangeSetText } from "./Proposal";

const changeSet = (name: string | null) => ({ id: "c1", name }) as ChangeSet;

describe("the band's button to the person's change set (0.12 Z5, D324)", () => {
  it("names it and counts its changes once counted", () => {
    expect(ownChangeSetText({})).toBeUndefined();
    expect(ownChangeSetText({ changeSet: changeSet("Spring") })).toBe("Your change set: Spring");
    expect(ownChangeSetText({ changeSet: changeSet("Spring"), changes: 1 })).toBe("Your change set: Spring · 1 change");
    expect(ownChangeSetText({ changeSet: changeSet(null), changes: 3 })).toBe(
      "Your change set: Untitled change set · 3 changes",
    );
  });
});
