import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { Icon } from "@/ui/Icon";

/** How long a toast stays once nothing holds it: no pointer over it and no focus in it. */
export const TOAST_TIMEOUT_MS = 8000;

type ShowToast = (message: string) => void;

const ToastContext = createContext<ShowToast | undefined>(undefined);

/**
 * Confirmations of a completed action, in one polite live region at the page's corner (Track U
 * U3). A toast stays until it is dismissed or has been visible for eight seconds without hover or
 * focus. Errors are never toasts: they stay inline beside what failed.
 */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<{ id: number; message: string }[]>([]);
  const sequence = useRef(0);
  const show = useCallback((message: string) => {
    sequence.current += 1;
    const id = sequence.current;
    setToasts((items) => [...items, { id, message }]);
  }, []);
  const dismiss = useCallback((id: number) => setToasts((items) => items.filter((item) => item.id !== id)), []);
  return (
    <ToastContext.Provider value={show}>
      {children}
      <div className="toast-region" role="status" aria-live="polite">
        {toasts.map((toast) => (
          <ToastItem key={toast.id} message={toast.message} onDismiss={() => dismiss(toast.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastItem({ message, onDismiss }: { message: string; onDismiss: () => void }) {
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
      className="toast"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocus={() => setFocused(true)}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setFocused(false);
      }}
    >
      <Icon name="check" />
      <span>{message}</span>
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
