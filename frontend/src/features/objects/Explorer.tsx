import { useCallback, useMemo, useRef, useState, type KeyboardEvent, type MouseEvent } from "react";
import { useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { TreeMoveDialog } from "@/features/objects/TreeMoveDialog";
import { useTreeMoves } from "@/features/objects/useTreeMoves";
import { AnchoredMenu } from "@/ui/AnchoredMenu";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import { objectTypeFor } from "@/model/lookup";
import { collectionGroups, rootObjectTypeKeys } from "@/model/collections";
import { objectTypeHue } from "@/model/hues";
import type { ApplicationDefinition, EngineModel, ObjectItem } from "@/types";
import { HueTile } from "@/ui/HueTile";
import { Icon } from "@/ui/Icon";
import { RecordTree, type TreeConfiguration } from "@/features/objects/RecordTree";

export function Explorer({
  model,
  application,
  workspaceKey,
  activeObjectId,
  activeObjectTypeKey,
  activeViewKey,
  refreshToken,
  readOnly = false,
  onOpen,
  onOpenCollection,
  onChanged,
}: {
  model: EngineModel;
  application: ApplicationDefinition;
  workspaceKey: string;
  activeObjectId?: string;
  activeObjectTypeKey?: string;
  activeViewKey?: string;
  refreshToken: number;
  /** A retired workspace: records are browsed, never moved. */
  readOnly?: boolean;
  onOpen: (item: ObjectItem) => void;
  onOpenCollection?: (viewKey: string, parent?: ObjectItem) => void;
  /** Records were moved, so what shows them reads again. */
  onChanged?: () => void;
}) {
  const [searchInput, setSearchInput] = useState("");
  const search = useDebouncedValue(searchInput.trim());
  const groups = collectionGroups(application);

  // The sidebar drags and moves as the lens does (UA9, U-D22, U-D28), by the one move rule; a type
  // changes only in the lens, which previews it.
  const { changeSet, publication } = useWorkspaceData();
  const writable = !readOnly && !publication;
  const roots = useMemo(() => rootObjectTypeKeys(model, application), [model, application]);
  const treeTypes = useMemo(
    () => ({ nodeTypes: new Set(application.objectTypeKeys), rootTypes: roots }),
    [application.objectTypeKeys, roots],
  );
  const { movable, refusalOf } = useTreeMoves({
    model,
    application,
    treeTypes,
    rootObjectTypeKeys: roots,
    canMove: writable,
    typeChanges: false,
    live: !changeSet && !publication,
  });
  const [selection, setSelection] = useState<ObjectItem[]>([]);
  const [moving, setMoving] = useState<{ item: ObjectItem; others?: ObjectItem[]; target?: ObjectItem | null }>();
  const [menu, setMenu] = useState<ObjectItem>();
  const menuAnchor = useRef<HTMLElement | null>(null);
  /** The records Move to… moves from `item`: the selection it belongs to, in tree order, or just `item`. */
  const movingFrom = useCallback(
    (item: ObjectItem) =>
      selection.length > 1 && selection.some((selected) => selected.id === item.id)
        ? { item: selection[0], others: selection.slice(1) }
        : { item },
    [selection],
  );
  /** Opens the record's menu, which holds Move to… only, where the record can move. */
  const openMenu = (item: ObjectItem, anchor: HTMLElement | null) => {
    if (!writable || !movable(item.objectTypeKey)) return false;
    menuAnchor.current = anchor;
    setMenu(item);
    return true;
  };
  const treeConfig: TreeConfiguration = {
    onItemKeyDown: (event: KeyboardEvent<HTMLElement>, item: ObjectItem) => {
      if (event.key !== "ContextMenu" && !(event.key === "F10" && event.shiftKey)) return;
      if (openMenu(item, event.currentTarget.querySelector<HTMLElement>(".tree-row"))) event.preventDefault();
    },
    onItemContextMenu: (event: MouseEvent<HTMLElement>, item: ObjectItem) => {
      if (openMenu(item, event.currentTarget)) event.preventDefault();
    },
    drag: writable
      ? {
          canDrag: (item: ObjectItem) => movable(item.objectTypeKey),
          refusal: refusalOf,
          onDrop: ([item, ...others]: ObjectItem[], parent: ObjectItem | null) =>
            setMoving({ item, others, target: parent }),
        }
      : undefined,
  };

  return (
    <section className="explorer" aria-label={`${application.name} explorer`}>
      {groups.length > 0 && (
        <nav className="collection-tree" aria-label={`${application.name} collections`}>
          <p className="nav-label">Collections</p>
          {groups.map((group) => {
            const type = objectTypeFor(model, group.objectTypeKey);
            const active = group.views.some((view) => view.key === activeViewKey);
            return (
              <button
                key={group.objectTypeKey}
                className={active ? "active" : ""}
                aria-current={active ? "page" : undefined}
                onClick={() => onOpenCollection?.(group.defaultView.key)}
              >
                <HueTile hue={objectTypeHue(model, group.objectTypeKey)} icon={type?.icon} />
                <span className="collection-name">{type?.pluralName ?? group.objectTypeKey}</span>
                {group.views.some((view) => view.type === "mappingGrid") && (
                  <span className="collection-hint" title="Includes a mapping view">
                    <Icon name="mapping" size={13} label="Includes a mapping view" />
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      )}
      <div className="browse-section">
        <p className="nav-label" id={`${application.key}-browse-label`}>
          Browse records
        </p>
        <label className="search-box compact">
          <Icon name="search" />
          <input
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            aria-label="Search this explorer"
            placeholder="Find a record"
          />
        </label>
        <RecordTree
          model={model}
          application={application}
          workspaceKey={workspaceKey}
          search={search}
          activeObjectId={activeObjectId}
          activeObjectTypeKey={activeObjectTypeKey}
          refreshToken={refreshToken}
          labelledBy={`${application.key}-browse-label`}
          config={treeConfig}
          onOpen={onOpen}
          onOpenCollection={onOpenCollection}
          onSelectionChange={setSelection}
        />
      </div>
      {menu && (
        <AnchoredMenu
          anchorRef={menuAnchor}
          label={`Actions for ${menu.name}`}
          items={[
            {
              id: "move",
              label: "Move to…",
              onAction: () => {
                setMenu(undefined);
                setMoving(movingFrom(menu));
              },
            },
          ]}
          onClose={() => setMenu(undefined)}
        />
      )}
      {moving && (
        <TreeMoveDialog
          model={model}
          item={moving.item}
          others={moving.others}
          refusalOf={refusalOf}
          label={moving.item.name}
          workspaceKey={workspaceKey}
          target={moving.target}
          topLevel={{ refusal: refusalOf(moving.item, null) }}
          withinObjectTypeKeys={application.objectTypeKeys}
          onClose={() => setMoving(undefined)}
          onMoved={() => {
            setMoving(undefined);
            onChanged?.();
          }}
        />
      )}
    </section>
  );
}
