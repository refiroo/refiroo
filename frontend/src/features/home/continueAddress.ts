/**
 * "Continue where you left off" (0.12 HM1, D334): the last data address a person opened, kept in
 * this browser per person. It is navigation state like a remembered tab: it does not follow the
 * person to another browser, and clearing site data forgets it. Home shows it only while its
 * workspace is among the person's cards.
 */

import { applicationFor, typeName } from "@/model/lookup";
import { readLocalPreference, writeLocalPreference } from "@/lib/localPreference";
import { routePath } from "@/routing/routes";
import type { ApplicationRoute, EngineModel } from "@/types";

export interface ContinueAddress {
  path: string;
  workspaceKey: string;
  workspaceLabel: string;
  /** What was open: a view's name, a kind of record's name, or a change-set page's. */
  what: string;
  /** The record, for a record's page: Home reads its name. */
  record?: { objectTypeKey: string; objectId: string; changeSetId?: string; publicationId?: string };
  changeSetName?: string;
}

const key = (personId: string) => `rdm:home:continue:v1:${personId}`;

function isAddress(value: unknown): value is ContinueAddress {
  const entry = value as Partial<ContinueAddress> | null;
  return (
    typeof entry === "object" &&
    entry !== null &&
    typeof entry.path === "string" &&
    entry.path.startsWith("/apps/") &&
    typeof entry.workspaceKey === "string" &&
    typeof entry.workspaceLabel === "string" &&
    typeof entry.what === "string"
  );
}

export function readContinueAddress(personId: string): ContinueAddress | undefined {
  return readLocalPreference<ContinueAddress | undefined>(key(personId), undefined, isAddress);
}

export function forgetContinueAddress(personId: string) {
  writeLocalPreference(key(personId), undefined);
}

export function rememberContinueAddress(personId: string, address: ContinueAddress) {
  writeLocalPreference(key(personId), address);
}

/** The address to remember for `route`, opened in the workspace labelled `workspaceLabel`. */
export function continueAddressFor(
  model: EngineModel,
  route: ApplicationRoute,
  workspaceLabel: string,
  changeSetName?: string | null,
): ContinueAddress {
  const application = applicationFor(model, route.applicationKey);
  const what =
    route.kind === "list"
      ? (application?.views.find((view) => view.key === route.viewKey)?.name ?? application?.name ?? "")
      : route.kind === "detail"
        ? typeName(model, route.objectTypeKey)
        : route.kind === "changeSets"
          ? "Change sets"
          : route.kind === "changeSetChanges"
            ? "Change set review"
            : route.kind === "publications"
              ? "Publications"
              : (application?.name ?? "");
  return {
    path: routePath(route),
    workspaceKey: route.workspaceKey,
    workspaceLabel,
    what,
    ...(route.kind === "detail"
      ? {
          record: {
            objectTypeKey: route.objectTypeKey,
            objectId: route.objectId,
            ...(route.changeSetId ? { changeSetId: route.changeSetId } : {}),
            ...(route.publicationId ? { publicationId: route.publicationId } : {}),
          },
        }
      : {}),
    ...(changeSetName ? { changeSetName } : {}),
  };
}

/** The link's two lines: what to continue, and where it is. */
export function continueLines(address: ContinueAddress, recordName?: string): { title: string; where: string } {
  const inChangeSet = address.changeSetName ? `, in the change set “${address.changeSetName}”` : "";
  if (address.record)
    return {
      title: recordName ?? address.what,
      where: `${address.what} in ${address.workspaceLabel}${inChangeSet}`,
    };
  return { title: address.what, where: `${address.workspaceLabel}${inChangeSet}` };
}
