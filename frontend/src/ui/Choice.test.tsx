import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Choice } from "@/ui/Choice";

describe("the segmented choice (0.9 K6a, D166)", () => {
  it("takes any number of options, each optionally with a glyph", () => {
    const onChange = vi.fn();
    const { container, rerender } = render(
      <Choice
        name="two"
        value="set"
        options={[
          ["set", "Set to"],
          ["clear", "Clear"],
        ]}
        onChange={onChange}
      />,
    );
    expect(screen.getAllByRole("radio")).toHaveLength(2);
    rerender(
      <Choice
        name="four"
        value="add"
        options={[
          ["add", "Add", "plus"],
          ["remove", "Remove", "minus"],
          ["replace", "Replace with", "replace"],
          ["clear", "Clear", "close"],
        ]}
        onChange={onChange}
      />,
    );
    expect(screen.getAllByRole("radio")).toHaveLength(4);
    expect(container.querySelectorAll("label svg")).toHaveLength(4);
    expect(screen.getByRole("radio", { name: "Add" })).toBeChecked();
    fireEvent.click(screen.getByRole("radio", { name: "Remove" }));
    expect(onChange).toHaveBeenLastCalledWith("remove");
  });
});
