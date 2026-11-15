/**
 * An on/off setting that takes effect when flipped: a button with the `switch` role (0.12 I4a). The `canvas`
 * variant is the workbook canvas's own smaller switch (SR5); the name is `label`, or the element that says it
 * (`labelledBy`).
 */
export function Switch({
  label,
  labelledBy,
  checked,
  disabled,
  variant,
  onChange,
}: {
  label?: string;
  labelledBy?: string;
  checked: boolean;
  disabled?: boolean;
  variant?: "canvas";
  onChange: (checked: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      className={variant === "canvas" ? "canvas-switch" : "switch"}
      aria-checked={checked}
      aria-label={label}
      aria-labelledby={labelledBy}
      disabled={disabled}
      onClick={() => onChange(!checked)}
    />
  );
}
