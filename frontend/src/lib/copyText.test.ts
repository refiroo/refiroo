import { afterEach, describe, expect, it, vi } from "vitest";
import { copyText } from "@/lib/copyText";

describe("copyText", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("answers true once the text is on the clipboard", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    expect(await copyText("abc")).toBe(true);
    expect(writeText).toHaveBeenCalledWith("abc");
  });

  it("answers false when there is no clipboard or the write is refused", async () => {
    vi.stubGlobal("navigator", {});
    expect(await copyText("abc")).toBe(false);
    vi.stubGlobal("navigator", { clipboard: { writeText: vi.fn().mockRejectedValue(new Error("denied")) } });
    expect(await copyText("abc")).toBe(false);
  });
});
