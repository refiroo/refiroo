/**
 * "Change this model…" on a workspace's ⋯ menu (0.16 AP12): the assistant is on, and the person holds Use AI
 * proposals, Model authoring and Model release there (without the model groups the session could not install
 * what it proposes, so the flow could not finish and nothing is offered). Not for a retired workspace.
 */

import { useHoldsGroup } from "@/app/useMe";
import { holds, useWorkspacePermissions } from "@/features/security/permissions";
import { useAssistantOfferIn } from "@/features/settings/useWorkspaceAiOffer";

export function useChangeModelOffer(workspaceKey: string, status: string | undefined): boolean {
  const permissions = useWorkspacePermissions(workspaceKey);
  const authors = useHoldsGroup("model-authoring");
  const offer = useAssistantOfferIn(workspaceKey, permissions);
  return Boolean(offer?.assistant && authors && holds(permissions, "model-release") && status === "active");
}
