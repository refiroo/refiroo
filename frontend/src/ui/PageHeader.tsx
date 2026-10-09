import type { HTMLAttributes, ReactNode, Ref } from "react";

/**
 * A page's header: an optional icon and eyebrow, the page title (the page's only `h1`), a
 * description and the page actions (Track U U2). The title takes the 30px step of the type scale.
 *
 * `focusTitle` makes the title a programmatic focus target (route changes move focus to it);
 * `variant="detail"` lets the title take the free width and wraps the actions under it when narrow.
 * A title edited in place (UA8) passes `titleLabel`, so the heading is named by the title and not
 * by its control, and `titleEditor`, which takes the heading's place while it is open.
 */
export function PageHeader({
  title,
  titleLabel,
  titleEditor,
  titleRef,
  titleId,
  focusTitle = false,
  eyebrow,
  description,
  descriptionClassName,
  icon,
  actions,
  variant = "collection",
  className,
  ...rest
}: {
  title: ReactNode;
  /** The heading's accessible name, where `title` is a control. */
  titleLabel?: string;
  /** Shown instead of the heading while the title is edited. */
  titleEditor?: ReactNode;
  titleRef?: Ref<HTMLHeadingElement>;
  /** Lets a region elsewhere on the page name itself after the title. */
  titleId?: string;
  focusTitle?: boolean;
  eyebrow?: ReactNode;
  description?: ReactNode;
  descriptionClassName?: string;
  /** Decorative: hidden from assistive technology. */
  icon?: ReactNode;
  actions?: ReactNode;
  variant?: "collection" | "detail" | "plain";
} & Omit<HTMLAttributes<HTMLElement>, "title">) {
  return (
    <header className={["page-header", `${variant}-header`, className].filter(Boolean).join(" ")} {...rest}>
      <div className="page-title">
        {icon && (
          <span className="page-icon" aria-hidden="true">
            {icon}
          </span>
        )}
        <div className="page-title-text">
          {eyebrow && <p className="eyebrow">{eyebrow}</p>}
          {titleEditor ?? (
            <h1 ref={titleRef} id={titleId} aria-label={titleLabel} tabIndex={focusTitle || titleRef ? -1 : undefined}>
              {title}
            </h1>
          )}
          {description !== undefined &&
            description !== null &&
            description !== "" &&
            (typeof description === "string" ? (
              <p className={descriptionClassName}>{description}</p>
            ) : (
              <div className={["page-description", descriptionClassName].filter(Boolean).join(" ")}>{description}</div>
            ))}
        </div>
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  );
}
