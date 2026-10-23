/**
 * Settings › Security › Groups (0.12 SP1, U8): local groups beside the selected one, searched by
 * name (D300). A group's page renames or deletes it, lists the roles granted to it (they apply to
 * every member) and its members, with Add a member and Remove. Groups from a sign-in provider come
 * with I3. Deleting a group, or removing a member, that would leave no active Security
 * administrator is refused by the engine (`LAST_SECURITY_ADMINISTRATOR`), shown as worded.
 */

import { useEffect, useRef, useState } from "react";
import { errorMessage, isApiError, refusalMessage } from "@/api/errors";
import { security } from "@/api/securityClient";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import { routePath } from "@/routing/routes";
import type { Group, GroupMember, RouteState, SettingsRoute } from "@/types";
import { CatalogueEntry, CatalogueLayout } from "@/ui/CatalogueLayout";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { Icon } from "@/ui/Icon";
import { InlineError } from "@/ui/InlineError";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { RouteLink } from "@/ui/RouteLink";
import { SearchField } from "@/ui/SearchField";
import { Section } from "@/ui/Section";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { SettingsTable } from "@/ui/SettingsTable";
import { useToast } from "@/ui/Toast";
import { GrantsSection } from "./GrantsSection";
import { PickDialog } from "./PickDialog";

type GroupsRoute = Extract<SettingsRoute, { page: "groups" }>;

const GROUPS: GroupsRoute = { kind: "settings", page: "groups" };

const members = (count: number) => `${count} member${count === 1 ? "" : "s"}`;

export function GroupsPage({ route, onNavigate }: { route: GroupsRoute; onNavigate: (route: RouteState) => void }) {
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<Group | "new">();
  const newButtonRef = useRef<HTMLButtonElement>(null);
  const q = useDebouncedValue(search.trim());
  const feed = useCursorFeed((cursor) => security.groups({ q, cursor }), [q]);
  const toast = useToast();

  const changed = (group: Group) =>
    feed.setItems((items) => items.map((item) => (item.id === group.id ? group : item)));

  const catalogue = (
    <nav className="model-catalogue security-catalogue" aria-label="Groups">
      <section>
        <SearchField label="Search groups" placeholder="Group name" value={search} onChange={setSearch} clearOnEscape />
        {feed.items.map((group) => (
          <CatalogueEntry
            key={group.id}
            icon="users"
            title={group.name}
            subtitle={group.description ? `${members(group.members)} · ${group.description}` : members(group.members)}
            current={route.groupId === group.id}
            onSelect={() => onNavigate({ ...GROUPS, groupId: group.id })}
          />
        ))}
        {feed.loading && !feed.items.length && <p className="explorer-empty">Loading groups…</p>}
        {!feed.loading && !feed.error && !feed.items.length && (
          <p className="explorer-empty">{q ? `No group matches “${q}”.` : "No groups yet."}</p>
        )}
        {feed.error && (
          <div className="catalogue-error">
            <InlineError message={feed.error} onRetry={feed.retry} />
          </div>
        )}
        {feed.hasMore && (
          <button className="load-more" disabled={feed.loading} onClick={feed.loadMore}>
            Load more groups
          </button>
        )}
      </section>
    </nav>
  );

  return (
    <SettingsLayout
      eyebrow="Security"
      title="Groups"
      description="People grouped to hold roles together: a role granted to a group applies to every member, and stops applying when they leave it."
      actions={
        <button ref={newButtonRef} className="primary" onClick={() => setEditing("new")}>
          <Icon name="plus" /> New group
        </button>
      }
    >
      <CatalogueLayout
        catalogue={catalogue}
        hasSelection={!!route.groupId}
        backLabel="All groups"
        onBack={() => onNavigate(GROUPS)}
      >
        {route.groupId ? (
          <GroupDetail
            key={route.groupId}
            groupId={route.groupId}
            onNavigate={onNavigate}
            onRename={(group) => setEditing(group)}
            onChanged={changed}
            onDeleted={(group) => {
              toast(`The group ${group.name} was deleted. Its roles no longer apply to its members.`);
              feed.reload();
              onNavigate(GROUPS);
            }}
          />
        ) : (
          <div className="panel-state">Choose a group.</div>
        )}
      </CatalogueLayout>
      {editing && (
        <GroupDialog
          group={editing === "new" ? undefined : editing}
          onClose={() => {
            setEditing(undefined);
            newButtonRef.current?.focus();
          }}
          onSaved={(group, created) => {
            setEditing(undefined);
            if (created) {
              feed.reload();
              onNavigate({ ...GROUPS, groupId: group.id });
              toast(`The group ${group.name} was created. Add members and grant it a role.`);
            } else {
              changed(group);
              toast("Saved.");
            }
          }}
        />
      )}
    </SettingsLayout>
  );
}

function GroupDetail({
  groupId,
  onNavigate,
  onRename,
  onChanged,
  onDeleted,
}: {
  groupId: string;
  onNavigate: (route: RouteState) => void;
  onRename: (group: Group) => void;
  onChanged: (group: Group) => void;
  onDeleted: (group: Group) => void;
}) {
  const [group, setGroup] = useState<Group>();
  const [loadError, setLoadError] = useState("");
  const [loadToken, setLoadToken] = useState(0);
  const [deleting, setDeleting] = useState(false);
  const [pending, setPending] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  useEffect(() => {
    let current = true;
    security.group(groupId).then(
      (loaded) => {
        if (!current) return;
        setGroup(loaded);
        setLoadError("");
      },
      (cause) => current && setLoadError(errorMessage(cause)),
    );
    return () => {
      current = false;
    };
  }, [groupId, loadToken]);

  async function remove() {
    if (!group) return;
    setPending(true);
    setDeleteError("");
    try {
      await security.deleteGroup(group.id);
      onDeleted(group);
    } catch (cause) {
      setDeleteError(errorMessage(cause));
      setPending(false);
    }
  }

  const reload = () =>
    void security.group(groupId).then((loaded) => {
      setGroup(loaded);
      onChanged(loaded);
    });

  if (loadError) return <InlineError message={loadError} onRetry={() => setLoadToken((token) => token + 1)} />;
  if (!group) return <div className="panel-state">Loading group…</div>;

  return (
    <div className="model-editor-stack security-detail">
      <header className="model-detail-header">
        <div>
          <p className="eyebrow">Group</p>
          <h2>{group.name}</h2>
          <p>{group.description ? `${group.description} · ${members(group.members)}` : members(group.members)}</p>
        </div>
      </header>
      <div className="model-actions">
        <button className="secondary" onClick={() => onRename(group)}>
          Rename…
        </button>
        <button className="danger-ghost" onClick={() => setDeleting(true)}>
          Delete group
        </button>
      </div>
      <GrantsSection
        subject={{ principal: { kind: "group", id: group.id, name: group.name } }}
        description="A role granted to the group applies to every member."
        load={(cursor) => security.grantsOf(group.id, cursor)}
        deps={[group.id]}
        onNavigate={onNavigate}
      />
      <GroupMembers group={group} onNavigate={onNavigate} onChanged={reload} />
      {deleting && (
        <ConfirmDialog
          title={`Delete ${group.name}?`}
          confirmLabel="Delete group"
          pending={pending}
          error={deleteError}
          onCancel={() => {
            setDeleting(false);
            setDeleteError("");
          }}
          onConfirm={() => void remove()}
        >
          <p>
            The group, its memberships and the roles granted to it are removed. Its {members(group.members)} keep any
            roles granted to them directly.
          </p>
        </ConfirmDialog>
      )}
    </div>
  );
}

function GroupMembers({
  group,
  onNavigate,
  onChanged,
}: {
  group: Group;
  onNavigate: (route: RouteState) => void;
  onChanged: () => void;
}) {
  const feed = useCursorFeed((cursor) => security.members(group.id, cursor), [group.id]);
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState("");
  const addRef = useRef<HTMLButtonElement>(null);
  const toast = useToast();

  async function remove(member: GroupMember) {
    setError("");
    try {
      await security.removeMember(group.id, member.id);
      feed.setItems((items) => items.filter((item) => item.id !== member.id));
      onChanged();
      toast(`${member.name} left ${group.name}.`);
    } catch (cause) {
      setError(errorMessage(cause));
    }
  }

  return (
    <Section
      title="Members"
      actions={
        <button ref={addRef} type="button" className="secondary" onClick={() => setAdding(true)}>
          <Icon name="plus" /> Add a member
        </button>
      }
    >
      {error && (
        <Notice tone="error" title="The member was not removed">
          {error}
        </Notice>
      )}
      {feed.error ? (
        <InlineError message={feed.error} onRetry={feed.retry} />
      ) : !feed.items.length ? (
        <p className="admin-hint">{feed.loading ? "Loading members…" : "No members yet."}</p>
      ) : (
        <SettingsTable label="Members" columns={["Person", "Username", "Status", { hidden: "Actions" }]}>
          {feed.items.map((member) => {
            const route: SettingsRoute = { kind: "settings", page: "people", userId: member.id };
            return (
              <tr key={member.id}>
                <th scope="row">
                  <RouteLink href={routePath(route)} onNavigate={() => onNavigate(route)}>
                    {member.name}
                  </RouteLink>
                </th>
                <td data-label="Username">{member.username}</td>
                <td data-label="Status">{member.active ? "Active" : "Deactivated"}</td>
                <td className="grant-action">
                  <button
                    type="button"
                    className="ghost"
                    aria-label={`Remove ${member.name} from ${group.name}`}
                    onClick={() => void remove(member)}
                  >
                    Remove
                  </button>
                </td>
              </tr>
            );
          })}
        </SettingsTable>
      )}
      {feed.hasMore && (
        <button className="load-more" disabled={feed.loading} onClick={feed.loadMore}>
          Load more members
        </button>
      )}
      {adding && (
        <PickDialog
          title={`Add a member to ${group.name}`}
          label="Person"
          kinds={["user"]}
          confirmLabel="Add to the group"
          onClose={() => {
            setAdding(false);
            addRef.current?.focus();
          }}
          onPicked={async (person) => {
            await security.addMember(group.id, person.id);
            setAdding(false);
            feed.reload();
            onChanged();
            toast(`${person.name} is now in ${group.name}.`);
            addRef.current?.focus();
          }}
        />
      )}
    </Section>
  );
}

function GroupDialog({
  group,
  onClose,
  onSaved,
}: {
  group?: Group;
  onClose: () => void;
  onSaved: (group: Group, created: boolean) => void;
}) {
  const [name, setName] = useState(group?.name ?? "");
  const [description, setDescription] = useState(group?.description ?? "");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const changed = name.trim() !== (group?.name ?? "") || description.trim() !== (group?.description ?? "");

  async function save() {
    setPending(true);
    setError("");
    try {
      if (group)
        onSaved(
          await security.updateGroup(group.id, {
            expectedVersion: group.version,
            name: name.trim(),
            description: description.trim() || null,
          }),
          false,
        );
      else
        onSaved(
          await security.createGroup({
            name: name.trim(),
            ...(description.trim() ? { description: description.trim() } : {}),
          }),
          true,
        );
    } catch (cause) {
      setError(
        isApiError(cause, "VERSION_CONFLICT")
          ? "Someone changed this group while you were editing. Close the dialog to see it as it is now."
          : refusalMessage(cause, { name: "Name", description: "Description" }),
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <Modal
      title={group ? `Rename ${group.name}` : "New group"}
      eyebrow="Security"
      size="compact"
      busy={pending}
      dirty={changed}
      onClose={onClose}
    >
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        <label>
          Name
          <input autoFocus required maxLength={200} value={name} onChange={(event) => setName(event.target.value)} />
        </label>
        <label>
          Description (optional)
          <input maxLength={2000} value={description} onChange={(event) => setDescription(event.target.value)} />
        </label>
        {error && (
          <Notice tone="error" title="Not saved">
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" disabled={pending} onClick={onClose}>
            Cancel
          </button>
          <button className="primary" disabled={pending || !changed || !name.trim()}>
            {pending ? "Saving…" : group ? "Save" : "Create group"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
