import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import { proposeRequest, ProposeFields, type ProposeChoice } from "@/features/model-editor/ProposeFields";
import type { AiSystemInfo } from "@/types";

const offer: AiSystemInfo = { configured: true, provider: "anthropic", sendLevel: "samples" };
const label = "Also ask the AI assistant for clearer names";

const sent = () => JSON.parse(screen.getByTestId("request").textContent ?? "null");
function Harness({ assistantOffer }: { assistantOffer?: AiSystemInfo }) {
  const [choice, setChoice] = useState<ProposeChoice>({ mode: "newApplication", applicationName: "Items" });
  return (
    <>
      <ProposeFields value={choice} onChange={setChoice} start assistantOffer={assistantOffer} />
      <output data-testid="request">{JSON.stringify(proposeRequest(choice, Boolean(assistantOffer)))}</output>
    </>
  );
}

describe("New from a workbook › the AI assistant (0.16 AP1)", () => {
  it("shows the choice, checked, with what is sent, and sends it", () => {
    render(<Harness assistantOffer={offer} />);
    const box = screen.getByLabelText(label) as HTMLInputElement;
    expect(box.checked).toBe(true);
    expect(screen.getByText("Sends the sheets' names, headers and first rows to anthropic")).toBeTruthy();
    expect(sent()).toEqual({ mode: "newApplication", applicationName: "Items", assistant: true });
    fireEvent.click(box);
    expect(sent()).toEqual(expect.objectContaining({ assistant: false }));
  });

  it("renders no checkbox and sends no assistant when it is not offered", () => {
    render(<Harness />);
    expect(screen.queryByLabelText(label)).toBeNull();
    expect(sent()).not.toHaveProperty("assistant");
  });

  it("offers nothing when the person will map by hand", () => {
    render(<Harness assistantOffer={offer} />);
    fireEvent.click(screen.getByRole("radio", { name: /Nothing: I will map it by hand/ }));
    expect(screen.queryByLabelText(label)).toBeNull();
  });
});
