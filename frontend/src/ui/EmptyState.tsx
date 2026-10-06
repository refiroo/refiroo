import type { ReactNode } from "react";

/** What a list shows when it has nothing to show, and the action that fills it (Track U U3). */
export function EmptyState({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div className="empty-message">
      <p>{children}</p>
      {action && <div className="empty-message-action">{action}</div>}
    </div>
  );
}
