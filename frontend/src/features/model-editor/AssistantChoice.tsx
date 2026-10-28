/**
 * "Also ask the AI assistant for clearer names" (0.16 AP1): offered wherever a proposal is asked for,
 * only when a provider is set and the person holds ai-proposals, and not rendered at all otherwise.
 */

import { useId } from "react";
import { holdsAnywhere, useHeldAnywhere } from "@/features/security/permissions";
import { sentToProvider } from "@/features/settings/aiText";
import { useSystem } from "@/features/settings/useSystem";
import type { AiSystemInfo } from "@/types";

/** The provider, when the assistant may be offered to this person; otherwise nothing. */
export function useAssistantOffer(): AiSystemInfo | undefined {
  const { system } = useSystem();
  const held = useHeldAnywhere();
  return system?.ai?.configured && holdsAnywhere(held, "ai-proposals") ? system.ai : undefined;
}

export function AssistantChoice({
  offer,
  checked,
  onChange,
}: {
  offer: AiSystemInfo;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  const hintId = useId();
  return (
    <div className="assistant-choice">
      <label className="checkbox">
        <input
          type="checkbox"
          checked={checked}
          aria-describedby={hintId}
          onChange={(event) => onChange(event.target.checked)}
        />
        Also ask the AI assistant for clearer names
      </label>
      <p id={hintId} className="admin-hint">
        {sentToProvider(offer.sendLevel, offer.provider)}
      </p>
    </div>
  );
}
