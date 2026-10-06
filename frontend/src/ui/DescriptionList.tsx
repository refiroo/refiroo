import type { ReactNode } from "react";

export interface DescriptionItem {
  term: ReactNode;
  value: ReactNode;
  /** Needed when `term` is not a string. */
  key?: string;
}

/** Facts as term and value pairs (Track U U3): a record's, a release's or the deployment's. */
export function DescriptionList({ items, className }: { items: DescriptionItem[]; className?: string }) {
  return (
    <dl className={["description-list", className].filter(Boolean).join(" ")}>
      {items.map((item, index) => (
        <div key={item.key ?? (typeof item.term === "string" ? item.term : index)}>
          <dt>{item.term}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}
