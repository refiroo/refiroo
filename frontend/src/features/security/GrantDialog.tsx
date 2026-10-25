/**
 * Grant a role or a consumer API (0.12 SP1, SP2, U8): one dialog for a workspace's Access and a
 * person's, group's or client's page. From Access it asks who (a person, group or client); from a
 * principal it asks where (the whole instance or one workspace). A consumer API is granted in one
 * workspace, chosen from those its model declares, and never narrowed (D306, D354). The choices
 * come from the workspace's grant options, which a Security administrator reads without Browse
 * (D355). The role is chosen with its action groups named; a
 * workspace grant of a role with narrowable groups may narrow what they may change to applications
 * and record types of that workspace's model, and reading is never narrowed (D243). A role held only
 * at the instance offers only the whole instance (D302). A sentence says what the grant allows.
 */

import { useEffect, useMemo, useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { security } from "@/api/securityClient";
import type { ActionGroup, Grant, GrantCreate, GrantOptions, Role, Workspace } from "@/types";
import { Choice } from "@/ui/Choice";
import { Modal } from "@/ui/Modal";
import { MultiSelect } from "@/ui/MultiSelect";
import { Notice } from "@/ui/Notice";
import { SelectField } from "@/ui/Selection";
import { Skeleton } from "@/ui/Skeleton";
import { PrincipalPicker, type PickedPrincipal } from "./PrincipalPicker";
import { consumerApiSentence, grantSentence, instanceOnly } from "./securityText";

export function GrantDialog({
  who,
  workspace,
  onClose,
  onGranted,
}: {
  /** The person, group or client the page is about; without it the dialog asks who. */
  who?: PickedPrincipal;
  /** The workspace the page is about; without it the dialog asks where. */
  workspace?: { key: string; label: string };
  onClose: () => void;
  onGranted: (grant: Grant) => void;
}) {
  const [roles, setRoles] = useState<Role[]>();
  const [catalogue, setCatalogue] = useState<ActionGroup[]>();
  const [workspaces, setWorkspaces] = useState<Workspace[]>();
  const [loadError, setLoadError] = useState("");
  const [principal, setPrincipal] = useState<PickedPrincipal | undefined>(who);
  const [what, setWhat] = useState<"role" | "consumer-api">("role");
  const [apiKey, setApiKey] = useState("");
  const [roleKey, setRoleKey] = useState("reader");
  const [whereKind, setWhereKind] = useState<"workspace" | "instance">("workspace");
  const [workspaceKey, setWorkspaceKey] = useState(workspace?.key ?? "");
  const [narrow, setNarrow] = useState<"everything" | "some">("everything");
  const [narrowedTo, setNarrowedTo] = useState<string[]>([]);
  const [options, setOptions] = useState<GrantOptions>();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    Promise.all([security.roles(), security.actionGroups(), workspace ? undefined : api.workspaces()])
      .then(([rolePage, groups, workspacePage]) => {
        if (!active) return;
        setRoles(rolePage.items);
        setCatalogue(groups);
        if (workspacePage) {
          setWorkspaces(workspacePage.items);
          setWorkspaceKey((current) => current || workspacePage.items[0]?.key || "");
        }
      })
      .catch((cause) => active && setLoadError(errorMessage(cause)));
    return () => {
      active = false;
    };
  }, [workspace]);

  const role = roles?.find((item) => item.key === roleKey);
  const groups = useMemo(() => role?.actionGroups ?? [], [role]);
  const onlyInstance = !!catalogue && groups.length > 0 && instanceOnly(groups, catalogue).length === groups.length;
  const consumer = what === "consumer-api";
  // A consumer API is always granted in one workspace (D306).
  const instance = !workspace && !consumer && (whereKind === "instance" || onlyInstance);
  const narrowable =
    !instance && !consumer && !!catalogue?.some((group) => groups.includes(group.key) && group.narrowable);

  // What the chosen workspace's model offers: applications and record types to narrow to, and
  // consumer APIs to grant (D355).
  useEffect(() => {
    if (instance || !workspaceKey) return;
    let active = true;
    security.grantOptions(workspaceKey).then(
      (loaded) => {
        if (!active) return;
        setOptions(loaded);
        setApiKey((current) =>
          loaded.consumerApis.some((item) => item.key === current) ? current : (loaded.consumerApis[0]?.key ?? ""),
        );
      },
      (cause) => active && setError(errorMessage(cause)),
    );
    return () => {
      active = false;
    };
  }, [instance, workspaceKey]);

  const narrowOptions = useMemo(
    () =>
      options
        ? [
            ...options.applications.map((item) => ({
              id: `a:${item.key}`,
              label: item.name,
              description: "Application",
            })),
            ...options.recordTypes.map((item) => ({
              id: `t:${item.key}`,
              label: item.name,
              description: "Record type",
            })),
          ]
        : [],
    [options],
  );

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

  const workspaceLabel =
    workspace?.label ?? workspaces?.find((item) => item.key === workspaceKey)?.label ?? workspaceKey;
  const narrowing = narrowable && narrow === "some" ? narrowedTo : [];
  const narrowedNames = narrowOptions.filter((option) => narrowing.includes(option.id)).map((option) => option.label);
  const title = who ? `Grant ${who.name} access` : `Grant access in ${workspace?.label ?? ""}`;
  const chosenApi = options?.consumerApis.find((item) => item.key === apiKey);
  const ready = consumer
    ? !!principal && !!workspaceKey && !!chosenApi
    : !!principal && !!role && (instance || !!workspaceKey) && !(narrow === "some" && narrowable && !narrowing.length);

  async function grant() {
    if (!principal || (!consumer && !role)) return;
    setPending(true);
    setError("");
    if (consumer) {
      try {
        onGranted(
          await security.createGrant({
            principal: { kind: principal.kind, id: principal.id },
            consumerApi: apiKey,
            scope: { workspaceKey },
          }),
        );
      } catch (cause) {
        setError(errorMessage(cause));
      } finally {
        setPending(false);
      }
      return;
    }
    const scope: GrantCreate["scope"] = instance
      ? { instance: true }
      : {
          workspaceKey,
          applications: narrowing.filter((id) => id.startsWith("a:")).map((id) => id.slice(2)),
          recordTypes: narrowing.filter((id) => id.startsWith("t:")).map((id) => id.slice(2)),
        };
    try {
      onGranted(
        await security.createGrant({ principal: { kind: principal.kind, id: principal.id }, role: role!.key, scope }),
      );
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }

  return (
    <Modal title={title} eyebrow="Security" busy={pending} dirty={!!principal && principal !== who} onClose={onClose}>
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
              onPick={setPrincipal}
            />
          )}
          <fieldset className="form-field grant-what">
            <legend>What</legend>
            <Choice
              name="grant-what"
              value={what}
              options={[
                ["role", "A role"],
                ["consumer-api", "A consumer API"],
              ]}
              onChange={setWhat}
            />
            <p className="admin-hint">
              {consumer
                ? "Lets them read that consumer API in one workspace. It opens nothing on the management API."
                : "Lets them use the management API and the interface, as the role's action groups say."}
            </p>
          </fieldset>
          {!consumer && (
            <SelectField
              label="Role"
              value={roleKey}
              options={roles
                // In a named workspace, a role held only at the instance is not offered (D302).
                .filter(
                  (item) =>
                    !workspace ||
                    !item.actionGroups.length ||
                    instanceOnly(item.actionGroups, catalogue).length < item.actionGroups.length,
                )
                .map((item) => ({
                  id: item.key,
                  label: item.name,
                  description: catalogue
                    .filter((group) => item.actionGroups.includes(group.key))
                    .map((group) => group.name)
                    .join(", "),
                }))}
              onChange={setRoleKey}
            />
          )}
          {!workspace && consumer && (
            <SelectField
              label="Workspace"
              value={workspaceKey}
              options={(workspaces ?? []).map((item) => ({ id: item.key, label: item.label, description: item.key }))}
              onChange={(key) => {
                setWorkspaceKey(key);
                setOptions(undefined);
              }}
            />
          )}
          {consumer &&
            (!options ? (
              <Skeleton label="Loading the workspace's consumer APIs" lines={1} />
            ) : options.consumerApis.length ? (
              <SelectField
                label="Consumer API"
                value={apiKey}
                options={options.consumerApis.map((item) => ({
                  id: item.key,
                  label: item.name,
                  description: item.key,
                }))}
                onChange={setApiKey}
              />
            ) : (
              <p className="admin-hint">{workspaceLabel}’s model declares no consumer API.</p>
            ))}
          {!workspace && !consumer && (
            <fieldset className="form-field grant-where">
              <legend>Where</legend>
              <Choice
                name="grant-where"
                value={onlyInstance ? "instance" : whereKind}
                options={[
                  ["workspace", "One workspace", "workspace"],
                  ["instance", "The whole instance", "globe"],
                ]}
                onChange={(value) => !onlyInstance && setWhereKind(value)}
              />
              {onlyInstance ? (
                <p className="admin-hint">
                  {role?.name} is granted for the whole instance only: its action groups are not held per workspace.
                </p>
              ) : instance ? (
                <p className="admin-hint">Every workspace, now and later.</p>
              ) : (
                <SelectField
                  label="Workspace"
                  value={workspaceKey}
                  options={(workspaces ?? []).map((item) => ({
                    id: item.key,
                    label: item.label,
                    description: item.key,
                  }))}
                  onChange={(key) => {
                    setWorkspaceKey(key);
                    setNarrowedTo([]);
                    setOptions(undefined);
                  }}
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
                  ["everything", `Everything in ${workspaceLabel}`],
                  ["some", "Only these applications and record types"],
                ]}
                onChange={setNarrow}
              />
              {narrow === "some" &&
                (options ? (
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
          {consumer && chosenApi && principal && (
            <p className="grant-sentence" role="status">
              {consumerApiSentence(principal.name, chosenApi.name, workspaceLabel)}
            </p>
          )}
          {!consumer && role && principal && (
            <p className="grant-sentence" role="status">
              {grantSentence({
                who: principal.name,
                groups,
                catalogue,
                where: instance ? undefined : workspaceLabel,
                narrowedTo: narrowedNames,
              })}
            </p>
          )}
          {error && (
            <Notice tone="error" title="Nothing was granted">
              {error}
            </Notice>
          )}
          <div className="dialog-actions">
            <button type="button" className="secondary" disabled={pending} onClick={onClose}>
              Cancel
            </button>
            <button className="primary" disabled={pending || !ready}>
              {pending ? "Granting…" : "Grant"}
            </button>
          </div>
        </form>
      )}
    </Modal>
  );
}
