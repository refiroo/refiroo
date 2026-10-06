import type { ReactNode } from "react";

/**
 * What a list shows when it has nothing to show, and the action that fills it (Track U U3). An
 * optional icon (decorative) sits above the message, as a table's empty state shows its type tile.
 */
export function EmptyState({ children, icon, action }: { children: ReactNode; icon?: ReactNode; action?: ReactNode }) {
  return (
    <div className="empty-message">
      {icon && (
        <span className="empty-message-icon" aria-hidden="true">
          {icon}
        </span>
      )}
      <p>{children}</p>
      {action && <div className="empty-message-action">{action}</div>}
    </div>
  );
}
