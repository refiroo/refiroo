/**
 * The check of a designed load (0.16 AP6, board 9, state `checked`): every row checked, the sheets
 * with their figures (the sheets the engine added for the structure folded into one row), the
 * records each sheet would change (folded, a page at a time), the refused groups with examples, and what
 * confirming does in order. The button installs and
 * activates the model change first when the design changes the model, which needs `model-release`.
 */

import type { AiTask, AiTaskDesignCheck } from "@/types";
import { count } from "@/features/settings/limits";
import { Card } from "@/ui/Card";
import { Disclosure } from "@/ui/Disclosure";
import { Notice } from "@/ui/Notice";
import { Section } from "@/ui/Section";
import { SettingsTable } from "@/ui/SettingsTable";
import { LoadFoot, type LoadChoice } from "./LoadFoot";
import { TableChanges } from "./TableChanges";
import { changesModel } from "./aiTaskDesign";
import { plural, refusalText, taskTitle } from "./aiTaskText";

/** The sheets of the check with the structure sheets gathered into one row. */
export function checkRows(check: AiTaskDesignCheck) {
  const own = check.sheets.filter((sheet) => !sheet.structure);
  const structure = check.sheets.filter((sheet) => sheet.structure);
  const sum = (pick: (sheet: AiTaskDesignCheck["sheets"][number]) => number) =>
    structure.reduce((total, sheet) => total + pick(sheet), 0);
  return [
    ...own.map((sheet) => ({ label: sheet.sheet ?? sheet.objectTypeKey ?? "The file", ...sheet })),
    ...(structure.length > 0
      ? [
          {
            label: "Records the structure needs",
            rows: sum((s) => s.rows),
            created: sum((s) => s.created),
            updated: sum((s) => s.updated),
            unchanged: sum((s) => s.unchanged),
            refused: sum((s) => s.refused),
          },
        ]
      : []),
  ];
}

export function DesignCheckView({
  task,
  check,
  workspaceLabel,
  pending,
  canLoad,
  canRelease,
  onLoad,
}: {
  task: AiTask;
  check: AiTaskDesignCheck;
  workspaceLabel: string;
  pending: boolean;
  /** Needs Work in change sets in the task's workspace. */
  canLoad: boolean;
  /** Needs the model-release group in the task's workspace. */
  canRelease: boolean;
  onLoad: (choice: LoadChoice) => void;
}) {
  const design = task.design;
  const model = !!design && changesModel(design);
  const { summary } = check;
  const hasLinks = (design?.links?.length ?? 0) > 0 || (check.links?.length ?? 0) > 0;
  const hasProfile = (design?.profile?.sources.length ?? 0) > 0;
  const relationships =
    summary.relationships ??
    (check.links ?? []).reduce((total, link) => total + (link.refused ? 0 : (link.pairs ?? 0)), 0);
  const linksOnly = check.sheets.length === 0 && !check.dryRunJobId;
  const rows = summary.created + summary.updated + summary.unchanged + summary.refused;
  const allowed = canLoad && (!model || canRelease);
  const changing = check.sheets.filter((sheet) => sheet.updated > 0 && sheet.source != null && !sheet.structure);
  return (
    <div className="task-check">
      <Section title="What the load would do" description={linksOnly ? undefined : "Every row checked"}>
        <Card as="section" className="task-summary" aria-label="What the check found">
          <p>
            <strong>
              {linksOnly ? (
                <>
                  No rows to check: the instruction makes {plural(relationships, "relationship")} between stored
                  records.
                </>
              ) : (
                <>
                  {plural(rows, "row")} checked: {count(summary.created)} created, {count(summary.updated)} changed,{" "}
                  {count(summary.unchanged)} unchanged, {count(summary.refused)} refused
                  {hasLinks ? `, ${plural(relationships, "relationship")}` : ""}.
                </>
              )}
            </strong>
          </p>
        </Card>
        {!linksOnly && (
          <SettingsTable
            label="Check per sheet"
            columns={["Sheet", "Rows", "Created", "Changed", "Unchanged", "Refused"]}
          >
            {checkRows(check).map((row) => (
              <tr key={row.label}>
                <th scope="row" data-label="Sheet">
                  {row.label}
                </th>
                <td data-label="Rows">{count(row.rows)}</td>
                <td data-label="Created">{count(row.created)}</td>
                <td data-label="Changed">{count(row.updated)}</td>
                <td data-label="Unchanged">{count(row.unchanged)}</td>
                <td data-label="Refused">{count(row.refused)}</td>
              </tr>
            ))}
          </SettingsTable>
        )}
      </Section>
      {changing.length > 0 && (
        <Section title="The changes" headingLevel={2}>
          {changing.map((sheet) => {
            const label = sheet.sheet ?? sheet.objectTypeKey ?? "The file";
            return (
              <Disclosure
                key={sheet.source}
                variant="button"
                label={`Show the ${plural(sheet.updated, "changed record")} of ${label}`}
                openLabel={`Hide the changed records of ${label}`}
              >
                <TableChanges taskId={task.id} table={sheet.source as number} sheet={label} checkedAt={check.ranAt} />
              </Disclosure>
            );
          })}
        </Section>
      )}
      {check.refused.length > 0 && (
        <Section title="Refused rows" headingLevel={2}>
          {check.refused.map((group, index) => (
            <Card
              key={`${group.sheet}-${group.code}-${index}`}
              as="section"
              className="task-table"
              aria-label={`Refused in ${group.sheet ?? group.objectTypeKey ?? "the file"}: ${refusalText(group.code)}`}
            >
              <p>
                <strong>
                  {plural(group.rows, "row")}: {refusalText(group.code)}
                </strong>{" "}
                <span className="task-reason">in {group.sheet ?? group.objectTypeKey ?? "the file"}</span>
              </p>
              <ul className="task-refusals">
                {group.examples.map((example) => (
                  <li key={example.row}>
                    Row {example.row}: {example.message}
                  </li>
                ))}
              </ul>
            </Card>
          ))}
        </Section>
      )}
      <Section title="What confirming does, in this order">
        <ol className="task-order">
          {model && <li>Installs the model change and activates it in {workspaceLabel}.</li>}
          <li>Loads into a change set; live data is unchanged until it is published.</li>
          {hasLinks && <li>Writes the relationships into the same change set.</li>}
          {hasProfile && <li>Saves the import, so the next file of this layout loads without the assistant.</li>}
        </ol>
      </Section>
      <LoadFoot
        fileName={taskTitle(task)}
        pending={pending}
        canLoad={allowed}
        canSave={hasProfile}
        saveByDefault
        loadLabel={model ? "Activate the model and load" : "Load into a change set"}
        noLoad={
          canLoad && model && !canRelease ? (
            <Notice tone="info">
              This design changes the model, so a model administrator runs this load. They can open this task: it is
              visible to the administrators of {workspaceLabel}.
            </Notice>
          ) : undefined
        }
        onLoad={onLoad}
      />
    </div>
  );
}
