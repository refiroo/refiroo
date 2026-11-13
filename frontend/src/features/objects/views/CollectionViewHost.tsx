/**
 * Dispatches a configured view to its renderer. Views that share a source object type are lenses
 * of one collection; the host builds the lens switch and the renderer places it under its heading.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { useDataApi } from "@/state/WorkspaceDataContext";
import { viewComponentRegistry } from "./registry";
import type { ViewComponentProps } from "./types";
import { useViewExport } from "./useViewExport";
import type { ExportViewExtra } from "./types";
import { collectionGroups, viewSourceObjectTypeKey } from "@/model/collections";
import type { ViewDefinition } from "@/types";
import { Icon, type IconName } from "@/ui/Icon";

const lensIcons: Record<ViewDefinition["type"], IconName> = {
  table: "table",
  mappingGrid: "mapping",
  relationMatrix: "matrix",
  relationTable: "link",
  tree: "tree",
};

/**
 * Under a parent, the mapping views worth offering: those with a record already mapped below it.
 * `undefined` while the answers load; `null` when every view stays (none mapped, or a request failed).
 */
function useMappedLensKeys(props: ViewComponentProps, views: ViewDefinition[]): Set<string> | null | undefined {
  const dataApi = useDataApi();
  const parentObjectId = props.query.parentObjectId;
  const viewKeys = views.map((view) => view.key).join("|");
  // The views are the application's, read by key.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const mappingViews = useMemo(() => views.filter((view) => view.type === "mappingGrid"), [viewKeys]);
  const scope =
    parentObjectId && mappingViews.length > 0 ? `${props.workspaceKey}|${props.application.key}|${parentObjectId}` : "";
  const [answer, setAnswer] = useState<{ scope: string; keys: Set<string> | null }>();
  useEffect(() => {
    if (!scope || !parentObjectId) return;
    let active = true;
    Promise.all(
      mappingViews.map(async (view) => {
        if (view.type !== "mappingGrid") return undefined;
        const { relationTypeKey, fromObjectTypeKey, toObjectTypeKey, direction } = view.config;
        const page = await dataApi.mappingCoverage({
          workspaceKey: props.workspaceKey,
          applicationKey: props.application.key,
          viewKey: view.key,
          relationTypeKey,
          fromObjectTypeKey,
          toObjectTypeKey,
          direction,
          parentObjectId,
          state: "mapped",
          pageSize: 1,
        });
        return page.items.length > 0 ? view.key : undefined;
      }),
    )
      .then((found) => {
        if (!active) return;
        const keys = new Set(found.filter((key): key is string => key !== undefined));
        setAnswer({ scope, keys: keys.size > 0 ? keys : null });
      })
      .catch(() => {
        if (active) setAnswer({ scope, keys: null });
      });
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scope, mappingViews, dataApi]);
  if (!scope) return null;
  return answer?.scope === scope ? answer.keys : undefined;
}

export function CollectionView(props: ViewComponentProps) {
  const Component = viewComponentRegistry[props.view.type];
  // The page's Export reads the view and its state through this one hook, whatever the kind (EX1).
  const exportExtraRef = useRef<ExportViewExtra | undefined>(undefined);
  useViewExport(props, exportExtraRef);
  const group = collectionGroups(props.application).find(
    (candidate) => candidate.objectTypeKey === viewSourceObjectTypeKey(props.view),
  );
  const groupViews = useMemo(() => group?.views ?? [], [group]);
  const mapped = useMappedLensKeys(props, groupViews);
  const shown = groupViews.filter(
    (view) =>
      view.type !== "mappingGrid" ||
      view.key === props.view.key ||
      (mapped === undefined ? false : mapped === null || mapped.has(view.key)),
  );
  const lenses =
    group && group.views.length > 1 ? (
      <nav className="collection-lenses" aria-label="Collection lenses">
        {shown.map((view) => (
          <button
            key={view.key}
            aria-current={view.key === props.view.key ? "page" : undefined}
            onClick={() => props.onViewChange?.(view.key)}
          >
            <Icon name={lensIcons[view.type]} size={15} />
            {view.name}
          </button>
        ))}
      </nav>
    ) : undefined;
  return <Component {...props} exportExtraRef={exportExtraRef} lenses={lenses} />;
}
