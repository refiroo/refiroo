import { useId, type ReactNode } from "react";

/**
 * A titled block on the raised surface with a light outline and no shadow (Track U U2, U-D8).
 * Kept so that cards can be judged in the product against ADR-039's ruled sections; U6 moves
 * today's `.surface` panels onto `Card` or onto a section, depending on which reads better.
 *
 * With a title the card is a labelled region (`section` named by its heading); without one it
 * is a plain container.
 */
export function Card({
  title,
  headingLevel = 2,
  actions,
  children,
  className,
}: {
  title?: ReactNode;
  headingLevel?: 2 | 3;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  const headingId = useId();
  const Heading = headingLevel === 2 ? "h2" : "h3";
  const classes = ["card", className].filter(Boolean).join(" ");
  if (!title) return <div className={classes}>{children}</div>;
  return (
    <section className={classes} aria-labelledby={headingId}>
      <div className="card-header">
        <Heading id={headingId}>{title}</Heading>
        {actions && <div className="card-actions">{actions}</div>}
      </div>
      {children}
    </section>
  );
}
