/**
 * What the browser may do with moves (D14, D146): mapping steps need background jobs; a move also
 * needs model administration. Without them the mappings and moves are read only, and the page says
 * which setting turns them on.
 */

import type { CapabilitiesResponse } from "@/types";

export interface MoveAbility {
  canMap: boolean;
  canMove: boolean;
  reason: string;
}

export function moveAbility(capabilities: CapabilitiesResponse | undefined): MoveAbility {
  if (!capabilities) return { canMap: false, canMove: false, reason: "" };
  const jobs = capabilities.integrationJobs.createJobs;
  const admin = capabilities.modelAdmin.activate;
  const canMap = jobs && admin;
  const reason = !jobs
    ? `Mappings and moves need background jobs, which this instance does not run (${capabilities.integrationJobs.setting}).`
    : !admin
      ? `Moves need model administration, which this instance has switched off (${capabilities.modelAdmin.setting}).`
      : "";
  return { canMap, canMove: canMap, reason };
}
