import type { RefObject } from "react";
import { Menu, MenuItem, Popover } from "react-aria-components";

export type AnchoredMenuItem = {
  id: string;
  label: string;
  /** A keyboard shortcut that does the same, shown beside the label. */
  hint?: string;
  onAction: () => void;
};

/**
 * A menu opened on demand beside an element that is not its own button: a row of a tree opened
 * with Shift+F10 or the context menu key, so the row keeps the list's single tab stop. The caller
 * owns whether it is open; `onClose` runs when it is dismissed without choosing an item.
 */
export function AnchoredMenu({
  anchorRef,
  label,
  items,
  onClose,
}: {
  anchorRef: RefObject<HTMLElement | null>;
  label: string;
  items: readonly AnchoredMenuItem[];
  onClose: () => void;
}) {
  return (
    <Popover
      triggerRef={anchorRef}
      isOpen
      onOpenChange={(open) => !open && onClose()}
      placement="bottom end"
      className="action-menu-popover"
    >
      <Menu
        className="action-menu"
        aria-label={label}
        autoFocus="first"
        onAction={(key) => items.find((item) => item.id === key)?.onAction()}
      >
        {items.map((item) => (
          <MenuItem key={item.id} id={item.id} className="action-menu-item" textValue={item.label}>
            {item.label}
            {item.hint && <kbd className="menu-hint">{item.hint}</kbd>}
          </MenuItem>
        ))}
      </Menu>
    </Popover>
  );
}
