import { act, fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DebouncedSearchField } from "@/ui/SearchField";

/** A list whose search lives outside the box, as the URL holds it. */
function List({ initial = "" }: { initial?: string }) {
  const [search, setSearch] = useState(initial);
  return (
    <>
      <DebouncedSearchField appliedValue={search} onApply={setSearch} placeholder="Search countries" />
      <output aria-label="applied">{search}</output>
      <button onClick={() => setSearch("")}>Clear search</button>
    </>
  );
}

const box = () => screen.getByPlaceholderText("Search countries") as HTMLInputElement;

describe("DebouncedSearchField", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("keeps focus and text while typing slowly, each pause applying the search", () => {
    render(<List initial="fra" />);
    const input = box();
    input.focus();
    fireEvent.change(input, { target: { value: "fr" } });
    act(() => vi.advanceTimersByTime(300));
    expect(screen.getByLabelText("applied").textContent).toBe("fr");
    expect(box()).toBe(input);
    expect(document.activeElement).toBe(input);
    fireEvent.change(input, { target: { value: "fra " } });
    act(() => vi.advanceTimersByTime(300));
    expect(screen.getByLabelText("applied").textContent).toBe("fra");
    expect(input.value).toBe("fra ");
    expect(document.activeElement).toBe(input);
  });

  it("shows a search changed outside the box", () => {
    render(<List />);
    fireEvent.change(box(), { target: { value: "ger" } });
    act(() => vi.advanceTimersByTime(300));
    fireEvent.click(screen.getByText("Clear search"));
    expect(box().value).toBe("");
    act(() => vi.advanceTimersByTime(300));
    expect(screen.getByLabelText("applied").textContent).toBe("");
  });
});
