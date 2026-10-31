/**
 * What the assistant read (0.16 AP6a, state `read`, board 5): a summary of the file, the tables that
 * need the person each as a card with only the choices that apply, every other table folded by the
 * way the model is organised, and what was skipped. Prepare the load sends only the choices the
 * person changed; they stay theirs.
 */

import { useMemo, useState } from "react";
import type { AiTask, ApplicationDefinition } from "@/types";
import { Notice } from "@/ui/Notice";
import { Section } from "@/ui/Section";
import { GroupedTables, typesAndRows } from "./GroupedTables";
import { NeedsCard } from "./NeedsCard";
import { NotLoaded } from "./NotLoaded";
import { ReadingSummary } from "./ReadingSummary";
import { TaskNotes } from "./TaskNotes";
import { groupLabels } from "./aiTaskStructure";
import {
  alsoLoads,
  changedChoices,
  choicesOf,
  foundOn,
  languagesOf,
  needsPerson,
  skippedByReading,
  skippedText,
  type TableChoices,
} from "./aiTaskText";

export function ReadingView({
  task,
  applications,
  pending,
  onPrepare,
  onCancel,
}: {
  task: AiTask;
  applications: ApplicationDefinition[];
  pending: boolean;
  onPrepare: (tables: ReturnType<typeof changedChoices>) => void;
  onCancel: () => void;
}) {
  const reading = task.reading;
  const tables = useMemo(() => reading?.tables ?? [], [reading]);
  const [choices, setChoices] = useState<Record<string, TableChoices>>(() =>
    Object.fromEntries(tables.map((table) => [table.table, choicesOf(table)])),
  );
  const loads = tables.some((table) => table.as === "update");
  const needing = tables.filter(needsPerson);
  const others = tables.filter((table) => table.as === "update" && !needsPerson(table));
  const groups = useMemo(() => groupLabels(tables, applications), [tables, applications]);
  const skipped = skippedByReading(task);
  const empty = tables.length === 0 && (reading?.sheets ?? []).length === 0;
  return (
    <div className="task-reading">
      <TaskNotes notes={task.notes} />
      <Section title="What the assistant read">
        {empty ? (
          <Notice tone="warning">The assistant found no table in this workbook.</Notice>
        ) : (
          <ReadingSummary task={task} applications={applications} />
        )}
      </Section>
      {needing.length > 0 && (
        <Section title="Needs you" description="These lists have something only you can decide.">
          {needing.map((table) => (
            <NeedsCard
              key={table.table}
              table={table}
              group={groups.get(table.table)}
              choices={choices[table.table] ?? choicesOf(table)}
              onChange={(next) => setChoices((now) => ({ ...now, [table.table]: next }))}
            />
          ))}
        </Section>
      )}
      {others.length > 0 && (
        <Section
          title="As your model is organised"
          description="These match their stored records. Open a group to see its lists."
        >
          <GroupedTables
            label="lists read"
            tables={others}
            applications={applications}
            columns={["Found on", "Rows", "Match", "Also loads"]}
            cells={(table) => [
              foundOn(table),
              table.rows.toLocaleString("en-GB"),
              `${table.matched.toLocaleString("en-GB")} of ${(table.matched + table.new).toLocaleString("en-GB")}`,
              alsoLoads(table),
            ]}
            figures={(group) => {
              const languages = [...new Set(group.flatMap(languagesOf))].map((language) => `${language} translations`);
              return [typesAndRows(group), "all match", ...languages].join(" · ");
            }}
          />
        </Section>
      )}
      <NotLoaded
        label={`Not loaded: ${skippedText([
          [skipped.titles, "title row"],
          [skipped.sheets, "sheet with no list", "sheets with no list"],
        ])}`}
        entries={skipped.entries}
      />
      <div className="task-actions">
        <button type="button" className="secondary" disabled={pending} onClick={onCancel}>
          Cancel
        </button>
        <button
          type="button"
          className="primary"
          disabled={pending || !loads}
          onClick={() => onPrepare(changedChoices(tables, choices))}
        >
          {pending ? "Preparing…" : "Prepare the load"}
        </button>
      </div>
    </div>
  );
}
