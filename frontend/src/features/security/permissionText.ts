/**
 * What the data-context band says a person may do here (0.12 Z5, D322, D329), in place of "Edits
 * apply immediately in this workspace.": a reader is told they can read, a person who proposes
 * that their changes go into their change set, a narrowed writer which records they change. The
 * model's names are data; nothing here names an application or record type.
 */

import type { EngineModel } from "@/types";
import type { RecordWrites } from "./permissions";

export interface BandSituation {
  /** "live" or "changeSet"; a publication's line is its own. */
  context: "live" | "changeSet";
  workspaceLabel: string;
  /** Which records the person may write here; undefined while the permissions load. */
  writes?: RecordWrites;
  /** Live data, no Edit live, but Work in change sets: their changes go into their change set. */
  proposing: boolean;
  /** In a change set: whether the person may publish it. */
  publishes: boolean;
}

export function listedNames(names: string[]): string {
  if (names.length <= 1) return names.join("");
  return `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;
}

/** The records a narrowing names, by the model's names: "Specimen and Determination records". */
export function narrowedRecords(model: EngineModel, narrowing: { applications: string[]; recordTypes: string[] }) {
  const types = narrowing.recordTypes
    .map((key) => model.objectTypes.find((type) => type.key === key)?.name)
    .filter((name): name is string => Boolean(name));
  const applications = narrowing.applications
    .map((key) => model.applications.find((application) => application.key === key)?.name)
    .filter((name): name is string => Boolean(name));
  const parts = [
    ...(types.length ? [`${listedNames(types)} records`] : []),
    ...(applications.length ? [`the records of ${listedNames(applications)}`] : []),
  ];
  return parts.length ? listedNames(parts) : "no records of this model";
}

/** The band's line, or undefined to keep the context's own. */
export function permissionLine(model: EngineModel, situation: BandSituation): string | undefined {
  const { writes, workspaceLabel } = situation;
  if (!writes) return undefined;
  if (situation.context === "live" && situation.proposing)
    return `Changes you make go into your change set, not live. Someone who holds Publish in ${workspaceLabel} publishes it.`;
  if (!writes.any)
    return situation.context === "live"
      ? "You can read this workspace. To change records, ask a security administrator for a role that allows it."
      : "You can read this change set. To change records in it, ask a security administrator for a role that allows it.";
  if (writes.narrowing)
    return `Your role changes ${narrowedRecords(model, writes.narrowing)} here; others you can read.`;
  if (situation.context === "changeSet" && !situation.publishes)
    return `Edits stay in this change set until someone who holds Publish in ${workspaceLabel} publishes it.`;
  return undefined;
}
