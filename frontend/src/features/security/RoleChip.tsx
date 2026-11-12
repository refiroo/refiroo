/**
 * A role as the Access tab shows it (`.access-chip`): coloured by the kind of the grant's role
 * (`chipHue`). Used by the Access list, where the chip is a list item with its extras, and by
 * Settings › Account, where it is the role's heading.
 */

import type { ReactNode } from "react";
import type { Grant } from "@/types";
import { chipHue, roleKeyHue } from "./accessGroups";

export function RoleChip({
  grant,
  as: Tag = "span",
  title,
  children,
}: {
  grant: Grant;
  as?: "span" | "li";
  title?: string;
  children: ReactNode;
}) {
  return (
    <Tag className="access-chip" data-hue={chipHue(grant)} title={title}>
      {children}
    </Tag>
  );
}

/** A role named by its key (a person's roles in a list), in the colour its kind has everywhere. */
export function RoleKeyChip({ roleKey, title, children }: { roleKey: string; title?: string; children: ReactNode }) {
  return (
    <span className="access-chip" data-hue={roleKeyHue(roleKey)} title={title}>
      {children}
    </span>
  );
}
