/**
 * What the assistant may be asked from a workspace (0.16 AP12, AP13, AP-D59): "Change this model…" and "Ask about
 * these records…", on the workspace's ⋯ menu and on a published task's page. Both are offered only where every
 * step can finish: the assistant is on, the person holds Use AI proposals and Work in change sets in the active
 * workspace (the load is a change set), Bulk and import and job creation (every task route needs them), and for the model also Model authoring and
 * Model release (without the model groups the session could not install what it proposes). One hook, so the two
 * places never disagree.
 */

import { useHoldsGroup } from "@/app/useMe";
import { useCapabilities } from "@/state/useSystem";
import { holds, useWorkspacePermissions } from "@/state/permissions";
import { useAssistantOfferIn } from "@/state/useWorkspaceAiOffer";

export interface AssistantOffers {
  changeModel: boolean;
  askRecords: boolean;
}

export function useAssistantOffers(workspaceKey: string | undefined, status: string | undefined): AssistantOffers {
  const permissions = useWorkspacePermissions(workspaceKey);
  const authors = useHoldsGroup("model-authoring");
  const offer = useAssistantOfferIn(workspaceKey, permissions);
  const { capabilities } = useCapabilities();
  // Every /ai/tasks route needs Bulk and import and job creation, so neither offer is drawn without them.
  const assistant =
    Boolean(offer?.assistant) &&
    status === "active" &&
    holds(permissions, "change-sets") &&
    holds(permissions, "bulk") &&
    Boolean(capabilities?.integrationJobs.createJobs);
  return {
    changeModel: assistant && Boolean(authors) && holds(permissions, "model-release"),
    askRecords: assistant,
  };
}
