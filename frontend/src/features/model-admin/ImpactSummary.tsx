/**
 * The account of what a model change does, beside the check of a workspace's data (0.16 AO1, the approved
 * mock-up). Nothing is sent until the person asks: the line says what goes. The engine wrote the facts; the
 * provider only words them, and each statement leads, by a number, to the facts it rests on. When the
 * provider fails the facts stand alone. The component is used by the activation dialog and by Apply, which
 * pass what to ask and a `key` that changes with each new check, so a new check clears the account. The account
 * itself is the shared `ui/AiAccount`, which what changed in a period (0.16 AO2) uses too.
 */

import { useId } from "react";
import { useImpactSummaryOffer } from "@/features/settings/useWorkspaceAiOffer";
import type { ImpactSummary as Summary } from "@/types";
import { AiAccount, useAccountRequest } from "@/ui/AiAccount";

export function ImpactSummary({
  workspaceKey,
  ask,
}: {
  workspaceKey: string;
  /** Asks for the account; aborted when the dialog closes or another check starts. */
  ask: (signal: AbortSignal) => Promise<Summary>;
}) {
  const offer = useImpactSummaryOffer(workspaceKey);
  const { current, explain } = useAccountRequest(ask);
  const prefix = useId();
  const heading = `${prefix}-heading`;
  if (!offer) return null;
  const provider = offer.provider ?? "the AI provider";

  return (
    <section className="impact-summary" aria-labelledby={heading}>
      <h3 id={heading} className="install-heading">
        What this change does
      </h3>
      <AiAccount
        current={current}
        provider={provider}
        prefix={prefix}
        onExplain={() => void explain()}
        askingLabel="Writing the account"
        errorTitle="The account could not be asked for"
        idle={
          <div className="impact-ask">
            <p className="muted">The model's changes and record counts go to {provider}. No record value is sent.</p>
            <button type="button" className="secondary" onClick={() => void explain()}>
              Explain this change
            </button>
          </div>
        }
      />
    </section>
  );
}
