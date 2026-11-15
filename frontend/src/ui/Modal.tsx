import { createContext, useCallback, useContext, useEffect } from "react";
import type { ReactNode, RefObject } from "react";
import { Dialog, Heading, Modal as AriaModal, ModalOverlay } from "react-aria-components";
import { confirmDiscard as askDiscard } from "@/lib/confirmDiscard";
import { Icon, type IconName } from "@/ui/Icon";

const ModalClose = createContext<(() => void) | undefined>(undefined);

/**
 * The close a dialog's own buttons use: it asks "Discard your unsaved changes?" while the dialog is
 * dirty and does nothing while it is busy, as the corner button and Escape do. Outside a modal it
 * is undefined.
 */
export function useModalClose() {
  return useContext(ModalClose);
}

/** A dialog's Cancel: the modal's `requestClose`, so a dialog with input asks before it discards. */
export function CancelButton({
  disabled = false,
  className = "secondary",
  children = "Cancel",
}: {
  disabled?: boolean;
  className?: string;
  children?: ReactNode;
}) {
  const requestClose = useModalClose();
  return (
    <button type="button" className={className} disabled={disabled} onClick={requestClose}>
      {children}
    </button>
  );
}

/**
 * RDM's dialog contract. React Aria owns the portal, focus scope, outside interaction and Escape;
 * this wrapper owns product dismissal rules, action hierarchy and styling.
 */

export function Modal({
  title,
  eyebrow,
  icon,
  description,
  children,
  onClose,
  busy = false,
  size,
  width,
  role = "dialog",
  showClose = true,
  initialFocusRef,
  dirty = false,
  confirmDiscard = askDiscard,
}: {
  title: string;
  /** Small label above the title, naming the action rather than its subject. */
  eyebrow?: string;
  /** A glyph in a tile beside the title, naming the kind of action (0.9 K6a). */
  icon?: IconName;
  /** A line under the title, naming what the dialog acts on ("12 system values"). */
  description?: string;
  children: ReactNode;
  onClose: () => void;
  /** While true the dialog refuses to close, so an in-flight write is not abandoned half way. */
  busy?: boolean;
  size?: "compact" | "confirm" | "navigation" | "wide";
  /** A CSS length for a dialog whose content sets its own width (a table's columns); never wider than the window. */
  width?: string;
  role?: "dialog" | "alertdialog";
  showClose?: boolean;
  /**
   * What to focus on open. Defaults to whatever a child claimed with `autoFocus`, and falls back to
   * the dialog itself so that focus is never left behind on the control that opened it.
   */
  initialFocusRef?: RefObject<HTMLElement | null>;
  /** Clean dialogs dismiss immediately. Dirty dialogs require an explicit confirmation. */
  dirty?: boolean;
  confirmDiscard?: () => boolean;
}) {
  const requestClose = useCallback(() => {
    if (busy) return;
    if (dirty && !confirmDiscard()) return;
    onClose();
  }, [busy, confirmDiscard, dirty, onClose]);

  useEffect(() => {
    initialFocusRef?.current?.focus();
  }, [initialFocusRef]);

  return (
    <ModalOverlay
      className="dialog-backdrop"
      isOpen
      isDismissable={!busy}
      isKeyboardDismissDisabled={busy}
      onOpenChange={(open) => !open && requestClose()}
    >
      <AriaModal
        className={`dialog${size ? ` ${size}-dialog` : ""}`}
        style={width ? { width: `min(${width}, 100%)` } : undefined}
      >
        <Dialog role={role}>
          <div className="dialog-header">
            {icon && (
              <span className="dialog-icon" aria-hidden="true">
                <Icon name={icon} size={18} />
              </span>
            )}
            <div className="dialog-heading">
              {eyebrow && <p className="eyebrow">{eyebrow}</p>}
              <Heading slot="title">{title}</Heading>
              {description && <p className="dialog-description">{description}</p>}
            </div>
            {showClose && (
              <button
                type="button"
                className="close icon-button"
                aria-label="Close"
                disabled={busy}
                onClick={requestClose}
              >
                <Icon name="close" />
              </button>
            )}
          </div>
          <ModalClose.Provider value={requestClose}>{children}</ModalClose.Provider>
        </Dialog>
      </AriaModal>
    </ModalOverlay>
  );
}
