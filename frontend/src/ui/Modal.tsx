import { useEffect, useId, useRef } from "react";
import type { ReactNode, RefObject } from "react";

/**
 * The shared modal shell: backdrop, dialog container, header, and the keyboard behavior a dialog
 * owes its user.
 *
 * Before this existed, five dialogs each rebuilt the same markup and disagreed about all of it —
 * two closed on Escape, two restored focus, none trapped it, and two carried hardcoded
 * `aria-labelledby` ids that collide if both are ever open. AGENTS.md requires that keyboard
 * operation and semantic HTML are preserved, so the behavior belongs in one place.
 *
 * The children are rendered as direct children of the dialog container, after the header, because
 * the stylesheet targets `.dialog form` and `.confirm-dialog > .dialog-actions` directly.
 */

/**
 * Open modals, innermost last. Escape and the scroll lock consult this so that a dialog opened over
 * another does not close both, and so the last one to close is the one that restores scrolling.
 */
const stack: string[] = [];

/**
 * The page's own `overflow`, captured when the first modal opens and restored when the last one
 * closes. It has to be module state: a second modal opening over a first would otherwise capture
 * the locked value and restore that instead of the page's.
 */
let unlockedOverflow = "";

const FOCUSABLE = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled]):not([type='hidden'])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

function focusableWithin(container: HTMLElement) {
  // Everything a dialog hides, it hides by not rendering it, so presence in the DOM is enough.
  // Measuring layout instead would be wrong under jsdom, where nothing has an offset parent.
  return Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE));
}

export function Modal({
  title,
  eyebrow,
  children,
  onClose,
  busy = false,
  size,
  role = "dialog",
  showClose = true,
  initialFocusRef,
}: {
  title: string;
  /** Small label above the title, naming the action rather than its subject. */
  eyebrow?: string;
  children: ReactNode;
  onClose: () => void;
  /** While true the dialog refuses to close, so an in-flight write is not abandoned half way. */
  busy?: boolean;
  size?: "compact" | "confirm";
  role?: "dialog" | "alertdialog";
  showClose?: boolean;
  /**
   * What to focus on open. Defaults to whatever a child claimed with `autoFocus`, and falls back to
   * the dialog itself so that focus is never left behind on the control that opened it.
   */
  initialFocusRef?: RefObject<HTMLElement | null>;
}) {
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  // React applies a child's `autoFocus` before passive effects run. Capture the opener during the
  // modal's first render, while focus still sits outside the newly mounted subtree, so cleanup can
  // restore it even when a form field claims focus during commit.
  const returnFocusRef = useRef(document.activeElement as HTMLElement | null);
  // Read by the key handler, which is registered once and must not close over a stale `busy`.
  const busyRef = useRef(busy);
  const closeRef = useRef(onClose);

  useEffect(() => {
    busyRef.current = busy;
    closeRef.current = onClose;
  });

  useEffect(() => {
    const id = `${Math.random()}`;
    if (!stack.length) unlockedOverflow = document.body.style.overflow;
    stack.push(id);
    const previous = returnFocusRef.current;
    document.body.style.overflow = "hidden";

    const dialog = dialogRef.current;
    if (dialog && !dialog.contains(document.activeElement)) {
      // A child with autoFocus has already claimed focus by now; only act when none did.
      (initialFocusRef?.current ?? dialog).focus();
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if (stack[stack.length - 1] !== id) return;
      if (event.key === "Escape" && !busyRef.current) {
        closeRef.current();
        return;
      }
      if (event.key !== "Tab" || !dialogRef.current) return;
      const focusable = focusableWithin(dialogRef.current);
      if (!focusable.length) {
        event.preventDefault();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement;
      if (!event.shiftKey && (active === last || !dialogRef.current.contains(active))) {
        event.preventDefault();
        first.focus();
      } else if (event.shiftKey && (active === first || !dialogRef.current.contains(active))) {
        event.preventDefault();
        last.focus();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      const index = stack.indexOf(id);
      if (index !== -1) stack.splice(index, 1);
      if (!stack.length) document.body.style.overflow = unlockedOverflow;
      previous?.focus();
    };
    // Mount and unmount only: re-running would re-steal focus and re-enter the stack.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="dialog-backdrop" onMouseDown={() => !busy && onClose()}>
      <div
        ref={dialogRef}
        tabIndex={-1}
        className={`dialog${size ? ` ${size}-dialog` : ""}`}
        role={role}
        aria-modal="true"
        aria-labelledby={titleId}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="dialog-header">
          <div>
            {eyebrow && <p className="eyebrow">{eyebrow}</p>}
            <h2 id={titleId}>{title}</h2>
          </div>
          {showClose && (
            <button type="button" className="close" aria-label="Close" disabled={busy} onClick={onClose}>
              ×
            </button>
          )}
        </div>
        {children}
      </div>
    </div>
  );
}
