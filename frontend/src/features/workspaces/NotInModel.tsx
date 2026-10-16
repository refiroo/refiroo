/**
 * What the shell shows when an address asks for something the workspace's model has no place for
 * (0.11 M5, D48): a bookmark to a collection of another model, a record type a release removed, a
 * workspace that does not exist or whose release cannot be loaded (D29). It names what was asked
 * for, the model the workspace runs and the workspaces whose model has it, and offers the
 * workspace's start; nothing was changed. It replaces opening the start page silently.
 */

import { useEffect, useState } from "react";
import { api } from "@/api/client";
import type { RouteProblem } from "@/app/useRouter";
import { applicationFor, objectTypeFor } from "@/model/lookup";
import { navigationGroupFor } from "@/model/collections";
import { workspaceModel } from "@/model/workspaceModels";
import { missingElement, parseRoute, type MissingElement } from "@/routing/routes";
import type { EngineModel, RouteState, Workspace } from "@/types";
import { PageHeader } from "@/ui/PageHeader";
import { RuledList, RuledListItem } from "@/ui/RuledList";

/** The address of the element, as the router reads it: the path is all `missingElement` needs. */
function elementPath(element: MissingElement) {
  const app = `/apps/${encodeURIComponent(element.applicationKey)}`;
  if (element.kind === "application") return app;
  const segment = element.kind === "view" ? "views" : element.kind === "objectType" ? "objects" : "groups";
  return `${app}/${segment}/${encodeURIComponent(element.key)}${element.kind === "objectType" ? "/-" : ""}`;
}

/** The element's name in a model that has it. */
function elementName(model: EngineModel, element: MissingElement): string | undefined {
  const application = applicationFor(model, element.applicationKey);
  if (element.kind === "application") return application?.name;
  if (element.kind === "view") return application?.views.find((view) => view.key === element.key)?.name;
  if (element.kind === "objectType") return objectTypeFor(model, element.key)?.pluralName;
  return navigationGroupFor(application, element.key)?.label;
}

const KIND_WORD: Record<MissingElement["kind"], string> = {
  application: "application",
  view: "collection",
  objectType: "kind of record",
  group: "navigation group",
};

interface Holder {
  workspace: Workspace;
  name?: string;
  route: RouteState;
}

export function NotInModel({
  problem,
  model,
  workspace,
  startRoute,
  onNavigate,
}: {
  problem: RouteProblem;
  /** The model of the workspace shown. */
  model: EngineModel;
  /** The workspace shown, once resolved. */
  workspace?: Workspace;
  /** The shown workspace's start. */
  startRoute: RouteState;
  onNavigate: (route: RouteState) => void;
}) {
  const [holders, setHolders] = useState<Holder[]>();

  useEffect(() => {
    if (problem.kind === "workspace") return;
    let active = true;
    const element = problem as MissingElement;
    const path = elementPath(element);
    // Workspaces are few (ADR-042); each model is read once and kept for the switch that follows.
    api
      .workspaces({ status: "active", pageSize: 100 })
      .then(async (page) => {
        const found: Holder[] = [];
        for (const item of page.items) {
          if (item.key === problem.workspaceKey) continue;
          const other = await workspaceModel(item.key).catch(() => undefined);
          if (!other || missingElement(other, { pathname: path })) continue;
          const search = new URLSearchParams(window.location.search);
          search.set("workspaceKey", item.key);
          const route = parseRoute(other, item.key, { pathname: window.location.pathname, search: `?${search}` });
          found.push({ workspace: item, name: elementName(other, element), route });
        }
        if (active) setHolders(found);
      })
      .catch(() => active && setHolders([]));
    return () => {
      active = false;
    };
  }, [problem]);

  const label = workspace?.label ?? problem.workspaceKey;
  const runs = workspace ? `${workspace.model.releaseName} ${workspace.model.releaseVersion}` : "its model";
  const start = model.applications[0]?.name ?? "the start page";
  const openStart = (
    <button type="button" className="primary" onClick={() => onNavigate(startRoute)}>
      Open {start} in {label}
    </button>
  );
  const back = (
    <button type="button" className="secondary" onClick={() => window.history.back()}>
      Go back
    </button>
  );

  if (problem.kind === "workspace") {
    const missingKey = problem.workspaceKey;
    return (
      <section className="not-in-model">
        <PageHeader
          variant="plain"
          focusTitle
          title={problem.unavailable ? `Workspace ${missingKey} cannot be opened` : `No workspace ${missingKey}`}
          description={
            problem.unavailable
              ? `${problem.unavailable} The other workspaces are not affected. Nothing was changed.`
              : `The address names a workspace that does not exist, or was deleted. Nothing was changed.`
          }
          actions={
            <>
              {openStart}
              {back}
            </>
          }
        />
      </section>
    );
  }

  const element = problem as MissingElement;
  const name =
    holders?.find((holder) => holder.name)?.name ??
    (element.kind === "application" ? element.applicationKey : element.key);
  return (
    <section className="not-in-model">
      <PageHeader
        variant="plain"
        focusTitle
        title={`${name} is not in this workspace's model`}
        description={`${label} runs ${runs}, which has no ${KIND_WORD[element.kind]} ${name}. The address was made in a workspace of another model, or a release removed it. Nothing was changed.`}
        actions={
          <>
            {openStart}
            {back}
          </>
        }
      />
      <p className="eyebrow">Workspaces whose model has {name}</p>
      {holders === undefined ? (
        <p className="muted">Looking through the other workspaces…</p>
      ) : holders.length ? (
        <RuledList label={`Workspaces whose model has ${name}`}>
          {holders.map((holder) => (
            <RuledListItem
              key={holder.workspace.key}
              title={holder.workspace.label}
              meta={`${holder.workspace.model.releaseName} ${holder.workspace.model.releaseVersion}`}
              actions={
                <button type="button" className="secondary" onClick={() => onNavigate(holder.route)}>
                  Open in {holder.workspace.label}
                </button>
              }
            />
          ))}
        </RuledList>
      ) : (
        <p className="muted">No other workspace's model has it.</p>
      )}
    </section>
  );
}
