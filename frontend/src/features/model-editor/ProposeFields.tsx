/**
 * What to propose from a workbook (0.10 A6b, D87): a new application (its name), a new model (the
 * same application in a draft that starts empty, not from the active model; the start only, the
 * user's request 2026-10-14), additions to the model (columns matched to its types and attributes
 * first, D91), or nothing (mapping by hand, A5b). Shared by New from a workbook and ⋯ › Propose again….
 */

import { AssistantChoice } from "@/features/model-editor/AssistantChoice";
import type { AiSystemInfo, InferenceRequest } from "@/types";
import { FormField } from "@/ui/FormField";

export interface ProposeChoice {
  mode: InferenceRequest["mode"] | "newModel" | "none";
  applicationName: string;
  /** Whether the AI assistant is asked too; sent only where it is offered. */
  assistant?: boolean;
}

/** The request a choice sends; none for mapping by hand. A new model proposes a new application into
 * the empty draft it starts. */
export function proposeRequest(choice: ProposeChoice, assistantOffered = false): InferenceRequest | undefined {
  if (choice.mode === "none") return undefined;
  const asked = assistantOffered ? { assistant: choice.assistant ?? true } : {};
  if (choice.mode === "extend") return { mode: "extend", ...asked };
  const name = choice.applicationName.trim();
  return { mode: "newApplication", ...(name ? { applicationName: name } : {}), ...asked };
}

/** An application name from a file's name: "office-supplies.xlsx" → "Office supplies". */
export function nameOfFile(fileName: string): string {
  const stem = fileName
    .replace(/\.[^.]+$/, "")
    .replace(/[_-]+/g, " ")
    .trim();
  return stem ? stem[0].toUpperCase() + stem.slice(1) : "";
}

export function ProposeFields({
  value,
  onChange,
  start,
  assistantOffer,
}: {
  value: ProposeChoice;
  onChange: (choice: ProposeChoice) => void;
  /** At the start, a new model and mapping by hand are offered too; not when proposing again. */
  start?: boolean;
  /** The provider, when the AI assistant is offered (`useAssistantOffer`); the choice is not rendered without it. */
  assistantOffer?: AiSystemInfo;
}) {
  const options: { mode: ProposeChoice["mode"]; title: string; text: string }[] = [
    {
      mode: "newApplication",
      title: "A new application",
      text: "Each sheet becomes types and lists in an application of its own, added to the model the draft starts from.",
    },
    ...(start
      ? [
          {
            mode: "newModel" as const,
            title: "A new model",
            text: "The same application in a model of its own: the draft starts empty, without the active model's applications.",
          },
        ]
      : []),
    {
      mode: "extend",
      title: "Additions to the model",
      text: "Matched to the model's types and attributes first, by name and by its records' values; only the rest is added.",
    },
    ...(start
      ? [
          {
            mode: "none" as const,
            title: "Nothing: I will map it by hand",
            text: "The editor opens on an untouched model; you map each column.",
          },
        ]
      : []),
  ];
  return (
    <>
      <fieldset className="map-kinds propose-fields">
        <legend>Propose</legend>
        {options.map((item) => (
          <label key={item.mode} className={value.mode === item.mode ? "selected" : undefined}>
            <input
              type="radio"
              name="propose-mode"
              value={item.mode}
              checked={value.mode === item.mode}
              onChange={() => onChange({ ...value, mode: item.mode })}
            />
            <span>
              <strong>{item.title}</strong>
              <span className="muted">{item.text}</span>
            </span>
          </label>
        ))}
      </fieldset>
      {(value.mode === "newApplication" || value.mode === "newModel") && (
        <FormField label="Application name">
          {(control) => (
            <input
              {...control}
              value={value.applicationName}
              maxLength={200}
              onChange={(event) => onChange({ ...value, applicationName: event.target.value })}
            />
          )}
        </FormField>
      )}
      {value.mode !== "none" && assistantOffer && (
        <AssistantChoice
          offer={assistantOffer}
          checked={value.assistant ?? true}
          onChange={(assistant) => onChange({ ...value, assistant })}
        />
      )}
    </>
  );
}
