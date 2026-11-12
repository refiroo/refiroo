/**
 * One grant as a chip (0.12 Access; shared since 0.17 ST1): the role or consumer API in its kind's colour, what
 * its writes are narrowed to, a stale narrowing's warning, and a trash button where the page may remove it. Used
 * by a workspace's Access (one line per principal) and by a person's, group's or client's access (one line per
 * place). Styles: `.access-chip` in `styles/workspace-access.css`.
 */

import type { ReactNode } from "react";
import type { Grant } from "@/types";
import { Icon } from "@/ui/Icon";
import { grantHeld, grantNarrowing, narrowingShort } from "./accessGroups";
import { RoleChip } from "./RoleChip";
import { staleNote } from "./securityText";

export function GrantChip({
  grant,
  label,
  note,
  extra,
  removeLabel,
  removing = false,
  onRemove,
}: {
  grant: Grant;
  /** What the chip says, where the list around it already says the kind ("RDM API" under "Consumer APIs"). */
  label?: string;
  /** More for the chip's tooltip, such as "Granted for the whole instance". */
  note?: string;
  /** Said after the narrowing, inside the chip: "· whole instance", "· through Curators". */
  extra?: ReactNode;
  /** The remove button's accessible name; without `onRemove` there is no button. */
  removeLabel?: string;
  removing?: boolean;
  onRemove?: () => void;
}) {
  const stale = staleNote(grant);
  const short = narrowingShort(grant);
  const title = [note, short && `Writes: ${grantNarrowing(grant)}`, stale].filter(Boolean).join(". ");
  return (
    <RoleChip as="li" grant={grant} title={title || undefined}>
      <span className="access-chip-name">{label ?? grantHeld(grant)}</span>
      {short && <small>· writes: {short}</small>}
      {extra}
      {stale && (
        <span className="access-chip-stale" role="img" aria-label={stale} title={stale}>
          <Icon name="state-conflict" size={13} />
        </span>
      )}
      {onRemove && (
        <button
          type="button"
          className="access-chip-remove"
          disabled={removing}
          aria-label={removeLabel}
          onClick={onRemove}
        >
          <Icon name="trash" size={13} />
        </button>
      )}
    </RoleChip>
  );
}
