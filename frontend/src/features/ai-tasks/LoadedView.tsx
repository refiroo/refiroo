/** The load's end (0.16 AP6a, board 7): into the change set, what it holds, where to go next, and what was not loaded (folded). */

import { useState } from "react";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import type { AiTask, RouteState } from "@/types";
import { Notice } from "@/ui/Notice";
import { RouteLink } from "@/ui/RouteLink";
import { Section } from "@/ui/Section";
import { NotLoaded } from "./NotLoaded";
import { TellAssistant } from "./TellAssistant";
import { WayOnward } from "./WayOnward";
import type { AssistantOffers } from "./useAssistantOffers";
import { routePath } from "@/routing/routes";
import { notLoadedEntries, plural, skippedText } from "./aiTaskText";

/** What was loaded, in a sentence: the new, changed and removed records the import counted. */
export function loadedSentence(task: AiTask): { done: string; rest: string } {
  const counts = task.result?.counts;
  const created = counts?.created ?? 0;
  const changed = counts?.updated ?? 0;
  const removed = counts?.deleted ?? 0;
  const unchanged = counts?.unchanged ?? 0;
  const linked = counts?.relationsCreated ?? 0;
  const relinked = counts?.relationsUpdated ?? 0;
  const unlinked = counts?.relationsRemoved ?? 0;
  const said = [
    created > 0 && `${plural(created, "record")} new`,
    changed > 0 && `${plural(changed, "record")} changed`,
    removed > 0 && `${plural(removed, "record")} removed`,
    linked > 0 && `${plural(linked, "relationship")} new`,
    relinked > 0 && `${plural(relinked, "relationship")} changed`,
    unlinked > 0 && `${plural(unlinked, "relationship")} removed`,
  ].filter((part): part is string => !!part);
  const joined = said.length > 1 ? `${said.slice(0, -1).join(", ")} and ${said[said.length - 1]}` : said[0];
  return {
    done: joined ?? "",
    rest: joined
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
  pending,
  canChange,
  offers,
  publications,
  onNavigate,
  onClose,
  onTell,
  onDiscard,
}: {
  task: AiTask;
  /** The change set's review, when an application to show it in is known. */
  review?: RouteState;
  /** The workspace's name, for the line about an installed model change. */
  workspaceLabel?: string;
  pending: boolean;
  /** Whether the person holds Work in change sets: discarding the change set, or loading again, needs it. */
  canChange: boolean;
  /** What the assistant may be asked after a publication (AP-D58). */
  offers: AssistantOffers;
  /** The application's publications, where the published change set is listed. */
  publications?: RouteState;
  onNavigate: (route: RouteState) => void;
  /** Back to the workspace, the change set kept. */
  onClose?: () => void;
  /** The person's words: the change set is discarded and the same session loads again (AP-D56). */
  onTell: (words: string) => void;
  /** Discards the task with its change set. */
  onDiscard: () => void;
}) {
  const [discarding, setDiscarding] = useState(false);
  const [again, setAgain] = useState<string>();
  const result = task.result;
  const sentence = loadedSentence(task);
  const entries = notLoadedEntries(task, true);
  const columns = entries.filter((entry) => entry.text.startsWith("Column “")).length;
  const sheets = entries.length - columns;
  const followed = task.reading?.profile;
  const profile: RouteState | undefined = result?.profileKey
    ? { kind: "settings", page: "import-profiles", profileKey: result.profileKey }
    : undefined;
  if (result?.published)
    return (
      <>
        <Section title={`Published: “${result.changeSetName ?? "Unnamed"}”`}>
          <Notice tone="success">
            <strong>Published.</strong> {sentence.done ? `${sentence.done}. ` : ""}It is live in{" "}
            {workspaceLabel ?? task.workspaceKey}.{" "}
            {publications && (
              <RouteLink href={routePath(publications)} onNavigate={() => onNavigate(publications)}>
                Open the publications
              </RouteLink>
            )}
          </Notice>
          {profile && (
            <div className="task-actions">
              <button type="button" className="secondary" onClick={() => onNavigate(profile)}>
                Open the profile
              </button>
            </div>
          )}
        </Section>
        <Section title="Something not right?">
          <WayOnward
            task={task}
            workspaceLabel={workspaceLabel ?? task.workspaceKey}
            offers={offers}
            onNavigate={onNavigate}
          />
          {onClose && (
            <div className="task-actions">
              <button type="button" className="secondary" onClick={onClose}>
                Back to the workspace
              </button>
            </div>
          )}
        </Section>
      </>
    );
  return (
    <Section title={`Loaded into the change set “${result?.changeSetName ?? "Unnamed"}”`}>
      <Notice tone="success">
        {sentence.done && (
          <>
            <strong>{sentence.done}.</strong>{" "}
          </>
        )}
        {sentence.rest && `${sentence.rest} `}Live data is unchanged until the change set is approved and published.
        {/* A session's changes do not carry this yet (AP9). */}
        {!task.design?.agentSession &&
          " Each change notes that the AI assistant prepared the load and that you confirmed it."}
      </Notice>
      <ul className="task-next">
        {result?.releaseId && (
          <li>
            {task.design?.itemsLoad
              ? `The model change was installed, not activated: publishing the change set moves ${workspaceLabel ?? task.workspaceKey} to it.`
              : `The model change was installed and activated in ${workspaceLabel ?? task.workspaceKey}.`}
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
        {result?.profileNotSaved && <li>{result.profileNotSaved}</li>}
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
          {onClose && (
            <button type="button" className="secondary" onClick={onClose}>
              Close
            </button>
          )}
        </div>
      )}
      {result &&
        (canChange ? (
          <TellAssistant
            label="Not what you wanted? Tell the assistant"
            hint={
              task.canTell
                ? "The same assistant loads again from its proposal with your words. This change set is discarded first, with any edits you made in it."
                : undefined
            }
            sendLabel="Discard and load again"
            pending={pending}
            onSend={setAgain}
            hideSend={!task.canTell}
          >
            <button type="button" className="secondary" disabled={pending} onClick={() => setDiscarding(true)}>
              Discard the change set
            </button>
          </TellAssistant>
        ) : (
          <p className="admin-hint">
            Discarding the change set, or telling the assistant to load again, needs Work in change sets in{" "}
            {workspaceLabel ?? task.workspaceKey}.
          </p>
        ))}
      {!task.canTell && task.design?.agentSession && (
        <>
          <p className="admin-hint">
            The assistant&apos;s session for this task has ended, so it cannot load again. Discard the change set above,
            or start a new task from here.
          </p>
          <WayOnward
            task={task}
            workspaceLabel={workspaceLabel ?? task.workspaceKey}
            offers={offers}
            onNavigate={onNavigate}
          />
        </>
      )}
      {again !== undefined && (
        <ConfirmDialog
          title="Discard this change set and load again?"
          confirmLabel="Discard and load again"
          onCancel={() => setAgain(undefined)}
          onConfirm={() => {
            const words = again;
            setAgain(undefined);
            onTell(words);
          }}
        >
          Everything loaded into “{result?.changeSetName ?? "Unnamed"}” is removed, with any edits you made in it.{" "}
          {task.design?.itemsLoad
            ? "Your words go to the assistant as a correction of its proposal, which is checked again and accepted again before anything is loaded."
            : "The same assistant then loads again with your words."}{" "}
          Live data was never changed.
        </ConfirmDialog>
      )}
      {discarding && (
        <ConfirmDialog
          title="Discard this change set?"
          confirmLabel="Discard"
          onCancel={() => setDiscarding(false)}
          onConfirm={() => {
            setDiscarding(false);
            onDiscard();
          }}
        >
          Everything loaded into “{result?.changeSetName ?? "Unnamed"}” is removed and the task ends. Live data was
          never changed.
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
