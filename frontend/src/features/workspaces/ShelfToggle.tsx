/**
 * Brings the list a person is looking at to their shelf on the workspace's page, or takes it off (0.17 UX1): one
 * button in the list's header, pressed while the list is on the shelf. The shelf is `workspacePins`.
 */

import { useWorkspacePins } from "@/features/workspaces/workspacePins";
import { Icon } from "@/ui/Icon";
import { useOptionalToast } from "@/ui/Toast";

export function ShelfToggle({
  workspaceKey,
  applicationKey,
  viewKey,
  name,
}: {
  workspaceKey: string;
  applicationKey: string;
  viewKey: string;
  /** The list's name, for the button's accessible name and the toast. */
  name: string;
}) {
  const shelf = useWorkspacePins(workspaceKey);
  const toast = useOptionalToast();
  const pin = { applicationKey, viewKey };
  const pinned = shelf.isPinned(pin);
  return (
    <button
      type="button"
      className="secondary shelf-toggle"
      aria-pressed={pinned}
      aria-label={pinned ? `Take ${name} off your shelf` : `Add ${name} to your shelf`}
      title={
        pinned
          ? "On your shelf on the workspace's page: press to take it off"
          : "Add to your shelf on the workspace's page"
      }
      onClick={() => {
        shelf.toggle(pin);
        toast(pinned ? `${name} is off your shelf` : `${name} is on your shelf`, {
          actions: [{ label: "Undo", onPress: () => shelf.toggle(pin) }],
        });
      }}
    >
      <Icon name="pin" size={15} />
    </button>
  );
}
