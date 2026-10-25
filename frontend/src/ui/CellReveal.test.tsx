// @vitest-environment jsdom
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useCellReveal } from "@/ui/CellReveal";

/** Makes an element report a content width wider (or not) than its box, as a cut-off cell does. */
function widths(element: HTMLElement, scroll: number, client: number) {
  Object.defineProperty(element, "scrollWidth", { configurable: true, value: scroll });
  Object.defineProperty(element, "clientWidth", { configurable: true, value: client });
}

function Table() {
  const reveal = useCellReveal();
  return (
    <>
      <table>
        <tbody {...reveal.handlers}>
          <tr>
            <td data-reveal="" data-testid="cut">
              Codelist, Master value, System, System group, Language, Translation group
            </td>
            <td data-reveal="" data-testid="fits">
              Text
            </td>
            <td data-reveal="" data-testid="labelled">
              <span className="visually-hidden">Edit Shared with:</span> Codelist, Master value, System group
            </td>
            <td data-reveal="" data-testid="link">
              <button type="button">A very long linked name that the column cuts</button>
            </td>
            <td data-reveal="" data-testid="editing">
              <form aria-label="Edit Cardinality">
                <select aria-label="Cardinality" defaultValue="one">
                  <option value="one">One to one</option>
                </select>
              </form>
            </td>
          </tr>
        </tbody>
      </table>
      {reveal.overlay}
    </>
  );
}

const box = () => document.querySelector(".cell-reveal");

afterEach(() => vi.restoreAllMocks());

describe("a cut-off cell's whole value (CellReveal)", () => {
  it("shows the whole value on hover, wrapped, and only for a cell the column cuts", () => {
    render(<Table />);
    widths(screen.getByTestId("cut"), 600, 200);
    widths(screen.getByTestId("fits"), 40, 200);
    fireEvent.pointerOver(screen.getByTestId("fits"), { pointerType: "mouse" });
    expect(box()).toBeNull();
    fireEvent.pointerOver(screen.getByTestId("cut"), { pointerType: "mouse" });
    expect(box()?.textContent).toBe("Codelist, Master value, System, System group, Language, Translation group");
    expect(box()?.getAttribute("aria-hidden")).toBe("true");
    fireEvent.keyDown(window, { key: "Escape" });
    expect(box()).toBeNull();
  });

  it("on a touch screen, a tap on the text toggles it and a long press shows it", () => {
    render(<Table />);
    widths(screen.getByTestId("cut"), 600, 200);
    fireEvent.pointerUp(screen.getByTestId("cut"), { pointerType: "touch" });
    expect(box()).not.toBeNull();
    fireEvent.pointerUp(screen.getByTestId("cut"), { pointerType: "touch" });
    expect(box()).toBeNull();
    const longPress = fireEvent.contextMenu(screen.getByTestId("cut"));
    expect(longPress).toBe(false); // the browser's own menu is not opened
    expect(box()).not.toBeNull();
  });

  it("leaves a tap on a link or button in the cell to that control", () => {
    render(<Table />);
    const link = screen.getByTestId("link");
    widths(link, 600, 200);
    fireEvent.pointerUp(screen.getByRole("button"), { pointerType: "touch" });
    expect(box()).toBeNull();
    fireEvent.focus(screen.getByRole("button"));
    expect(box()?.textContent).toBe("A very long linked name that the column cuts");
  });

  it("shows nothing over a cell being edited in place", () => {
    render(<Table />);
    widths(screen.getByTestId("editing"), 600, 200);
    fireEvent.focus(screen.getByLabelText("Cardinality"));
    fireEvent.pointerOver(screen.getByTestId("editing"), { pointerType: "mouse" });
    expect(box()).toBeNull();
  });

  it("shows only what a reader sees, not words for assistive technology", () => {
    render(<Table />);
    widths(screen.getByTestId("labelled"), 600, 200);
    fireEvent.pointerOver(screen.getByTestId("labelled"), { pointerType: "mouse" });
    expect(box()?.textContent).toBe("Codelist, Master value, System group");
  });

  it("shows nothing for a cell passing under a still pointer while the list scrolls (0.12 LS1, D373)", () => {
    render(<Table />);
    widths(screen.getByTestId("cut"), 600, 200);
    fireEvent.scroll(window);
    fireEvent.pointerOver(screen.getByTestId("cut"), { pointerType: "mouse" });
    expect(box()).toBeNull();
    // Once the list is still, the pointer's own movement shows it.
    const later = performance.now() + 1000;
    vi.spyOn(performance, "now").mockReturnValue(later);
    fireEvent.pointerMove(screen.getByTestId("cut"), { pointerType: "mouse" });
    expect(box()?.textContent).toBe("Codelist, Master value, System, System group, Language, Translation group");
  });
});
