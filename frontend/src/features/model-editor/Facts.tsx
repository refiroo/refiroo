/**
 * A row of facts about the draft or an element, each a quiet chip with its glyph (0.10 A4a): the
 * base release and version in the editor's header, the key and whether it can change on an element.
 */

import type { ReactNode } from "react";
import { Icon, type IconName } from "@/ui/Icon";

export type Fact = { icon: IconName; label: ReactNode; title?: string };

export function Facts({ facts, label }: { facts: Fact[]; label: string }) {
  return (
    <ul className="editor-facts" aria-label={label}>
      {facts.map((fact, index) => (
        <li key={index} className="editor-fact" title={fact.title}>
          <Icon name={fact.icon} size={13} />
          <span>{fact.label}</span>
        </li>
      ))}
    </ul>
  );
}
