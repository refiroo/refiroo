/**
 * A table's selection checkbox (0.9 K1): checked, unchecked or, for a header standing for several
 * rows, partly checked. `onSelect` receives whether Shift was held, from a click or from Space, so
 * a caller can extend a range by pointer and by keyboard alike.
 */

import { useEffect, useRef } from "react";

export function SelectionCheckbox({
  label,
  state,
  onSelect,
  gridColumn,
}: {
  label: string;
  state: "all" | "some" | "none";
  onSelect: (extend: boolean) => void;
  /** Lets ↑ and ↓ move between the rows' checkboxes (`ui/ScrollWindow`). */
  gridColumn?: string;
}) {
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (input.current) input.current.indeterminate = state === "some";
  }, [state]);
  return (
    <input
      ref={input}
      type="checkbox"
      className="selection-checkbox"
      aria-label={label}
      checked={state === "all"}
      data-grid-col={gridColumn}
      // The click is handled below, where Shift is known; the browser's own toggle is undone by React.
      onChange={() => undefined}
      onMouseDown={(event) => {
        // Shift+click would otherwise select the page's text between the two rows.
        if (event.shiftKey) event.preventDefault();
      }}
      onClick={(event) => onSelect(event.shiftKey)}
      onKeyDown={(event) => {
        if (event.key !== " ") return;
        event.preventDefault();
        onSelect(event.shiftKey);
      }}
      onKeyUp={(event) => {
        if (event.key === " ") event.preventDefault();
      }}
    />
  );
}
