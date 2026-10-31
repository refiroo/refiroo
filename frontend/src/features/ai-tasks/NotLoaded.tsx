/** What a load does not carry, folded and grouped by sheet (0.16 AP6a): never one unbroken list of left-outs. */

import { Disclosure } from "@/ui/Disclosure";
import { bySheet } from "./aiTaskText";

export function NotLoaded({ label, entries }: { label: string; entries: { sheet: string; text: string }[] }) {
  if (entries.length === 0) return null;
  return (
    <Disclosure variant="link" label={label}>
      {bySheet(entries).map((group) => (
        <div key={group.sheet}>
          <strong>Sheet “{group.sheet}”</strong>
          <ul className="task-sheet-list">
            {group.items.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </div>
      ))}
    </Disclosure>
  );
}
