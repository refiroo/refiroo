import { Notice } from "@/ui/Notice";

export function InlineError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <Notice
      tone="error"
      title="Could not load this content"
      actions={
        <button type="button" className="secondary" onClick={onRetry}>
          Retry
        </button>
      }
    >
      {message}
    </Notice>
  );
}
