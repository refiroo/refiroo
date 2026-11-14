import { describe, expect, it } from "vitest";
import { initials } from "./SettingsParts";

// The one `initials`: the top bar, People's rows, a workspace's Access list and every `NameMark`
// (people and clients) read it (0.17.2 FX1, D5).
describe("initials", () => {
  it("takes the first letter of the first and last words", () => {
    expect(initials("Ada Lovelace")).toBe("AL");
    expect(initials("Mary Ann Smith")).toBe("MS");
  });

  it("gives one letter for a one-word name", () => {
    expect(initials("Admin")).toBe("A");
  });

  it("counts letters only, so a digit leading a word does not stand for it", () => {
    expect(initials("2nd line")).toBe("NL");
  });

  it("leaves a bracketed note out of the name", () => {
    expect(initials("Name (temporary)")).toBe("N");
    expect(initials("Ada (temp) Lovelace")).toBe("AL");
  });

  it("keeps the letters of a name that is only a bracketed note", () => {
    expect(initials("(temporary)")).toBe("T");
  });

  it("falls back on the first characters of a name with no letter, so a client named 42 keeps its mark", () => {
    expect(initials("42")).toBe("42");
    expect(initials("  7-1 ")).toBe("7-");
    expect(initials("")).toBe("");
  });
});
