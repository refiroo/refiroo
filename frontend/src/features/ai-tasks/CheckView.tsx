/**
 * What the load would do (0.16 AP6a, state `checked`, board 6): one summary of the dry run of every
 * row, the changes of the tables that change something, the tables with nothing to change folded by
 * the way the model is organised, and what the assistant fixed. The foot loads the plan into a change
 * set, optionally saving it as an import profile.
 */

import { useMemo } from "react";
import { count } from "@/features/settings/limits";
import type { AiTask, AiTaskCheckSummary, AiTaskCheckTable, AiTaskFix, ApplicationDefinition } from "@/types";
import { AiOriginMark } from "@/ui/AiOriginMark";
import { Card } from "@/ui/Card";
import { Disclosure } from "@/ui/Disclosure";
import { OutcomeCards, type OutcomeCard } from "@/ui/OutcomeCards";
import { Section } from "@/ui/Section";
import { GroupedTables, typesAndRows } from "./GroupedTables";
import { LoadFoot, type LoadChoice } from "./LoadFoot";
import { NotLoaded } from "./NotLoaded";
import { TableChanges } from "./TableChanges";
import { TaskNotes } from "./TaskNotes";
import { groupLabels } from "./aiTaskStructure";
import { foundOn, notLoadedEntries, plainCheck, plural, refusalText, shown, skippedText } from "./aiTaskText";

/** A table of the check changes something or refuses something: the rest load exactly what is stored. */
// From the figures, not `nothingToDo`: a check stored before that flag reads it as false.
const hasWork = (table: AiTaskCheckTable) =>
  table.changed + table.created + table.removed + (table.translations ?? 0) > 0 ||
  table.refused.some((group) => group.rows > 0);

/** The check's totals: the server's, else summed from its tables. */
export function checkSummary(tables: AiTaskCheckTable[], given?: AiTaskCheckSummary): AiTaskCheckSummary {
  if (given) return given;
  const sum = (pick: (table: AiTaskCheckTable) => number) => tables.reduce((total, table) => total + pick(table), 0);
  return {
    changed: sum((t) => t.changed),
    unchanged: sum((t) => t.unchanged),
    created: sum((t) => t.created),
    removed: sum((t) => t.removed),
    refused: sum((t) => t.refused.reduce((rows, group) => rows + group.rows, 0)),
    translations: sum((t) => t.translations ?? 0),
    tablesWithChanges: tables.filter(hasWork).length,
  };
}

export type { LoadChoice };

export function CheckView({
  task,
  applications,
  pending,
  canLoad,
  onBack,
  onLoad,
}: {
  task: AiTask;
  applications: ApplicationDefinition[];
  pending: boolean;
  /** Loading writes a change set: needs Work in change sets in the task's workspace. */
  canLoad: boolean;
  onBack: () => void;
  onLoad: (choice: LoadChoice) => void;
}) {
  const check = plainCheck(task);
  const readingTables = useMemo(() => task.reading?.tables ?? [], [task.reading]);
  const groups = useMemo(() => groupLabels(readingTables, applications), [readingTables, applications]);
  if (!check) return null;
  const fixed = check.fixes.filter((fix) => fix.to !== null).length;
  const summary = checkSummary(check.tables, check.summary);
  const working = check.tables.filter(hasWork);
  const quietIds = new Set(check.tables.filter((table) => !hasWork(table)).map((table) => table.table));
  const quiet = readingTables.filter((table) => quietIds.has(table.table));
  const cards: OutcomeCard[] = [
    { key: "created", count: summary.created, label: "Records new" },
    { key: "changed", count: summary.changed, label: "Records changed" },
    { key: "translations", count: summary.translations, label: "Translations new or changed" },
    { key: "unchanged", count: summary.unchanged, label: "Records as stored" },
    { key: "refused", count: summary.refused, label: "Rows refused", tone: "error" },
    ...(summary.removed > 0 ? [{ key: "removed", count: summary.removed, label: "Records removed" }] : []),
  ];
  const columns = notLoadedEntries(task, true).filter((entry) => entry.text.startsWith("Column “"));
  const fixesList = (fixes: AiTaskFix[]) =>
    fixes.map((fix, index) => (
      <li key={`${fix.table}-${fix.column}-${fix.value}-${index}`}>
        <span>
          Fixed by the assistant: “{fix.value}” in column {fix.column}{" "}
          {fix.to === null ? "stays refused" : <>is read as “{fix.to}”</>}.
        </span>
        {fix.origin && <AiOriginMark origin={fix.origin} variant="target" />}
        {!fix.origin && fix.reason && <span className="task-reason">{fix.reason}</span>}
      </li>
    ));
  return (
    <div className="task-check">
      <TaskNotes notes={task.notes} />
      <Section
        title="What the load would do"
        description={`Every row checked${fixed > 0 ? ` · the assistant fixed ${fixed} ${fixed === 1 ? "problem" : "problems"} and checked again` : ""}`}
      >
        <Card as="section" className="task-summary" aria-label="What the check found">
          <p>
            <strong>
              {count(summary.tablesWithChanges)} of {plural(check.tables.length, "list")}{" "}
              {summary.tablesWithChanges === 1 ? "changes" : "change"} something.
            </strong>{" "}
            {check.tables.length - summary.tablesWithChanges > 0
              ? check.tables.length - summary.tablesWithChanges > 1
                ? `The other ${count(check.tables.length - summary.tablesWithChanges)} load exactly what is stored.`
                : "The other one loads exactly what is stored."
              : ""}
          </p>
          <OutcomeCards label="Figures of the check" items={cards} />
        </Card>
      </Section>
      {working.length > 0 && (
        <Section title="The changes">
          {working.map((table) => (
            <TableCheck
              key={table.table}
              task={task}
              table={table}
              group={groups.get(table.table)}
              range={readingTables.find((read) => read.table === table.table)?.range ?? null}
            />
          ))}
        </Section>
      )}
      {quiet.length > 0 && (
        <Disclosure variant="link" label={`${plural(quiet.length, "list")} with nothing to change, by group`}>
          <GroupedTables
            label="lists with nothing to change"
            tables={quiet}
            applications={applications}
            columns={["Found on", "Rows", "As stored"]}
            cells={(table) => [
              foundOn(table),
              table.rows.toLocaleString("en-GB"),
              (check.tables.find((read) => read.table === table.table)?.unchanged ?? 0).toLocaleString("en-GB"),
            ]}
            figures={typesAndRows}
          />
        </Disclosure>
      )}
      {check.fixes.length > 0 && (
        <Section title="Fixed by the assistant" headingLevel={2}>
          <ul className="task-fixes" aria-label="Fixes of the assistant">
            {fixesList(check.fixes.slice(0, 3))}
          </ul>
          {check.fixes.length > 3 && (
            <Disclosure variant="link" label={plural(check.fixes.length - 3, "more fix", "more fixes")}>
              <ul className="task-fixes" aria-label="More fixes of the assistant">
                {fixesList(check.fixes.slice(3))}
              </ul>
            </Disclosure>
          )}
        </Section>
      )}
      <NotLoaded
        label={`Not loaded: ${skippedText([[columns.length, "column left out", "columns left out"]])}`}
        entries={columns}
      />
      <LoadFoot
        fileName={task.fileName}
        pending={pending}
        canLoad={canLoad}
        loadLabel="Load into a change set"
        note={
          task.reading?.profile && (
            <p className="admin-hint">The load reads through the profile “{task.reading.profile.name}”.</p>
          )
        }
        onBack={onBack}
        onLoad={onLoad}
      />
    </div>
  );
}

function TableCheck({
  task,
  table,
  group,
  range,
}: {
  task: AiTask;
  table: AiTaskCheckTable;
  group?: string;
  range: string | null;
}) {
  const checkedAt = plainCheck(task)?.ranAt;
  const refused = table.refused.reduce((total, item) => total + item.rows, 0);
  const title = [table.typeName ?? table.sheet, group].filter(Boolean).join(" · ");
  const figures = [
    `${count(table.changed)} changed`,
    `${count(table.created)} new`,
    ...((table.translations ?? 0) > 0 ? [`${count(table.translations ?? 0)} translations`] : []),
    `${count(table.unchanged)} as stored`,
    ...(refused > 0 ? [`${count(refused)} refused`] : []),
    ...(table.removed > 0 ? [`${count(table.removed)} removed`] : []),
    ...(table.skipped > 0 ? [`${plural(table.skipped, "row")} skipped`] : []),
  ].join(" · ");
  return (
    <Card
      as="section"
      className="task-table"
      aria-label={`Check of ${title}, sheet ${table.sheet}${range ? ` ${range}` : ""}`}
    >
      <div className="task-table-head">
        <h3>{title}</h3>
        <span className="task-reason">
          Sheet “{table.sheet}”{range ? ` ${range}` : ""} · {plural(table.rows, "row")}
        </span>
      </div>
      <p className="task-figures">{figures}</p>
      {table.refused.length > 0 && (
        <ul className="task-refusals" aria-label={`Refused rows of ${table.sheet}`}>
          {table.refused.map((item, index) => (
            <li key={`${item.code}-${item.column}-${index}`}>
              <strong>
                {count(item.rows)} {item.rows === 1 ? "row" : "rows"}: {refusalText(item.code)}
              </strong>
              {item.header && <> in column “{item.header}”</>}
              {item.message && <>. {item.message}</>}
              {item.values && item.values.length > 0 && (
                <>. Most refused: {item.values.map((v) => `“${shown(v.value)}” (${count(v.count)})`).join(", ")}</>
              )}
            </li>
          ))}
        </ul>
      )}
      {table.changed > 0 && checkedAt && (
        <TableChanges taskId={task.id} table={table.table} sheet={table.sheet} checkedAt={checkedAt} />
      )}
    </Card>
  );
}
