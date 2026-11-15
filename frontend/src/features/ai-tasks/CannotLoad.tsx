/**
 * The load step without its permission (0.16 AP13, AP-D59): the page names who can do it instead of showing a button
 * the person cannot use, and offers the task's link to pass on. Loading is a change set, so it needs Work in change
 * sets in the task's workspace.
 */

import { useState } from "react";
import { Notice } from "@/ui/Notice";
import { copyText } from "@/lib/copyText";

export function CannotLoad({ workspaceLabel }: { workspaceLabel: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <Notice tone="info" title="The load is for someone else to start">
      <p>
        Loading needs Work in change sets in {workspaceLabel}, which you do not hold. Someone who does can load it from
        this page.
      </p>
      <div className="task-actions">
        <button
          type="button"
          className="secondary"
          onClick={() => {
            void copyText(window.location.href).then((copied) => copied && setCopied(true));
          }}
        >
          Copy the link to this task
        </button>
        {copied && <span role="status">Link copied</span>}
      </div>
    </Notice>
  );
}
