import type { ButtonHTMLAttributes } from "react";
import { Icon, type IconName } from "@/ui/Icon";

/**
 * An action shown as an icon (UA8, U-D18): its accessible name says the action and what it acts
 * on, its tooltip says the action. A 32px target, 40px on touch; `danger` turns red on hover and
 * focus. Every icon-only action uses it, so none copies button markup.
 */
export function IconButton({
  icon,
  label,
  tooltip,
  tone = "default",
  quiet = false,
  className,
  ...rest
}: {
  icon: IconName;
  /** The accessible name: the action and what it acts on ("Delete Kept by: System B"). */
  label: string;
  /** The tooltip: the action alone; the label when not given. */
  tooltip?: string;
  tone?: "default" | "danger";
  /** Borderless, in the tertiary ink until hovered or focused: for actions repeated on every row. */
  quiet?: boolean;
} & Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children" | "aria-label" | "title">) {
  return (
    <button
      type="button"
      className={["icon-button", quiet && "icon-button-quiet", tone === "danger" && "icon-button-danger", className]
        .filter(Boolean)
        .join(" ")}
      aria-label={label}
      title={tooltip ?? label}
      {...rest}
    >
      <Icon name={icon} size={15} />
    </button>
  );
}
