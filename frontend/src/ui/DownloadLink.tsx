import { useState, type ReactNode } from "react";
import { errorMessage } from "@/api/errors";

/**
 * A link that saves a file through the page instead of navigating to it (0.12 I2, D247), so the
 * request can carry the access token. `save` fetches and saves; a failure is said beside the link.
 */
export function DownloadLink({
  href,
  save,
  className,
  children,
}: {
  href: string;
  save: () => Promise<void>;
  className?: string;
  children: ReactNode;
}) {
  const [failure, setFailure] = useState<string>();
  const [saving, setSaving] = useState(false);
  return (
    <>
      <a
        className={className}
        href={href}
        aria-busy={saving || undefined}
        onClick={(event) => {
          event.preventDefault();
          if (saving) return;
          setFailure(undefined);
          setSaving(true);
          save()
            .catch((cause: unknown) => setFailure(errorMessage(cause)))
            .finally(() => setSaving(false));
        }}
      >
        {children}
      </a>
      {failure && (
        <span className="download-failure" role="alert">
          {failure}
        </span>
      )}
    </>
  );
}
