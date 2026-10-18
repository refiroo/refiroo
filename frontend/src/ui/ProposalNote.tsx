/**
 * Why an element is as it is while it is still as an engine's proposal made it (0.10 A6b, D94;
 * the move editor's mapping rows, 0.11 X4, D141): the heading, what proposed it, the finding in one
 * sentence, its evidence on demand, and its alternatives as actions, each one step. Any edit makes
 * the element the user's, and the caller removes the note with the mark.
 */

import { useId, useState } from "react";

export interface ProposalAlternative {
  label: string;
  onSelect: () => void;
}

export function ProposalNote({
  subtitle,
  summary,
  evidence,
  alternatives,
  busy,
}: {
  subtitle: string;
  summary?: string;
  evidence: string[];
  alternatives: ProposalAlternative[];
  busy: boolean;
}) {
  const [open, setOpen] = useState(false);
  const id = useId();
  // A proposal read has its evidence, however short; none is read yet without one (0.10 A6b).
  const read = Boolean(summary) || evidence.length > 0;
  return (
    <section className="proposed-because" aria-labelledby={`${id}-title`}>
      <header className="proposed-because-head">
        <h3 id={`${id}-title`}>Proposed because</h3>
        <span className="muted">{subtitle}</span>
      </header>
      {summary ? <p className="proposed-because-summary">{summary}</p> : null}
      {read && (
        <ul id={`${id}-evidence`} className="proposed-because-evidence" hidden={!open}>
          {evidence.map((line, index) => (
            <li key={index}>{line}</li>
          ))}
        </ul>
      )}
      {read && (
        <div className="proposed-because-actions">
          <button
            type="button"
            className="secondary"
            aria-expanded={open}
            aria-controls={`${id}-evidence`}
            onClick={() => setOpen((current) => !current)}
          >
            {open ? "Hide the evidence" : "Evidence"}
          </button>
          {alternatives.map((alternative) => (
            <button
              key={alternative.label}
              type="button"
              className="secondary"
              disabled={busy}
              onClick={alternative.onSelect}
            >
              {alternative.label}
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
