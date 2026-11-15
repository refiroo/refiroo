/** "Where each sheet goes" (0.16 AP6, board 8): the design's profile sources, with every column's target folded. */

import { count, counted } from "@/lib/count";
import type { AiTaskDesign } from "@/types";
import { Card } from "@/ui/Card";
import { Disclosure } from "@/ui/Disclosure";
import { SettingsTable } from "@/ui/SettingsTable";
import { columnTargets, sourceKey, type ModelNames } from "./aiTaskDesign";

export function DesignSheets({ design, names }: { design: AiTaskDesign; names: ModelNames }) {
  const sources = design.profile?.sources ?? [];
  if (sources.length === 0) return null;
  return (
    <Card as="section" title="Where each sheet goes" className="task-table">
      <SettingsTable label="Sheets and the types they load" columns={["Sheet", "Goes to", "Key", "Columns"]}>
        {sources.map((source, index) => (
          <tr key={`${source.sheet}-${source.objectTypeKey}-${index}`}>
            <th scope="row" data-label="Sheet">
              {source.sheet ?? "The file"}
            </th>
            <td data-label="Goes to">
              {source.record === "existing"
                ? `Adds to ${names.typePlural(source.objectTypeKey)}`
                : names.typePlural(source.objectTypeKey)}
            </td>
            <td data-label="Key">{sourceKey(source, names)}</td>
            <td data-label="Columns">{count(source.columns.length)}</td>
          </tr>
        ))}
      </SettingsTable>
      <Disclosure variant="button" label="Show what each column fills" openLabel="Hide what each column fills">
        {sources.map((source, index) => (
          <div key={`${source.sheet}-${index}`}>
            <strong>
              Sheet “{source.sheet ?? "the file"}”: {counted(source.columns.length, "column")}
            </strong>
            <ul className="task-sheet-list">
              {columnTargets(source, names).map((item, at) => (
                <li key={at}>{item.line}</li>
              ))}
            </ul>
          </div>
        ))}
      </Disclosure>
    </Card>
  );
}
