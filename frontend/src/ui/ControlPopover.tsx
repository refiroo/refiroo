import { useRef, useState, type ReactNode } from "react";
import { Button, Dialog, DialogTrigger, Heading, Popover } from "react-aria-components";
import { Icon, type IconName } from "@/ui/Icon";

/** A keyboard/touch disclosure for collection settings, with dismissal and focus restore. */
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
  const [container, setContainer] = useState<Element>();
  return (
    <DialogTrigger
      onOpenChange={(open) => {
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
