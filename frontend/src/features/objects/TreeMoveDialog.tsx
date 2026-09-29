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
 */

import { useState } from "react";
import { errorMessage, isApiError } from "@/api/errors";
import { useDataApi } from "@/features/workspaces/WorkspaceDataContext";
import { useCursorWindow } from "@/lib/hooks/useCursorWindow";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import { objectTypeFor } from "@/model/lookup";
import { MOVE_REFUSAL_TEXT } from "@/model/treeDrop";
import type { EngineModel, ObjectItem, ParentCandidate } from "@/types";
import { Icon } from "@/ui/Icon";
import { InlineError } from "@/ui/InlineError";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { ScrollWindow } from "@/ui/ScrollWindow";

const PAGE_SIZE = 20;

/** The top level as a choice: no parent. */
const TOP_LEVEL = "top-level";

export function TreeMoveDialog({
  model,
  item: initial,
  label,
  workspaceKey,
  target,
  topLevel,
  onClose,
  onMoved,
}: {
  model: EngineModel;
  item: ObjectItem;
  label: string;
  workspaceKey: string;
  /** A parent chosen before the dialog opens, such as a drop target; `null` is the top level. */
  target?: Pick<ObjectItem, "id" | "objectTypeKey" | "name" | "path"> | null;
  /** Offers the top level, refused with the reason in words when `refusal` is set. */
  topLevel?: { refusal?: string };
  onClose: () => void;
  onMoved: (moved: ObjectItem) => void;
}) {
  const api = useDataApi();
  const [item, setItem] = useState(initial);
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
        ...selector,
        pageSize: PAGE_SIZE,
      }),
    [item.objectTypeKey, item.id, workspaceKey, debounced],
  );
  const top = chosen === TOP_LEVEL;
  const selected =
    chosen === TOP_LEVEL ? undefined : (candidates.items.find((candidate) => candidate.id === chosen?.id) ?? chosen);
  const eligible = top ? Boolean(topLevel && !topLevel.refusal) : Boolean(selected?.eligible);
  const types = new Set(candidates.items.map((candidate) => candidate.objectTypeKey));
  const where = item.path
    .slice(0, -1)
    .map((part) => part.name)
    .join(" / ");

  async function move() {
    if (!eligible) return;
    setMoving(true);
    setError("");
    try {
      const moved = await api.updateObject(item.objectTypeKey, item.id, {
        expectedVersion: item.version,
        parentObjectId: top ? null : (selected?.id ?? null),
      });
      onMoved(moved);
    } catch (cause) {
      setError(errorMessage(cause));
      if (isApiError(cause, "version_conflict")) {
        // Someone changed the record: claim its new version so a repeated move is judged afresh.
        const current = await api.object(item.objectTypeKey, item.id, workspaceKey).catch(() => undefined);
        if (current) setItem(current);
      }
      setMoving(false);
    }
  }

  return (
    <Modal title={`Move ${label}`} eyebrow="Move to" onClose={onClose} busy={moving}>
      <form
        className="mapping-dialog tree-move"
        onSubmit={(event) => {
          event.preventDefault();
          void move();
        }}
      >
        <p className="muted">{where ? `Now in ${where}.` : "Now at the top of the hierarchy."}</p>
        <label className="search-box candidate-search">
          <Icon name="search" />
          <input
            aria-label="Search new locations"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search by name…"
            autoFocus
            disabled={moving}
          />
        </label>
        <fieldset className="candidate-list" aria-busy={candidates.loading || undefined} disabled={moving}>
          <legend className="visually-hidden">Choose where to move {label}</legend>
          {topLevel && (
            <label
              className={`candidate candidate-top-level${top ? " selected" : ""}${topLevel.refusal ? " is-disabled" : ""}`}
            >
              <input
                type="radio"
                name="tree-move-target"
                value=""
                checked={top}
                disabled={Boolean(topLevel.refusal)}
                onChange={() => setSelected(TOP_LEVEL)}
              />
              <span className="candidate-text">
                <span className="candidate-name">Top level</span>
                <small>No parent</small>
              </span>
              {topLevel.refusal && <span className="pill">{topLevel.refusal}</span>}
            </label>
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
            {candidates.items.map((candidate, position) => {
              const ancestors = candidate.path
                .slice(0, -1)
                .map((part) => part.name)
                .join(" / ");
              const typeName = types.size > 1 ? objectTypeFor(model, candidate.objectTypeKey)?.name : undefined;
              return (
                <label
                  key={candidate.id}
                  data-row-key={candidate.id}
                  data-row-index={candidates.startIndex + position}
                  className={`candidate${selected?.id === candidate.id ? " selected" : ""}${candidate.eligible ? "" : " is-disabled"}`}
                >
                  <input
                    type="radio"
                    name="tree-move-target"
                    value={candidate.id}
                    checked={selected?.id === candidate.id}
                    disabled={!candidate.eligible}
                    onChange={() => setSelected(candidate)}
                  />
                  <span className="candidate-text">
                    <span className="candidate-name">{candidate.name}</span>
                    <small>{[typeName, ancestors].filter(Boolean).join(" · ")}</small>
                  </span>
                  {!candidate.eligible && candidate.reason && (
                    <span className="pill">{MOVE_REFUSAL_TEXT[candidate.reason]}</span>
                  )}
                </label>
              );
            })}
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
          </ScrollWindow>
          {candidates.error && <InlineError message={candidates.error} onRetry={candidates.retry} />}
        </fieldset>
        {error && (
          <Notice tone="error" title={`Could not move ${label}`}>
            {error}
          </Notice>
        )}
        <p className="visually-hidden" role="status">
          {moving ? `Moving ${label}…` : ""}
        </p>
        <div className="dialog-actions">
          {moving && (
            <span className="muted tree-move-progress" aria-hidden="true">
              Moving {label} and everything in it; a large branch can take a few seconds.
            </span>
          )}
          <span className="dialog-actions-spacer" />
          <button type="button" className="secondary" disabled={moving} onClick={onClose}>
            Cancel
          </button>
          <button className="primary" disabled={moving || !eligible}>
            {moving ? "Moving…" : top ? "Move to the top level" : selected ? `Move to ${selected.name}` : "Move"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
