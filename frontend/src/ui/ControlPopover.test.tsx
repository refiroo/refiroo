import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ControlPopover } from "@/ui/ControlPopover";
import { ComboBoxField } from "@/ui/Selection";

const options = [
  { id: "north", label: "North" },
  { id: "south", label: "South" },
];

describe("ControlPopover", () => {
  it("keeps a choice made in a list opened from inside it (0.11 M6: the phone band's workspace)", async () => {
    const onSelect = vi.fn();
    render(
      <ControlPopover label="Workspace: North" trigger="North">
        <ComboBoxField
          label="Workspace"
          value="North"
          options={options}
          onChange={() => undefined}
          onSelect={onSelect}
        />
      </ControlPopover>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Workspace: North" }));
    fireEvent.click(await screen.findByRole("button", { name: /^Show workspace options/ }));
    const option = await screen.findByRole("option", { name: "South" });
    // A tap: the press starts on the option, outside the popover's own element.
    fireEvent.pointerDown(option);
    fireEvent.click(option);

    expect(onSelect).toHaveBeenCalledWith("south");
  });

  it("still closes on a press outside it", async () => {
    render(
      <>
        <button type="button">Elsewhere</button>
        <ControlPopover label="Settings">
          <p>Inside</p>
        </ControlPopover>
      </>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Settings" }));
    await screen.findByText("Inside");
    fireEvent.pointerDown(screen.getByRole("button", { name: "Elsewhere" }));

    expect(screen.queryByText("Inside")).not.toBeInTheDocument();
  });
});
