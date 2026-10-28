/**
 * ⋯ › Propose again… (0.10 A6b, D92): the draft's workbook read by the patterns once more, as a new
 * application or as additions. What is still as proposed follows the workbook, each change a step;
 * what the administrator changed stays, and where the workbook reads it otherwise is an issue.
 */

import { useState } from "react";
import { Modal } from "@/ui/Modal";
import { nameOfFile, proposeRequest, ProposeFields, type ProposeChoice } from "@/features/model-editor/ProposeFields";
import { useAssistantOffer } from "@/features/model-editor/AssistantChoice";
import type { InferenceRequest } from "@/types";

export function ProposeDialog({
  fileName,
  initialMode,
  onPropose,
  onClose,
}: {
  fileName: string;
  /** The mode of the draft's last inference, if it had one. */
  initialMode?: InferenceRequest["mode"];
  onPropose: (request: InferenceRequest) => void;
  onClose: () => void;
}) {
  const [choice, setChoice] = useState<ProposeChoice>({
    mode: initialMode ?? "newApplication",
    applicationName: nameOfFile(fileName),
  });
  // The AI assistant is offered only where a provider is set and the person may use it (0.16 AP1).
  const offer = useAssistantOffer();
  const request = proposeRequest(choice, Boolean(offer));
  return (
    <Modal
      title="Propose again"
      eyebrow={fileName}
      description="The workbook is read again. Only what is still as proposed changes, each change a step you can undo; what you changed stays yours."
      size="compact"
      onClose={onClose}
    >
      <form
        className="dialog-body"
        onSubmit={(event) => {
          event.preventDefault();
          if (request) onPropose(request);
        }}
      >
        <ProposeFields value={choice} onChange={setChoice} assistantOffer={offer} />
        <div className="dialog-actions">
          <button type="button" className="secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="primary" disabled={!request}>
            Propose
          </button>
        </div>
      </form>
    </Modal>
  );
}
