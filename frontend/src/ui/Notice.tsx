import type { ReactNode } from "react";

export function Notice({
  tone = "info",
  title,
  children,
  actions,
  focusable = false,
}: {
  tone?: "info" | "success" | "warning" | "error";
  title?: string;
  children: ReactNode;
  actions?: ReactNode;
  focusable?: boolean;
}) {
  const urgent = tone === "error";
  return (
    <div
      className={`notice ${tone}-notice`}
      role={urgent ? "alert" : "status"}
      aria-live={urgent ? "assertive" : "polite"}
      tabIndex={focusable ? -1 : undefined}
    >
      <div>
        {title && <strong>{title}</strong>}
        <div>{children}</div>
      </div>
      {actions && <div className="notice-actions">{actions}</div>}
    </div>
  );
}
