import { describe, expect, it } from "vitest";
import { outlineFixture } from "@/test/draftOutline";
import { matchOptions } from "@/features/model-editor/consumer";

describe("an XREF rule's fields (found 2026-10-19)", () => {
  it("lists a field several exposed types share once, under no one type's name", () => {
    const options = matchOptions(outlineFixture(), {}, { verb: "under", types: ["area", "shelf"] });
    expect(options.filter((option) => option.value === "code")).toEqual([
      { value: "code", label: "Code", group: "Attributes of the exposed types" },
    ]);
  });
});
