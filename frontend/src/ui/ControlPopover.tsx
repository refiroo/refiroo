import type { ReactNode } from "react";
import { Button, Dialog, DialogTrigger, Heading, Popover } from "react-aria-components";

/** A keyboard/touch disclosure for collection settings, with dismissal and focus restore. */
export function ControlPopover({ label, children }: { label: string; children: ReactNode }) {
  return (
    <DialogTrigger>
      <Button className="secondary">{label}</Button>
      <Popover className="control-popover" placement="bottom end">
        <Dialog>
          {({ close }) => (
            <>
              <header>
                <Heading slot="title">{label}</Heading>
                <Button className="secondary" onPress={close}>
                  Done
                </Button>
              </header>
              {children}
            </>
          )}
        </Dialog>
      </Popover>
    </DialogTrigger>
  );
}
