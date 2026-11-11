/**
 * The migration a draft states (0.13 MG, MG-D3): read from `GET /model-drafts/{id}/migration`, derived by
 * the server from the steps that stand now, and shown where a draft is installed or applied. The install
 * and apply dialogs say what the migration does before anything changes, name each key change with the
 * consumer APIs that read the old key, and start the workspace migration with the same mappings, so the
 * migration page opens filled in.
 */

import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import type { DraftMigration, DraftMigrationRow, MigrationProposal, ModelDraftOutline } from "@/types";
import { Notice } from "@/ui/Notice";

const count = (value: number | string) => (typeof value === "number" ? value.toLocaleString("en-GB") : value);

/** The migration the draft states, read for `workspaceKey` while `enabled`; again when `version` moves. */
export function useDraftMigration(
  draftId: string,
  workspaceKey: string | undefined,
  enabled: boolean,
  version: number,
) {
  // The state belongs to what it was read for: another draft, workspace or version starts unread.
  const key = `${draftId}|${workspaceKey ?? ""}|${version}`;
  const [read, setRead] = useState<{ key: string; migration?: DraftMigration; error?: string }>();
  useEffect(() => {
    if (!enabled) return;
    let active = true;
    api
      .modelDraftMigration(draftId, workspaceKey)
      .then((loaded) => active && setRead({ key, migration: loaded }))
      .catch((cause) => active && setRead({ key, error: errorMessage(cause) }));
    return () => {
      active = false;
    };
  }, [draftId, workspaceKey, enabled, version, key]);
  const current = enabled && read?.key === key ? read : undefined;
  return {
    migration: current?.migration,
    error: current?.error ?? "",
    /** Wanted and not read yet: nothing may start with the mappings missing. */
    pending: enabled && !current,
  };
}

/** The request fields of the workspace migration the draft states, with the draft that proposed them. */
export function proposalOf(
  migration: DraftMigration | undefined,
  draftId: string,
): Partial<MigrationProposal> & { draftId?: string } {
  // Without it the migration starts with no mapping, as it always did.
  if (!migration) return {};
  return {
    typeMappings: migration.typeMappings,
    relationTypeMappings: migration.relationTypeMappings,
    splits: migration.splits,
    listConversions: migration.listConversions,
    draftId,
  };
}

function applicationName(outline: ModelDraftOutline, key: string): string {
  return outline.applications.find((item) => item.key === key)?.name ?? key;
}

/** One type the migration changes, in a line: what it becomes, where its records go and under what. */
function rowWords(row: DraftMigrationRow, outline: ModelDraftOutline): string {
  const parts: string[] = [];
  if (row.toObjectTypeKey !== row.fromObjectTypeKey) parts.push(`becomes ${row.toName}`);
  if (row.attributes.length) parts.push(`${row.attributes.length === 1 ? "a field is" : "fields are"} renamed`);
  if (row.toApplicationKey) parts.push(`moves to ${applicationName(outline, row.toApplicationKey)}`);
  if (row.parent === "topLevel") parts.push("its records become top-level records");
  if (row.parent === "changed")
    parts.push("it stands under other types; records the new parents do not hold are refused");
  const held = row.records.records;
  const records = held === 0 ? "no records" : `${count(held)} ${held === 1 ? "record" : "records"}`;
  return `${row.fromName}: ${parts.join(", ")} (${records})`;
}

/**
 * "Activation needs a migration", stated: the steps that need one, what each part of the migration does,
 * the figures for the workspace, and every key change with the consumer APIs that name the old key.
 */
export function DraftMigrationNotice({
  migration,
  outline,
  label,
  reasons,
}: {
  migration: DraftMigration;
  outline: ModelDraftOutline;
  /** The workspace the figures are for. */
  label: string;
  /** The compatibility check's own words, shown when the draft states nothing. */
  reasons?: string;
}) {
  const steps = new Set(migration.steps.map((item) => item.step)).size;
  const landing = migration.landing;
  const refused = landing?.refused.reduce((sum, item) => sum + item.count, 0) ?? 0;
  const spawned = migration.splits.length + migration.listConversions.length;
  const lines = [
    ...migration.rows.map((row) => rowWords(row, outline)),
    ...migration.splits.map(
      (item) =>
        `Split: ${typeLabel(outline, item.fromObjectTypeKey)} gets a related ${typeLabel(outline, item.toObjectTypeKey)} record for each value`,
    ),
    ...migration.listConversions.map(
      (item) =>
        `List: the values of ${attributeLabel(outline, item.attributeTypeKey)} become ${typeLabel(outline, item.toObjectTypeKey)} records`,
    ),
    ...migration.relationTypeMappings.map(
      (item) => `Relationships of ${item.fromRelationTypeKey} carry on as ${item.toRelationTypeKey}`,
    ),
  ];
  return (
    <div className="draft-migration">
      <Notice tone="warning" title="Activation needs a migration">
        {steps > 0
          ? `${steps === 1 ? "One step" : `${steps} steps`} of this draft change${steps === 1 ? "s" : ""} stored data. The migration below comes from ${steps === 1 ? "it" : "them"}; review it before activating.`
          : "The draft's data does not fit as it is."}
        {lines.length > 0 && (
          <ul className="draft-migration-lines">
            {lines.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        )}
        {!lines.length && reasons ? ` ${reasons}` : null}
        {migration.notes.map((note, position) => (
          <p key={`${note.code}:${position}`}>{note.message}.</p>
        ))}
      </Notice>
      {landing && (
        <dl className="draft-migration-figures" aria-label={`What the migration does to ${label}`}>
          <div>
            <dt>records move</dt>
            <dd>{count(landing.moved)}</dd>
          </div>
          {spawned > 0 && (
            <>
              <div>
                <dt>records created</dt>
                <dd>{count(landing.createdRecords)}</dd>
              </div>
              <div>
                <dt>relationships created</dt>
                <dd>{count(landing.createdRelationships)}</dd>
              </div>
            </>
          )}
          <div>
            <dt>refused</dt>
            <dd>{count(refused)}</dd>
          </div>
        </dl>
      )}
      {migration.keyChanges.map((change) => (
        <Notice
          key={`${change.from}:${change.to}`}
          tone="warning"
          title={`The key ${change.from} changes to ${change.to}`}
        >
          Integrations naming <code>{change.from}</code> must change with it.{" "}
          {change.consumerApis.length > 0
            ? `Consumer APIs naming it: ${change.consumerApis.map((item) => item.name).join(", ")}.`
            : "No consumer API of the base release names it."}
        </Notice>
      ))}
    </div>
  );
}

function typeLabel(outline: ModelDraftOutline, key: string): string {
  return outline.objectTypes.find((item) => item.key === key)?.name ?? key;
}

function attributeLabel(outline: ModelDraftOutline, key: string): string {
  return outline.attributeTypes.find((item) => item.key === key)?.name ?? key;
}
