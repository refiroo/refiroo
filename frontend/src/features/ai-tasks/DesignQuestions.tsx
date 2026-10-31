/**
 * The assistant's questions (0.16 AP6, board 8): each a group of radio options with the assumed
 * answer (or the one already given) chosen, and one button that sends every choice and designs again.
 */

import { useState } from "react";
import type { AiTaskQuestion } from "@/types";
import { Choice } from "@/ui/Choice";
import { Card } from "@/ui/Card";

export function DesignQuestions({
  questions,
  answers,
  pending,
  onAnswer,
}: {
  questions: AiTaskQuestion[];
  answers: Record<string, string>;
  pending: boolean;
  onAnswer: (answers: Record<string, string>) => void;
}) {
  const [chosen, setChosen] = useState<Record<string, string>>(() =>
    Object.fromEntries(questions.map((q) => [q.text, answers[q.text] ?? q.assumed ?? q.options[0] ?? ""])),
  );
  if (questions.length === 0) return null;
  return (
    <Card as="section" title="Questions" className="task-table" id="journey-questions" tabIndex={-1}>
      <p className="task-reason">
        The assistant assumed the marked answers. Change any that is wrong and design again.
      </p>
      {questions.map((question, index) => (
        <fieldset key={question.text} className="task-question" disabled={pending}>
          <legend>{question.text}</legend>
          <Choice
            name={`question-${index}`}
            value={chosen[question.text] ?? ""}
            options={question.options.map((option) => [option, option] as const)}
            onChange={(option) => setChosen({ ...chosen, [question.text]: option })}
          />
        </fieldset>
      ))}
      <div className="task-actions">
        <button type="button" className="secondary" disabled={pending} onClick={() => onAnswer(chosen)}>
          {pending ? "Starting…" : "Answer and design again"}
        </button>
      </div>
    </Card>
  );
}
