/** What the assistant said, a provider failure or an operation the engine refused (0.16 AP6a), above the tables: the newest three, the earlier ones folded (0.16 AP13: what the person just did is the newest). */

import type { AiTaskNote } from "@/types";
import { AssistantText } from "@/ui/AssistantText";
import { Disclosure } from "@/ui/Disclosure";
import { Notice } from "@/ui/Notice";
import { plural } from "./aiTaskText";

const LAST = 3;

function One({ note }: { note: AiTaskNote }) {
  return (
    <Notice
      tone={note.kind === "note" ? "info" : "warning"}
      title={note.kind === "refused" ? "The engine refused an operation" : undefined}
    >
      <AssistantText text={note.text} />
    </Notice>
  );
}

export function TaskNotes({ notes }: { notes: AiTaskNote[] }) {
  const shown = notes.filter((note) => note.kind !== "note" || note.text.trim());
  if (shown.length === 0) return null;
  const earlier = shown.slice(0, -LAST);
  return (
    <div className="task-notes">
      {earlier.length > 0 && (
        <Disclosure variant="link" label={`${plural(earlier.length, "earlier note")}`}>
          {earlier.map((note, index) => (
            <One key={`${note.at}-${index}`} note={note} />
          ))}
        </Disclosure>
      )}
      {shown.slice(-LAST).map((note, index) => (
        <One key={`${note.at}-${earlier.length + index}`} note={note} />
      ))}
    </div>
  );
}
