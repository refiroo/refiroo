/**
 * Grant roles or consumer APIs (0.12 SP1, SP2, U8, U9): one dialog for a workspace's Access and a
 * person's, group's or client's page. From Access it asks who (a person, group or client); from a
 * principal it asks where. Several things are granted at once: consumer APIs by ticking cells of a
 * grid (APIs × workspaces), roles by ticking cards and choosing workspaces or the whole instance.
 * One tick is one grant; what the holder already has is shown and not sent again, and a failed one
 * stays ticked with its reason while the others are made. A consumer API is granted in a workspace,
 * never narrowed (D306, D354). The choices come from the workspace's grant options, which a Security
 * administrator reads without Browse (D355). A workspace grant of one role with narrowable groups may
 * narrow what they may change to applications and record types of that workspace's model, and
 * reading is never narrowed (D243). A role held only at the instance offers only the whole instance
 * (D302). A sentence says what the grants allow.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { security } from "@/api/securityClient";
import type { ActionGroup, Grant, GrantCreate, GrantOptions, Role, Workspace } from "@/types";
import { Choice } from "@/ui/Choice";
import { Modal } from "@/ui/Modal";
import { MultiSelect } from "@/ui/MultiSelect";
import { Notice } from "@/ui/Notice";
import { Skeleton } from "@/ui/Skeleton";
import { ConsumerApiGrid } from "./ConsumerApiGrid";
import {
  cellKey,
  consumerPlanSentence,
  consumerRequests,
  heldConsumerApis,
  heldRoles,
  roleRequests,
  rolePlanSentence,
} from "./grantPlan";
import { PrincipalPicker, type PickedPrincipal } from "./PrincipalPicker";
import { grantSentence, instanceOnly } from "./securityText";

type Place = { key: string; label: string };

/** Every grant the principal holds directly, page after page. */
async function grantsHeldBy(principalId: string): Promise<Grant[]> {
  const held: Grant[] = [];
  let cursor: string | undefined;
  do {
    const page = await security.grantsOf(principalId, cursor);
    held.push(...page.items);
    cursor = page.nextCursor ?? undefined;
  } while (cursor);
  return held;
}

export function GrantDialog({
  who,
  workspace,
  onClose,
  onGranted,
}: {
  /** The person, group or client the page is about; without it the dialog asks who. */
  who?: PickedPrincipal;
  /** The workspace the page is about; without it the dialog asks where. */
  workspace?: Place;
  onClose: () => void;
  /** After the dialog closes having made grants (all that were made, even if others failed). */
  onGranted: (grants: Grant[]) => void;
}) {
  const [roles, setRoles] = useState<Role[]>();
  const [catalogue, setCatalogue] = useState<ActionGroup[]>();
  const [workspaces, setWorkspaces] = useState<Workspace[]>();
  const [loadError, setLoadError] = useState("");
  const [principal, setPrincipal] = useState<PickedPrincipal | undefined>(who);
  const [what, setWhat] = useState<"roles" | "apis">(who?.kind === "client" ? "apis" : "roles");
  const [held, setHeld] = useState<Grant[]>([]);
  const [options, setOptions] = useState<Record<string, GrantOptions | "error">>({});
  const [ticked, setTicked] = useState<ReadonlySet<string>>(new Set());
  const [pickedRoles, setPickedRoles] = useState<string[]>([]);
  const [whereKind, setWhereKind] = useState<"workspace" | "instance">("workspace");
  const [placeKeys, setPlaceKeys] = useState<string[]>(workspace ? [workspace.key] : []);
  const [narrow, setNarrow] = useState<"everything" | "some">("everything");
  const [narrowedTo, setNarrowedTo] = useState<string[]>([]);
  const [pending, setPending] = useState(false);
  const [failures, setFailures] = useState<string[]>([]);
  const [made, setMade] = useState<Grant[]>([]);
  const requested = useRef(new Set<string>());

  useEffect(() => {
    let active = true;
    Promise.all([security.roles(), security.actionGroups(), workspace ? undefined : api.workspaces({ pageSize: 500 })])
      .then(([rolePage, groups, workspacePage]) => {
        if (!active) return;
        setRoles(rolePage.items);
        setCatalogue(groups);
        if (workspacePage) {
          setWorkspaces(workspacePage.items);
          setPlaceKeys((current) => (current.length ? current : workspacePage.items[0] ? [workspacePage.items[0].key] : []));
        }
      })
      .catch((cause) => active && setLoadError(errorMessage(cause)));
    return () => {
      active = false;
    };
  }, [workspace]);

  // What the principal already holds, to show it and not grant it twice.
  const principalId = principal?.id;
  useEffect(() => {
    if (!principalId) return;
    let active = true;
    grantsHeldBy(principalId).then(
      (grants) => active && setHeld(grants),
      () => active && setHeld([]),
    );
    return () => {
      active = false;
    };
  }, [principalId]);

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
  const narrowKey = what === "roles" && !instance && chosenPlaces.length === 1 ? chosenPlaces[0] : undefined;

  useEffect(() => {
    if (what === "apis" && workspaces !== undefined) loadOptions(places.map((place) => place.key));
    if (what === "apis" && workspace) loadOptions([workspace.key]);
    if (narrowKey) loadOptions([narrowKey]);
  }, [what, workspaces, workspace, places, narrowKey, loadOptions]);

  const heldApis = useMemo(() => heldConsumerApis(held), [held]);
  const heldRoleSet = useMemo(() => heldRoles(held), [held]);

  const roleList = (roles ?? []).filter((item) => {
    // In a named workspace, a role held only at the instance is not offered (D302).
    return !workspace || !catalogue || !isInstanceOnly(item, catalogue);
  });
  function isInstanceOnly(role: Role, groups: ActionGroup[]) {
    return role.actionGroups.length > 0 && instanceOnly(role.actionGroups, groups).length === role.actionGroups.length;
  }

  const onlyOneRole = pickedRoles.length === 1 ? roles?.find((item) => item.key === pickedRoles[0]) : undefined;
  const narrowable =
    !!narrowKey && !!onlyOneRole && !!catalogue?.some((group) => onlyOneRole.actionGroups.includes(group.key) && group.narrowable);
  const narrowLoaded = narrowKey ? options[narrowKey] : undefined;
  const narrowOptions = useMemo(
    () =>
      narrowLoaded && narrowLoaded !== "error"
        ? [
            ...narrowLoaded.applications.map((item) => ({ id: `a:${item.key}`, label: item.name, description: "Application" })),
            ...narrowLoaded.recordTypes.map((item) => ({ id: `t:${item.key}`, label: item.name, description: "Record type" })),
          ]
        : [],
    [narrowLoaded],
  );
  const narrowing = narrowable && narrow === "some" ? narrowedTo : [];
  const narrowingKeys = {
    applications: narrowing.filter((id) => id.startsWith("a:")).map((id) => id.slice(2)),
    recordTypes: narrowing.filter((id) => id.startsWith("t:")).map((id) => id.slice(2)),
  };

  const identity = principal ? { kind: principal.kind, id: principal.id } : undefined;
  const requests: GrantCreate[] = !identity
    ? []
    : what === "apis"
      ? consumerRequests(identity, ticked, heldApis)
      : roleRequests(identity, pickedRoles, instance ? "instance" : chosenPlaces, narrowingKeys, heldRoleSet);

  const apiName = (key: string) => {
    for (const loaded of Object.values(options))
      if (loaded !== "error") {
        const found = loaded.consumerApis.find((item) => item.key === key);
        if (found) return found.name;
      }
    return key;
  };
  const roleName = (key: string) => roles?.find((item) => item.key === key)?.name ?? key;

  /** What one request gives, as a failure names it: "Master data in default". */
  const describe = (request: GrantCreate) =>
    request.consumerApi
      ? `${apiName(request.consumerApi)} in ${labelOf("workspaceKey" in request.scope ? request.scope.workspaceKey : "")}`
      : `${roleName(request.role ?? "")} ${"instance" in request.scope ? "for the whole instance" : `in ${labelOf("workspaceKey" in request.scope ? request.scope.workspaceKey : "")}`}`;

  const sentence = (() => {
    if (!principal || !requests.length) return "";
    if (what === "apis") {
      const byApi = new Map<string, string[]>();
      for (const request of requests) {
        const key = request.consumerApi ?? "";
        const where = labelOf("workspaceKey" in request.scope ? request.scope.workspaceKey : "");
        byApi.set(key, [...(byApi.get(key) ?? []), where]);
      }
      return consumerPlanSentence(principal.name, [...byApi].map(([key, where]) => ({ api: apiName(key), where })));
    }
    if (pickedRoles.length === 1 && catalogue && onlyOneRole) {
      return grantSentence({
        who: principal.name,
        groups: onlyOneRole.actionGroups,
        catalogue,
        where: instance ? undefined : chosenPlaces.map(labelOf).join(", "),
        narrowedTo: narrowOptions.filter((option) => narrowing.includes(option.id)).map((option) => option.label),
      });
    }
    const skipped = pickedRoles.length * (instance ? 1 : chosenPlaces.length) - requests.length;
    return rolePlanSentence({
      who: principal.name,
      roles: pickedRoles.map(roleName),
      where: instance ? "instance" : chosenPlaces.map(labelOf),
      count: requests.length,
      skipped: Math.max(0, skipped),
    });
  })();

  const alreadyHeld =
    !!principal && !requests.length && (what === "apis" ? false : pickedRoles.length > 0 && (instance || chosenPlaces.length > 0));

  function finish() {
    if (made.length) onGranted(made);
    else onClose();
  }

  async function grant() {
    if (!requests.length) return;
    setPending(true);
    setFailures([]);
    const done: Grant[] = [];
    const failed: { request: GrantCreate; message: string }[] = [];
    for (const request of requests) {
      try {
        done.push(await security.createGrant(request));
      } catch (cause) {
        failed.push({ request, message: errorMessage(cause) });
      }
    }
    const all = [...made, ...done];
    setMade(all);
    setHeld((current) => [...current, ...done]);
    // What was made is no longer a tick to make; a failure stays ticked to be tried again.
    setTicked((current) => {
      const next = new Set(current);
      for (const grant of done)
        if (grant.consumerApi && grant.scope.workspaceKey) next.delete(cellKey(grant.consumerApi.key, grant.scope.workspaceKey));
      return next;
    });
    setPending(false);
    if (!failed.length) {
      onGranted(all);
      return;
    }
    setFailures(failed.map(({ request, message }) => `${describe(request)}: ${message}`));
  }

  if (loadError)
    return (
      <Modal title="Grant access" eyebrow="Security" onClose={onClose}>
        <div className="dialog-body">
          <Notice tone="error" title="The roles could not be read">
            {loadError}
          </Notice>
        </div>
      </Modal>
    );

  const title = who ? `Grant ${who.name} access` : `Grant access in ${workspace?.label ?? ""}`;
  const allInstanceOnly = (role: Role) => !!catalogue && isInstanceOnly(role, catalogue);

  return (
    <Modal
      title={title}
      eyebrow="Security"
      size="wide"
      busy={pending}
      dirty={requests.length > 0 || (!!principal && principal !== who)}
      onClose={finish}
    >
      {!roles || !catalogue || (!workspace && !workspaces) ? (
        <div className="dialog-body">
          <Skeleton label="Loading roles" lines={4} />
        </div>
      ) : (
        <form
          className="grant-form"
          onSubmit={(event) => {
            event.preventDefault();
            void grant();
          }}
        >
          {!who && (
            <PrincipalPicker
              label="Who"
              kinds={["user", "group", "client"]}
              description="A person, a group or a client, found by name."
              onPick={(picked) => {
                setPrincipal(picked);
                setHeld([]);
                setTicked(new Set());
              }}
            />
          )}
          <fieldset className="form-field grant-what">
            <legend>What</legend>
            <Choice
              name="grant-what"
              value={what}
              options={[
                ["apis", "Consumer APIs"],
                ["roles", "Roles"],
              ]}
              onChange={setWhat}
            />
            <p className="admin-hint">
              {what === "apis"
                ? "Lets them read a consumer API in a workspace. It opens nothing on the management API."
                : "Lets them use the management API and the interface, as each role’s action groups say."}
            </p>
          </fieldset>

          {what === "apis" ? (
            <div className="grant-pick">
              <p className="admin-hint">
                Tick what they may read, one tick for one grant. A row or column heading ticks the whole line;
                Shift extends a range. Ticked and grey is already granted.
              </p>
              <ConsumerApiGrid
                workspaces={places}
                options={Object.fromEntries(places.map((place) => [place.key, options[place.key]]))}
                held={heldApis}
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
                        const disabled = !workspace && whereKind === "workspace" && allInstanceOnly(item);
                        const on = pickedRoles.includes(item.key);
                        const toggleRole = () =>
                          setPickedRoles((current) =>
                            current.includes(item.key) ? current.filter((key) => key !== item.key) : [...current, item.key],
                          );
                        const groupNames = catalogue
                          .filter((group) => item.actionGroups.includes(group.key))
                          .map((group) => group.name)
                          .join(", ");
                        return (
                          <tr
                            key={item.key}
                            className={`${on ? "grant-on" : ""}${disabled ? " grant-off" : ""}`}
                            onClick={(event) => {
                              if (!disabled && !(event.target instanceof HTMLInputElement)) toggleRole();
                            }}
                          >
                            <td className="grant-tick">
                              <input
                                type="checkbox"
                                aria-label={item.name}
                                checked={on}
                                disabled={disabled}
                                onChange={toggleRole}
                              />
                            </td>
                            <th scope="row">{item.name}</th>
                            <td className="grant-muted">
                              {disabled ? "Whole instance only. " : ""}
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
                    Roles in grey are held for the whole instance only: choose “The whole instance” below.
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
                      if (value === "workspace")
                        setPickedRoles((current) =>
                          current.filter((key) => {
                            const role = roles.find((item) => item.key === key);
                            return role ? !allInstanceOnly(role) : false;
                          }),
                        );
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
                        setNarrowedTo([]);
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
              {!narrowable && !instance && pickedRoles.length > 0 && (pickedRoles.length > 1 || chosenPlaces.length > 1) && (
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
            <Notice tone="error" title={`${failures.length} could not be granted`}>
              <ul className="grant-failures">
                {failures.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
              {made.length > 0 && <p>The others were made.</p>}
            </Notice>
          )}
          <div className="dialog-actions">
            <button type="button" className="secondary" disabled={pending} onClick={finish}>
              {made.length ? "Close" : "Cancel"}
            </button>
            <button className="primary" disabled={pending || !requests.length}>
              {pending ? "Granting…" : requests.length > 1 ? `Grant ${requests.length}` : failures.length ? "Try again" : "Grant"}
            </button>
          </div>
        </form>
      )}
    </Modal>
  );
}
