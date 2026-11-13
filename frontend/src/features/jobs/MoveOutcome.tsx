/**
 * What a move job did (its page, `/settings/jobs/{id}`): one sentence and four counts, the record
 * types and relationship types it went through, and its items, refused ones first. A job from before
 * relationship types were counted has no `relationships` in its stored summary; its table then lists
 * the record types only, and the relationships made are the made items the record types do not hold.
 * The rows are the move editor's report's table (`features/moves/MoveRowsTable`); here a name opens
 * its record in the source workspace and a refusal by a rule of the model leads to the model.
 */

import { useState, type ReactNode } from "react";
import { useHoldsGroup } from "@/app/useMe";
import { count } from "@/ui/limits";
import { MoveRowsTable, type MoveRowsFilter } from "@/ui/MoveRowsTable";
import { modeWords, reasonText } from "@/model/moveRun";
import { useWorkspaceModel } from "@/model/workspaceModels";
import { routePath } from "@/routing/routes";
import type { EngineModel, Job, MoveCounts, MoveOutcome as Outcome, MoveReason, MoveRow, MoveSummary } from "@/types";
import type { RouteState } from "@/types";
import { Choice } from "@/ui/Choice";
import { OutcomeCards } from "@/ui/OutcomeCards";
import { RouteLink } from "@/ui/RouteLink";
import { Section } from "@/ui/Section";
import { SettingsTable } from "@/ui/SettingsTable";

type Show = "all" | Outcome;

const made = (counts: MoveCounts) => counts.create + counts.update + counts.updateOriginal;

/** The row types listed in full before the rest are folded into one row. */
const LISTED = 3;

const plural = (value: number, one: string, many: string) => `${count(value)} ${value === 1 ? one : many}`;

export function MoveOutcome({
  job,
  summary,
  model,
  onNavigate,
}: {
  job: Job;
  summary: MoveSummary;
  model: EngineModel;
  onNavigate?: (route: RouteState) => void;
}) {
  const source = useWorkspaceModel(summary.sourceWorkspaceKey, model);
  const target = useWorkspaceModel(summary.targetWorkspaceKey, model);
  // The model's page is for those who author or release models (the settings navigation's rule).
  const authors = useHoldsGroup("model-authoring");
  const releases = useHoldsGroup("model-release");
  const loaded = Boolean(job.confirmedAt);
  const words = modeWords(summary.mode);
  const { counts } = summary;
  const total = summary.rows;
  const madeAll = made(counts);
  const recordsMade = summary.types.reduce((sum, item) => sum + made(item.counts), 0);
  const relationshipsMade = Math.max(0, madeAll - recordsMade);
  const unmoved = counts.refused + counts.notMoved;

  const sentence = [
    `${count(madeAll)} of ${count(total)} items ${loaded ? "were" : "would be"} made in ${summary.targetWorkspaceKey}.`,
    counts.refused
      ? `${count(counts.refused)} ${loaded ? "were" : "would be"} refused and ${loaded ? "are" : "would be"} not there.`
      : "",
    counts.notMoved ? `${count(counts.notMoved)} ${loaded ? "were" : "would be"} left out by the mapping.` : "",
    loaded && summary.mode === "move" && summary.source
      ? `${plural(summary.source.deleted, "record was", "records were")} deleted in ${summary.sourceWorkspaceKey}, ${count(summary.source.kept)} kept.`
      : `Nothing ${loaded ? "changed" : "has changed"} in ${summary.sourceWorkspaceKey}.`,
  ]
    .filter(Boolean)
    .join(" ");

  // A name opens its record in the source workspace, where the relationship still is.
  const record = (row: MoveRow, end: "record" | "from" | "to", name: string): ReactNode => {
    const type = end === "record" ? row.sourceType : endType(source, row, end);
    const id = end === "record" ? row.sourceId : end === "from" ? row.fromId : row.toId;
    const application = type && source.applications.find((item) => item.objectTypeKeys.includes(type));
    if (!onNavigate || !id || !type || !application) return name;
    const route: RouteState = {
      kind: "detail",
      applicationKey: application.key,
      objectTypeKey: type,
      objectId: id,
      workspaceKey: summary.sourceWorkspaceKey,
    };
    return (
      <RouteLink href={routePath(route)} onNavigate={() => onNavigate(route)}>
        {name}
      </RouteLink>
    );
  };
  const modelRoute: RouteState | undefined = summary.targetReleaseId
    ? { kind: "settings", page: "model", releaseId: summary.targetReleaseId }
    : undefined;
  const criteria = (reason: MoveReason): ReactNode =>
    reason.details?.criteria && modelRoute && onNavigate && (authors || releases) ? (
      <RouteLink href={routePath(modelRoute)} onNavigate={() => onNavigate(modelRoute)}>
        The criteria
      </RouteLink>
    ) : null;

  return (
    <>
      <Section title="What happened">
        <p className="job-sentence">{sentence}</p>
        <OutcomeCards
          label="What the move did"
          items={[
            { key: "records", count: recordsMade, label: loaded ? "records made" : "records to make" },
            {
              key: "relationships",
              count: relationshipsMade,
              label: loaded ? "relationships made" : "relationships to make",
            },
            { key: "refused", count: counts.refused, label: "refused", tone: "warning" },
            { key: "notMoved", count: counts.notMoved, label: "not moved" },
          ]}
        />
      </Section>
      <TypeCounts summary={summary} source={source} target={target} />
      <Section
        title="The items"
        description={
          unmoved
            ? `The names open the records in ${summary.sourceWorkspaceKey}. An item that did not move is not tried again: fix it there or in the model, then ${words.verb} again.`
            : undefined
        }
      >
        <MoveItems
          job={job}
          summary={summary}
          source={source}
          target={target}
          loaded={loaded}
          record={record}
          criteria={criteria}
        />
      </Section>
    </>
  );
}

/** A relationship row's record at an end: the type its binding names, from the refusal's own path first. */
function endType(model: EngineModel, row: MoveRow, end: "from" | "to"): string | undefined {
  // `/objectTypeRelations/{relation}/{from type}/{to type}/candidates/{end}`
  for (const reason of row.reasons) {
    const path = reason.details?.criteria;
    const parts = typeof path === "string" ? path.split("/") : [];
    if (parts[1] === "objectTypeRelations" && parts[2] === row.relationTypeKey && parts[4])
      return decodeURIComponent(end === "from" ? parts[3] : parts[4]);
  }
  // Else the one binding of the relationship from (or to) the row's own type.
  const outgoing = row.direction ? row.direction === "outgoing" : true;
  const own = row.sourceType;
  const bindings = model.objectTypeRelations.filter(
    (item) =>
      item.relationTypeKey === row.relationTypeKey &&
      (outgoing ? item.fromObjectTypeKey === own : item.toObjectTypeKey === own),
  );
  if (bindings.length !== 1) return undefined;
  const other = outgoing ? bindings[0].toObjectTypeKey : bindings[0].fromObjectTypeKey;
  return (end === "from") === outgoing ? own : other;
}

interface TypeLine {
  key: string;
  type: string;
  becomes: string;
  made: number;
  refused: number;
  notMoved: number;
}

function TypeCounts({ summary, source, target }: { summary: MoveSummary; source: EngineModel; target: EngineModel }) {
  const [all, setAll] = useState(false);
  const name = (model: EngineModel, key?: string) =>
    (key && model.objectTypes.find((item) => item.key === key)?.name) || key || "";
  const relation = (model: EngineModel, key?: string) =>
    (key && model.relationTypes.find((item) => item.key === key)?.name) || key || "";
  const records: TypeLine[] = summary.types.map((item) => ({
    key: `record:${item.sourceType}`,
    type: name(source, item.sourceType),
    becomes: name(target, item.targetType ?? item.sourceType),
    made: made(item.counts),
    refused: item.counts.refused,
    notMoved: item.counts.notMoved,
  }));
  const relationships: TypeLine[] = (summary.relationships ?? []).map((item) => ({
    key: `relation:${item.relationTypeKey}`,
    type: `Relationships: ${relation(source, item.relationTypeKey)}`,
    becomes: relation(target, item.targetRelationTypeKey ?? item.relationTypeKey),
    made: made(item.counts),
    refused: item.counts.refused,
    notMoved: item.counts.notMoved,
  }));
  // The types with something to look at stay; of the rest the largest are listed and the others folded.
  const fold = (lines: TypeLine[], noun: string): (TypeLine | { key: string; folded: TypeLine[]; noun: string })[] => {
    const problems = lines.filter((line) => line.refused || line.notMoved);
    const rest = lines.filter((line) => !line.refused && !line.notMoved).sort((a, b) => b.made - a.made);
    const shown = all ? rest : rest.slice(0, Math.max(0, LISTED - problems.length));
    const folded = all ? [] : rest.slice(shown.length);
    return [
      ...lines.filter((line) => problems.includes(line) || shown.includes(line)),
      ...(folded.length > 1 ? [{ key: `${noun}:folded`, folded, noun }] : folded),
    ];
  };
  const lines = [...fold(records, "record types"), ...fold(relationships, "relationship types")];
  const showNotMoved = summary.counts.notMoved > 0;
  const foldable = [...records, ...relationships].filter((line) => !line.refused && !line.notMoved).length > LISTED;
  if (!lines.length) return null;
  const cells = (line: { made: number; refused: number; notMoved: number }) => (
    <>
      <td data-label="Made">{count(line.made)}</td>
      <td data-label="Refused" className={line.refused ? "job-attention" : undefined}>
        {count(line.refused)}
      </td>
      {showNotMoved && <td data-label="Not moved">{count(line.notMoved)}</td>}
    </>
  );
  return (
    <Section
      title="By type"
      actions={
        foldable && (
          <button type="button" className="secondary" aria-expanded={all} onClick={() => setAll(!all)}>
            {all ? "Fold the types" : "Show every type"}
          </button>
        )
      }
    >
      <SettingsTable
        label="The move by type"
        columns={["Type", "Becomes", "Made", "Refused", ...(showNotMoved ? ["Not moved"] : [])]}
      >
        {lines.map((line) =>
          "folded" in line ? (
            <tr key={line.key}>
              <th scope="row">
                {count(line.folded.length)} more {line.noun}
              </th>
              <td data-label="Becomes" />
              {cells({
                made: line.folded.reduce((sum, item) => sum + item.made, 0),
                refused: 0,
                notMoved: 0,
              })}
            </tr>
          ) : (
            <tr key={line.key}>
              <th scope="row">{line.type}</th>
              <td data-label="Becomes">{line.becomes}</td>
              {cells(line)}
            </tr>
          ),
        )}
      </SettingsTable>
    </Section>
  );
}

function MoveItems({
  job,
  summary,
  source,
  target,
  loaded,
  record,
  criteria,
}: {
  job: Job;
  summary: MoveSummary;
  source: EngineModel;
  target: EngineModel;
  loaded: boolean;
  record: (row: MoveRow, end: "record" | "from" | "to", name: string) => ReactNode;
  criteria: (reason: MoveReason) => ReactNode;
}) {
  const { counts } = summary;
  const [show, setShow] = useState<Show>(counts.refused > 0 ? "refused" : "all");
  const [reason, setReason] = useState("");
  const updated = counts.update + counts.updateOriginal > 0;
  const options: [Show, string][] = [
    ...(counts.refused ? [["refused", `Refused (${count(counts.refused)})`] as [Show, string]] : []),
    ["create", `${updated ? "Created" : "Made"} (${count(counts.create)})`],
    ...(counts.update ? [["update", `Updated (${count(counts.update)})`] as [Show, string]] : []),
    ...(counts.updateOriginal
      ? [["updateOriginal", `Moved back (${count(counts.updateOriginal)})`] as [Show, string]]
      : []),
    ...(counts.notMoved ? [["notMoved", `Not moved (${count(counts.notMoved)})`] as [Show, string]] : []),
    ["all", `All (${count(summary.rows)})`],
  ];
  const filter: MoveRowsFilter = {
    ...(show === "all" ? {} : { outcome: show }),
    ...(reason ? { reason } : {}),
  };
  return (
    <>
      <div className="job-filters">
        <Choice name={`move-items-${job.id}`} value={show} options={options} onChange={setShow} />
        {summary.reasons.length > 0 && (
          <label>
            Why{" "}
            <select value={reason} onChange={(event) => setReason(event.target.value)}>
              <option value="">Every reason</option>
              {summary.reasons.map((item) => (
                <option key={item.code} value={item.code}>
                  {reasonText(item.code).label} ({count(item.count)})
                </option>
              ))}
            </select>
          </label>
        )}
      </div>
      <MoveRowsTable
        key={`${job.id}:${show}:${reason}`}
        jobId={job.id}
        filter={filter}
        source={source}
        target={target}
        label={`The items of the ${modeWords(summary.mode).verb}`}
        emptyMessage="None here."
        record={record}
        criteria={criteria}
      />
      {!loaded && <p className="muted">These are the dry run's items: nothing is written until the move is loaded.</p>}
    </>
  );
}
