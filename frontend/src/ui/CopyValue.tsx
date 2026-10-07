/**
 * A value a person copies elsewhere, such as a record's ID (UA4 revision): its label, the value in
 * the monospace face (selectable), and a button that copies it, announcing the result.
 */

import { useState } from "react";
import { Icon } from "@/ui/Icon";

export function CopyValue({ label, value }: { label: string; value: string }) {
  const [message, setMessage] = useState("");
  async function copy() {
    try {
      if (!navigator.clipboard) throw new Error("Clipboard access is unavailable");
      await navigator.clipboard.writeText(value);
      setMessage(`${label} copied.`);
    } catch {
      setMessage(`Could not copy the ${label}. Select it and copy it manually.`);
    }
  }
  return (
    <span className="copy-value">
      <span className="copy-value-label">{label}</span>
      <code>{value}</code>
      <button
        type="button"
        className="copy-value-button"
        aria-label={`Copy ${label}`}
        title={`Copy ${label}`}
        onClick={copy}
      >
        <Icon name="copy" size={13} />
      </button>
      <span className="visually-hidden" role="status">
        {message}
      </span>
    </span>
  );
}
