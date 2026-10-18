import { useCallback, useState, type ReactNode } from "react";
import { PHONE_WIDTH, useMediaQuery } from "@/lib/hooks/useMediaQuery";
import { createPortal } from "react-dom";
import { Modal } from "@/ui/Modal";
import { NAVIGATION_RAIL_ATTRIBUTE, useRailScroll } from "@/ui/navigationRail";

/** Move one persistent navigation tree into the focus-managed drawer without resetting its state. */
export function NavigationDrawer({
  open,
  onClose,
  title = "Application navigation",
  scrollScope,
  children,
}: {
  open: boolean;
  /** Names the drawer after the destination whose navigation it holds. */
  title?: string;
  /** What the rail's scroll position belongs to (`useRailScroll`). */
  scrollScope: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const [host] = useState(() => {
    const element = document.createElement("div");
    element.setAttribute(NAVIGATION_RAIL_ATTRIBUTE, "");
    return element;
  });
  const mobile = useMediaQuery(PHONE_WIDTH);
  // The element that scrolls the rail: the desktop rail itself, or the drawer's dialog on a phone.
  const [scroller, setScroller] = useState<HTMLElement | null>(null);
  const attach = useCallback(
    (node: HTMLDivElement | null) => {
      if (node) node.appendChild(host);
      setScroller(node && (node.classList.contains("workspace-sidebar") ? node : node.closest<HTMLElement>(".dialog")));
    },
    [host],
  );
  useRailScroll(scroller, scrollScope);
  return (
    <>
      {mobile && open ? (
        <Modal title={title} size="navigation" onClose={onClose}>
          <div ref={attach} />
        </Modal>
      ) : (
        <div ref={attach} hidden={mobile} className="workspace-sidebar" />
      )}
      {createPortal(children, host)}
    </>
  );
}
