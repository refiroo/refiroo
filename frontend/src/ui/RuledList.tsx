/**
 * A short list of items, each a few lines with its actions at the end, as ruled rows on one card
 * (ADR-040: ruled rows on a white card; pills only for states). The change set and publication
 * lists use it. Each item is an `article` named by its heading.
 */

import { useId, type ReactNode } from "react";
import { Card } from "@/ui/Card";

export function RuledList({ label, children }: { label: string; children: ReactNode }) {
  return (
    <Card flush className="ruled-list-card">
      <ul className="ruled-list list-reset" aria-label={label}>
        {children}
      </ul>
    </Card>
  );
}

export function RuledListItem({
  title,
  marker,
  meta,
  children,
  actions,
  className,
}: {
  /** The item's heading (level 2), which names its article. */
  title: ReactNode;
  /** A small decorative mark before the heading, such as a context's dot. */
  marker?: ReactNode;
  /** One secondary line under the heading. */
  meta?: ReactNode;
  /** Further detail under the meta line. */
  children?: ReactNode;
  actions?: ReactNode;
  className?: string;
}) {
  const headingId = useId();
  return (
    <li>
      <article className={["ruled-list-item", className].filter(Boolean).join(" ")} aria-labelledby={headingId}>
        <div className="ruled-list-main">
          <h2 id={headingId}>
            {marker}
            {title}
          </h2>
          {meta && <p className="ruled-list-meta">{meta}</p>}
          {children}
        </div>
        {actions && <div className="ruled-list-actions">{actions}</div>}
      </article>
    </li>
  );
}
