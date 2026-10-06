import { useId, type ReactNode } from "react";

/** What a field's control takes so its label, help and error reach assistive technology. */
export interface FieldControlProps {
  id: string;
  "aria-describedby"?: string;
  "aria-invalid"?: true;
}

/**
 * A form field: its label, the control, a help line and an error (Track U U3). A single control
 * receives the field's `id` and description through the render prop; `group` makes the field a
 * fieldset whose legend names a set of controls, such as radio buttons.
 */
export function FormField({
  label,
  help,
  error,
  group = false,
  className,
  children,
}: {
  label: ReactNode;
  help?: ReactNode;
  error?: ReactNode;
  group?: boolean;
  className?: string;
  children: (control: FieldControlProps) => ReactNode;
}) {
  const id = useId();
  const helpId = `${id}-help`;
  const errorId = `${id}-error`;
  const describedBy = [help ? helpId : "", error ? errorId : ""].filter(Boolean).join(" ") || undefined;
  const control: FieldControlProps = {
    id,
    ...(describedBy && !group ? { "aria-describedby": describedBy } : {}),
    ...(error ? { "aria-invalid": true as const } : {}),
  };
  const notes = (
    <>
      {help && (
        <small id={helpId} className="field-description">
          {help}
        </small>
      )}
      {error && (
        <small id={errorId} className="field-error">
          {error}
        </small>
      )}
    </>
  );
  const classes = ["form-field", className].filter(Boolean).join(" ");
  if (group)
    return (
      <fieldset className={classes} aria-describedby={describedBy}>
        <legend>{label}</legend>
        {children(control)}
        {notes}
      </fieldset>
    );
  return (
    <div className={classes}>
      <label htmlFor={id}>{label}</label>
      {children(control)}
      {notes}
    </div>
  );
}
