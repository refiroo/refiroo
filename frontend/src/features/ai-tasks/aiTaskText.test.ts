import { describe, expect, it } from "vitest";
import { cutAtWord, taskTitle } from "./aiTaskText";

describe("taskTitle", () => {
  const words = "can you move the objecttypes and objects under th person group in the person application please";

  it("uses the title the session wrote, over the words", () => {
    expect(taskTitle({ fileName: "", words, title: "Move types under the person group" })).toBe(
      "Move types under the person group",
    );
  });

  it("keeps a file name first", () => {
    expect(taskTitle({ fileName: "Leads.xlsx", words, title: "A title" })).toBe("Leads.xlsx");
  });

  it("cuts the words at a word boundary, never mid-word, until there is a title", () => {
    const named = taskTitle({ fileName: "", words, title: null });
    expect(named.endsWith("…")).toBe(true);
    expect(named.length).toBeLessThanOrEqual(80);
    expect(words.startsWith(named.slice(0, -1))).toBe(true);
    expect(words.charAt(named.length - 1)).toBe(" ");
  });

  it("names a task with no words an instruction", () => {
    expect(taskTitle({ fileName: "", words: null, title: null })).toBe("Instruction");
  });
});

describe("cutAtWord", () => {
  it("leaves a short text as it is", () => {
    expect(cutAtWord("  move   it ", 80)).toBe("move it");
  });
  it("cuts a word longer than the limit at the limit", () => {
    expect(cutAtWord("x".repeat(100), 10)).toBe("xxxxxxxxx…");
  });
});
