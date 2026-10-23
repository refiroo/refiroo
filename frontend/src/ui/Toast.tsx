import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { Icon } from "@/ui/Icon";
import { DownloadLink } from "@/ui/DownloadLink";
import { RouteLink } from "@/ui/RouteLink";

/** How long a toast stays once nothing holds it: no pointer over it and no focus in it. */
export const TOAST_TIMEOUT_MS = 8000;

/** A link a toast carries: a route of this application (`onNavigate`) or a file to download. */
export interface ToastAction {
  label: string;
  href: string;
  onNavigate?: () => void;
  /** Saves the file `href` names through the page, with the access token (0.12 I2). */
  download?: () => Promise<void>;
}

/** `info` for news that is not a success, such as a job that failed or was cancelled. */
type ToastTone = "success" | "info";

type ShowToast = (message: string, options?: { actions?: ToastAction[]; tone?: ToastTone }) => void;

interface ShownToast {
  id: number;
  message: string;
  actions: ToastAction[];
  tone: ToastTone;
}

const ToastContext = createContext<ShowToast | undefined>(undefined);

/**
 * Confirmations of a completed action, in one polite live region at the page's corner (Track U
 * U3). A toast stays until it is dismissed or has been visible for eight seconds without hover or
 * focus. Errors are never toasts: they stay inline beside what failed; a background job's outcome
 * is told here with a link to the page that shows it (0.9 J1u, D59). A toast may carry links.
 */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ShownToast[]>([]);
  const sequence = useRef(0);
  const show = useCallback<ShowToast>((message, options) => {
    sequence.current += 1;
    const id = sequence.current;
    setToasts((items) => [
      ...items,
      { id, message, actions: options?.actions ?? [], tone: options?.tone ?? "success" },
    ]);
  }, []);
  const dismiss = useCallback((id: number) => setToasts((items) => items.filter((item) => item.id !== id)), []);
  return (
    <ToastContext.Provider value={show}>
      {children}
      <div className="toast-region" role="status" aria-live="polite">
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onDismiss={() => dismiss(toast.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastItem({ toast, onDismiss }: { toast: ShownToast; onDismiss: () => void }) {
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const dismiss = useRef(onDismiss);
  useEffect(() => {
    dismiss.current = onDismiss;
  });
  useEffect(() => {
    if (hovered || focused) return;
    const timer = window.setTimeout(() => dismiss.current(), TOAST_TIMEOUT_MS);
    return () => window.clearTimeout(timer);
  }, [hovered, focused]);
  return (
    <div
      className={toast.tone === "info" ? "toast info" : "toast"}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocus={() => setFocused(true)}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setFocused(false);
      }}
    >
      <Icon name={toast.tone === "info" ? "info" : "check"} />
      <span className="toast-body">
        <span>{toast.message}</span>
        {toast.actions.length > 0 && (
          <span className="toast-actions">
            {toast.actions.map((action) =>
              action.onNavigate ? (
                <RouteLink
                  key={action.label}
                  href={action.href}
                  onNavigate={() => {
                    action.onNavigate?.();
                    onDismiss();
                  }}
                >
                  {action.label}
                </RouteLink>
              ) : action.download ? (
                <DownloadLink key={action.label} href={action.href} save={action.download}>
                  {action.label}
                </DownloadLink>
              ) : (
                <a key={action.label} href={action.href}>
                  {action.label}
                </a>
              ),
            )}
          </span>
        )}
      </span>
      <button type="button" className="toast-dismiss" aria-label="Dismiss" onClick={onDismiss}>
        <Icon name="close" size={14} />
      </button>
    </div>
  );
}

/** Shows a confirmation; needs a `ToastProvider` above. */
export function useToast(): ShowToast {
  const show = useContext(ToastContext);
  if (!show) throw new Error("useToast needs a ToastProvider");
  return show;
}
