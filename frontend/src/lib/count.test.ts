import { describe, expect, it } from "vitest";
import { count, counted, plural } from "@/lib/count";

describe("counts and plurals", () => {
  it("formats numbers as the browser's locale does and passes strings through", () => {
    expect(count(1234567)).toBe(new Intl.NumberFormat().format(1234567));
    expect(count(1.5)).toBe(new Intl.NumberFormat().format(1.5));
    expect(count("1,000+")).toBe("1,000+");
  });

  it("picks the word for one, and for every other count", () => {
    expect(plural(1, "record")).toBe("record");
    expect(plural(0, "record")).toBe("records");
    expect(plural(2, "person", "people")).toBe("people");
    expect(counted(1, "person", "people")).toBe(`${count(1)} person`);
    expect(counted(2500, "entry", "entries")).toBe(`${count(2500)} entries`);
  });
});
