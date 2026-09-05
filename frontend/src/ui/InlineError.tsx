export function InlineError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="inline-state error-notice" role="alert">
      <span>{message}</span>
      <button type="button" className="secondary" onClick={onRetry}>
        Retry
      </button>
    </div>
  );
}
