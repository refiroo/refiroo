import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { Popover } from "react-aria-components";
import { Icon } from "@/ui/Icon";

/**
 * A small blue circled "i" that explains something beside the thing it explains, such as a panel's
 * heading. The text shows while the mouse is over the button or the keyboard is on it, and Escape,
 * leaving or moving focus away hides it. On touch a tap shows it and a second tap, or a tap
 * elsewhere, hides it: the open state is held here because a hover-only tooltip never opens on
 * touch. It carries no native title, so there is one tooltip, not two.
 */
export function InfoHint({ label, children }: { label: string; children: ReactNode }) {
  const buttonRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLElement>(null);
  const pointer = useRef("");
  const [open, setOpen] = useState(false);
  const [container, setContainer] = useState<Element>();
  const id = useId();
  function show() {
    // Render inside a landmark, as ControlPopover does: the enclosing dialog, otherwise the main one.
    setContainer(buttonRef.current?.closest('[role="dialog"]') ?? document.getElementById("main-content") ?? undefined);
    setOpen(true);
  }
  useEffect(() => {
    if (!open) return;
    const outside = (event: Event) => {
      const target = event.target as Node;
      if (buttonRef.current?.contains(target) || popoverRef.current?.contains(target)) return;
      setOpen(false);
    };
    const escape = (event: KeyboardEvent) => event.key === "Escape" && setOpen(false);
    document.addEventListener("pointerdown", outside, true);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("pointerdown", outside, true);
      document.removeEventListener("keydown", escape);
    };
  }, [open]);
  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        className="info-hint"
        aria-label={label}
        aria-expanded={open}
        aria-describedby={open ? id : undefined}
        onPointerDown={(event) => (pointer.current = event.pointerType)}
        onPointerEnter={(event) => event.pointerType === "mouse" && show()}
        onPointerLeave={(event) => event.pointerType === "mouse" && setOpen(false)}
        onFocus={(event) => {
          // A tap focuses the button too, and its click then toggles: only keyboard focus opens.
          try {
            if (event.currentTarget.matches(":focus-visible")) show();
          } catch {
            /* a browser without :focus-visible opens on click only */
          }
        }}
        onBlur={() => setOpen(false)}
        onClick={() => {
          // The mouse has already opened it by hovering: its click must not close it again.
          if (pointer.current === "mouse" || !open) show();
          else setOpen(false);
          pointer.current = "";
        }}
      >
        <Icon name="info" size={14} />
      </button>
      <Popover
        ref={popoverRef}
        triggerRef={buttonRef}
        isOpen={open}
        onOpenChange={setOpen}
        isNonModal
        placement="bottom start"
        offset={6}
        className="info-hint-popover"
        UNSTABLE_portalContainer={container}
      >
        <div id={id} role="tooltip">
          {children}
        </div>
      </Popover>
    </>
  );
}
