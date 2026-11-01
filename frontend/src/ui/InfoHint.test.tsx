import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { InfoHint } from "@/ui/InfoHint";

describe("InfoHint", () => {
  const renderHint = () =>
    render(
      <div>
        <InfoHint label="About Map to">Only some records can have this.</InfoHint>
        <button>elsewhere</button>
      </div>,
    );
  const button = () => screen.getByRole("button", { name: "About Map to" });

  it("shows on mouse hover and hides on leave and Escape", async () => {
    renderHint();
    fireEvent.pointerEnter(button(), { pointerType: "mouse" });
    expect(await screen.findByText("Only some records can have this.")).toBeInTheDocument();
    expect(button()).toHaveAttribute("aria-describedby");
    fireEvent.pointerLeave(button(), { pointerType: "mouse" });
    expect(screen.queryByText("Only some records can have this.")).toBeNull();
    fireEvent.pointerEnter(button(), { pointerType: "mouse" });
    await screen.findByText("Only some records can have this.");
    fireEvent.keyDown(document.body, { key: "Escape" });
    expect(screen.queryByText("Only some records can have this.")).toBeNull();
  });

  it("toggles on a tap and closes on a tap elsewhere", async () => {
    renderHint();
    fireEvent.pointerDown(button(), { pointerType: "touch" });
    fireEvent.click(button());
    expect(await screen.findByText("Only some records can have this.")).toBeInTheDocument();
    fireEvent.pointerDown(button(), { pointerType: "touch" });
    fireEvent.click(button());
    expect(screen.queryByText("Only some records can have this.")).toBeNull();
    fireEvent.pointerDown(button(), { pointerType: "touch" });
    fireEvent.click(button());
    await screen.findByText("Only some records can have this.");
    fireEvent.pointerDown(screen.getByRole("button", { name: "elsewhere" }), { pointerType: "touch" });
    expect(screen.queryByText("Only some records can have this.")).toBeNull();
  });
});
