/**
 * Set or grant access (0.12 SP1, SP2, U8, U9; 0.17 edits): one dialog for a workspace's Access and a person's,
 * group's or client's page. From Access it asks who (a person, group or client) and only grants. From a
 * principal's page it is that holder's access, "<name>'s access", and sets it: what the holder has is ticked,
 * unticking removes it on Save and ticking adds it, in one Save. Consumer APIs (a client's alone) are cells of a
 * grid (APIs x workspaces); roles are ticked as cards at the chosen workspaces or the whole instance. A grant
 * the dialog cannot express (a role narrowed to applications or record types, one held through a group) has no
 * control here; it stays removable by its chip on the page. A failed change stays as it was ticked with its
 * reason while the others are made. A consumer API is granted in a workspace, never narrowed (D306, D354). The
 * choices come from the workspace's grant options, which a Security administrator reads without Browse (D355).
 * A workspace grant of one role with narrowable groups may narrow what they may change to applications and
 * record types of that workspace's model, and reading is never narrowed (D243). A role held only at the
 * instance offers only the whole instance, said in words (D302). A sentence says what is added and removed.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { errorMessage } from "@/api/errors";
import { security } from "@/api/securityClient";
import type { ActionGroup, Grant, GrantCreate, GrantOptions, Role, Workspace } from "@/types";
import { Choice } from "@/ui/Choice";
import { Modal } from "@/ui/Modal";
import { MultiSelect } from "@/ui/MultiSelect";
import { Notice } from "@/ui/Notice";
import { SelectionCheckbox } from "@/ui/SelectionCheckbox";
import { Skeleton } from "@/ui/Skeleton";
import { ConsumerApiGrid } from "./ConsumerApiGrid";
import {
  cellKey,
  changeSentence,
  consumerPlanSentence,
  consumerRequests,
  grantCells,
  list as joinList,
  recreation,
  removals,
  roleKey,
  roleRequests,
  rolePlanSentence,
  type GrantChange,
} from "./grantPlan";
import { PrincipalPicker, type PickedPrincipal } from "./PrincipalPicker";
import { grantSentence, instanceOnly } from "./securityText";
import { allWorkspaces } from "@/api/allWorkspaces";
import { everyPage } from "@/lib/everyPage";

type Place = { key: string; label: string };

/** Every grant the principal holds directly, page after page. */
const grantsHeldBy = (principalId: string): Promise<Grant[]> =>
  everyPage((cursor) => security.grantsOf(principalId, cursor));

export function GrantDialog({
  who,
  workspace,
  onClose,
  onChanged,
}: {
  /** The person, group or client the page is about; without it the dialog asks who. */
  who?: PickedPrincipal;
  /** The workspace the page is about; without it the dialog asks where. */
  workspace?: Place;
  onClose: () => void;
  /** After the dialog closes having changed access: all that was added and removed, even if others failed. */
  onChanged: (change: GrantChange) => void;
}) {
  /** From a principal's page the dialog sets the holder's access; from Access it only grants. */
  const editing = !!who;
  const [roles, setRoles] = useState<Role[]>();
  const [catalogue, setCatalogue] = useState<ActionGroup[]>();
  const [workspaces, setWorkspaces] = useState<Workspace[]>();
  const [loadError, setLoadError] = useState("");
  const [principal, setPrincipal] = useState<PickedPrincipal | undefined>(who);
  const [wanted, setWanted] = useState<"roles" | "apis">(who?.kind === "client" ? "apis" : "roles");
  const [held, setHeld] = useState<Grant[]>([]);
  const [heldLoaded, setHeldLoaded] = useState(!who);
  const [options, setOptions] = useState<Record<string, GrantOptions | "error">>({});
  // Only a client holds a consumer API (CONSUMER_API_CLIENTS_ONLY); for anyone else, or no one yet,
  // the choice is hidden and only roles are granted.
  const clientHolder = principal?.kind === "client";
  const what: "roles" | "apis" = clientHolder ? wanted : "roles";
  const [ticked, setTicked] = useState<ReadonlySet<string>>(new Set());
  // Role cells (`roleKey`) ticked: when editing, seeded with what the holder has.
  const [wantedRoles, setWantedRoles] = useState<ReadonlySet<string>>(new Set());
  const [whereKind, setWhereKind] = useState<"workspace" | "instance">("workspace");
  const [placeKeys, setPlaceKeys] = useState<string[]>(workspace ? [workspace.key] : []);
  const [narrow, setNarrow] = useState<"everything" | "some">("everything");
  const [narrowedTo, setNarrowedTo] = useState<string[]>([]);
  const [pending, setPending] = useState(false);
  const [failures, setFailures] = useState<string[]>([]);
  const [made, setMade] = useState<GrantChange>({ added: [], removed: [] });
  const requested = useRef(new Set<string>());

  useEffect(() => {
    let active = true;
    Promise.all([security.roles(), security.actionGroups(), workspace ? undefined : allWorkspaces()])
      .then(([rolePage, groups, everyWorkspace]) => {
        if (!active) return;
        setRoles(rolePage.items);
        setCatalogue(groups);
        if (everyWorkspace) {
          setWorkspaces(everyWorkspace);
          setPlaceKeys((current) => (current.length ? current : everyWorkspace[0] ? [everyWorkspace[0].key] : []));
        }
      })
      .catch((cause) => active && setLoadError(errorMessage(cause)));
    return () => {
      active = false;
    };
  }, [workspace]);

  // What the principal already holds: ticked when editing, said in words when granting.
  const principalId = principal?.id;
  useEffect(() => {
    if (!principalId) return;
    let active = true;
    grantsHeldBy(principalId).then(
      (grants) => {
        if (!active) return;
        setHeld(grants);
        if (editing) {
          const cells = grantCells(grants);
          setTicked(new Set(cells.apis.keys()));
          setWantedRoles(new Set(cells.roles.keys()));
        }
        setHeldLoaded(true);
      },
      () => {
        if (!active) return;
        setHeld([]);
        setHeldLoaded(true);
      },
    );
    return () => {
      active = false;
    };
  }, [principalId, editing]);

  /** The grid's rows and the narrowing's choices: what each workspace's model offers (D355). */
  const loadOptions = useCallback((keys: readonly string[]) => {
    for (const key of keys) {
      if (requested.current.has(key)) continue;
      requested.current.add(key);
      security.grantOptions(key).then(
        (loaded) => setOptions((current) => ({ ...current, [key]: loaded })),
        () => setOptions((current) => ({ ...current, [key]: "error" })),
      );
    }
  }, []);

  const places: Place[] = useMemo(
    () => (workspace ? [workspace] : (workspaces ?? []).map((item) => ({ key: item.key, label: item.label }))),
    [workspace, workspaces],
  );
  const labelOf = (key: string) => places.find((place) => place.key === key)?.label ?? key;

  const instance = !workspace && what === "roles" && whereKind === "instance";
  const chosenPlaces = placeKeys.filter((key) => places.some((place) => place.key === key));

  const cells = useMemo(() => grantCells(held), [held]);
  const heldApis = useMemo(() => new Set(cells.apis.keys()), [cells]);
  const heldRoleSet = useMemo(() => new Set(cells.roles.keys()), [cells]);

  const roleList = (roles ?? []).filter((item) => {
    // In a named workspace, a role held only at the instance is not offered (D302).
    return !workspace || !catalogue || !isInstanceOnly(item, catalogue);
  });
  function isInstanceOnly(role: Role, groups: ActionGroup[]) {
    return role.actionGroups.length > 0 && instanceOnly(role.actionGroups, groups).length === role.actionGroups.length;
  }
  const allInstanceOnly = (role: Role) => !!catalogue && isInstanceOnly(role, catalogue);
  /** A role is ticked where the dialog places it; a role held only at the instance has no workspace to tick. */
  const placeable = (role: Role) => instance || !allInstanceOnly(role);
  const roleCells = (role: string) =>
    instance ? [roleKey(role, "*")] : chosenPlaces.map((place) => roleKey(role, place));
  const shownRoleCells = new Set(
    what === "roles" ? roleList.filter(placeable).flatMap((item) => roleCells(item.key)) : [],
  );
  /** Roles ticked to be added go with a change of where: the held ones stay, the added ones are made wherever
   * the dialog now places roles. */
  function retarget(targets: readonly string[] | "instance") {
    setNarrowedTo([]);
    // With no place chosen yet the ticks wait where they are, for the next place chosen.
    if (targets !== "instance" && !targets.length) return;
    setWantedRoles((current) => {
      const next = new Set<string>();
      const carried = new Set<string>();
      for (const cell of current) {
        if (heldRoleSet.has(cell)) next.add(cell);
        else carried.add(cell.split("|")[0] ?? "");
      }
      for (const role of carried)
        for (const target of targets === "instance" ? ["*"] : targets) next.add(roleKey(role, target));
      return next;
    });
  }
  const wantedShownRoles = [...wantedRoles].filter((cell) => shownRoleCells.has(cell));
  const addedRoleCells = wantedShownRoles.filter((cell) => !heldRoleSet.has(cell));
  const removedRoleGrants = editing ? removals(cells.roles, wantedRoles, shownRoleCells) : [];

  // Narrowing is offered for a single role grant added in one workspace.
  const [addedRole, addedWhere] = addedRoleCells.length === 1 ? (addedRoleCells[0] ?? "").split("|") : [];
  const narrowKey = what === "roles" && addedWhere && addedWhere !== "*" ? addedWhere : undefined;
  const onlyOneRole = addedRole ? roles?.find((item) => item.key === addedRole) : undefined;

  useEffect(() => {
    if (what === "apis" && workspaces !== undefined) loadOptions(places.map((place) => place.key));
    if (what === "apis" && workspace) loadOptions([workspace.key]);
    if (narrowKey) loadOptions([narrowKey]);
  }, [what, workspaces, workspace, places, narrowKey, loadOptions]);

  const narrowable =
    !!narrowKey &&
    !!onlyOneRole &&
    !!catalogue?.some((group) => onlyOneRole.actionGroups.includes(group.key) && group.narrowable);
  const narrowLoaded = narrowKey ? options[narrowKey] : undefined;
  const narrowOptions = useMemo(
    () =>
      narrowLoaded && narrowLoaded !== "error"
        ? [
            ...narrowLoaded.applications.map((item) => ({
              id: `a:${item.key}`,
              label: item.name,
              description: "Application",
            })),
            ...narrowLoaded.recordTypes.map((item) => ({
              id: `t:${item.key}`,
              label: item.name,
              description: "Record type",
            })),
          ]
        : [],
    [narrowLoaded],
  );
  const narrowing = narrowable && narrow === "some" ? narrowedTo : [];
  const narrowingKeys = {
    applications: narrowing.filter((id) => id.startsWith("a:")).map((id) => id.slice(2)),
    recordTypes: narrowing.filter((id) => id.startsWith("t:")).map((id) => id.slice(2)),
  };

  // The grid's cells the workspaces' models declare: the only ones a tick can add or remove.
  const gridCells = useMemo(() => {
    const declared = new Set<string>();
    for (const place of places) {
      const loaded = options[place.key];
      if (loaded && loaded !== "error")
        for (const item of loaded.consumerApis) declared.add(cellKey(item.key, place.key));
    }
    return declared;
  }, [places, options]);
  const removedApiGrants = editing && what === "apis" ? removals(cells.apis, ticked, gridCells) : [];

  const identity = principal ? { kind: principal.kind, id: principal.id } : undefined;
  const requests: GrantCreate[] = !identity
    ? []
    : what === "apis"
      ? consumerRequests(identity, ticked, heldApis)
      : roleRequests(identity, addedRoleCells, heldRoleSet, narrowingKeys);
  const removed = what === "apis" ? removedApiGrants : removedRoleGrants;
  const changed = requests.length > 0 || removed.length > 0;

  const apiName = (key: string) => {
    for (const loaded of Object.values(options))
      if (loaded !== "error") {
        const found = loaded.consumerApis.find((item) => item.key === key);
        if (found) return found.name;
      }
    return key;
  };
  const roleName = (key: string) => roles?.find((item) => item.key === key)?.name ?? key;
  const whereOf = (scope: GrantCreate["scope"]) => ("workspaceKey" in scope ? labelOf(scope.workspaceKey) : "");

  /** What one request gives, as a failure names it: "Master data in default". */
  const describe = (request: GrantCreate) =>
    request.consumerApi
      ? `${apiName(request.consumerApi)} in ${whereOf(request.scope)}`
      : `${roleName(request.role ?? "")} ${"instance" in request.scope ? "for the whole instance" : `in ${whereOf(request.scope)}`}`;

  const sentence = (() => {
    if (!principal || !changed) return "";
    if (what === "apis") {
      const byApi = (items: GrantCreate[]) => {
        const grouped = new Map<string, string[]>();
        for (const request of items) {
          const key = request.consumerApi ?? "";
          grouped.set(key, [...(grouped.get(key) ?? []), whereOf(request.scope)]);
        }
        return [...grouped].map(([key, where]) => ({ api: apiName(key), where }));
      };
      if (!editing) return consumerPlanSentence(principal.name, byApi(requests));
      const part = (read: { api: string; where: string[] }) => `${read.api} in ${joinList(read.where)}`;
      return changeSentence({
        who: principal.name,
        verb: "read",
        added: byApi(requests).map(part),
        removed: byApi(removed.map(recreation)).map(part),
      });
    }
    const addedRoles = [...new Set(addedRoleCells.map((cell) => cell.split("|")[0] ?? ""))];
    if (addedRoles.length === 1 && catalogue && onlyOneRole && (!editing || !removed.length)) {
      return grantSentence({
        who: principal.name,
        groups: onlyOneRole.actionGroups,
        catalogue,
        where: instance ? undefined : chosenPlaces.map(labelOf).join(", "),
        narrowedTo: narrowOptions.filter((option) => narrowing.includes(option.id)).map((option) => option.label),
      });
    }
    if (editing)
      return changeSentence({
        who: principal.name,
        verb: "hold",
        added: requests.map(describe),
        removed: removed.map((grant) => describe(recreation(grant))),
      });
    const pickedRoles = [...new Set(wantedShownRoles.map((cell) => cell.split("|")[0] ?? ""))];
    const skipped = wantedShownRoles.length - requests.length;
    return rolePlanSentence({
      who: principal.name,
      roles: pickedRoles.map(roleName),
      where: instance ? "instance" : chosenPlaces.map(labelOf),
      count: requests.length,
      skipped: Math.max(0, skipped),
    });
  })();

  const alreadyHeld = !editing && !!principal && !requests.length && what === "roles" && wantedShownRoles.length > 0;

  function finish() {
    if (made.added.length || made.removed.length) onChanged(made);
    else onClose();
  }

  async function save() {
    if (!changed) return;
    setPending(true);
    setFailures([]);
    const gone: Grant[] = [];
    const done: Grant[] = [];
    const failed: string[] = [];
    // Removals first, so a grant made again in the same place is not refused as a duplicate.
    for (const grant of removed) {
      try {
        await security.deleteGrant(grant.id);
        gone.push(grant);
      } catch (cause) {
        failed.push(`Removing ${describe(recreation(grant))}: ${errorMessage(cause)}`);
      }
    }
    for (const request of requests) {
      try {
        done.push(await security.createGrant(request));
      } catch (cause) {
        failed.push(`${describe(request)}: ${errorMessage(cause)}`);
      }
    }
    const goneIds = new Set(gone.map((grant) => grant.id));
    const nextHeld = [...held.filter((grant) => !goneIds.has(grant.id)), ...done];
    const nextCells = grantCells(nextHeld);
    const all: GrantChange = {
      added: [...made.added.filter((grant) => !goneIds.has(grant.id)), ...done],
      removed: [...made.removed, ...gone.filter((grant) => !made.added.some((item) => item.id === grant.id))],
    };
    setMade(all);
    setHeld(nextHeld);
    // What was made and is not held as a cell (a narrowed role) is no tick to make again; a failure stays
    // as it was ticked or unticked, to be tried again.
    setTicked((current) => {
      const next = new Set(current);
      for (const grant of done)
        if (grant.consumerApi && grant.scope.workspaceKey) {
          const cell = cellKey(grant.consumerApi.key, grant.scope.workspaceKey);
          if (!nextCells.apis.has(cell)) next.delete(cell);
        }
      return next;
    });
    setWantedRoles((current) => {
      const next = new Set(current);
      for (const grant of done)
        if (grant.role) {
          const cell = roleKey(grant.role.key, grant.scope.instance ? "*" : (grant.scope.workspaceKey ?? ""));
          if (!nextCells.roles.has(cell)) next.delete(cell);
        }
      return next;
    });
    setPending(false);
    if (!failed.length) {
      onChanged(all);
      return;
    }
    setFailures(failed);
  }

  if (loadError)
    return (
      <Modal title="Grant access" eyebrow="People and access" onClose={onClose}>
        <div className="dialog-body">
          <Notice tone="error" title="The roles could not be read">
            {loadError}
          </Notice>
        </div>
      </Modal>
    );

  const title = who ? `${who.name}'s access` : `Grant access in ${workspace?.label ?? ""}`;

  return (
    <Modal
      title={title}
      eyebrow="People and access"
      size="wide"
      busy={pending}
      // Compared by id: a page that builds `who` inline hands a new object on every render.
      dirty={changed || (!!principal && principal.id !== who?.id)}
      onClose={finish}
    >
      {!roles || !catalogue || (!workspace && !workspaces) || !heldLoaded ? (
        <div className="dialog-body">
          <Skeleton label="Loading roles" lines={4} />
        </div>
      ) : (
        <form
          className="grant-form"
          onSubmit={(event) => {
            event.preventDefault();
            void save();
          }}
        >
          {!who && (
            <PrincipalPicker
              label="Who"
              kinds={["user", "group", "client"]}
              description="A person, a group or a client, found by name. Only a client can be given a consumer API."
              onPick={(picked) => {
                setPrincipal(picked);
                setHeld([]);
                // Consumer APIs are a client's alone: ticks made for a client go with it.
                setTicked(new Set());
                setWantedRoles(new Set());
              }}
            />
          )}
          {clientHolder && (
            <fieldset className="form-field grant-what">
              <legend>What</legend>
              <Choice
                name="grant-what"
                value={what}
                options={[
                  ["apis", "Consumer APIs"],
                  ["roles", "Roles"],
                ]}
                onChange={setWanted}
              />
              <p className="admin-hint">
                {what === "apis"
                  ? "Lets them read a consumer API in a workspace. It opens nothing on the management API."
                  : "Lets them use the management API and the interface, as each role’s action groups say."}
              </p>
            </fieldset>
          )}

          {what === "apis" ? (
            <div className="grant-pick">
              <p className="admin-hint">
                {editing ? "Tick what they may read, untick what they may not" : "Tick what they may read"}, one tick
                for one grant. A row or column heading ticks the whole line; Shift extends a range.
              </p>
              <ConsumerApiGrid
                workspaces={places}
                options={Object.fromEntries(places.map((place) => [place.key, options[place.key]]))}
                held={editing ? new Set() : heldApis}
                ticked={ticked}
                onChange={setTicked}
              />
            </div>
          ) : (
            <>
              <fieldset className="form-field grant-roles">
                <legend>Roles</legend>
                <div className="grant-table-wrap">
                  <table className="grant-table grant-roles-table">
                    <thead>
                      <tr>
                        <th scope="col" className="grant-tick">
                          <span className="visually-hidden">Grant</span>
                        </th>
                        <th scope="col">Role</th>
                        <th scope="col">May</th>
                      </tr>
                    </thead>
                    <tbody>
                      {roleList.map((item) => {
                        const offered = placeable(item);
                        const rowCells = roleCells(item.key);
                        const ticks = rowCells.filter((cell) => wantedRoles.has(cell)).length;
                        const state = ticks === 0 ? "none" : ticks === rowCells.length ? "all" : "some";
                        const toggleRole = () => {
                          if (!rowCells.length) return;
                          setNarrowedTo([]);
                          setWantedRoles((current) => {
                            const next = new Set(current);
                            for (const cell of rowCells) {
                              if (state === "all") next.delete(cell);
                              else next.add(cell);
                            }
                            return next;
                          });
                        };
                        const groupNames = catalogue
                          .filter((group) => item.actionGroups.includes(group.key))
                          .map((group) => group.name)
                          .join(", ");
                        return (
                          <tr
                            key={item.key}
                            className={`${state !== "none" ? "grant-on" : ""}${offered ? "" : " grant-off"}`}
                            onClick={(event) => {
                              if (offered && !(event.target instanceof HTMLInputElement)) toggleRole();
                            }}
                          >
                            <td className="grant-tick">
                              {offered && <SelectionCheckbox label={item.name} state={state} onSelect={toggleRole} />}
                            </td>
                            <th scope="row">{item.name}</th>
                            <td className="grant-muted">
                              {offered ? "" : "Whole instance only. "}
                              {groupNames || "Nothing"}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
                {!workspace && whereKind === "workspace" && roleList.some(allInstanceOnly) && (
                  <p className="admin-hint">
                    A role marked “Whole instance only” has no workspace to tick: choose “The whole instance” below.
                  </p>
                )}
              </fieldset>
              {!workspace && (
                <fieldset className="form-field grant-where">
                  <legend>Where</legend>
                  <Choice
                    name="grant-where"
                    value={whereKind}
                    options={[
                      ["workspace", "Workspaces", "workspace"],
                      ["instance", "The whole instance", "globe"],
                    ]}
                    onChange={(value) => {
                      setWhereKind(value);
                      retarget(value === "instance" ? "instance" : chosenPlaces);
                    }}
                  />
                  {instance ? (
                    <p className="admin-hint">Every workspace, now and later.</p>
                  ) : (
                    <MultiSelect
                      label="Workspaces"
                      options={places.map((place) => ({ id: place.key, label: place.label, description: place.key }))}
                      selected={placeKeys}
                      onChange={(keys) => {
                        setPlaceKeys(keys);
                        retarget(keys.filter((key) => places.some((place) => place.key === key)));
                      }}
                      addLabel="Add workspace"
                      emptyLabel="No workspace chosen yet"
                    />
                  )}
                </fieldset>
              )}
              {narrowable && (
                <fieldset className="form-field grant-narrowing">
                  <legend>Narrow what they may change</legend>
                  <Choice
                    name="grant-narrowing"
                    value={narrow}
                    options={[
                      ["everything", `Everything in ${chosenPlaces.map(labelOf).join(", ")}`],
                      ["some", "Only these applications and record types"],
                    ]}
                    onChange={setNarrow}
                  />
                  {narrow === "some" &&
                    (narrowLoaded ? (
                      <MultiSelect
                        label="Applications and record types"
                        options={narrowOptions}
                        selected={narrowedTo}
                        onChange={setNarrowedTo}
                        addLabel="Add"
                        emptyLabel="Nothing chosen yet"
                      />
                    ) : (
                      <Skeleton label="Loading the workspace's model" lines={1} />
                    ))}
                  <p className="admin-hint">Reading is never narrowed: they read the whole workspace.</p>
                </fieldset>
              )}
              {!narrowable && !instance && addedRoleCells.length > 1 && (
                <p className="admin-hint">Narrowing is offered when one role is granted in one workspace.</p>
              )}
            </>
          )}

          {sentence && (
            <p className="grant-sentence" role="status">
              {sentence}
            </p>
          )}
          {alreadyHeld && (
            <p className="grant-sentence" role="status">
              {principal?.name} already holds everything chosen.
            </p>
          )}
          {failures.length > 0 && (
            <Notice tone="error" title={`${failures.length} could not be ${editing ? "saved" : "granted"}`}>
              <ul className="grant-failures">
                {failures.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
              {(made.added.length > 0 || made.removed.length > 0) && (
                <p>The others were {editing ? "saved" : "made"}.</p>
              )}
            </Notice>
          )}
          <div className="dialog-actions">
            <button type="button" className="secondary" disabled={pending} onClick={finish}>
              {made.added.length || made.removed.length ? "Close" : "Cancel"}
            </button>
            <button className="primary" disabled={pending || !changed}>
              {editing
                ? pending
                  ? "Saving…"
                  : "Save"
                : pending
                  ? "Adding…"
                  : requests.length > 1
                    ? `Add ${requests.length} grants`
                    : failures.length
                      ? "Try again"
                      : "Add grant"}
            </button>
          </div>
        </form>
      )}
    </Modal>
  );
}
