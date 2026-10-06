import { useId, type ReactNode } from "react";

/**
 * A titled block of a page with a rule under its heading and no card (ADR-039's ruled sections,
 * Track U U3). The section is a region named by its heading; `actions` sit at the heading's right.
 */
export function Section({
  title,
  description,
  actions,
  headingLevel = 2,
  children,
  className,
}: {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  headingLevel?: 2 | 3;
  children?: ReactNode;
  className?: string;
}) {
  const headingId = useId();
  const Heading = headingLevel === 2 ? "h2" : "h3";
  return (
    <section className={["section", className].filter(Boolean).join(" ")} aria-labelledby={headingId}>
      <div className="section-header">
        <Heading id={headingId}>{title}</Heading>
        {actions && <div className="section-actions">{actions}</div>}
      </div>
      {description && <p className="section-description">{description}</p>}
      {children}
    </section>
  );
}
