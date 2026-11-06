import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AssistantText } from "./AssistantText";

describe("AssistantText", () => {
  it("reads paragraphs, bold and dash lists, and never HTML", () => {
    render(<AssistantText text={"**Done.** It adds <b>two</b> types:\n- Line\n- Platform\n\nSecond paragraph."} />);
    expect(screen.getByText("Done.").tagName).toBe("STRONG");
    expect(screen.getAllByRole("listitem").map((item) => item.textContent)).toEqual(["Line", "Platform"]);
    expect(screen.getByText(/It adds <b>two<\/b> types:/)).toBeInTheDocument();
    expect(screen.getByText("Second paragraph.").tagName).toBe("P");
  });
});
