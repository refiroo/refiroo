import { useCallback, useEffect, useState, type ReactNode } from "react";
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
  const [mobile, setMobile] = useState(() => window.matchMedia("(max-width: 760px)").matches);
  const attach = useCallback(
    (node: HTMLDivElement | null) => {
      if (node) node.appendChild(host);
    },
    [host],
  );
  useEffect(() => {
    const query = window.matchMedia("(max-width: 760px)");
    const update = () => setMobile(query.matches);
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);
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
