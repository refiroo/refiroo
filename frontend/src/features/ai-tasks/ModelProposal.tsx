/**
 * The assistant's proposal of the model (0.16 AP6r, stage "model"): what it would build in plain
 * sentences, its own checks, what it left out, and two ways on: tell it what to change, or accept.
 * Nothing is loaded before the model is accepted.
 */

import { useState } from "react";
import type { AiTask, EngineModel } from "@/types";
import { Card } from "@/ui/Card";
import { Disclosure } from "@/ui/Disclosure";
import { FormField } from "@/ui/FormField";
import { Notice } from "@/ui/Notice";
import { Section } from "@/ui/Section";
import { StatusPill } from "@/ui/StatusPill";
import { DesignModel } from "./DesignModel";
import { DesignQuestions } from "./DesignQuestions";
import { TaskNotes } from "./TaskNotes";
import { modelNames, proposalRefusal } from "./aiTaskDesign";
import { isDesignCheck, notLoadedEntries } from "./aiTaskText";
import { count } from "@/features/settings/limits";

export function ModelProposal({
  task,
  pending,
  model,
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
  onOpenEditor?: (draftId: string) => void;
  /** Back to the workspace; the proposal stays for later. */
  onClose?: () => void;
  /** Throws the proposal and its draft away. */
  onDiscard?: () => void;
  onAnswer: (answers: Record<string, string>) => void;
  onCorrect: (correction: string) => void;
  onAccept: () => void;
}) {
  const [words, setWords] = useState("");
  const design = task.design;
  if (!design) return null;
  const names = modelNames(model, design.operations);
  const draftId = task.draftId;
  const outline = design.outline ?? [];
  const checks = design.checks ?? [];
  const corrections = design.corrections ?? [];
  const leftOut = notLoadedEntries(task, true);
  const empty = words.trim() === "";
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
              <button type="button" className="primary" disabled={pending} onClick={onAccept}>
                Accept the model
              </button>
            </span>
          )
        }
      >
        {refusal && (
          <Notice tone="warning">
            The engine could not apply this proposal: {refusal} Tell the assistant what to change below.
          </Notice>
        )}
        <p>{design.summary}</p>
        {outline.length > 0 && (
          <ul className="task-sheet-list" aria-label="The types it proposes">
            {outline.map((item) => (
              <li key={item.objectTypeKey}>
                <strong>{item.name ?? names.type(item.objectTypeKey)}</strong> {item.text}
              </li>
            ))}
          </ul>
        )}
        <p className="task-reason">Nothing is installed or loaded before you accept the model.</p>
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
      <Disclosure variant="button" label="Show the model change" openLabel="Hide the model change">
        <DesignModel
          design={design}
          names={names}
          onOpenEditor={draftId && onOpenEditor ? () => onOpenEditor(draftId) : undefined}
        />
      </Disclosure>
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
      <Section title="Correct the model" headingLevel={3}>
        {corrections.length > 0 && (
          <ul className="task-sheet-list" aria-label="What you asked">
            {corrections.map((correction, index) => (
              <li key={index}>You asked: {correction}</li>
            ))}
          </ul>
        )}
        <FormField label="Tell the assistant what to change">
          {(control) => (
            <textarea
              {...control}
              rows={3}
              value={words}
              placeholder="e.g. “Sponsors belong to operators, not to locations”"
              onChange={(event) => setWords(event.target.value)}
            />
          )}
        </FormField>
        <div className="task-actions">
          <button
            type="button"
            className="secondary"
            disabled={empty || pending}
            onClick={() => onCorrect(words.trim())}
          >
            Send to the assistant
          </button>
        </div>
      </Section>
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
