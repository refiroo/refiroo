/**
 * A role as the Access tab shows it (`.access-chip`): coloured by the kind of the grant's role
 * (`chipHue`). Used by the Access list, where the chip is a list item with its extras, and by
 * Settings › Account, where it is the role's heading.
 */

import type { ReactNode } from "react";
import type { Grant } from "@/types";
import { chipHue } from "./accessGroups";

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
