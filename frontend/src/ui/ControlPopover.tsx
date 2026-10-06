import { useEffect, useRef, useState, type ReactNode } from "react";
import { Button, Dialog, DialogTrigger, Heading, Popover } from "react-aria-components";
import { Icon, type IconName } from "@/ui/Icon";

/**
 * A keyboard/touch disclosure for collection settings, with dismissal and focus restore.
 *
 * Non-modal: the page stays live while it is open, so a press elsewhere closes it and also acts
 * (a tab, a link, a row). A modal popover makes the page inert and lays an underlay over it, which
 * swallowed that first press. React Aria leaves two things to a non-modal popover's owner, done
 * here: it does not close on an outside press, and it closes on any scroll around its trigger,
 * including the page's own when an applied setting shortens the list. So the popover closes on a
 * press outside or the user's own scrolling (wheel, touch) and ignores scrolls the layout causes.
 * Escape and focus leaving it still close it through React Aria.
 */
export function ControlPopover({
  label,
  icon,
  count = 0,
  trigger,
  triggerClassName,
  className,
  placement = "bottom end",
  children,
}: {
  label: string;
  icon?: IconName;
  /** Number of active settings, shown on the trigger and announced with its name. */
  count?: number;
  /** Custom trigger content; the trigger is then named by `label`. */
  trigger?: ReactNode;
  triggerClassName?: string;
  className?: string;
  placement?: "bottom end" | "top start";
  children: ReactNode | ((close: () => void) => ReactNode);
}) {
  const triggerRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLElement>(null);
  const [isOpen, setOpen] = useState(false);
  const [container, setContainer] = useState<Element>();
  useEffect(() => {
    if (!isOpen) return;
    const closeOutside = (event: Event) => {
      const target = event.target as Node;
      if (!popoverRef.current?.contains(target) && !triggerRef.current?.contains(target)) setOpen(false);
    };
    const events = ["pointerdown", "wheel", "touchmove"] as const;
    for (const type of events) document.addEventListener(type, closeOutside, { capture: true, passive: true });
    return () => {
      for (const type of events) document.removeEventListener(type, closeOutside, { capture: true });
    };
  }, [isOpen]);
  return (
    <DialogTrigger
      isOpen={isOpen}
      onOpenChange={(open) => {
        // React Aria's close-on-scroll, called from inside the scroll event; see above.
        if (!open && window.event?.type === "scroll") return;
        setOpen(open);
        // Render inside a landmark so React Aria's hidden dismiss buttons are not stray page
        // content: the enclosing dialog (such as the mobile drawer, which makes the page inert),
        // otherwise the main landmark.
        if (open)
          setContainer(
            triggerRef.current?.closest('[role="dialog"]') ?? document.getElementById("main-content") ?? undefined,
          );
      }}
    >
      {trigger ? (
        <Button ref={triggerRef} className={triggerClassName} aria-label={label}>
          {trigger}
        </Button>
      ) : (
        <Button ref={triggerRef} className={`secondary toolbar-button${count ? " has-count" : ""}`}>
          {icon && <Icon name={icon} size={15} />}
          {label}
          {count > 0 && (
            <>
              <span className="count-badge" aria-hidden="true">
                {count}
              </span>
              <span className="visually-hidden">, {count} applied</span>
            </>
          )}
        </Button>
      )}
      <Popover
        ref={popoverRef}
        isNonModal
        className={`control-popover${className ? ` ${className}` : ""}`}
        placement={placement}
        UNSTABLE_portalContainer={container}
      >
        <Dialog>
          {({ close }) => (
            <>
              <header>
                <Heading slot="title">{label}</Heading>
                <Button className="ghost" onPress={close}>
                  Done
                </Button>
              </header>
              {typeof children === "function" ? children(close) : children}
            </>
          )}
        </Dialog>
      </Popover>
    </DialogTrigger>
  );
}
