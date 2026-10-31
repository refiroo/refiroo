/** What the assistant said, a provider failure or an operation the engine refused (0.16 AP6a), above the tables; past three, folded. */

import type { AiTaskNote } from "@/types";
import { Disclosure } from "@/ui/Disclosure";
import { Notice } from "@/ui/Notice";
import { plural } from "./aiTaskText";

const FIRST = 3;

function One({ note }: { note: AiTaskNote }) {
  return (
    <Notice
      tone={note.kind === "note" ? "info" : "warning"}
      title={note.kind === "refused" ? "The engine refused an operation" : undefined}
    >
      {note.text}
    </Notice>
  );
}

export function TaskNotes({ notes }: { notes: AiTaskNote[] }) {
  const shown = notes.filter((note) => note.kind !== "note" || note.text.trim());
  if (shown.length === 0) return null;
  const more = shown.slice(FIRST);
  return (
    <div className="task-notes">
      {shown.slice(0, FIRST).map((note, index) => (
        <One key={`${note.at}-${index}`} note={note} />
      ))}
      {more.length > 0 && (
        <Disclosure variant="link" label={`${plural(more.length, "more note")}`}>
          {more.map((note, index) => (
            <One key={`${note.at}-${index}`} note={note} />
          ))}
        </Disclosure>
      )}
    </div>
  );
}
