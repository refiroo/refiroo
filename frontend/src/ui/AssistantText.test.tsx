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

  it("reads a markdown table as a table, its cells as text", () => {
    render(
      <AssistantText
        text={"The load:\n\n| Result | Count |\n|---|---|\n| New **records** | 172 |\n| <i>Bad</i> | 3 |\n\nDone."}
      />,
    );
    const table = screen.getByRole("table");
    expect(screen.getAllByRole("columnheader").map((cell) => cell.textContent)).toEqual(["Result", "Count"]);
    expect(screen.getByText("records").tagName).toBe("STRONG");
    expect(screen.getByText("172")).toHaveAttribute("data-label", "Count");
    expect(screen.getByText("<i>Bad</i>")).toBeInTheDocument();
    expect(table.querySelectorAll("tbody tr")).toHaveLength(2);
    expect(screen.getByText("Done.").tagName).toBe("P");
    expect(screen.queryByText(/---/)).toBeNull();
  });
});
