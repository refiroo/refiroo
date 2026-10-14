/**
 * Why an element is as it is, while it is still as the inference proposed it (0.10 A6b, D94): the
 * pattern, the rule's finding in one sentence, its evidence on demand, and its alternatives as
 * actions, each one step. Shown in the centre of a selected type, attribute type, relation type and
 * column; any edit makes the element the administrator's, and the section goes with the mark.
 */

import { useId, useState } from "react";
import type { DraftOperation, Proposal } from "@/types";
import { StatusPill } from "@/ui/StatusPill";
import { patternLabel } from "@/features/model-editor/proposing";

/** The mark of an element still as proposed: in place of New, until an edit makes it the administrator's. */
export function ProposedPill() {
  return (
    <StatusPill tone="proposed" className="mark-pill">
      Proposed
    </StatusPill>
  );
}

type Value = unknown;

function words(value: Value): string {
  if (value === null || value === undefined) return "—";
  if (Array.isArray(value)) return value.map(words).join(", ");
  if (typeof value === "object") {
    const item = value as Record<string, Value>;
    if ("value" in item && "count" in item) return `${String(item.value)} ×${String(item.count)}`;
    if ("column" in item && "constantIn" in item)
      return `${String(item.column)}: constant in ${String(item.constantIn)}`;
    if ("code" in item && "names" in item) return `${String(item.code)}: ${words(item.names)}`;
    return Object.entries(item)
      .map(([key, inner]) => `${key} ${words(inner)}`)
      .join(" · ");
  }
  if (typeof value === "number" && value > 0 && value < 1) return `${Math.round(value * 100)}%`;
  return String(value);
}

/** The evidence of a proposal in lines: each column's statistics, then the pattern's own facts. */
export function evidenceLines(evidence: Record<string, Value>): string[] {
  const lines: string[] = [];
  const columns = Array.isArray(evidence.columns) ? (evidence.columns as Record<string, Value>[]) : [];
  for (const column of columns)
    lines.push(
      `${String(column.column)} (${String(column.letter)}): ${String(column.filled)} of ${String(column.rows)} filled · ` +
        `${String(column.distinct)} distinct${Array.isArray(column.values) && column.values.length ? ` · ${words(column.values)}` : ""}`,
    );
  for (const [key, value] of Object.entries(evidence)) {
    if (key === "columns" || value === null || value === undefined || (Array.isArray(value) && !value.length)) continue;
    const label = key.replace(/([A-Z])/g, " $1").toLowerCase();
    lines.push(`${label[0].toUpperCase()}${label.slice(1)}: ${words(value)}`);
  }
  return lines;
}

export function ProposedBecause({
  proposal,
  busy,
  run,
}: {
  /** The proposal the element is still as; its evidence reads once the inference's proposals are read. */
  proposal: Proposal | undefined;
  busy: boolean;
  run: (operations: DraftOperation[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <section className="proposed-because" aria-labelledby={`${id}-title`}>
      <header className="proposed-because-head">
        <h3 id={`${id}-title`}>Proposed because</h3>
        <span className="muted">
          {proposal ? patternLabel(proposal.pattern) : "From the workbook"} · edit anything here to make it yours
        </span>
      </header>
      {proposal ? <p className="proposed-because-summary">{proposal.summary}</p> : null}
      {proposal && (
        <ul id={`${id}-evidence`} className="proposed-because-evidence" hidden={!open}>
          {evidenceLines(proposal.evidence).map((line, index) => (
            <li key={index}>{line}</li>
          ))}
        </ul>
      )}
      {proposal && (
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
          {proposal.alternatives.map((alternative) => (
            <button
              key={alternative.label}
              type="button"
              className="secondary"
              disabled={busy}
              onClick={() => run(alternative.operations)}
            >
              {alternative.label}
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
