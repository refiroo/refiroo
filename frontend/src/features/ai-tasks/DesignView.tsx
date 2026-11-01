/**
 * The assistant's design (0.16 AP6, board 8, state `checked` and, with what is there so far, while
 * `checking`): what it understood, the model change it proposes,
 * where each sheet goes, its questions and the problems the engine still reports. Nothing is
 * written until the person confirms in the check below.
 */

import type { AiTask, EngineModel } from "@/types";
import { Card } from "@/ui/Card";
import { Notice } from "@/ui/Notice";
import { DesignModel } from "./DesignModel";
import { DesignQuestions } from "./DesignQuestions";
import { DesignSheets } from "./DesignSheets";
import { TaskNotes } from "./TaskNotes";
import { modelNames } from "./aiTaskDesign";
import { plural } from "./aiTaskText";

const problems = (list: unknown[] | undefined): string[] =>
  (list ?? []).map((item) => {
    if (typeof item === "string") return item;
    const entry = item as { message?: unknown; path?: unknown };
    return typeof entry.message === "string"
      ? `${typeof entry.path === "string" ? `${entry.path}: ` : ""}${entry.message}`
      : JSON.stringify(item);
  });

export function DesignView({
  task,
  pending,
  model,
  onOpenEditor,
  onAnswer,
}: {
  task: AiTask;
  pending: boolean;
  /** The workspace's active model, for the names of its types and attributes. */
  model?: EngineModel;
  /** Opens the task's model draft in the editor. */
  onOpenEditor?: (draftId: string) => void;
  onAnswer: (answers: Record<string, string>) => void;
}) {
  const design = task.design;
  if (!design) return null;
  const draftId = task.draftId;
  const names = modelNames(model, design.operations);
  // While the assistant works these are an earlier step's findings, not what the design ends with.
  const reported =
    task.state === "checking"
      ? []
      : [...problems(design.outcome?.draftErrors), ...problems(design.outcome?.profileProblems)];
  // The same questions with other answers are a new design: the form starts again from the answers.
  const questionsKey = `${task.version}-${design.rounds}`;
  return (
    <div className="task-check">
      <TaskNotes notes={task.notes} />
      <Card as="section" className="task-summary" aria-label="What the assistant understood">
        <p>{design.summary}</p>
        <p className="task-reason">
          {task.words && <>You said: “{task.words}”. </>}
          {design.questions.length > 0 && <>{plural(design.questions.length, "question")} below. </>}
          Nothing is written until you confirm.
        </p>
      </Card>
      {reported.length > 0 && (
        <Notice tone="warning" title="The engine still reports problems with this design">
          <ul className="task-sheet-list">
            {reported.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        </Notice>
      )}
      <DesignModel
        design={design}
        names={names}
        onOpenEditor={draftId && onOpenEditor ? () => onOpenEditor(draftId) : undefined}
      />
      <DesignSheets design={design} names={names} />
      <DesignQuestions
        key={questionsKey}
        questions={design.questions}
        answers={design.answers}
        pending={pending || task.state === "checking"}
        onAnswer={onAnswer}
      />
    </div>
  );
}
