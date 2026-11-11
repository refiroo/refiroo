/**
 * Moves a record to another parent from the tree lens (Base 0.8 B3). The candidates are the B2
 * move targets, searchable and paged; one the move would refuse or would not change is listed
 * disabled with its reason (D14), so the count stays truthful. The record's parent and its typed
 * containment relation change together in one write, live or in the open change set.
 *
 * Moving a record that holds many related records can take seconds (D29), so the dialog says it is
 * moving until the write returns, and a refused move leaves it open with the reason.
 *
 * A drop in the tree (B5) opens the same dialog with its target chosen. The candidates have no seek,
 * so the search starts at the target's name to list it, selected, and Enter confirms the move. The
 * listed candidate replaces the dropped one once it arrives, so the server's judgement of it holds.
 *
 * The tree can also offer its top level (B5b, D36) as one more choice above the candidates, enabled
 * or disabled with the tree's reason. It is not a candidate, so the list's totals stay truthful;
 * choosing it writes no parent.
 *
 * In a change set the dialog can also offer places where the record's type cannot stand but another
 * type can (C4, ADR-034): the candidates then carry the types the record would become, and such a
 * place says “Becomes <type>”. Choosing one does not move the record here; it hands the place to
 * the restructuring preview, which shows what changes before anything is written. A caller that shows
 * only some types keeps the candidates to them (`withinObjectTypeKeys`), and the server filters, so
 * the list's totals stay truthful.
 *
 * Several records move together (UA9, U-D27): given the tree's selection (`others` beside `item`),
 * the candidates are read for `item` and every other record is judged by the tree's own rule
 * (`refusalOf`); a place that refuses one is refused with its name, and no place changes a type
 * (U-D25). Moving sends one atomic batch of `update` items, each with its record's version, live or
 * in the change set, so nothing is half moved.
 */

import { StatusPill } from "@/ui/StatusPill";
import { Candidate } from "@/ui/Candidate";
import { objectTypeTile } from "@/model/hues";
import { useState } from "react";
import { errorMessage, isApiError } from "@/api/errors";
import { useDataApi, useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { newIdempotencyKey } from "@/features/jobs/importRequest";
import { useCursorWindow } from "@/lib/hooks/useCursorWindow";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import { objectTypeFor } from "@/model/lookup";
import { typeNames } from "@/model/restructuring";
import { MOVE_REFUSAL_TEXT } from "@/model/treeDrop";
import type { EngineModel, ObjectItem, ParentCandidate } from "@/types";
import { SearchField } from "@/ui/SearchField";
import { InlineError } from "@/ui/InlineError";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { ScrollWindow, WindowPlaceholder, WindowSpacer } from "@/ui/ScrollWindow";

const PAGE_SIZE = 20;

/** The top level as a choice: no parent. */
const TOP_LEVEL = "top-level";

export function TreeMoveDialog({
  model,
  item: initial,
  others = [],
  refusalOf,
  label,
  workspaceKey,
  target,
  topLevel,
  typeChanges = false,
  withinObjectTypeKeys,
  onClose,
  onMoved,
  onTypeChange,
}: {
  model: EngineModel;
  item: ObjectItem;
  /** The rest of the tree's selection, moved with `item` (UA9). */
  others?: ObjectItem[];
  /** The tree's rule: why a record cannot move into a parent (`null` the top level), in words. */
  refusalOf?: (item: ObjectItem, parent: ObjectItem | null) => string | undefined;
  label: string;
  workspaceKey: string;
  /** A parent chosen before the dialog opens, such as a drop target; `null` is the top level. */
  target?: Pick<ObjectItem, "id" | "objectTypeKey" | "name" | "path"> | null;
  /**
   * Offers the top level, refused with the reason in words when `refusal` is set; `becomes` names the
   * types the record would become there, where its own cannot stand.
   */
  topLevel?: { refusal?: string; becomes?: string[] };
  /** Also offers places that change the record's type (in a change set only, D38). */
  typeChanges?: boolean;
  /** Keeps candidates, and the types the record would become, to these types. */
  withinObjectTypeKeys?: readonly string[];
  onClose: () => void;
  onMoved: (moved: ObjectItem) => void;
  /** A place that changes the record's type was chosen; `null` is the top level. */
  onTypeChange?: (parent: ParentCandidate | null) => void;
}) {
  const api = useDataApi();
  const { changeSet, refresh } = useWorkspaceData();
  const [item, setItem] = useState(initial);
  const several = others.length > 0;
  // A type changes one record at a time (U-D25).
  const offersTypeChanges = typeChanges && !several;
  const [search, setSearch] = useState(target?.name ?? "");
  const debounced = useDebouncedValue(search.trim());
  const [chosen, setSelected] = useState<ParentCandidate | typeof TOP_LEVEL | undefined>(
    target === null
      ? TOP_LEVEL
      : target && {
          id: target.id,
          objectTypeKey: target.objectTypeKey,
          name: target.name,
          path: target.path,
          eligible: true,
          reason: null,
        },
  );
  const [moving, setMoving] = useState(false);
  const [error, setError] = useState("");
  const candidates = useCursorWindow<ParentCandidate>(
    (selector) =>
      api.parentCandidates(item.objectTypeKey, item.id, {
        workspaceKey,
        search: debounced || undefined,
        includeTypeChanges: offersTypeChanges || undefined,
        withinObjectTypeKeys,
        ...selector,
        pageSize: PAGE_SIZE,
      }),
    [item.objectTypeKey, item.id, workspaceKey, debounced, offersTypeChanges, withinObjectTypeKeys?.join(",")],
  );
  /** The types the record would become under a candidate, when its own cannot stand there. */
  const becomes = (candidate: ParentCandidate) =>
    candidate.objectTypeKeys && !candidate.objectTypeKeys.includes(item.objectTypeKey)
      ? candidate.objectTypeKeys
      : undefined;
  const top = chosen === TOP_LEVEL;
  const selected =
    chosen === TOP_LEVEL ? undefined : (candidates.items.find((candidate) => candidate.id === chosen?.id) ?? chosen);
  /** The first other record a place refuses, by name and reason (U-D24). */
  const othersRefusal = () => {
    if (!several || !refusalOf || (!top && !selected)) return undefined;
    const parent = top
      ? null
      : ({
          ...selected!,
          applicationKey: item.applicationKey,
          parentObjectId: selected!.path.at(-2)?.id ?? null,
        } as unknown as ObjectItem);
    for (const other of others) {
      const refusal = refusalOf(other, parent);
      if (refusal) return `${other.name}: ${refusal}`;
    }
    return undefined;
  };
  const refusedOther = othersRefusal();
  const eligible = !refusedOther && (top ? Boolean(topLevel && !topLevel.refusal) : Boolean(selected?.eligible));
  const changesType = !several && (top ? Boolean(topLevel?.becomes) : Boolean(selected && becomes(selected)));
  const types = new Set(candidates.items.map((candidate) => candidate.objectTypeKey));
  const where = item.path
    .slice(0, -1)
    .map((part) => part.name)
    .join(" / ");

  async function move() {
    if (!eligible) return;
    if (changesType) {
      onTypeChange?.(top ? null : selected!);
      return;
    }
    setMoving(true);
    setError("");
    if (several) {
      await moveSeveral();
      return;
    }
    try {
      const moved = await api.updateObject(item.objectTypeKey, item.id, {
        expectedVersion: item.version,
        parentObjectId: top ? null : (selected?.id ?? null),
      });
      onMoved(moved);
    } catch (cause) {
      setError(errorMessage(cause));
      if (isApiError(cause, "VERSION_CONFLICT")) {
        // Someone changed the record: claim its new version so a repeated move is judged afresh.
        const current = await api.object(item.objectTypeKey, item.id, workspaceKey).catch(() => undefined);
        if (current) setItem(current);
      }
      setMoving(false);
    }
  }

  /** Moves every record in one atomic batch, each claiming the version it was read at. */
  async function moveSeveral() {
    const parent = top ? null : { id: selected!.id };
    try {
      const current = changeSet ? ((await refresh?.()) ?? changeSet) : undefined;
      const result = await api.runBatch(
        {
          ...(current ? { changeSetId: current.id, expectedChangeSetVersion: current.version } : { workspaceKey }),
          policy: "atomic",
          run: "inline",
          stage: "execute",
          items: [item, ...others].map((record) => ({
            op: "update" as const,
            ref: record.name,
            target: { id: record.id },
            expectedVersion: record.version,
            parent,
          })),
        },
        newIdempotencyKey(),
      );
      if (result.job.result !== "applied") {
        const refused = result.items.find((outcome) => outcome.status === "rejected" && outcome.error);
        setError(
          refused?.error
            ? `${refused.ref ?? "A record"}: ${refused.error.message}`
            : (result.job.error?.message ?? "The records were not moved."),
        );
        setMoving(false);
        return;
      }
      onMoved({ ...item, parentObjectId: parent?.id ?? null });
    } catch (cause) {
      setError(errorMessage(cause));
      setMoving(false);
    }
  }

  const count = others.length + 1;
  const title = several ? `Move ${count} records` : `Move ${label}`;
  const names = [item, ...others].map((record) => record.name);
  return (
    <Modal title={title} eyebrow="Move to" onClose={onClose} busy={moving}>
      <form
        className="mapping-dialog tree-move"
        onSubmit={(event) => {
          event.preventDefault();
          void move();
        }}
      >
        {several ? (
          <p className="muted">
            {names.slice(0, 10).join(", ")}
            {names.length > 10 ? ` and ${names.length - 10} more` : ""}.
          </p>
        ) : (
          <p className="muted">{where ? `Now in ${where}.` : "Now at the top of the hierarchy."}</p>
        )}
        <SearchField
          className="candidate-search"
          label="Search new locations"
          value={search}
          onChange={setSearch}
          placeholder="Search by name…"
          autoFocus
          disabled={moving}
        />
        <fieldset className="candidate-list" aria-busy={candidates.loading || undefined} disabled={moving}>
          <legend className="visually-hidden">Choose where to move {label}</legend>
          {topLevel && (
            <Candidate
              className="candidate-top-level"
              selected={top}
              disabled={Boolean(topLevel.refusal)}
              control={
                <input
                  type="radio"
                  name="tree-move-target"
                  value=""
                  checked={top}
                  disabled={Boolean(topLevel.refusal)}
                  onChange={() => setSelected(TOP_LEVEL)}
                />
              }
              type={null}
              name="Top level"
              detail="No parent"
            >
              {topLevel.refusal && (
                <StatusPill tone="neutral" marker={false}>
                  {topLevel.refusal}
                </StatusPill>
              )}
              {!topLevel.refusal && topLevel.becomes && (
                <StatusPill tone="success" marker={false}>
                  Becomes {typeNames(model, topLevel.becomes)}
                </StatusPill>
              )}
            </Candidate>
          )}
          <ScrollWindow
            list={candidates}
            label="New locations"
            noun={["location", "locations"]}
            pageSize={PAGE_SIZE}
            rowNavigation={false}
            footer={false}
            className="candidate-scroll"
          >
            {(drawn) => (
              <>
                <WindowSpacer as="div" edge="before" height={drawn.before} />
                {drawn.rows.map(({ index, item: candidate, size }) => {
                  if (candidate === undefined)
                    return (
                      <WindowPlaceholder
                        key={`placeholder-${index}`}
                        as="div"
                        index={index}
                        size={size}
                        className="candidate"
                      />
                    );
                  const ancestors = candidate.path
                    .slice(0, -1)
                    .map((part) => part.name)
                    .join(" / ");
                  const typeName = types.size > 1 ? objectTypeFor(model, candidate.objectTypeKey)?.name : undefined;
                  const newTypes = candidate.eligible ? becomes(candidate) : undefined;
                  return (
                    <Candidate
                      key={candidate.id}
                      ref={drawn.measure}
                      data-row-key={candidate.id}
                      data-row-index={index}
                      selected={selected?.id === candidate.id}
                      disabled={!candidate.eligible}
                      control={
                        <input
                          type="radio"
                          name="tree-move-target"
                          value={candidate.id}
                          checked={selected?.id === candidate.id}
                          disabled={!candidate.eligible}
                          onChange={() => setSelected(candidate)}
                        />
                      }
                      type={objectTypeTile(model, candidate.objectTypeKey)}
                      name={candidate.name}
                      detail={[typeName, ancestors].filter(Boolean).join(" · ")}
                    >
                      {!candidate.eligible && candidate.reason && (
                        <StatusPill tone="neutral" marker={false}>
                          {MOVE_REFUSAL_TEXT[candidate.reason]}
                        </StatusPill>
                      )}
                      {newTypes && (
                        <StatusPill tone="success" marker={false}>
                          Becomes {typeNames(model, newTypes)}
                        </StatusPill>
                      )}
                    </Candidate>
                  );
                })}
                <WindowSpacer as="div" edge="after" height={drawn.after} />
                {candidates.loading && !candidates.items.length && <p className="candidate-state">Loading…</p>}
                {!candidates.loading && !candidates.error && !candidates.items.length && (
                  <p className="candidate-state">
                    {debounced
                      ? `No location matches “${debounced}”.`
                      : topLevel && !topLevel.refusal
                        ? `No other record can contain ${label}.`
                        : `${label} cannot move anywhere else.`}
                  </p>
                )}
              </>
            )}
          </ScrollWindow>
          {candidates.error && <InlineError message={candidates.error} onRetry={candidates.retry} />}
        </fieldset>
        {refusedOther && (
          <Notice tone="warning" title="Not every record can move there">
            {refusedOther}
          </Notice>
        )}
        {error && (
          <Notice tone="error" title={several ? `Could not move the ${count} records` : `Could not move ${label}`}>
            {error}
          </Notice>
        )}
        <p className="visually-hidden" role="status">
          {moving ? (several ? `Moving ${count} records…` : `Moving ${label}…`) : ""}
        </p>
        <div className="dialog-actions">
          {moving && (
            <span className="muted tree-move-progress" aria-hidden="true">
              Moving {several ? `${count} records` : label} and everything in them; a large branch can take a few
              seconds.
            </span>
          )}
          <span className="dialog-actions-spacer" />
          <button type="button" className="secondary" disabled={moving} onClick={onClose}>
            Cancel
          </button>
          <button className="primary" disabled={moving || !eligible}>
            {moving
              ? "Moving…"
              : changesType
                ? "Preview the type change"
                : top
                  ? "Move to the top level"
                  : selected
                    ? `Move to ${selected.name}`
                    : "Move"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
