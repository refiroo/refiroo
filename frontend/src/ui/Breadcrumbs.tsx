import type { ReactNode } from "react";

/** One place in a trail: its content (a link or a button to go there), the current one last. */
export interface Crumb {
  key: string;
  content: ReactNode;
  current?: boolean;
}

/**
 * Where a page stands, as a trail of places separated by "›" (a record's application and
 * ancestors; a Settings page under its group and list, 0.10 A5c). Left-out places are skipped.
 */
export function Breadcrumbs({ items }: { items: (Crumb | false | undefined)[] }) {
  return (
    <nav className="breadcrumbs" aria-label="Breadcrumb">
      <ol>
        {items
          .filter((item): item is Crumb => Boolean(item))
          .map((item) => (
            <li key={item.key} {...(item.current ? { "aria-current": "location" as const } : {})}>
              {item.content}
            </li>
          ))}
      </ol>
    </nav>
  );
}
