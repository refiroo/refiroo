import { describe, expect, it } from "vitest";
import { list, presentText, record, stringList, text, trimmedText } from "@/lib/coerce";

describe("coercing a value of unknown shape", () => {
  it("reads text, trimmed text and present text apart", () => {
    expect([text("  a "), text(3), text(null)]).toEqual(["  a ", "", ""]);
    expect([trimmedText("  a "), trimmedText(3)]).toEqual(["a", ""]);
    expect([presentText("a"), presentText(""), presentText(undefined)]).toEqual(["a", undefined, undefined]);
  });

  it("reads lists and records, an array being no record", () => {
    expect([list([1]), list("x"), stringList(["a"]), stringList({})]).toEqual([[1], [], ["a"], []]);
    expect([record({ a: 1 }), record([1]), record(null)]).toEqual([{ a: 1 }, {}, {}]);
  });
});
