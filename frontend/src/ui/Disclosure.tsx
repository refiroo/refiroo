import { useId, useState, type ReactNode } from "react";

/**
 * A folded part of a page: a real button that opens and closes what it names (`aria-expanded`), the
 * content not in the page while folded (0.16 AP6a: groups of tables, left-out lists). `row` is a
 * ruled row with a chevron for a group; `link` is a line of text with a Show or Hide button after it,
 * for what is long and seldom wanted. `button` is one button whose text says what it does (`label`, then
 * `openLabel`). The button's name holds the label; the content is a labelled
 * region.
 */
export function Disclosure({
  label,
  detail,
  openLabel,
  variant = "row",
  children,
}: {
  label: ReactNode;
  /** The row's figures, after the label. */
  detail?: ReactNode;
  /** `button` only: the button's text while open; `label` is its text while folded. */
  openLabel?: ReactNode;
  variant?: "row" | "link" | "button";
  children: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const id = useId();
  if (variant === "button") {
    return (
      <div className={`disclosure is-button${open ? " is-open" : ""}`}>
        <div className="disclosure-line">
          <button
            type="button"
            className="secondary"
            aria-expanded={open}
            aria-controls={id}
            onClick={() => setOpen(!open)}
          >
            {open ? (openLabel ?? label) : label}
          </button>
        </div>
        {open && (
          <div id={id} className="disclosure-body">
            {children}
          </div>
        )}
      </div>
    );
  }
  if (variant === "link") {
    return (
      <div className={`disclosure is-link${open ? " is-open" : ""}`}>
        <div className="disclosure-line">
          <span id={`${id}-label`} className="disclosure-label">
            {label}
          </span>
          {detail && <span className="disclosure-detail">{detail}</span>}
          <button
            type="button"
            id={`${id}-toggle`}
            className="secondary"
            aria-expanded={open}
            aria-controls={id}
            aria-labelledby={`${id}-toggle ${id}-label`}
            onClick={() => setOpen(!open)}
          >
            {open ? "Hide" : "Show"}
          </button>
        </div>
        {open && (
          <div id={id} className="disclosure-body">
            {children}
          </div>
        )}
      </div>
    );
  }
  return (
    <div className={`disclosure is-${variant}${open ? " is-open" : ""}`}>
      <button
        type="button"
        className="disclosure-toggle"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen(!open)}
      >
        <span className="disclosure-label">{label}</span>
        {detail && (
          <>
            {" "}
            <span className="disclosure-detail">{detail}</span>
          </>
        )}
      </button>
      {open && (
        <div id={id} className="disclosure-body">
          {children}
        </div>
      )}
    </div>
  );
}
