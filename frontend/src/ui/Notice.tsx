import { useEffect, useRef } from "react";
import type { ReactNode } from "react";

export function Notice({
  tone = "info",
  title,
  children,
  actions,
  focusOnMount = false,
}: {
  tone?: "info" | "success" | "warning" | "error";
  title?: string;
  children: ReactNode;
  actions?: ReactNode;
  /** Moves focus to a newly mounted task-level error or conflict summary. */
  focusOnMount?: boolean;
}) {
  const urgent = tone === "error";
  const noticeRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (focusOnMount) noticeRef.current?.focus();
  }, [focusOnMount]);

  return (
    <div
      ref={noticeRef}
      className={`notice ${tone}-notice`}
      role={urgent ? "alert" : "status"}
      aria-live={urgent ? "assertive" : "polite"}
      tabIndex={focusOnMount ? -1 : undefined}
    >
      <div>
        {title && <strong>{title}</strong>}
        <div>{children}</div>
      </div>
      {actions && <div className="notice-actions">{actions}</div>}
    </div>
  );
}
