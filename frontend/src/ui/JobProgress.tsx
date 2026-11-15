/**
 * A job's progress (SR5): the native `progress` with the line that says how far it is. No total, or a total of
 * zero, is the indeterminate bar. `role` puts the live status on the wrapper or on the text, as each place does;
 * without a line it is the bare bar (the editor's "Proposing", which has its own styling).
 */

import type { ReactNode } from "react";

export function JobProgress({
  label = "Progress",
  processed,
  total,
  role,
  className,
  children,
}: {
  /** The bar's accessible name. */
  label?: string;
  processed?: number;
  /** `null` or `undefined` when the work has no known size. */
  total?: number | null;
  role?: "wrapper" | "text";
  /** Only for the bare bar. */
  className?: string;
  children?: ReactNode;
}) {
  const bar = (
    <progress
      value={total ? processed : undefined}
      max={total ?? undefined}
      aria-label={label}
      className={children === undefined ? className : undefined}
    />
  );
  if (children === undefined) return bar;
  return (
    <div className="job-progress" role={role === "wrapper" ? "status" : undefined}>
      {bar}
      <span role={role === "text" ? "status" : undefined}>{children}</span>
    </div>
  );
}
