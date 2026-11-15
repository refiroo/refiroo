/**
 * The small questions the canvas asks at a drop or from a menu (0.17 PL3b): a searchable chooser for
 * the lists a menu would otherwise name one by one, and which of several tied columns carries a join
 * (the questions of the readings are the model editor's `ReadingAsks`, shared). Each is
 * a titled popover under the element it concerns (`AnchoredPopover`, as the editor's small operations
 * are) and sends nothing itself: its answer goes back to the page, which sends one request.
 */

import { useMemo, useState } from "react";
import { count } from "@/lib/count";
import type { JoinCandidate } from "@/types/sources";
import { Frame } from "@/features/model-editor/ReadingAsks";

export interface Choice {
  id: string;
  label: string;
  /** A second, quieter line: which field of which list, how many rows. */
  hint?: string;
}

/** Many lists or columns behind one control: a search, then the choices that match, each a button. */
export function ChooserPopover({
  anchor,
  title,
  searchLabel,
  choices,
  onChoose,
  onClose,
}: {
  anchor: HTMLElement;
  title: string;
  searchLabel: string;
  choices: readonly Choice[];
  onChoose: (id: string) => void;
  onClose: () => void;
}) {
  const [query, setQuery] = useState("");
  const shown = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return needle
      ? choices.filter((item) => `${item.label} ${item.hint ?? ""}`.toLowerCase().includes(needle))
      : choices;
  }, [choices, query]);
  return (
    <Frame anchor={anchor} title={title} onClose={onClose}>
      <div className="editor-popover-form canvas-chooser">
        <input
          type="search"
          autoFocus
          aria-label={searchLabel}
          placeholder={searchLabel}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && shown.length === 1) {
              event.preventDefault();
              onChoose(shown[0].id);
            }
          }}
        />
        <ul className="canvas-chooser-list" aria-label={title}>
          {shown.map((item) => (
            <li key={item.id}>
              <button type="button" className="canvas-chooser-choice" onClick={() => onChoose(item.id)}>
                <span>{item.label}</span>
                {item.hint && <small>{item.hint}</small>}
              </button>
            </li>
          ))}
          {shown.length === 0 && <li className="canvas-chooser-none">Nothing matches.</li>}
        </ul>
      </div>
    </Frame>
  );
}

/** Two columns carry the join equally well: which one names the records is asked, never guessed. */
export function TiePopover({
  anchor,
  other,
  candidates,
  onChoose,
  onClose,
}: {
  anchor: HTMLElement;
  /** The list whose records the columns name. */
  other: string;
  candidates: readonly JoinCandidate[];
  /** A column's letter, or none to make the link and fill nothing. */
  onChoose: (letter: string | null) => void;
  onClose: () => void;
}) {
  return (
    <Frame anchor={anchor} title={`Which column names the ${other} records?`} onClose={onClose}>
      <div className="editor-popover-form canvas-chooser">
        <p className="muted">These columns hold the same values of {other}, so refiroo does not choose one for you.</p>
        <ul className="canvas-chooser-list" aria-label="Columns that match equally">
          {candidates.map((item) => (
            <li key={item.letter}>
              <button type="button" className="canvas-chooser-choice" onClick={() => onChoose(item.letter)}>
                <span>{item.header}</span>
                <small>
                  column {item.letter} · {count(item.matchedRows)} rows match
                </small>
              </button>
            </li>
          ))}
          <li>
            <button type="button" className="canvas-chooser-choice" onClick={() => onChoose(null)}>
              <span>None of them</span>
              <small>Make the link and fill nothing yet</small>
            </button>
          </li>
        </ul>
      </div>
    </Frame>
  );
}
