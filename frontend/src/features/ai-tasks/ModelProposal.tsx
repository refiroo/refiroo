/**
 * The assistant's proposal of the model (0.16 AP6r, stage "model"): what it would build in plain
 * sentences, its own checks, what it left out, and two ways on: tell it what to change, or accept.
 * Nothing is loaded before the model is accepted.
 */

import type { AiTask, EngineModel } from "@/types";
import { AssistantText } from "@/ui/AssistantText";
import { Card } from "@/ui/Card";
import { Disclosure } from "@/ui/Disclosure";
import { Notice } from "@/ui/Notice";
import { Section } from "@/ui/Section";
import { StatusPill } from "@/ui/StatusPill";
import { CannotLoad } from "./CannotLoad";
import { DesignLoad } from "./DesignLoad";
import { DesignModel } from "./DesignModel";
import { DesignQuestions } from "./DesignQuestions";
import { ProposalMoves } from "./ProposalMoves";
import { TaskNotes } from "./TaskNotes";
import { TellAssistant } from "./TellAssistant";
import { changesModel, modelNames, proposalRefusal } from "./aiTaskDesign";
import { notLoadedEntries } from "./aiTaskText";
import { count } from "@/features/settings/limits";

export function ModelProposal({
  task,
  pending,
  model,
  canLoad = true,
  workspaceLabel,
  onOpenEditor,
  onClose,
  onDiscard,
  onAnswer,
  onCorrect,
  onAccept,
}: {
  task: AiTask;
  pending: boolean;
  model?: EngineModel;
  /** Whether the person holds Work in change sets: accepting loads (0.16 AP13, AP-D59). */
  canLoad?: boolean;
  workspaceLabel?: string;
  onOpenEditor?: (draftId: string) => void;
  /** Back to the workspace; the proposal stays for later. */
  onClose?: () => void;
  /** Throws the proposal and its draft away. */
  onDiscard?: () => void;
  onAnswer: (answers: Record<string, string>) => void;
  onCorrect: (correction: string) => void;
  onAccept: () => void;
}) {
  const design = task.design;
  if (!design) return null;
  const names = modelNames(model, design.operations);
  const draftId = task.draftId;
  // A words task whose model does not change has no draft: the proposal is the change it will make.
  const unchanged = !draftId && !!design.modelUnchanged;
  const outline = design.outline ?? [];
  const checks = design.checks ?? [];
  const corrections = design.corrections ?? [];
  const leftOut = notLoadedEntries(task, true);
  const refusal = proposalRefusal(task);
  const check = task.check ?? undefined;
  // The engine checked the assistant's items (0.13 AB): the card says what the load does, and accepting loads exactly that.
  const load = design.load ?? undefined;
  // With moves, accepting installs the model for the migration; the load is not run (the bottom block is not shown).
  const moving = (design.moves?.length ?? 0) > 0;
  const accepts = !load || moving;
  return (
    <div className="task-check">
      <TaskNotes notes={task.notes} />
      <Section
        title="The assistant’s proposal"
        actions={
          refusal ? undefined : (
            <span id={accepts ? "journey-accept" : undefined}>
              {draftId && onOpenEditor && (
                <button type="button" className="secondary" disabled={pending} onClick={() => onOpenEditor(draftId)}>
                  Open in the model editor
                </button>
              )}{" "}
              {canLoad && accepts && (
                <button type="button" className="primary" disabled={pending} onClick={onAccept}>
                  {unchanged ? "Accept" : "Accept the model"}
                </button>
              )}
            </span>
          )
        }
      >
        {refusal && (
          <Notice tone="warning">
            The engine could not apply this proposal: {refusal} Tell the assistant what to change below.
          </Notice>
        )}
        {!canLoad && !refusal && <CannotLoad workspaceLabel={workspaceLabel ?? task.workspaceKey} />}
        <AssistantText text={design.summary} />
        {outline.length > 0 && (
          <ul className="task-sheet-list" aria-label="The types it proposes">
            {outline.map((item) => (
              <li key={item.objectTypeKey}>
                <strong>{item.name ?? names.type(item.objectTypeKey)}</strong> {item.text}
              </li>
            ))}
          </ul>
        )}
        {unchanged && <p>No change to the model.</p>}
        {(design.removals?.length ?? 0) > 0 && (
          <Notice tone="warning" title="Deleted as you asked">
            <ul>
              {design.removals?.map((item) => (
                <li key={`${item.kind}:${item.key}`}>{item.text}</li>
              ))}
            </ul>
          </Notice>
        )}
        <p className="task-reason">
          {load && !design.moves?.length
            ? "Nothing is installed or loaded before you accept."
            : unchanged
              ? "Nothing is loaded before you accept. Accepting prepares the change in a change set for your review; nothing is published."
              : design.moves?.length
                ? "Nothing is installed before you accept the model, and no record moves before you confirm the migration."
                : "Nothing is installed or loaded before you accept the model."}
        </p>
        {check && !load && (
          <Notice
            tone={check.summary.refused > 0 || !!check.summary.skipped || check.draftChanged ? "warning" : "success"}
            title={check.draftChanged ? "The check from before the draft's last change" : "The check of every row"}
          >
            {check.draftChanged && <p>It does not cover the model as it stands now.</p>}
            {count(check.summary.created)} new,{" "}
            {!!check.summary.relationships && <>{count(check.summary.relationships)} relationships, </>}
            {count(check.summary.updated)} changed, {count(check.summary.unchanged)} unchanged,{" "}
            {count(check.summary.refused)} refused
            {!!check.summary.skipped && <>, {count(check.summary.skipped)} skipped for an empty key</>}.
            {check.refused.length > 0 && (
              <ul className="task-sheet-list">
                {check.refused.map((group, index) => (
                  <li key={index}>
                    <strong>{group.sheet}:</strong> {count(group.rows)} rows,{" "}
                    {group.examples?.[0]?.message ?? group.code}
                  </li>
                ))}
              </ul>
            )}
          </Notice>
        )}
      </Section>
      <ProposalMoves task={task} />
      {!unchanged && (
        <Disclosure variant="button" label="Show the model change" openLabel="Hide the model change">
          <DesignModel
            design={design}
            names={names}
            workbook={!!task.fileName}
            draft={!!draftId}
            onOpenEditor={draftId && onOpenEditor ? () => onOpenEditor(draftId) : undefined}
          />
        </Disclosure>
      )}
      {load && <DesignLoad load={load} names={names} stale={!!check?.draftChanged} moves={moving} />}
      {checks.length > 0 && (
        <Section title="Checks" headingLevel={3}>
          <ul className="task-sheet-list" aria-label="The assistant’s checks">
            {checks.map((check) => (
              <li key={check.id}>
                {check.open ? (
                  <StatusPill tone="warning">Needs attention</StatusPill>
                ) : (
                  <span aria-label="Checked">✓</span>
                )}{" "}
                {check.text}
                {check.explanation && <p className="task-reason">{check.explanation}</p>}
              </li>
            ))}
          </ul>
        </Section>
      )}
      <DesignQuestions
        key={`${task.version}-${design.rounds}`}
        questions={design.questions}
        answers={design.answers}
        pending={pending}
        onAnswer={onAnswer}
      />
      {leftOut.length > 0 && (
        <Card as="section" title="Columns left out" className="task-table">
          <ul className="task-sheet-list">
            {leftOut.map((entry, index) => (
              <li key={index}>
                <strong>{entry.sheet}:</strong> {entry.text}
              </li>
            ))}
          </ul>
        </Card>
      )}
      {load && !refusal && canLoad && !moving && (
        <div className="load-accept" id="journey-accept" tabIndex={-1}>
          <p>
            <strong>Accept and load to change set.</strong> The engine{" "}
            {changesModel(design) ? "installs the model and loads" : "loads"} exactly the records above into a new
            change set. No assistant turn, nothing published: you review and publish the change set.
          </p>
          <div className="task-actions">
            {task.canTell !== false && (
              <button
                type="button"
                className="secondary"
                disabled={pending}
                onClick={() => document.getElementById("task-tell")?.querySelector("textarea")?.focus()}
              >
                Give the assistant other words
              </button>
            )}
            <button type="button" className="primary" disabled={pending} onClick={onAccept}>
              Accept and load to change set
            </button>
          </div>
        </div>
      )}
      {task.canTell !== false && (
        <Section title={unchanged ? "Correct the proposal" : "Correct the model"} headingLevel={3}>
          {corrections.length > 0 && (
            <ul className="task-sheet-list" aria-label="What you asked">
              {corrections.map((correction, index) => (
                <li key={index}>You asked: {correction}</li>
              ))}
            </ul>
          )}
          <TellAssistant
            anchor="task-tell"
            label="Tell the assistant what to change"
            placeholder="e.g. “Sponsors belong to operators, not to locations”"
            pending={pending}
            onSend={onCorrect}
          />
        </Section>
      )}
      {(onClose || onDiscard) && (
        <div className="task-actions">
          {onDiscard && (
            <button type="button" className="secondary" disabled={pending} onClick={onDiscard}>
              Discard this proposal
            </button>
          )}
          {onClose && (
            <button type="button" className="secondary" onClick={onClose}>
              Close
            </button>
          )}
        </div>
      )}
    </div>
  );
}
