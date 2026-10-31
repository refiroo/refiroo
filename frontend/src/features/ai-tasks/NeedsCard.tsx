/** One table that needs the person (0.16 AP6a, board 5): what it is, the evidence and only the choices that apply. */

import type { AiTaskTable } from "@/types";
import { count } from "@/features/settings/limits";
import { AiOriginMark } from "@/ui/AiOriginMark";
import { Card } from "@/ui/Card";
import { Choice } from "@/ui/Choice";
import { Disclosure } from "@/ui/Disclosure";
import { FormField } from "@/ui/FormField";
import { StatusPill } from "@/ui/StatusPill";
import { attentionPill, foundOn, plural, type TableChoices } from "./aiTaskText";

export function NeedsCard({
  table,
  group,
  choices,
  onChange,
}: {
  table: AiTaskTable;
  /** The model group the table's type stands in. */
  group?: string;
  choices: TableChoices;
  onChange: (choices: TableChoices) => void;
}) {
  const pill = attentionPill(table);
  const leftOut = table.leftOut ?? [];
  const name = table.table;
  const title = [table.typeName ?? foundOn(table), group].filter(Boolean).join(" · ");
  const update = table.as === "update";
  return (
    <Card className="task-table" aria-label={`${title}, ${foundOn(table)}`} as="section">
      <div className="task-table-head">
        <h3>
          {title} · sheet “{table.sheet}”{table.range ? ` ${table.range}` : ""} · {plural(table.rows, "row")}
        </h3>
        <StatusPill tone={pill.tone}>{pill.text}</StatusPill>
      </div>
      {/* An update's reason ("An update of …") is the pill's, so its evidence says why; a table not
          loaded says its reason first. */}
      <p className="task-reason">
        {update ? table.evidence || table.reason : [table.reason, table.evidence].filter(Boolean).join(" ")}
      </p>
      {(table.notes ?? []).map((note) => (
        <p key={note} className="task-reason">
          {note}
        </p>
      ))}
      {table.owner === "assistant" && table.origin && <AiOriginMark origin={table.origin} variant="target" />}
      {update && (
        <div className="task-choices">
          {table.keyOptions.length > 1 ? (
            <FormField label="Match rows by" group>
              {() => (
                <Choice
                  name={`${name}-key`}
                  value={choices.keyColumn}
                  options={table.keyOptions.map((option) => [
                    option.column,
                    `${option.header} (${count(option.matched)} match)`,
                  ])}
                  onChange={(keyColumn) => onChange({ ...choices, keyColumn })}
                />
              )}
            </FormField>
          ) : table.keyOptions.length === 0 ? (
            <p className="admin-hint">No column of the sheet matches the stored records.</p>
          ) : null}
          {table.new > 0 && (
            <FormField label={`The ${count(table.new)} new ${table.new === 1 ? "key" : "keys"}`} group>
              {() => (
                <Choice
                  name={`${name}-new`}
                  value={choices.newRecords}
                  options={[
                    ["create", "Create them"],
                    ["leaveOut", "Leave them out"],
                  ]}
                  onChange={(newRecords) => onChange({ ...choices, newRecords })}
                />
              )}
            </FormField>
          )}
          {table.namesDiffer > 0 && (
            <FormField
              label={`${count(table.namesDiffer)} ${table.namesDiffer === 1 ? "name differs" : "names differ"} from the stored ${table.namesDiffer === 1 ? "one" : "ones"}`}
              group
            >
              {() => (
                <Choice
                  name={`${name}-names`}
                  value={choices.names}
                  options={[
                    ["stored", "Keep the stored names"],
                    ["file", "Take the file's names"],
                  ]}
                  onChange={(names) => onChange({ ...choices, names })}
                />
              )}
            </FormField>
          )}
          {table.missing > 0 && (
            <FormField
              label={`${count(table.missing)} stored ${table.missing === 1 ? "record is" : "records are"} missing from the file`}
              group
            >
              {() => (
                <Choice
                  name={`${name}-missing`}
                  value={choices.missing}
                  options={[
                    ["leave", "Leave them"],
                    ["remove", "Remove them (in the change set)"],
                  ]}
                  onChange={(missing) => onChange({ ...choices, missing })}
                />
              )}
            </FormField>
          )}
        </div>
      )}
      {table.meaning.length > 0 && (
        <ul className="task-meaning" aria-label="Matched by meaning">
          {table.meaning.map((match) => (
            <li key={`${match.value}-${match.record.id}`}>
              <span>
                “{match.value}” is “{match.record.name}”
              </span>
              <AiOriginMark origin={match.origin} variant="target" />
            </li>
          ))}
        </ul>
      )}
      {leftOut.length > 0 && (
        <Disclosure variant="link" label={plural(leftOut.length, "column") + " left out"}>
          <ul className="task-sheet-list">
            {leftOut.map((column) => (
              <li key={column.column}>
                “{column.header}”: {column.reason}
              </li>
            ))}
          </ul>
        </Disclosure>
      )}
    </Card>
  );
}
