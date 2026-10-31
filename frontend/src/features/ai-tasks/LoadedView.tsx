/** The load's end (0.16 AP6a, board 7): into the change set, what it holds, where to go next, and what was not loaded (folded). */

import { useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import type { AiTask, AiTaskCheckSummary, RouteState } from "@/types";
import { Notice } from "@/ui/Notice";
import { Section } from "@/ui/Section";
import { count } from "@/features/settings/limits";
import { NotLoaded } from "./NotLoaded";
import { checkSummary } from "./CheckView";
import { isDesignCheck, notLoadedEntries, plainCheck, plural, skippedText } from "./aiTaskText";

/** What was loaded, in a sentence: the new and changed records and translations, in how many lists. */
export function loadedSentence(task: AiTask): { done: string; rest: string } {
  const counts = task.result?.counts;
  const check = plainCheck(task);
  const summary: AiTaskCheckSummary | undefined = check ? checkSummary(check.tables, check.summary) : undefined;
  const created = counts?.created ?? summary?.created ?? 0;
  const changed = counts?.updated ?? summary?.changed ?? 0;
  const removed = counts?.deleted ?? summary?.removed ?? 0;
  const unchanged = counts?.unchanged ?? summary?.unchanged ?? 0;
  const translations = summary?.translations ?? 0;
  const said = [
    created > 0 && `${plural(created, "record")} new`,
    changed > 0 && `${plural(changed, "record")} changed`,
    removed > 0 && `${plural(removed, "record")} removed`,
    translations > 0 && `${plural(translations, "translation")} new or changed`,
  ].filter((part): part is string => !!part);
  const lists = check ? ` in ${count(summary?.tablesWithChanges ?? 0)} of ${plural(check.tables.length, "list")}` : "";
  const joined = said.length > 1 ? `${said.slice(0, -1).join(", ")} and ${said[said.length - 1]}` : said[0];
  // An instruction on stored records writes relationships, not records: the list item says so.
  const relationshipsOnly = !joined && !!task.result?.linksJobId;
  return {
    done: joined ? `${joined}${lists}` : "",
    rest: relationshipsOnly
      ? ""
      : joined
        ? unchanged > 0
          ? `The other ${plural(unchanged, "record")} ${unchanged === 1 ? "was" : "were"} already as the file says.`
          : ""
        : `Nothing changed: ${unchanged > 0 ? `all ${plural(unchanged, "record")} were` : "the records were"} already as the file says.`,
  };
}

export function LoadedView({
  task,
  review,
  workspaceLabel,
  onNavigate,
  onClose,
}: {
  task: AiTask;
  /** The change set's review, when an application to show it in is known. */
  review?: RouteState;
  /** The workspace's name, for the line about an installed model change. */
  workspaceLabel?: string;
  onNavigate: (route: RouteState) => void;
  /** Back to the workspace, the change set kept. */
  onClose?: () => void;
}) {
  const [discarding, setDiscarding] = useState(false);
  const [discardError, setDiscardError] = useState("");
  const result = task.result;
  const discard = async () => {
    if (!result) return;
    try {
      const held = await api.changeSet(result.changeSetId);
      await api.discardChangeSet(result.changeSetId, held.version);
      onClose?.();
    } catch (cause) {
      setDiscardError(errorMessage(cause));
    }
  };
  const sentence = loadedSentence(task);
  const relationships = isDesignCheck(task.check) ? (task.check.summary.relationships ?? 0) : 0;
  const entries = notLoadedEntries(task, true);
  const columns = entries.filter((entry) => entry.text.startsWith("Column “")).length;
  const sheets = entries.length - columns;
  const followed = task.reading?.profile;
  const profile: RouteState | undefined = result?.profileKey
    ? { kind: "settings", page: "import-profiles", profileKey: result.profileKey }
    : undefined;
  return (
    <Section title={`Loaded into the change set “${result?.changeSetName ?? "Unnamed"}”`}>
      <Notice tone="success">
        {sentence.done && (
          <>
            <strong>{sentence.done}.</strong>{" "}
          </>
        )}
        {sentence.rest && `${sentence.rest} `}Live data is unchanged until the change set is approved and published.
        Each change notes that the AI assistant prepared the load and that you confirmed it.
      </Notice>
      <ul className="task-next">
        {result?.releaseId && (
          <li>The model change was installed and activated in {workspaceLabel ?? task.workspaceKey}.</li>
        )}
        {result?.linksJobId && (
          <li>
            {relationships > 0 ? `${plural(relationships, "relationship")} written` : "The relationships written"} into
            the same change set, after the load.
          </li>
        )}
        {review && <li>Review the change set, and submit it for approval from there.</li>}
        {profile && (
          <li>
            {followed && followed.key === result?.profileKey
              ? `Read through the profile “${followed.name}”: the next file of this layout loads without the assistant.`
              : `Saved the profile “${result?.profileKey}”: the next file of this layout loads without the assistant.`}
          </li>
        )}
      </ul>
      {(review || profile || onClose) && (
        <div className="task-actions">
          {review && (
            <button type="button" onClick={() => onNavigate(review)}>
              Review the change set
            </button>
          )}
          {profile && (
            <button type="button" className="secondary" onClick={() => onNavigate(profile)}>
              Open the profile
            </button>
          )}
          {onClose && result && (
            <button type="button" className="secondary" onClick={() => setDiscarding(true)}>
              Discard the change set
            </button>
          )}
          {onClose && (
            <button type="button" className="secondary" onClick={onClose}>
              Close
            </button>
          )}
        </div>
      )}
      {discardError && <Notice tone="error">{discardError}</Notice>}
      {discarding && (
        <ConfirmDialog
          title="Discard this change set?"
          confirmLabel="Discard"
          onCancel={() => setDiscarding(false)}
          onConfirm={() => {
            setDiscarding(false);
            void discard();
          }}
        >
          Everything loaded into “{result?.changeSetName ?? "Unnamed"}” is removed. Live data was never changed.
        </ConfirmDialog>
      )}
      <NotLoaded
        label={`Not loaded: ${skippedText([
          [columns, "column left out", "columns left out"],
          [sheets, "sheet or block not loaded", "sheets and blocks not loaded"],
        ])}`}
        entries={entries}
      />
    </Section>
  );
}
