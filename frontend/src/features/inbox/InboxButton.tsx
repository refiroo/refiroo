/**
 * The bell in the top bar (0.12 A2): the inbox's unread count as a badge, and the popover that
 * lists the notices. Shown to a signed-in person only; a client never uses the browser.
 */

import { useMe } from "@/app/useMe";
import type { RouteState } from "@/types";
import { ControlPopover } from "@/ui/ControlPopover";
import { Icon } from "@/ui/Icon";
import { InboxPanel } from "./InboxPanel";
import { useInbox } from "./useInbox";

const BADGE_CAP = 9;

export function InboxButton({
  applicationKey,
  onNavigate,
}: {
  applicationKey: string | undefined;
  onNavigate: (route: RouteState) => void;
}) {
  const me = useMe();
  const person = me?.kind === "user";
  const { unreadCount } = useInbox(person);
  if (!person) return null;
  return (
    <ControlPopover
      label={unreadCount > 0 ? `Inbox, ${unreadCount} unread` : "Inbox"}
      header={false}
      className="inbox-popover"
      placement="bottom end"
      triggerClassName="topbar-icon-button inbox-button"
      trigger={
        <>
          <Icon name="bell" size={18} />
          {unreadCount > 0 && (
            <span className="inbox-badge" aria-hidden="true">
              {unreadCount > BADGE_CAP ? `${BADGE_CAP}+` : unreadCount}
            </span>
          )}
        </>
      }
    >
      {(close) => <InboxPanel applicationKey={applicationKey} onNavigate={onNavigate} close={close} />}
    </ControlPopover>
  );
}
