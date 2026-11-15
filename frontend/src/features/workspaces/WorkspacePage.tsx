/**
 * A workspace's own page (0.17 SH1, plain path PL3; redrawn in 0.17 UX1): where a card on Home leads. At the top
 * the person's shelf: the lists they brought here from any application, as tiles in their own order (drag, or
 * the tile's menu), each with how many records it holds. Then a search over every record of the workspace, the
 * applications with their lists one click away, the person's change sets that wait here, and what changed, by
 * day with repeats folded. The workspace's own actions are Edit model and a ⋯ menu to Settings' Workspaces
 * pages, each left out for a person who may not use it. It fills the window's width, as the list pages do.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { ShellFrame } from "@/app/ShellFrame";
import { TopBar } from "@/app/TopBar";
import { count, counted, plural } from "@/lib/count";
import { useHoldsGroup } from "@/state/useMe";
import { ChangeTitle } from "@/ui/ChangeTitle";
import { changeWhere } from "@/ui/changeText";
import { holds, useWorkspacePermissions } from "@/state/permissions";
import { useCapabilities } from "@/state/useSystem";
import { NewFromWorkbookAction } from "@/features/workspaces/NewFromWorkbookAction";
import { WorkspaceLoad } from "@/features/workspaces/WorkspaceLoad";
import { WorkspaceSearch } from "@/features/workspaces/WorkspaceSearch";
import { pinKey, useWorkspacePins, type WorkspacePin } from "@/lib/workspacePins";
import { useEditModel } from "@/features/workspaces/useEditModel";
import { byDay, formatServerAgo, timeOfDay } from "@/lib/dates";
import { collectionGroups, entryLabel, viewSourceObjectTypeKey } from "@/model/collections";
import { applicationHue, objectTypeTile } from "@/model/hues";
import { changeReviewFor, routePath, viewRoute } from "@/routing/routes";
import type {
  ApplicationDefinition,
  ChangeEntry,
  EngineModel,
  ObjectItem,
  OwnChangeSet,
  RouteState,
  ViewDefinition,
  Workspace,
} from "@/types";
import { ActionMenu, type ActionMenuItem } from "@/ui/ActionMenu";
import { Card } from "@/ui/Card";
import { HueTile } from "@/ui/HueTile";
import { ControlPopover } from "@/ui/ControlPopover";
import { Icon } from "@/ui/Icon";
import { actorText } from "@/ui/ActorName";
import { RouteLink } from "@/ui/RouteLink";
import { Skeleton } from "@/ui/Skeleton";
import { WorkspaceTile } from "@/ui/WorkspaceTile";
import { everyPage } from "@/lib/everyPage";

type Navigate = (route: RouteState) => void;

/** How many waiting change sets the page lists before it says how many more there are. */
/** A list dragged from an application onto the shelf carries its pin under this type. */
const PIN_DRAG_TYPE = "application/x-rdm-shelf-pin";
const WAITING_SHOWN = 4;
/** How many of the latest changes the page reads; repeats of one change fold into one line. */
const CHANGES_READ = 20;

/** The person's open change sets in one workspace, newest change first, every page (D333). */
function useWaitingChangeSets(workspaceKey: string) {
  const [state, setState] = useState<{ key: string; items: OwnChangeSet[]; error: string }>();
  useEffect(() => {
    let active = true;
    everyPage((cursor) => api.myChangeSets(cursor))
      .then((all) => all.filter((item) => item.workspaceKey === workspaceKey))
      .then(
        (items) => active && setState({ key: workspaceKey, items, error: "" }),
        (cause) => active && setState({ key: workspaceKey, items: [], error: errorMessage(cause) }),
      );
    return () => {
      active = false;
    };
  }, [workspaceKey]);
  return state?.key === workspaceKey ? state : undefined;
}

/** A list a person can bring to their shelf: a view of an application, named as the sidebar names it. */
type ShelfList = {
  pin: WorkspacePin;
  application: ApplicationDefinition;
  view: ViewDefinition;
  name: string;
  objectTypeKey: string;
  /** The collection's own list; false for another view of it (a matrix, a tree). */
  isList: boolean;
};

/**
 * Everything of the workspace's applications a person can bring to their shelf, in the applications' order: each
 * collection's own list, then its other views (a tree, a relation matrix, a mapping, a relationship table) under
 * their own names, so a matrix of relationships can stand on the shelf beside a plain list.
 */
function shelfLists(model: EngineModel): ShelfList[] {
  return model.applications.flatMap((application) =>
    collectionGroups(application).flatMap((collection) => {
      const objectTypeKey = viewSourceObjectTypeKey(collection.defaultView);
      const list = entryLabel(model, { kind: "collection", collection });
      return [
        {
          pin: { applicationKey: application.key, viewKey: collection.defaultView.key },
          application,
          view: collection.defaultView,
          name: list,
          objectTypeKey,
          isList: true,
        },
        ...collection.views
          .filter((view) => view.key !== collection.defaultView.key)
          .map((view) => ({
            pin: { applicationKey: application.key, viewKey: view.key },
            application,
            view,
            name: view.name === list ? `${list} (${view.type})` : view.name,
            objectTypeKey,
            isList: false,
          })),
      ];
    }),
  );
}

/** How many records each given type holds live in the workspace; a count that fails is left out. */
function useRecordCounts(workspaceKey: string, objectTypeKeys: readonly string[]) {
  const wanted = [...new Set(objectTypeKeys)].sort().join("\n");
  const [counts, setCounts] = useState<{ key: string; values: Record<string, number> }>();
  useEffect(() => {
    let active = true;
    const keys = wanted ? wanted.split("\n") : [];
    Promise.all(
      keys.map((key) =>
        api.countRecords(workspaceKey, key).then(
          (total) => [key, total] as const,
          () => [key, undefined] as const,
        ),
      ),
    ).then((pairs) => {
      if (!active) return;
      const values: Record<string, number> = {};
      for (const [key, total] of pairs) if (total !== undefined) values[key] = total;
      setCounts({ key: `${workspaceKey}\n${wanted}`, values });
    });
    return () => {
      active = false;
    };
  }, [workspaceKey, wanted]);
  return counts?.key === `${workspaceKey}\n${wanted}` ? counts.values : {};
}

export function WorkspacePage({
  model,
  workspaceKey,
  onNavigate,
  onHome,
}: {
  /** The model of the workspace (its applications). */
  model: EngineModel;
  workspaceKey: string;
  onNavigate: Navigate;
  onHome: () => void;
}) {
  const [workspace, setWorkspace] = useState<Workspace>();
  const [loadError, setLoadError] = useState("");
  useEffect(() => {
    let active = true;
    api.workspace(workspaceKey).then(
      (loaded) => active && setWorkspace(loaded),
      (cause) => active && setLoadError(errorMessage(cause)),
    );
    return () => {
      active = false;
    };
  }, [workspaceKey]);
  const current = workspace?.key === workspaceKey ? workspace : undefined;
  const label = current?.label ?? workspaceKey;
  const permissions = useWorkspacePermissions(workspaceKey);
  const editModel = useEditModel(workspaceKey, current?.status, onNavigate);
  const { capabilities } = useCapabilities();
  const workspaceAdmin = useHoldsGroup("workspace-admin");
  const securityAdmin = useHoldsGroup("security-admin");
  const copiesAndMoves = useHoldsGroup("copy-move");
  const manages = Boolean(capabilities?.workspaceAdmin.manageWorkspaces) && Boolean(workspaceAdmin);
  const inSettings = (workspaceTab?: "access" | "approval"): RouteState => ({
    kind: "settings",
    page: "workspaces",
    workspaceKey,
    ...(workspaceTab ? { workspaceTab } : {}),
  });
  // Today's Settings › Workspaces pages, each offered to whoever may use it there.
  const actions: ActionMenuItem[] = [
    ...(manages ? [{ id: "rename", label: "Rename", onAction: () => onNavigate(inSettings()) }] : []),
    ...(securityAdmin ? [{ id: "access", label: "Access", onAction: () => onNavigate(inSettings("access")) }] : []),
    ...(holds(permissions, "workspace-admin")
      ? [{ id: "approval", label: "Approval", onAction: () => onNavigate(inSettings("approval")) }]
      : []),
    ...(copiesAndMoves
      ? [{ id: "move", label: "Copy or move", onAction: () => onNavigate({ kind: "settings", page: "moves" }) }]
      : []),
    ...(manages && current?.status === "active"
      ? [{ id: "retire", label: "Retire", tone: "danger" as const, onAction: () => onNavigate(inSettings()) }]
      : []),
  ];
  const openRecord = (item: ObjectItem) =>
    onNavigate({
      kind: "detail",
      applicationKey: item.applicationKey,
      objectTypeKey: item.objectTypeKey,
      objectId: item.id,
      workspaceKey,
    });
  const waiting = useWaitingChangeSets(workspaceKey);
  const lists = useMemo(() => shelfLists(model), [model]);
  const shelf = useWorkspacePins(workspaceKey);
  const pinned = useMemo(
    () =>
      shelf.pins.flatMap((pin) => {
        const list = lists.find((item) => pinKey(item.pin) === pinKey(pin));
        return list ? [list] : [];
      }),
    [shelf.pins, lists],
  );
  const counts = useRecordCounts(
    workspaceKey,
    pinned.map((list) => list.objectTypeKey),
  );
  return (
    <ShellFrame
      topBar={
        <TopBar
          model={model}
          workspaceKey={workspaceKey}
          tabs={false}
          onHome={onHome}
          onSelectApplication={() => undefined}
          onNavigate={onNavigate}
        />
      }
      main={{ className: "workspace-overview" }}
    >
      <div className="ws-page">
        <header className="ws-head">
          <WorkspaceTile workspaceKey={workspaceKey} label={label} />
          <div className="ws-head-text">
            <p className="ws-eyebrow">Workspace</p>
            <h1 tabIndex={-1}>{label}</h1>
            {current && (
              <p>
                {current.model.releaseName} {current.model.releaseVersion}
                {current.status === "retired" ? " · Retired, read only" : ""}
              </p>
            )}
          </div>
          <ul className="ws-facts" aria-label="In this workspace">
            <li>
              <strong>{model.applications.length}</strong>
              {plural(model.applications.length, "application")}
            </li>
            <li>
              <strong>{lists.filter((list) => list.isList).length}</strong>
              {plural(lists.filter((list) => list.isList).length, "list")}
            </li>
            {waiting && !waiting.error && (
              <li>
                <strong>{waiting.items.length}</strong>
                {plural(waiting.items.length, "change set of yours", "change sets of yours")}
              </li>
            )}
          </ul>
          <div className="ws-head-actions">
            <NewFromWorkbookAction
              onNavigate={onNavigate}
              onOtherWays={() => onNavigate({ kind: "settings", page: "workspaces" })}
            />
            {editModel && (
              <button type="button" className="secondary" onClick={editModel}>
                Edit model
              </button>
            )}
            {actions.length > 0 && <ActionMenu label="Workspace actions" items={actions} />}
          </div>
        </header>
        {loadError && (
          <p className="muted-text" role="alert">
            {loadError}
          </p>
        )}
        <WorkspaceLoad workspaceKey={workspaceKey} onNavigate={onNavigate} />
        <Card as="section" className="ws-search" aria-labelledby="workspace-find-title">
          <h2 id="workspace-find-title" className="ws-title">
            Find a record <small>any list, any application</small>
          </h2>
          <WorkspaceSearch
            variant="page"
            workspaceKey={workspaceKey}
            model={model}
            label="Find a record in this workspace"
            placeholder="Type part of a name"
            onOpen={openRecord}
          />
        </Card>
        <div className="ws-columns">
          <div className="ws-main">
            <Shelf
              model={model}
              workspaceKey={workspaceKey}
              lists={lists}
              pinned={pinned}
              counts={counts}
              isPinned={shelf.isPinned}
              onToggle={shelf.toggle}
              onMove={shelf.move}
              onNavigate={onNavigate}
            />
            <section aria-labelledby="workspace-applications">
              <h2 id="workspace-applications" className="ws-title">
                Applications
              </h2>
              {model.applications.length ? (
                <ul className="ws-apps">
                  {model.applications.map((application) => {
                    const route = viewRoute(application, application.defaultView, workspaceKey);
                    return (
                      <li key={application.key}>
                        <Card className="ws-app">
                          <RouteLink
                            className="ws-app-head"
                            href={routePath(route)}
                            onNavigate={() => onNavigate(route)}
                          >
                            <HueTile hue={applicationHue(model, application.key)} icon={application.icon} size={22} />
                            {application.name}
                          </RouteLink>
                          {application.description && <p>{application.description}</p>}
                          <ul className="ws-lists" aria-label={`Lists of ${application.name}`}>
                            {lists
                              .filter((list) => list.isList && list.application.key === application.key)
                              .map((list) => {
                                const target = viewRoute(application, list.view.key, workspaceKey);
                                return (
                                  <li key={list.view.key}>
                                    <RouteLink
                                      className="ws-list"
                                      href={routePath(target)}
                                      data-pinned={shelf.isPinned(list.pin) || undefined}
                                      title={
                                        shelf.isPinned(list.pin)
                                          ? "On your shelf"
                                          : "Drag onto your shelf to keep it there"
                                      }
                                      draggable
                                      onDragStart={(event) => {
                                        event.dataTransfer.effectAllowed = "copy";
                                        event.dataTransfer.setData(PIN_DRAG_TYPE, JSON.stringify(list.pin));
                                        event.dataTransfer.setData("text/plain", list.name);
                                      }}
                                      onNavigate={() => onNavigate(target)}
                                    >
                                      {list.name}
                                    </RouteLink>
                                  </li>
                                );
                              })}
                          </ul>
                        </Card>
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <p className="muted-text">This version cannot open the workspace’s model.</p>
              )}
            </section>
          </div>
          <div className="ws-side">
            <WaitingList workspaceKey={workspaceKey} model={model} state={waiting} onNavigate={onNavigate} />
            <LatestChanges workspaceKey={workspaceKey} model={model} onNavigate={onNavigate} />
          </div>
        </div>
      </div>
    </ShellFrame>
  );
}

/** The person's shelf: the lists they pinned, as tiles they can drag into order, and the way to bring more. */
function Shelf({
  model,
  workspaceKey,
  lists,
  pinned,
  counts,
  isPinned,
  onToggle,
  onMove,
  onNavigate,
}: {
  model: EngineModel;
  workspaceKey: string;
  lists: ShelfList[];
  pinned: ShelfList[];
  counts: Record<string, number>;
  isPinned: (pin: WorkspacePin) => boolean;
  onToggle: (pin: WorkspacePin) => void;
  onMove: (from: number, to: number) => void;
  onNavigate: Navigate;
}) {
  const [dragging, setDragging] = useState<number>();
  const [over, setOver] = useState<number>();
  const menus = useRef(new Map<string, HTMLElement | null>());
  const picker = (label: string, className: string) => (
    <ControlPopover
      label="Choose the lists on your shelf"
      trigger={
        <>
          <Icon name="plus" size={14} /> {label}
        </>
      }
      triggerClassName={className}
      placement="bottom start"
    >
      <div className="ws-pick" role="group" aria-label="Lists of this workspace">
        {model.applications.map((application) => (
          <div key={application.key}>
            <p className="ws-pick-group">{application.name}</p>
            {lists
              .filter((list) => list.application.key === application.key)
              .map((list) => (
                <label key={list.view.key}>
                  <input type="checkbox" checked={isPinned(list.pin)} onChange={() => onToggle(list.pin)} />
                  <HueTile {...objectTypeTile(model, list.objectTypeKey)} size={20} />
                  {list.name}
                </label>
              ))}
          </div>
        ))}
      </div>
    </ControlPopover>
  );
  // A list dragged from an application below lands on the shelf: the whole section takes the drop.
  const [taking, setTaking] = useState(false);
  return (
    <section
      aria-labelledby="workspace-shelf"
      className="ws-shelf-section"
      data-taking={taking || undefined}
      onDragOver={(event) => {
        if (!event.dataTransfer.types.includes(PIN_DRAG_TYPE)) return;
        event.preventDefault();
        event.dataTransfer.dropEffect = "copy";
        setTaking(true);
      }}
      onDragLeave={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setTaking(false);
      }}
      onDrop={(event) => {
        const carried = event.dataTransfer.getData(PIN_DRAG_TYPE);
        setTaking(false);
        if (!carried) return;
        event.preventDefault();
        try {
          const pin = JSON.parse(carried) as WorkspacePin;
          if (typeof pin.applicationKey === "string" && typeof pin.viewKey === "string" && !isPinned(pin))
            onToggle(pin);
        } catch {
          // Not a pin of ours: nothing lands.
        }
      }}
    >
      <h2 id="workspace-shelf" className="ws-title">
        Your shelf <small>the lists you use most, in your order</small>
        {pinned.length > 0 && <span className="ws-title-action">{picker("Add a list", "secondary")}</span>}
      </h2>
      {pinned.length === 0 ? (
        <div className="ws-shelf-empty">
          <img src="/brand/refiroo-mascot.png" alt="" width={56} height={56} />
          <strong>Nothing on your shelf yet</strong>
          <span>Bring the lists you open most here, from any application. They stay in this browser.</span>
          {picker("Add a list", "primary")}
        </div>
      ) : (
        <ul className="ws-shelf">
          {pinned.map((list, index) => {
            const route = viewRoute(list.application, list.view.key, workspaceKey);
            const total = counts[list.objectTypeKey];
            const key = pinKey(list.pin);
            return (
              <li
                key={key}
                className="ws-pin"
                draggable
                data-dragging={dragging === index || undefined}
                data-over={(over === index && dragging !== undefined && dragging !== index) || undefined}
                onDragStart={(event) => {
                  event.dataTransfer.effectAllowed = "move";
                  event.dataTransfer.setData("text/plain", list.name);
                  setDragging(index);
                }}
                onDragOver={(event) => {
                  if (dragging === undefined) return;
                  event.preventDefault();
                  event.dataTransfer.dropEffect = "move";
                  setOver(index);
                }}
                onDragLeave={() => setOver((current) => (current === index ? undefined : current))}
                onDrop={(event) => {
                  event.preventDefault();
                  if (dragging !== undefined) onMove(dragging, index);
                  setDragging(undefined);
                  setOver(undefined);
                }}
                onDragEnd={() => {
                  setDragging(undefined);
                  setOver(undefined);
                }}
                // A right click opens the tile's own menu, where the keyboard and touch also find the moves.
                onContextMenu={(event) => {
                  const button = menus.current.get(key)?.querySelector("button");
                  if (!button) return;
                  event.preventDefault();
                  button.click();
                }}
              >
                <HueTile {...objectTypeTile(model, list.objectTypeKey)} size={40} />
                <RouteLink className="ws-pin-link" href={routePath(route)} onNavigate={() => onNavigate(route)}>
                  <span className="ws-pin-name">{list.name}</span>
                  <span className="ws-pin-where">
                    {total === undefined ? list.application.name : `${count(total)} · ${list.application.name}`}
                  </span>
                </RouteLink>
                <span
                  className="ws-pin-menu"
                  ref={(node) => {
                    menus.current.set(key, node);
                  }}
                >
                  <ActionMenu
                    label={`${list.name} on your shelf`}
                    items={[
                      ...(index > 0
                        ? [{ id: "earlier", label: "Move earlier", onAction: () => onMove(index, index - 1) }]
                        : []),
                      ...(index < pinned.length - 1
                        ? [{ id: "later", label: "Move later", onAction: () => onMove(index, index + 1) }]
                        : []),
                      { id: "remove", label: "Take off your shelf", onAction: () => onToggle(list.pin) },
                    ]}
                  />
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

function WaitingList({
  workspaceKey,
  model,
  state,
  onNavigate,
}: {
  workspaceKey: string;
  model: EngineModel;
  state: { items: OwnChangeSet[]; error: string } | undefined;
  onNavigate: Navigate;
}) {
  const application = model.applications[0]?.key;
  return (
    <Card as="section" className="ws-card" aria-labelledby="workspace-waiting">
      <h2 id="workspace-waiting" className="ws-title">
        Needs you
        {state && state.items.length > 0 && <small>{counted(state.items.length, "change set")}</small>}
      </h2>
      {!state ? (
        <Skeleton label="Loading your change sets" lines={2} />
      ) : state.error ? (
        <p className="muted-text" role="alert">
          {state.error}
        </p>
      ) : state.items.length === 0 ? (
        <p className="muted-text">None of your change sets is open here.</p>
      ) : (
        <>
          <ul className="ws-rows">
            {state.items.slice(0, WAITING_SHOWN).map((item) => {
              const name = item.name || "Untitled change set";
              const waits = item.submission?.state === "submitted";
              return (
                <li key={item.id} className="ws-row">
                  <span className="ws-row-text">
                    <strong>{name}</strong>
                    <small>
                      {counted(item.changeCount, "change")} · {waits ? "waits for approval" : "open"} ·{" "}
                      {formatServerAgo(item.updatedAt)}
                    </small>
                  </span>
                  {application && (
                    <button
                      type="button"
                      className="secondary"
                      aria-label={`${waits ? "Review" : "Open"} ${name}`}
                      onClick={() => onNavigate(changeReviewFor(application, workspaceKey, item.id))}
                    >
                      {waits ? "Review" : "Open"}
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
          {state.items.length > WAITING_SHOWN && (
            <p className="muted-text">{state.items.length - WAITING_SHOWN} more</p>
          )}
        </>
      )}
    </Card>
  );
}

/** Changes of one kind by one actor that follow each other, as the newest of them and how many they are. */
export function foldRepeats(entries: readonly ChangeEntry[]): { entry: ChangeEntry; times: number }[] {
  const folded: { entry: ChangeEntry; times: number }[] = [];
  for (const entry of entries) {
    const last = folded[folded.length - 1];
    if (last && last.entry.kind === entry.kind && actorText(last.entry.actor) === actorText(entry.actor))
      last.times += 1;
    else folded.push({ entry, times: 1 });
  }
  return folded;
}

function LatestChanges({
  workspaceKey,
  model,
  onNavigate,
}: {
  workspaceKey: string;
  model: EngineModel;
  onNavigate: Navigate;
}) {
  const [state, setState] = useState<{ key: string; items: ChangeEntry[]; error: string }>();
  useEffect(() => {
    let active = true;
    Promise.resolve()
      .then(() => api.changes({ workspaceKey, pageSize: CHANGES_READ }))
      .then(
        (page) => active && setState({ key: workspaceKey, items: page.items, error: "" }),
        (cause) => active && setState({ key: workspaceKey, items: [], error: errorMessage(cause) }),
      );
    return () => {
      active = false;
    };
  }, [workspaceKey]);
  const shown = state?.key === workspaceKey ? state : undefined;
  const application = useMemo(() => model.applications[0]?.key, [model]);
  return (
    <Card as="section" className="ws-card" aria-labelledby="workspace-latest">
      <h2 id="workspace-latest" className="ws-title">
        What changed
      </h2>
      {!shown ? (
        <Skeleton label="Loading the latest changes" lines={2} />
      ) : shown.error ? (
        <p className="muted-text" role="alert">
          {shown.error}
        </p>
      ) : shown.items.length === 0 ? (
        <p className="muted-text">Nothing has changed here yet.</p>
      ) : (
        byDay(shown.items).map((day) => (
          <div key={day.day}>
            <p className="ws-day">{day.day}</p>
            <ul className="ws-rows">
              {foldRepeats(day.entries).map(({ entry, times }) => (
                <li key={entry.id} className="ws-row">
                  <span className="ws-row-text">
                    <strong>
                      <ChangeTitle entry={entry} application={application} onNavigate={onNavigate} />
                    </strong>
                    <small>
                      {timeOfDay(entry.occurredAt)} · {actorText(entry.actor)}
                      {changeWhere(entry)
                        .slice(1)
                        .map((part) => ` · ${part}`)}
                    </small>
                  </span>
                  {times > 1 && (
                    <span className="ws-times" title={`${times} changes of this kind in a row`}>
                      {times} in a row
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))
      )}
    </Card>
  );
}
