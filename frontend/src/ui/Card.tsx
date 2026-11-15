import { useId, type HTMLAttributes, type ReactNode } from "react";

/**
 * A block on the raised surface with a light outline and no shadow (Track U U2, U-D8): every
 * panel, collection surface and detail pane of the content (UA6 moved the older `.surface` panels
 * onto it).
 *
 * With a title the card is a labelled region (`section` named by its heading). Without one it is a
 * plain container, a `section` when `as` says so (its caller names it). `flush` drops the padding
 * for contents that draw their own edges, such as a toolbar over a table.
 */
export function Card({
  title,
  headingLevel = 2,
  actions,
  children,
  className,
  as = "div",
  flush = false,
  ...rest
}: {
  title?: ReactNode;
  headingLevel?: 2 | 3;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  as?: "div" | "section";
  flush?: boolean;
} & Omit<HTMLAttributes<HTMLElement>, "title">) {
  const headingId = useId();
  const Heading = headingLevel === 2 ? "h2" : "h3";
  const classes = ["card", flush && "card-flush", className].filter(Boolean).join(" ");
  if (!title) {
    const Element = as;
    return (
      <Element className={classes} {...rest}>
        {children}
      </Element>
    );
  }
  return (
    <section className={classes} aria-labelledby={headingId} {...rest}>
      <div className="card-header">
        <Heading id={headingId}>{title}</Heading>
        {actions && <div className="card-actions wrap-row">{actions}</div>}
      </div>
      {children}
    </section>
  );
}
