import { useRef, type ReactNode, type RefObject } from "react";
import { Dialog, Heading, Popover } from "react-aria-components";

/**
 * A small form or list opened on demand under an element that is not its own trigger (UX1, PP-D40):
 * the control a menu was opened from, or the row a shortcut was pressed on. It is a titled dialog
 * in a popover: Escape or a press outside closes it (`onClose`), unless `dismissible` is off while
 * something is being sent. The caller owns whether it is open and where focus goes when it has
 * closed.
 */
export function AnchoredPopover({
  anchor,
  title,
  onClose,
  dismissible = true,
  className,
  titleClassName,
  children,
}: {
  anchor: HTMLElement;
  title: string;
  onClose: () => void;
  dismissible?: boolean;
  className?: string;
  titleClassName?: string;
  children: ReactNode;
}) {
  const anchorRef = useRef<HTMLElement>(anchor) as RefObject<HTMLElement>;
  return (
    <Popover
      triggerRef={anchorRef}
      isOpen
      onOpenChange={(open) => {
        if (!open && dismissible) onClose();
      }}
      placement="bottom start"
      offset={4}
      className={className}
    >
      <Dialog>
        <Heading slot="title" className={titleClassName}>
          {title}
        </Heading>
        {children}
      </Dialog>
    </Popover>
  );
}
