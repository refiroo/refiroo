import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SearchMenu } from "@/ui/SearchMenu";

const items = [
  { id: "a", label: "Country", hue: 1 as const, icon: "folder" },
  { id: "b", label: "Currency", hue: 2 as const },
];

describe("SearchMenu", () => {
  it("adds one thing from the list as before, with no choice shown", () => {
    const onSelect = vi.fn();
    render(<SearchMenu label="Add filter" items={items} onSelect={onSelect} />);
    fireEvent.click(screen.getByRole("button", { name: "Add filter" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Currency" }));
    expect(onSelect).toHaveBeenCalledWith("b");
  });

  it("with a selected id shows the choice on the button and ticks it in the list, each item in its tile", async () => {
    const onSelect = vi.fn();
    render(<SearchMenu label="Object type" items={items} selected="a" onSelect={onSelect} />);
    const button = screen.getByRole("button", { name: "Object type: Country" });
    expect(button.querySelector(".hue-tile")).toHaveAttribute("data-hue", "1");
    fireEvent.click(button);
    const list = await screen.findByRole("menu");
    const [country, currency] = within(list).getAllByRole("menuitemradio");
    expect(country).toHaveAttribute("aria-checked", "true");
    expect(country.querySelector(".picker-tick")).not.toBeNull();
    expect(currency).toHaveAttribute("aria-checked", "false");
    expect(currency.querySelector(".hue-tile")).toHaveAttribute("data-hue", "2");
    fireEvent.click(currency);
    expect(onSelect).toHaveBeenCalledWith("b");
  });

  it("closes with one Escape in either mode, the choice kept", async () => {
    const onSelect = vi.fn();
    render(<SearchMenu label="Object type" items={items} selected="a" onSelect={onSelect} />);
    fireEvent.click(screen.getByRole("button", { name: "Object type: Country" }));
    await screen.findByRole("menu");
    fireEvent.keyDown(document.activeElement as Element, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("menu")).not.toBeInTheDocument());
    expect(onSelect).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Object type: Country" })).toBeInTheDocument();
  });
});
