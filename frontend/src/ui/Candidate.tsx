import type { LabelHTMLAttributes, ReactNode } from "react";
import type { Hue } from "@/model/hues";
import { HueTile } from "@/ui/HueTile";

/**
 * One choice in a dialog's list of records (a new parent, a mapping target, a record to link, a
 * place to create one): its radio or checkbox, its type's tile (ADR-040), its name and a secondary
 * line, then any notes at the end. The label is the whole row, so a click anywhere on it chooses it.
 *
 * `type` gives the record's tile; `null` keeps the tile's room empty, for a choice that is not a
 * record (such as "Top level") in a list of records.
 */
export function Candidate({
  control,
  type,
  name,
  detail,
  selected = false,
  disabled = false,
  className,
  children,
  ...rest
}: {
  /** The row's input. */
  control: ReactNode;
  type?: { hue?: Hue; icon?: string } | null;
  name: ReactNode;
  detail?: ReactNode;
  selected?: boolean;
  disabled?: boolean;
  className?: string;
  /** Notes after the text, such as why the record cannot be chosen. */
  children?: ReactNode;
} & Omit<LabelHTMLAttributes<HTMLLabelElement>, "className" | "children">) {
  const classes = ["candidate", selected && "selected", disabled && "is-disabled", className].filter(Boolean).join(" ");
  return (
    <label className={classes} {...rest}>
      {control}
      {type === null ? (
        <span className="candidate-tile-space" aria-hidden="true" />
      ) : (
        type && <HueTile hue={type.hue} icon={type.icon} size={18} />
      )}
      <span className="candidate-text">
        <span className="candidate-name">{name}</span>
        {detail && <small>{detail}</small>}
      </span>
      {children}
    </label>
  );
}
