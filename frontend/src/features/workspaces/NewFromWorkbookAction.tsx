/**
 * The entry to New workspace from a workbook (0.17 PL4), the same button on Home, in Settings › Workspaces and
 * on a workspace's page. It is left out for a person who lacks any step the one route makes, never disabled
 * (D323). The sheet opens beside the page; Create workspace lands on the new workspace's page.
 */

import { useState } from "react";
import { useHeldAnywhere } from "@/state/permissions";
import { useCapabilities } from "@/state/useSystem";
import { openWorkspace } from "@/state/openWorkspace";
import { startsFromWorkbook } from "@/features/workspaces/fromWorkbook";
import { NewFromWorkbook } from "@/features/workspaces/NewFromWorkbook";
import type { RouteState } from "@/types";
import { Icon } from "@/ui/Icon";

export function NewFromWorkbookAction({
  onNavigate,
  onOtherWays,
  variant = "secondary",
}: {
  onNavigate: (route: RouteState) => void;
  /** Today's way: where the sheet's More ways to start leads. */
  onOtherWays: () => void;
  variant?: "primary" | "secondary";
}) {
  const held = useHeldAnywhere();
  const { capabilities } = useCapabilities();
  const [open, setOpen] = useState(false);
  if (!startsFromWorkbook(held, capabilities)) return null;
  return (
    <>
      <button type="button" className={variant} onClick={() => setOpen(true)}>
        <Icon name="plus" /> New workspace from a workbook
      </button>
      {open && (
        <NewFromWorkbook
          onClose={() => setOpen(false)}
          onCreated={(workspaceKey) => {
            setOpen(false);
            openWorkspace(workspaceKey, onNavigate);
          }}
          onNavigate={(route) => {
            setOpen(false);
            onNavigate(route);
          }}
          onOtherWays={() => {
            setOpen(false);
            onOtherWays();
          }}
        />
      )}
    </>
  );
}
