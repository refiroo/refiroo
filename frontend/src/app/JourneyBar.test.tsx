import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { JourneyBar } from "./JourneyBar";

const steps = [
  { key: "a", label: "File and words", status: "done" as const },
  { key: "b", label: "Check", status: "current" as const },
  { key: "c", label: "Load", status: "todo" as const },
];

describe("JourneyBar", () => {
  it("lists the steps, marks the current one and runs its buttons", () => {
    const primary = vi.fn();
    const back = vi.fn();
    const stop = vi.fn();
    render(
      <JourneyBar
        label="Import with the assistant"
        steps={steps}
        sentence="Checking every row."
        primary={{ label: "Show progress", onClick: primary }}
        back={{ label: "Back to the import", onClick: back }}
        stop={{ label: "Stop", onClick: stop }}
      />,
    );
    const bar = screen.getByRole("navigation", { name: "Import with the assistant" });
    const items = within(within(bar).getByRole("list")).getAllByRole("listitem");
    expect(items).toHaveLength(3);
    expect(items[1]).toHaveAttribute("aria-current", "step");
    expect(items[0]).not.toHaveAttribute("aria-current");
    expect(within(bar).getByText("Step 2 of 3: Check")).toBeInTheDocument();
    expect(within(bar).getByText("Checking every row.")).toBeInTheDocument();
    fireEvent.click(within(bar).getByRole("button", { name: "Show progress" }));
    fireEvent.click(within(bar).getByRole("button", { name: "Back to the import" }));
    fireEvent.click(within(bar).getByRole("button", { name: "Stop" }));
    expect([primary, back, stop].map((fn) => fn.mock.calls.length)).toEqual([1, 1, 1]);
  });

  it("shows only the buttons it is given", () => {
    render(<JourneyBar label="Import" steps={steps} sentence="Waiting." />);
    expect(screen.queryByRole("button")).toBeNull();
  });
});
