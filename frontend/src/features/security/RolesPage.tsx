/**
 * Settings › Security › Roles (0.12 SP1, U8): the matrix of roles by action group, each group with
 * its one-line description. Predefined roles are read-only; a custom role is created empty or
 * copied from any role and edited in place in its column (its groups, name and description), saved
 * with the version read, and deleted while nobody holds it (`ROLE_IN_USE` otherwise). A change
 * applies on its holders' next request. At phone width the matrix scrolls sideways in its box with
 * the group column fixed (D305).
 */

import { useEffect, useRef, useState } from "react";
import { errorMessage, isApiError, refusalMessage } from "@/api/errors";
import { security } from "@/api/securityClient";
import type { ActionGroup, Role } from "@/types";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { Icon } from "@/ui/Icon";
import { InlineError } from "@/ui/InlineError";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { SelectField } from "@/ui/Selection";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { SettingsGroup, SettingsPanel } from "@/ui/SettingsParts";
import { Skeleton } from "@/ui/Skeleton";
import { useToast } from "@/ui/Toast";
import { settingsHead } from "@/ui/settingsNavigation";

// A role's fields by the names its form shows them under.
const ROLE_FIELDS = { name: "Name", description: "Description", actionGroups: "Action groups" };

const held = (count: number) =>
  count === 0 ? "not granted to anyone" : `granted ${count === 1 ? "once" : `${count} times`}`;

export function RolesPage() {
  const [roles, setRoles] = useState<Role[]>();
  const [catalogue, setCatalogue] = useState<ActionGroup[]>();
  const [loadError, setLoadError] = useState("");
  const [loadToken, setLoadToken] = useState(0);
  const [editing, setEditing] = useState<{ role: Role; groups: string[]; name: string; description: string }>();
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const newButtonRef = useRef<HTMLButtonElement>(null);
  const toast = useToast();

  useEffect(() => {
    let active = true;
    Promise.all([security.roles(), security.actionGroups()]).then(
      ([page, groups]) => {
        if (!active) return;
        setRoles(page.items);
        setCatalogue(groups);
        setLoadError("");
      },
      (cause) => active && setLoadError(errorMessage(cause)),
    );
    return () => {
      active = false;
    };
  }, [loadToken]);

  function edit(role: Role) {
    setError("");
    setEditing({ role, groups: role.actionGroups, name: role.name, description: role.description ?? "" });
  }

  function replace(role: Role) {
    setRoles((items) => items?.map((item) => (item.key === role.key ? role : item)));
  }

  async function save() {
    if (!editing) return;
    setPending(true);
    setError("");
    try {
      const saved = await security.updateRole(editing.role.key, {
        expectedVersion: editing.role.version,
        name: editing.name.trim(),
        description: editing.description.trim() || null,
        actionGroups: catalogue?.filter((group) => editing.groups.includes(group.key)).map((group) => group.key),
      });
      replace(saved);
      setEditing(undefined);
      toast(`${saved.name} saved. Its holders have the change from their next request.`);
    } catch (cause) {
      if (isApiError(cause, "VERSION_CONFLICT")) {
        const page = await security.roles().catch(() => undefined);
        const current = page?.items.find((item) => item.key === editing.role.key);
        if (page) setRoles(page.items);
        if (current) setEditing({ ...editing, role: current });
        setError("Someone changed this role while you were editing. Save again to replace their change with yours.");
      } else {
        setError(refusalMessage(cause, ROLE_FIELDS));
      }
    } finally {
      setPending(false);
    }
  }

  async function remove() {
    if (!editing) return;
    setPending(true);
    setError("");
    try {
      await security.deleteRole(editing.role.key);
      setRoles((items) => items?.filter((item) => item.key !== editing.role.key));
      toast(`${editing.role.name} was deleted.`);
      setEditing(undefined);
      setDeleting(false);
      newButtonRef.current?.focus();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }

  const changed =
    !!editing &&
    (editing.name.trim() !== editing.role.name ||
      editing.description.trim() !== (editing.role.description ?? "") ||
      editing.groups.length !== editing.role.actionGroups.length ||
      editing.groups.some((group) => !editing.role.actionGroups.includes(group)));

  return (
    <SettingsLayout
      {...settingsHead("roles")}
      title="Roles"
      description="A role is a set of action groups. Predefined roles cannot change; copy one to make your own."
      actions={
        <button ref={newButtonRef} className="primary" disabled={!roles} onClick={() => setCreating(true)}>
          <Icon name="plus" /> New role
        </button>
      }
    >
      {loadError ? (
        <InlineError message={loadError} onRetry={() => setLoadToken((token) => token + 1)} />
      ) : !roles || !catalogue ? (
        <Skeleton label="Loading roles" lines={8} />
      ) : (
        <SettingsGroup
          stacked
          title="Roles by action group"
          description="Each column is a role, each row an action group. A custom role is edited in its own column."
        >
          <SettingsPanel>
            <div className="role-matrix-wrap" role="group" aria-label="Roles by action group" tabIndex={0}>
              <table className="role-matrix">
                <thead>
                  <tr>
                    <th scope="col" className="role-matrix-group">
                      Action group
                    </th>
                    {roles.map((role) => (
                      <th
                        key={role.key}
                        scope="col"
                        className={
                          role.predefined ? undefined : `role-custom${editing?.role.key === role.key ? " editing" : ""}`
                        }
                      >
                        <span>{editing?.role.key === role.key ? editing.name || role.name : role.name}</span>
                        {!role.predefined && (
                          <>
                            <small>Custom</small>
                            {editing?.role.key !== role.key && (
                              <button
                                type="button"
                                className="ghost role-edit"
                                disabled={!!editing}
                                aria-label={`Edit ${role.name}`}
                                onClick={() => edit(role)}
                              >
                                <Icon name="pencil" size={13} /> Edit
                              </button>
                            )}
                          </>
                        )}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {catalogue.map((group) => (
                    <tr key={group.key}>
                      <th scope="row" className="role-matrix-group">
                        {group.name}
                        <small>{group.description}</small>
                      </th>
                      {roles.map((role) =>
                        editing?.role.key === role.key ? (
                          <td key={role.key} className="role-custom editing">
                            <input
                              type="checkbox"
                              aria-label={`${editing.name || role.name}: ${group.name}`}
                              checked={editing.groups.includes(group.key)}
                              onChange={(event) =>
                                setEditing({
                                  ...editing,
                                  groups: event.target.checked
                                    ? [...editing.groups, group.key]
                                    : editing.groups.filter((key) => key !== group.key),
                                })
                              }
                            />
                          </td>
                        ) : (
                          <td key={role.key} className={role.predefined ? undefined : "role-custom"}>
                            {role.actionGroups.includes(group.key) ? (
                              <span className="role-yes">
                                <Icon name="check" size={14} />
                                <span className="visually-hidden">Yes</span>
                              </span>
                            ) : (
                              <span className="visually-hidden">No</span>
                            )}
                          </td>
                        ),
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </SettingsPanel>
          {editing && (
            <form
              aria-label={`Edit ${editing.role.name}`}
              onSubmit={(event) => {
                event.preventDefault();
                void save();
              }}
            >
              <SettingsPanel
                foot={
                  <>
                    <span className="settings-panel-state">
                      {editing.role.name} is {held(editing.role.grants)}
                      {editing.role.grants > 0 && "; a change applies on their next request"}.
                    </span>
                    <button
                      type="button"
                      className="danger-ghost"
                      disabled={pending || editing.role.grants > 0}
                      title={editing.role.grants > 0 ? "A role still granted cannot be deleted" : undefined}
                      onClick={() => setDeleting(true)}
                    >
                      Delete role
                    </button>
                    <button
                      type="button"
                      className="secondary"
                      disabled={pending}
                      onClick={() => setEditing(undefined)}
                    >
                      Cancel
                    </button>
                    <button className="primary" disabled={pending || !changed || !editing.name.trim()}>
                      {pending ? "Saving…" : "Save"}
                    </button>
                  </>
                }
              >
                <div className="settings-fields">
                  <label>
                    Name
                    <input
                      required
                      maxLength={200}
                      value={editing.name}
                      onChange={(event) => setEditing({ ...editing, name: event.target.value })}
                    />
                  </label>
                  <label>
                    Description (optional)
                    <input
                      maxLength={2000}
                      value={editing.description}
                      onChange={(event) => setEditing({ ...editing, description: event.target.value })}
                    />
                  </label>
                  {error && !deleting && (
                    <Notice tone="error" title="The role was not saved">
                      {error}
                    </Notice>
                  )}
                </div>
              </SettingsPanel>
            </form>
          )}
        </SettingsGroup>
      )}
      {creating && roles && (
        <NewRoleDialog
          roles={roles}
          onClose={() => {
            setCreating(false);
            newButtonRef.current?.focus();
          }}
          onCreated={(role) => {
            setCreating(false);
            setRoles((items) => [...(items ?? []), role]);
            edit(role);
            toast(`${role.name} was created. Choose its action groups and save.`);
          }}
        />
      )}
      {deleting && editing && (
        <ConfirmDialog
          title={`Delete ${editing.role.name}?`}
          confirmLabel="Delete role"
          pending={pending}
          error={error}
          onCancel={() => {
            setDeleting(false);
            setError("");
          }}
          onConfirm={() => void remove()}
        >
          <p>The role is removed. Nobody holds it, so no one loses access.</p>
        </ConfirmDialog>
      )}
    </SettingsLayout>
  );
}

// A key no role has: role keys are lowercase words joined by hyphens.
const NOTHING = " nothing";

function NewRoleDialog({
  roles,
  onClose,
  onCreated,
}: {
  roles: Role[];
  onClose: () => void;
  onCreated: (role: Role) => void;
}) {
  const [name, setName] = useState("");
  const [from, setFrom] = useState(NOTHING);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  async function create() {
    setPending(true);
    setError("");
    try {
      onCreated(
        await security.createRole(
          from !== NOTHING ? { name: name.trim(), copiedFrom: from } : { name: name.trim(), actionGroups: [] },
        ),
      );
    } catch (cause) {
      setError(refusalMessage(cause, ROLE_FIELDS));
      setPending(false);
    }
  }

  return (
    <Modal title="New role" eyebrow="People and access" size="compact" busy={pending} dirty={!!name} onClose={onClose}>
      <form
        className="grant-form"
        onSubmit={(event) => {
          event.preventDefault();
          void create();
        }}
      >
        <label>
          Name
          <input autoFocus required maxLength={200} value={name} onChange={(event) => setName(event.target.value)} />
        </label>
        <SelectField
          label="Start from"
          value={from}
          options={[
            { id: NOTHING, label: "Nothing", description: "Choose its action groups yourself" },
            ...roles.map((role) => ({ id: role.key, label: role.name, description: "Its action groups, copied" })),
          ]}
          onChange={setFrom}
        />
        {error && (
          <Notice tone="error" title="The role was not created">
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" disabled={pending} onClick={onClose}>
            Cancel
          </button>
          <button className="primary" disabled={pending || !name.trim()}>
            {pending ? "Adding…" : "Add role"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
