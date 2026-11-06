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
import { DesignModel } from "./DesignModel";
import { DesignQuestions } from "./DesignQuestions";
import { ProposalMoves } from "./ProposalMoves";
import { TaskNotes } from "./TaskNotes";
import { TellAssistant } from "./TellAssistant";
import { modelNames, proposalRefusal } from "./aiTaskDesign";
import { isDesignCheck, notLoadedEntries } from "./aiTaskText";
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
  const check = isDesignCheck(task.check) ? task.check : undefined;
  return (
    <div className="task-check">
      <TaskNotes notes={task.notes} />
      <Section
        title="The assistant’s proposal"
        actions={
          refusal ? undefined : (
            <span id="journey-accept">
              {draftId && onOpenEditor && (
                <button type="button" className="secondary" disabled={pending} onClick={() => onOpenEditor(draftId)}>
                  Open in the model editor
                </button>
              )}{" "}
              {canLoad && (
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
        <p className="task-reason">
          {unchanged
            ? "Nothing is loaded before you accept. Accepting prepares the change in a change set for your review; nothing is published."
            : design.moves?.length
              ? "Nothing is installed before you accept the model, and no record moves before you confirm the migration."
              : "Nothing is installed or loaded before you accept the model."}
        </p>
        {check && (
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
            onOpenEditor={draftId && onOpenEditor ? () => onOpenEditor(draftId) : undefined}
          />
        </Disclosure>
      )}
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
