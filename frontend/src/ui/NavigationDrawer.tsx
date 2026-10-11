import { useCallback, useState, type ReactNode } from "react";
import { PHONE_WIDTH, useMediaQuery } from "@/lib/hooks/useMediaQuery";
import { createPortal } from "react-dom";
import { Modal } from "@/ui/Modal";

/** Move one persistent navigation tree into the focus-managed drawer without resetting its state. */
export function NavigationDrawer({
  open,
  onClose,
  title = "Application navigation",
  children,
}: {
  open: boolean;
  /** Names the drawer after the destination whose navigation it holds. */
  title?: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const [host] = useState(() => document.createElement("div"));
  const mobile = useMediaQuery(PHONE_WIDTH);
  const attach = useCallback(
    (node: HTMLDivElement | null) => {
      if (node) node.appendChild(host);
    },
    [host],
  );
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
