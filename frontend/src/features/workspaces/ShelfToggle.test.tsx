import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ShelfToggle } from "@/features/workspaces/ShelfToggle";

const toggle = (workspaceKey = "stops") => (
  <ShelfToggle workspaceKey={workspaceKey} applicationKey="test-app" viewKey="domains" name="Domains" />
);

const stored = new Map<string, string>();
const read = (key: string) => JSON.parse(stored.get(key) ?? "[]") as unknown;

describe("ShelfToggle (0.17 UX1)", () => {
  // Node 26 leaves `localStorage` undefined in jsdom: the shelf is kept in a stand-in the test can read.
  beforeEach(() => {
    stored.clear();
    vi.stubGlobal("localStorage", {
      getItem: (key: string) => stored.get(key) ?? null,
      setItem: (key: string, value: string) => stored.set(key, value),
      removeItem: (key: string) => stored.delete(key),
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  it("is not pressed for a list off the shelf, and a press adds it", () => {
    render(toggle());
    const button = screen.getByRole("button", { name: "Add Domains to your shelf" });
    expect(button).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(button);
    const pressed = screen.getByRole("button", { name: "Take Domains off your shelf" });
    expect(pressed).toHaveAttribute("aria-pressed", "true");
    expect(read("rdm:workspace-pins:v1:stops")).toEqual([{ applicationKey: "test-app", viewKey: "domains" }]);
  });

  it("takes the list off the shelf with another press", () => {
    render(toggle());
    fireEvent.click(screen.getByRole("button", { name: "Add Domains to your shelf" }));
    fireEvent.click(screen.getByRole("button", { name: "Take Domains off your shelf" }));
    expect(screen.getByRole("button", { name: "Add Domains to your shelf" })).toHaveAttribute("aria-pressed", "false");
    expect(read("rdm:workspace-pins:v1:stops")).toEqual([]);
  });

  it("starts pressed when the stored shelf already holds the list, per workspace", () => {
    stored.set("rdm:workspace-pins:v1:stops", JSON.stringify([{ applicationKey: "test-app", viewKey: "domains" }]));
    const stops = render(toggle("stops"));
    expect(screen.getByRole("button", { name: "Take Domains off your shelf" })).toHaveAttribute("aria-pressed", "true");
    stops.unmount();
    render(toggle("other"));
    expect(screen.getByRole("button", { name: "Add Domains to your shelf" })).toHaveAttribute("aria-pressed", "false");
  });
});
