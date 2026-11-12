import { createEvent, fireEvent, render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { outlineFixture } from "@/test/draftOutline";
import { CanvasBoard, DRAG_COLUMN, DRAG_SHEET } from "./CanvasBoard";

function board() {
  const onColumnToSpace = vi.fn();
  const onSheetToSpace = vi.fn();
  const { container } = render(
    <CanvasBoard
      cards={[]}
      lines={[]}
      positions={{}}
      figures={{ byType: {} } as never}
      outline={outlineFixture()}
      onOperation={vi.fn()}
      editable
      canDrag
      busy={false}
      onSelect={vi.fn()}
      onMove={vi.fn()}
      onColumnDrop={vi.fn()}
      onColumnToSpace={onColumnToSpace}
      onSheetToSpace={onSheetToSpace}
      onConnect={vi.fn()}
      onConnectMenu={vi.fn()}
      onFilter={vi.fn()}
      onRemoveLine={vi.fn()}
      onRefused={vi.fn()}
      menuFor={() => []}
    />,
  );
  const surface = container.querySelector(".canvas-surface") as HTMLElement;
  // The board is scrolled: the surface's top-left is above and left of the visible area.
  surface.getBoundingClientRect = () => ({ left: -40, top: -30, right: 0, bottom: 0, width: 0, height: 0 }) as DOMRect;
  return { surface, container, onColumnToSpace, onSheetToSpace };
}

/** A drop at a point: jsdom has no DragEvent, so the point is put on the event. */
function dropAt(target: HTMLElement, drag: object, clientX: number, clientY: number) {
  const event = createEvent.drop(target, drag);
  Object.defineProperty(event, "clientX", { value: clientX });
  Object.defineProperty(event, "clientY", { value: clientY });
  fireEvent(target, event);
}

const dragOf = (type: string, value: string) => ({
  dataTransfer: { types: [type], getData: (asked: string) => (asked === type ? value : "") },
});

describe("a drop on the empty board", () => {
  it("places a sheet's card at the drop point, in the surface's own coordinates after a scroll", () => {
    const { container, onSheetToSpace } = board();
    dropAt(container.querySelector(".canvas-board") as HTMLElement, dragOf(DRAG_SHEET, "Shelves"), 300, 200);
    expect(onSheetToSpace).toHaveBeenCalledWith("Shelves", { x: 340, y: 230 });
  });

  it("never places a card nearer the corner than the board's edge, wherever it is dropped", () => {
    const { container, onColumnToSpace, onSheetToSpace } = board();
    const target = container.querySelector(".canvas-board") as HTMLElement;
    dropAt(target, dragOf(DRAG_SHEET, "Shelves"), -100, -100);
    expect(onSheetToSpace).toHaveBeenCalledWith("Shelves", { x: 24, y: 52 });
    dropAt(target, dragOf(DRAG_COLUMN, "Shelves\u0000Area"), 45, 31);
    expect(onColumnToSpace).toHaveBeenCalledWith(expect.anything(), { x: 85, y: 61 });
    dropAt(target, dragOf(DRAG_COLUMN, "Shelves\u0000Area"), 0, 0);
    expect(onColumnToSpace).toHaveBeenLastCalledWith(expect.anything(), { x: 40, y: 52 });
    dropAt(target, dragOf(DRAG_COLUMN, "Shelves\u0000Area"), -35, -25);
    expect(onColumnToSpace).toHaveBeenLastCalledWith(expect.anything(), { x: 24, y: 52 });
  });
});
