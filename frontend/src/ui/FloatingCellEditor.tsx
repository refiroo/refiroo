/**
 * A table cell's open editor as a layer over the cell instead of in it, for a table whose columns
 * and rows must not move while a value is edited (the relation matrix cell's table). The cell keeps
 * its value in place (hidden from assistive technology, since the editor holds the same value), and
 * the editor floats with its top left on the cell's, at least as wide as the cell, above the cells
 * beside it. It is fixed to the window, so the table's scroll container and its last row do not cut
 * it off, and it follows the cell when anything scrolls. It stays in the cell's place in the React
 * tree and the DOM, so focus, Enter and Escape, and a form's "focus left the form" read as they do
 * in the cell.
 */

import { useLayoutEffect, useRef, type ReactNode } from "react";

const MARGIN = 8;

export function FloatingCellEditor({
  value,
  onOutside,
  children,
}: {
  /** What the cell keeps showing under the layer; none where the cell shows it itself (a notice's layer). */
  value?: ReactNode;
  /** A press anywhere outside the layer, the cell's own value included. */
  onOutside?: () => void;
  children: ReactNode;
}) {
  const held = useRef<HTMLSpanElement>(null);
  const layer = useRef<HTMLDivElement>(null);
  const outside = useRef(onOutside);
  useLayoutEffect(() => {
    outside.current = onOutside;
  });

  useLayoutEffect(() => {
    const cell = (held.current ?? layer.current)?.closest("td");
    const box = layer.current;
    if (!cell || !box) return;
    function place() {
      if (!cell || !box) return;
      const at = cell.getBoundingClientRect();
      box.style.minWidth = `${at.width}px`;
      box.style.left = `${at.left}px`;
      box.style.top = `${at.top}px`;
      // A containing block other than the window (a transformed or filtered ancestor) offsets it.
      const first = box.getBoundingClientRect();
      let left = at.left - (first.left - at.left);
      let top = at.top - (first.top - at.top);
      // Kept inside the window, moved up or left only as far as it must.
      const size = box.getBoundingClientRect();
      left -= Math.max(0, size.right - (window.innerWidth - MARGIN));
      top -= Math.max(0, size.bottom - (window.innerHeight - MARGIN));
      box.style.left = `${Math.max(MARGIN, left)}px`;
      box.style.top = `${Math.max(MARGIN, top)}px`;
    }
    place();
    const press = (event: Event) => {
      if (!box?.contains(event.target as Node | null)) outside.current?.();
    };
    document.addEventListener("pointerdown", press, true);
    // Any scroll (the table's, the dialog's, the page's) and any resize of the cell or the editor.
    window.addEventListener("scroll", place, true);
    window.addEventListener("resize", place);
    const observer = typeof ResizeObserver === "undefined" ? undefined : new ResizeObserver(place);
    observer?.observe(box);
    observer?.observe(cell);
    return () => {
      document.removeEventListener("pointerdown", press, true);
      window.removeEventListener("scroll", place, true);
      window.removeEventListener("resize", place);
      observer?.disconnect();
    };
  }, []);

  return (
    <>
      {value !== undefined && (
        <span className="cell-edit" ref={held} aria-hidden="true">
          <span className="cell-edit-value">{value}</span>
          <span className="cell-edit-actions cell-edit-actions-kept" data-icons="1" />
        </span>
      )}
      <div className="popover floating-cell-editor" ref={layer}>
        {children}
      </div>
    </>
  );
}
