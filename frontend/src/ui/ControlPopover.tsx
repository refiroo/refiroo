import type { ReactNode } from "react";
import { Button, Dialog, DialogTrigger, Heading, Popover } from "react-aria-components";
import { Icon, type IconName } from "@/ui/Icon";

/** A keyboard/touch disclosure for collection settings, with dismissal and focus restore. */
export function ControlPopover({
  label,
  icon,
  count = 0,
  children,
}: {
  label: string;
  icon?: IconName;
  /** Number of active settings, shown on the trigger and announced with its name. */
  count?: number;
  children: ReactNode | ((close: () => void) => ReactNode);
}) {
  return (
    <DialogTrigger>
      <Button className={`secondary toolbar-button${count ? " has-count" : ""}`}>
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
      <Popover className="control-popover" placement="bottom end">
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
