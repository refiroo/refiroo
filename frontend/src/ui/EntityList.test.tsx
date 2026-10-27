import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { EntityList, type EntityGroup } from "@/ui/EntityList";
import { TrailBar, TrailLink } from "@/ui/TrailBar";

const row = (key: string, title: string, onOpen = vi.fn()) => ({
  key,
  title,
  subtitle: `${key} · sub`,
  icon: "workspace" as const,
  onOpen,
});

function show(groups: EntityGroup[], search = "", onSearch = vi.fn()) {
  render(<EntityList label="things" groups={groups} search={search} onSearch={onSearch} empty="Nothing here." />);
  return onSearch;
}

afterEach(() => vi.unstubAllGlobals());

describe("EntityList", () => {
  it("lists groups with counts, leaves empty groups out and opens a row", () => {
    const onOpen = vi.fn();
    show([
      { key: "a", title: "Active", count: 2, rows: [row("one", "One", onOpen), row("two", "Two")] },
      { key: "r", title: "Retired", count: 0, rows: [] },
    ]);
    const active = screen.getByRole("region", { name: "Active" });
    expect(active).toHaveTextContent("Active · 2");
    expect(screen.queryByRole("region", { name: "Retired" })).not.toBeInTheDocument();
    fireEvent.click(within(active).getByRole("button", { name: /One/ }));
    expect(onOpen).toHaveBeenCalledTimes(1);
  });

  it("shows labelled facts that belong to the row's accessible name", () => {
    show([
      {
        key: "a",
        title: "Active",
        count: 1,
        rows: [
          {
            ...row("one", "One"),
            facts: [
              { label: "Model", value: "Starter" },
              { label: "Release", value: "0.3.0", mono: true },
            ],
          },
          row("two", "Two"),
        ],
      },
    ]);
    const first = screen.getByRole("button", { name: /One/ });
    expect(first).toHaveAccessibleName(expect.stringContaining("Model: Starter, Release: 0.3.0"));
    // The labels are shown once, in the group's heading, and stay in the row for a screen reader.
    const heading = screen.getByRole("heading", { name: "Active · 1" });
    expect(within(heading).getByText("Model")).toBeInTheDocument();
    expect(within(heading).getByText("Release")).toBeInTheDocument();
    expect(screen.getAllByText("Model")).toHaveLength(2);
    expect(within(first).getByText("Starter")).toHaveAttribute("title", "Starter");
    expect(within(first).getByText("0.3.0")).toHaveClass("mono");
    expect(first.querySelector("button, a, dl")).toBeNull();
    expect(screen.getByRole("button", { name: /Two/ }).querySelector(".entity-facts")).toBeNull();
  });

  it("shows placeholders, an error with Retry, and the empty text once everything is settled", () => {
    const retry = vi.fn();
    show([
      { key: "a", title: "Active", count: 0, rows: [], loading: true },
      { key: "b", title: "Other", count: 0, rows: [], error: "Unavailable", onRetry: retry },
    ]);
    expect(screen.getByRole("status", { name: "Loading active things" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(retry).toHaveBeenCalled();
    expect(screen.queryByText("Nothing here.")).not.toBeInTheDocument();
  });

  it("says so when nothing is listed", () => {
    show([{ key: "a", title: "Active", count: 0, rows: [] }]);
    expect(screen.getByText("Nothing here.")).toBeInTheDocument();
  });

  it("reports the search text", () => {
    const onSearch = show([{ key: "a", title: "Active", count: 1, rows: [row("one", "One")] }]);
    fireEvent.change(screen.getByRole("searchbox", { name: "Search things" }), { target: { value: "x" } });
    expect(onSearch).toHaveBeenCalledWith("x");
  });

  it("calls onEnd when the end of a group scrolls into view", () => {
    let callback: IntersectionObserverCallback = () => undefined;
    class Observer {
      constructor(next: IntersectionObserverCallback) {
        callback = next;
      }
      observe() {}
      disconnect() {}
    }
    vi.stubGlobal("IntersectionObserver", Observer);
    const onEnd = vi.fn();
    show([{ key: "a", title: "Active", count: "1+", rows: [row("one", "One")], onEnd }]);
    callback([{ isIntersecting: false } as IntersectionObserverEntry], {} as IntersectionObserver);
    expect(onEnd).not.toHaveBeenCalled();
    callback([{ isIntersecting: true } as IntersectionObserverEntry], {} as IntersectionObserver);
    expect(onEnd).toHaveBeenCalledTimes(1);
  });

  it("steps through the search box and the rows with the arrow keys", () => {
    show([{ key: "a", title: "Active", count: 2, rows: [row("one", "One"), row("two", "Two")] }]);
    const search = screen.getByRole("searchbox");
    search.focus();
    fireEvent.keyDown(search, { key: "ArrowDown" });
    const one = screen.getByRole("button", { name: /One/ });
    expect(one).toHaveFocus();
    fireEvent.keyDown(one, { key: "ArrowDown" });
    expect(screen.getByRole("button", { name: /Two/ })).toHaveFocus();
    fireEvent.keyDown(screen.getByRole("button", { name: /Two/ }), { key: "ArrowUp" });
    expect(one).toHaveFocus();
  });
});

describe("TrailBar", () => {
  it("has a back button and a trail whose last item is the page", () => {
    const back = vi.fn();
    const up = vi.fn();
    render(
      <TrailBar
        back={{ label: "← All things", onClick: back }}
        trail={[<TrailLink onClick={up}>Things</TrailLink>, "Thing one"]}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "← All things" }));
    fireEvent.click(screen.getByRole("button", { name: "Things" }));
    expect(back).toHaveBeenCalled();
    expect(up).toHaveBeenCalled();
    expect(screen.getByText("Thing one")).toHaveAttribute("aria-current", "page");
  });
});
