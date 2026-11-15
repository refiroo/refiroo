import { useEffect, useRef, useState, type ReactNode } from "react";
import { Button, Dialog, DialogTrigger, Heading, Popover } from "react-aria-components";
import { scrollingAncestorOrNull } from "@/lib/scrollAncestor";
import { Icon, type IconName } from "@/ui/Icon";

/** The height the sticky top bar and data band cover at the top of the window. */
function coveredAtTop() {
  const root = getComputedStyle(document.documentElement);
  return (
    (parseFloat(root.getPropertyValue("--topbar-height")) || 0) +
    (parseFloat(root.getPropertyValue("--band-height")) || 0)
  );
}

/**
 * Sets an invisible box over the window below the sticky top bar and data band: the boundary a
 * popover is placed in, so that it never covers them. React Aria measures a boundary other than
 * the body in the window's coordinates, so its top is the inset and its height the window's less
 * the inset.
 */
function fitUnderTheTopBar(box: HTMLElement) {
  const inset = coveredAtTop();
  box.style.cssText = `position:absolute;left:0;width:100%;top:${inset}px;height:${Math.max(0, window.innerHeight - inset)}px;visibility:hidden;pointer-events:none`;
}

/** The boundary box; the caller removes it when the popover closes. */
function underTheTopBar() {
  const box = document.createElement("div");
  box.setAttribute("aria-hidden", "true");
  fitUnderTheTopBar(box);
  document.body.append(box);
  return box;
}

/**
 * A keyboard/touch disclosure for collection settings, with dismissal and focus restore.
 *
 * Non-modal: the page stays live while it is open, so a press elsewhere closes it and also acts
 * (a tab, a link, a row). A modal popover makes the page inert and lays an underlay over it, which
 * swallowed that first press. React Aria leaves two things to a non-modal popover's owner, done
 * here: it does not close on an outside press, and it closes on any scroll around its trigger,
 * including the page's own when an applied setting shortens the list. So the popover closes on a
 * press outside or the user's own scrolling (wheel, touch) and ignores scrolls the layout causes.
 * Escape and focus leaving it still close it through React Aria. A press on the trigger toggles it:
 * pressed while open, focus leaving closes it and the same press must not open it again (the user,
 * 2026-10-28: the bell opens its list and closes it).
 *
 * A popover is placed inside the area under the sticky top bar and data band, below its button or
 * above it where there is more room. When it cannot show all its content and the page (or the
 * trigger's own scroll container) can scroll far enough to give it the room below, it scrolls the
 * trigger up under the band once and places the popover again; that scroll is the layout's, so it
 * does not close it. Where no scroll helps it scrolls inside, with an always-visible scrollbar
 * (`.control-popover`): macOS hides overlay scrollbars, so a cut-off popover must say so. It measures its room from the nearest positioned ancestor, so the
 * app shell is not positioned (layout.css): a positioned, page-sized shell scrolls with the window
 * and gave a popover placed below its button on a scrolled page no height at all.
 */
export function ControlPopover({
  label,
  icon,
  count = 0,
  trigger,
  triggerClassName,
  className,
  placement = "bottom end",
  header = true,
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
  placement?: "bottom end" | "bottom start" | "top start";
  /** Whether the popover draws its own title and Done; an editor with its own header turns it off. */
  header?: boolean;
  children: ReactNode | ((close: () => void) => ReactNode);
}) {
  const triggerRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLElement>(null);
  const [isOpen, setOpen] = useState(false);
  const [container, setContainer] = useState<Element>();
  // The area under the sticky top bar and data band, which the popover stays inside (see above).
  const [boundary, setBoundary] = useState<HTMLElement>();
  useEffect(() => () => boundary?.remove(), [boundary]);
  // Set when a press on the trigger begins while the popover is open: that press only closes it.
  const closingPress = useRef(false);
  // The boundary follows the window while the popover is open. Capturing, so it is fitted before
  // React Aria places the popover on the same resize.
  useEffect(() => {
    if (!boundary) return;
    const fit = () => fitUnderTheTopBar(boundary);
    window.addEventListener("resize", fit, true);
    return () => window.removeEventListener("resize", fit, true);
  }, [boundary]);
  useEffect(() => {
    if (!isOpen) return;
    let frame = 0;
    let tries = 0;
    const bringIntoRoom = () => {
      const popover = popoverRef.current;
      const trigger = triggerRef.current;
      if (!popover || !trigger) {
        if (++tries < 10) frame = requestAnimationFrame(bringIntoRoom);
        return;
      }
      if (popover.scrollHeight <= popover.clientHeight) return;
      const target = scrollingAncestorOrNull(trigger);
      const rect = trigger.getBoundingClientRect();
      const topEdge = Math.max(coveredAtTop(), target ? target.getBoundingClientRect().top : 0);
      const bottomEdge = target ? target.getBoundingClientRect().bottom : window.innerHeight;
      const down = target
        ? target.scrollHeight - target.clientHeight - target.scrollTop
        : document.documentElement.scrollHeight - window.innerHeight - window.scrollY;
      const up = target ? target.scrollTop : window.scrollY;
      // The popover's height, with the gap to the button and the padding to the edge it is kept in.
      const height = popover.scrollHeight + 2 + 8 + 12;
      // (a) Scroll the page until the whole popover fits below the button, the button staying under
      // the bar; else (b) until it fits above the button, under the bar, the button staying in the
      // window; else (c) leave it, scrolling inside with its scrollbar. A scroll that does not fit
      // it would only move the cut.
      const below = Math.ceil(rect.bottom + height - bottomEdge);
      const above = Math.ceil(topEdge + height - rect.top);
      let by = 0;
      if (below <= 0 || above <= 0) by = 0;
      else if (below <= down && rect.top - below >= topEdge) by = below;
      else if (above <= up && rect.bottom + above <= bottomEdge) by = -above;
      if (!by) return;
      if (target) target.scrollTop += by;
      else window.scrollBy(0, by);
      // React Aria places again on a resize, not on a scroll.
      frame = requestAnimationFrame(() => window.dispatchEvent(new Event("resize")));
    };
    frame = requestAnimationFrame(bringIntoRoom);
    return () => cancelAnimationFrame(frame);
  }, [isOpen]);
  useEffect(() => {
    if (!isOpen) return;
    const closeOutside = (event: Event) => {
      const target = event.target as Node;
      if (popoverRef.current?.contains(target) || triggerRef.current?.contains(target)) return;
      // A list opened from inside, such as a combo box's options, is a React Aria popover of its
      // own elsewhere in the page: a press there is a choice inside, not a press outside (0.11 M6).
      const layered = target instanceof Element ? target.closest("[data-trigger]") : null;
      if (layered && layered !== popoverRef.current) return;
      setOpen(false);
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
        if (open && closingPress.current) {
          closingPress.current = false;
          setOpen(false);
          return;
        }
        setOpen(open);
        // Render inside a landmark so React Aria's hidden dismiss buttons are not stray page
        // content: the enclosing dialog (such as the mobile drawer, which makes the page inert),
        // otherwise the main landmark.
        if (open) {
          const dialog = triggerRef.current?.closest('[role="dialog"]');
          setContainer(dialog ?? document.getElementById("main-content") ?? undefined);
          setBoundary(dialog ? undefined : underTheTopBar());
        } else setBoundary(undefined);
      }}
    >
      {trigger ? (
        <Button
          ref={triggerRef}
          className={triggerClassName}
          aria-label={label}
          onPointerDown={() => (closingPress.current = isOpen)}
        >
          {trigger}
        </Button>
      ) : (
        <Button
          ref={triggerRef}
          className={`secondary toolbar-button${count ? " has-count" : ""}`}
          onPointerDown={() => (closingPress.current = isOpen)}
        >
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
        boundaryElement={boundary}
        UNSTABLE_portalContainer={container}
      >
        <Dialog aria-label={header ? undefined : label}>
          {({ close }) => (
            <>
              {header && (
                <header>
                  <Heading slot="title">{label}</Heading>
                  <Button className="ghost" onPress={close}>
                    Done
                  </Button>
                </header>
              )}
              {typeof children === "function" ? children(close) : children}
            </>
          )}
        </Dialog>
      </Popover>
    </DialogTrigger>
  );
}
