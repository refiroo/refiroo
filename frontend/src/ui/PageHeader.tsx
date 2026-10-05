import type { HTMLAttributes, ReactNode, Ref } from "react";

/**
 * A page's header: an optional icon and eyebrow, the page title (the page's only `h1`), a
 * description and the page actions (Track U U2). The title takes the 30px step of the type scale.
 *
 * `focusTitle` makes the title a programmatic focus target (route changes move focus to it);
 * `variant="detail"` lets the title take the free width and wraps the actions under it when narrow.
 */
export function PageHeader({
  title,
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
          <h1 ref={titleRef} id={titleId} tabIndex={focusTitle || titleRef ? -1 : undefined}>
            {title}
          </h1>
          {description !== undefined && description !== null && description !== "" && (
            <p className={descriptionClassName}>{description}</p>
          )}
        </div>
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  );
}
