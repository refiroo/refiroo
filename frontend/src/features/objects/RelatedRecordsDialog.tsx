/**
 * A record's related records of one kind, edited from a list's relation cell where it may hold
 * several (0.10 A9, D136): the records it holds ticked in a `RecordChecklist` (the whole set, read
 * by pages), the binding's candidates offered (0.9 K7), several types under their headings. Save
 * sends only what was ticked or unticked, as one inline, atomic batch of `ensureRelation` and
 * `ensureNoRelation` items, so a record someone else related meanwhile stays, and a refusal changes
 * nothing. Relationship values are edited on the record, not here (as K3).
 */

import { useEffect, useState } from "react";
import { errorMessage } from "@/api/errors";
import { newIdempotencyKey } from "@/model/importRequest";
import { useDataApi, useWorkspaceData } from "@/state/WorkspaceDataContext";
import { candidateHint, candidateScope } from "@/model/candidates";
import type { RelatedCellEdit } from "@/model/lookup";
import type { EngineModel, ObjectItem } from "@/types";
import { CancelButton, Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { OwnEndReasons, useOwnEndRefusals } from "./useOwnEndRefusals";
import { RecordChecklist, type ChecklistRecord } from "@/ui/RecordChecklist";
import { checklistChange, relationItems } from "./bulkRelations";
import { everyPage } from "@/lib/everyPage";

/** How many relationships one read of the held set asks for. */
const PAGE = 200;

export function RelatedRecordsDialog({
  model,
  object,
  edit,
  onClose,
  onSaved,
}: {
  model: EngineModel;
  object: ObjectItem;
  edit: RelatedCellEdit;
  onClose: () => void;
  /** Saved: the records added and removed. */
  onSaved: (added: number, removed: number) => void;
}) {
  const api = useDataApi();
  const { changeSet, refresh } = useWorkspaceData();
  const [held, setHeld] = useState<ChecklistRecord[]>();
  const [ticked, setTicked] = useState<ChecklistRecord[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  // Only the bindings the record meets from its own end are offered (0.9 K7, D172).
  const { offered, refusedReasons, checking } = useOwnEndRefusals(model, object, edit.choices);
  const types = [...new Set(offered.map((choice) => choice.otherObjectTypeKey))];
  const allTypes = [...new Set(edit.choices.map((choice) => choice.otherObjectTypeKey))];
  const scoped = offered
    .map((choice) => candidateScope(model, choice.relation, choice.direction, object.objectTypeKey))
    .find(Boolean);
  const hint = offered.map((choice) => candidateHint(model, choice.relation, choice.direction)).find(Boolean);
  const label = edit.choices[0].label;

  useEffect(() => {
    let current = true;
    (async () => {
      const read = await everyPage(
        (cursor) =>
          api.relations(object.id, {
            workspaceKey: object.workspaceKey,
            direction: edit.direction,
            relationTypeKey: edit.relationTypeKey,
            pageSize: PAGE,
            ...(cursor ? { cursor } : {}),
          }),
        { stop: () => !current },
      );
      if (!current) return;
      const records: ChecklistRecord[] = read
        .filter((item) => allTypes.includes(item.object.objectTypeKey))
        .map((item) => ({ id: item.object.id, name: item.object.name, objectTypeKey: item.object.objectTypeKey }));
      setHeld(records);
      setTicked(records);
    })().catch((cause) => current && setError(errorMessage(cause)));
    return () => {
      current = false;
    };
    // The set is read once, when the dialog opens.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const change = held && checklistChange(held, ticked);
  const changes = change ? change.add.length + change.remove.length : 0;

  async function save() {
    if (!change || !changes) return;
    setSaving(true);
    setError("");
    try {
      const context = changeSet ? ((await refresh?.()) ?? changeSet) : undefined;
      const { items } = relationItems([object], edit.choices[0], change);
      const result = await api.runBatch(
        {
          ...(context
            ? { changeSetId: context.id, expectedChangeSetVersion: context.version }
            : { workspaceKey: object.workspaceKey }),
          policy: "atomic",
          run: "inline",
          stage: "execute",
          items,
        },
        newIdempotencyKey(),
      );
      if (result.job.result !== "applied") {
        const refused = result.items.find((outcome) => outcome.status === "rejected" && outcome.error);
        setError(
          refused?.error
            ? `${refused.ref ?? "A relationship"}: ${refused.error.message}`
            : (result.job.error?.message ?? "Nothing was changed."),
        );
        setSaving(false);
        return;
      }
      if (context) await refresh?.().catch(() => undefined);
      onSaved(change.add.length, change.remove.length);
    } catch (cause) {
      setError(errorMessage(cause));
      setSaving(false);
    }
  }

  return (
    <Modal
      title={label}
      eyebrow={`Related records of ${object.name}`}
      busy={saving}
      dirty={changes > 0}
      onClose={onClose}
    >
      <form
        className="related-records-dialog"
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        {held && !checking ? (
          <>
            {types.length === 0 && <OwnEndReasons reasons={refusedReasons} />}
            {(types.length > 0 || held.length > 0) && (
              <RecordChecklist
                model={model}
                label={label}
                objectTypeKeys={types}
                heldTypeKeys={allTypes}
                records={types.length === 0 ? held : undefined}
                workspaceKey={object.workspaceKey}
                chosen={ticked}
                candidates={scoped}
                emptyText="No records to choose."
                onChange={setTicked}
              />
            )}
          </>
        ) : (
          !error && <p role="status">Reading the related records…</p>
        )}
        {hint && <p className="admin-hint">{hint}</p>}
        {change && changes > 0 && (
          <p className="related-records-change" aria-live="polite">
            {[
              change.add.length && `${change.add.length} to add`,
              change.remove.length && `${change.remove.length} to remove`,
            ]
              .filter(Boolean)
              .join(", ")}
          </p>
        )}
        {error && (
          <Notice tone="error" title="Nothing was changed" focusOnMount>
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          <CancelButton disabled={saving} />
          <button className="primary" disabled={saving || !changes}>
            {saving ? "Applying…" : "Apply"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
