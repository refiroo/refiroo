/**
 * Settings › Security › People (0.12 SP1, U8): the people of the instance beside the selected
 * person (U-D10's list and detail), searched by name, username or e-mail, active or deactivated,
 * each with the roles they hold (D298). A person's page edits their name and e-mail, makes a
 * one-time password link shown once (D304), signs them out everywhere, deactivates or restores them
 * (never deletes, D237), lists their roles directly and through groups (D299) and their groups.
 * Every write carries the version read; the engine's refusals are shown as it words them.
 */

import { useEffect, useRef, useState } from "react";
import { errorMessage, invalidFields, isApiError } from "@/api/errors";
import { security } from "@/api/securityClient";
import { initials } from "@/app/useMe";
import { formatServerTime } from "@/lib/dates";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import { routePath } from "@/routing/routes";
import type { Group, PasswordResetLink, RouteState, SettingsRoute, User } from "@/types";
import { CatalogueEntry, CatalogueLayout } from "@/ui/CatalogueLayout";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { FormField } from "@/ui/FormField";
import { Icon } from "@/ui/Icon";
import { InlineError } from "@/ui/InlineError";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { RouteLink } from "@/ui/RouteLink";
import { SearchField } from "@/ui/SearchField";
import { Section } from "@/ui/Section";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { ShownOnceDialog } from "@/ui/ShownOnceDialog";
import { StatusPill } from "@/ui/StatusPill";
import { useToast } from "@/ui/Toast";
import { GrantsSection } from "./GrantsSection";
import { PickDialog } from "./PickDialog";
import { userRoleLine } from "./securityText";

type PeopleRoute = Extract<SettingsRoute, { page: "people" }>;

const PEOPLE: PeopleRoute = { kind: "settings", page: "people" };

export function PeoplePage({ route, onNavigate }: { route: PeopleRoute; onNavigate: (route: RouteState) => void }) {
  const [search, setSearch] = useState("");
  const [active, setActive] = useState(true);
  const [counts, setCounts] = useState<{ active?: number; deactivated?: number }>({});
  const [creating, setCreating] = useState(false);
  const [link, setLink] = useState<{ user: User; link: PasswordResetLink; created: boolean }>();
  const newButtonRef = useRef<HTMLButtonElement>(null);
  const q = useDebouncedValue(search.trim());
  const feed = useCursorFeed((cursor) => security.users({ q, active, cursor }), [q, active]);
  const [countToken, setCountToken] = useState(0);

  useEffect(() => {
    let current = true;
    Promise.all([
      security.users({ active: true, pageSize: 1, includeTotal: true }),
      security.users({ active: false, pageSize: 1, includeTotal: true }),
    ]).then(
      ([on, off]) => current && setCounts({ active: on.totalCount, deactivated: off.totalCount }),
      () => undefined,
    );
    return () => {
      current = false;
    };
  }, [countToken]);

  function changed(user: User) {
    feed.setItems((items) => items.map((item) => (item.id === user.id ? user : item)));
    setCountToken((token) => token + 1);
  }

  const catalogue = (
    <nav className="model-catalogue security-catalogue" aria-label="People">
      <section>
        <SearchField
          label="Search people"
          placeholder="Name, username or e-mail"
          value={search}
          onChange={setSearch}
          clearOnEscape
        />
        <div className="security-filters" role="group" aria-label="Show">
          <button type="button" className="security-filter" aria-pressed={active} onClick={() => setActive(true)}>
            Active{counts.active !== undefined && <span>{counts.active}</span>}
          </button>
          <button type="button" className="security-filter" aria-pressed={!active} onClick={() => setActive(false)}>
            Deactivated{counts.deactivated !== undefined && <span>{counts.deactivated}</span>}
          </button>
        </div>
        {feed.items.map((user) => (
          <CatalogueEntry
            key={user.id}
            icon="user"
            title={user.name}
            subtitle={userRoleLine(user.roles)}
            current={route.userId === user.id}
            onSelect={() => onNavigate({ ...PEOPLE, userId: user.id })}
          />
        ))}
        {feed.loading && !feed.items.length && <p className="explorer-empty">Loading people…</p>}
        {!feed.loading && !feed.error && !feed.items.length && (
          <p className="explorer-empty">
            {q
              ? `No ${active ? "active" : "deactivated"} person matches “${q}”.`
              : `No ${active ? "active" : "deactivated"} people.`}
          </p>
        )}
        {feed.error && (
          <div className="catalogue-error">
            <InlineError message={feed.error} onRetry={feed.retry} />
          </div>
        )}
        {feed.hasMore && (
          <button className="load-more" disabled={feed.loading} onClick={feed.loadMore}>
            Load more people
          </button>
        )}
      </section>
    </nav>
  );

  return (
    <SettingsLayout
      eyebrow="Security"
      title="People"
      description="The people who sign in, the roles they hold and the groups they are in. A person is deactivated, never deleted, so their history keeps their name."
      actions={
        <button ref={newButtonRef} className="primary" onClick={() => setCreating(true)}>
          <Icon name="plus" /> New person
        </button>
      }
    >
      <CatalogueLayout
        catalogue={catalogue}
        hasSelection={!!route.userId}
        backLabel="All people"
        onBack={() => onNavigate(PEOPLE)}
      >
        {route.userId ? (
          <PersonDetail
            key={route.userId}
            userId={route.userId}
            onNavigate={onNavigate}
            onChanged={changed}
            onLink={(user, made) => setLink({ user, link: made, created: false })}
          />
        ) : (
          <div className="panel-state">Choose a person.</div>
        )}
      </CatalogueLayout>
      {creating && (
        <NewPersonDialog
          onClose={() => {
            setCreating(false);
            newButtonRef.current?.focus();
          }}
          onCreated={(user, made) => {
            setCreating(false);
            feed.reload();
            setCountToken((token) => token + 1);
            onNavigate({ ...PEOPLE, userId: user.id });
            if (made) setLink({ user, link: made, created: true });
          }}
        />
      )}
      {link && <PasswordLinkDialog {...link} onClose={() => setLink(undefined)} />}
    </SettingsLayout>
  );
}

/** The one-time password link, shown once (D272, D304). */
function PasswordLinkDialog({
  user,
  link,
  created,
  onClose,
}: {
  user: User;
  link: PasswordResetLink;
  created: boolean;
  onClose: () => void;
}) {
  return (
    <ShownOnceDialog
      title="Pass on the password link"
      eyebrow={created ? `${user.name} was created` : `Password link for ${user.name}`}
      label="Password link"
      value={link.url}
      confirmLabel="I have copied it"
      onClose={onClose}
    >
      {{
        before: (
          <p>
            {user.name} sets a password with this link. Pass it on yourself, for example in a chat: the engine sends no
            e-mail, and the link is not shown again.
          </p>
        ),
        after: (
          <p className="admin-hint">
            Works once, until {formatServerTime(link.expiresAt)}. A newer link replaces this one, and using it signs{" "}
            {user.name} out everywhere.
            {created && user.roles.length === 0 && ` ${user.name} has no roles yet: grant one on their page.`}
          </p>
        ),
      }}
    </ShownOnceDialog>
  );
}

// What a person's fields must be, said where the engine refused one (`422`, by field).
const PERSON_FIELDS: Record<string, string> = {
  username: "A username has no spaces and at most 150 characters. Use a dot, dash or underscore instead, as in user.1.",
  name: "A name has 1 to 200 characters.",
  email: "An e-mail address looks like name@example.org.",
};

/** The message under each field the engine refused, in the words above; others as it said them. */
function refusedFields(cause: unknown): Record<string, string> {
  const fields = invalidFields(cause);
  return Object.fromEntries(Object.keys(fields).map((key) => [key, PERSON_FIELDS[key] ?? fields[key]]));
}

function NewPersonDialog({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (user: User, link: PasswordResetLink | undefined) => void;
}) {
  const [username, setUsername] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [refused, setRefused] = useState<Record<string, string>>({});
  // A space is refused by the engine; said as it is typed, before anything is sent.
  const usernameProblem = /\s/.test(username) ? PERSON_FIELDS.username : refused.username;

  async function create() {
    setPending(true);
    setError("");
    setRefused({});
    let user: User;
    try {
      user = await security.createUser({
        username: username.trim(),
        name: name.trim(),
        ...(email.trim() ? { email: email.trim() } : {}),
      });
    } catch (cause) {
      const fields = refusedFields(cause);
      setRefused(fields);
      if (!Object.keys(fields).length) setError(errorMessage(cause));
      setPending(false);
      return;
    }
    // The person exists now; a link that fails is made again from their page.
    const link = await security.passwordLink(user.id).catch(() => undefined);
    setPending(false);
    onCreated(user, link);
  }

  return (
    <Modal
      title="New person"
      eyebrow="Security"
      size="compact"
      busy={pending}
      dirty={!!(username || name || email)}
      onClose={onClose}
    >
      <form
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          void create();
        }}
      >
        <FormField
          label="Username"
          help="What they type to sign in, without spaces; it cannot change later."
          error={usernameProblem}
        >
          {(control) => (
            <input
              {...control}
              autoFocus
              required
              maxLength={150}
              autoComplete="off"
              value={username}
              onChange={(event) => {
                setUsername(event.target.value);
                setRefused(({ username: _, ...rest }) => rest);
              }}
            />
          )}
        </FormField>
        <FormField label="Name" error={refused.name}>
          {(control) => (
            <input
              {...control}
              required
              maxLength={200}
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          )}
        </FormField>
        <FormField label="E-mail (optional)" error={refused.email}>
          {(control) => (
            <input
              {...control}
              type="email"
              maxLength={320}
              value={email}
              onChange={(event) => {
                setEmail(event.target.value);
                setRefused(({ email: _, ...rest }) => rest);
              }}
            />
          )}
        </FormField>
        {error && (
          <Notice tone="error" title="The person was not created">
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" disabled={pending} onClick={onClose}>
            Cancel
          </button>
          <button className="primary" disabled={pending || !username.trim() || !name.trim() || /\s/.test(username)}>
            {pending ? "Creating…" : "Create and make a password link"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function PersonDetail({
  userId,
  onNavigate,
  onChanged,
  onLink,
}: {
  userId: string;
  onNavigate: (route: RouteState) => void;
  onChanged: (user: User) => void;
  onLink: (user: User, link: PasswordResetLink) => void;
}) {
  const [user, setUser] = useState<User>();
  const [loadError, setLoadError] = useState("");
  const [loadToken, setLoadToken] = useState(0);
  const [editing, setEditing] = useState(false);
  const [confirming, setConfirming] = useState<"deactivate" | "sign-out">();
  const [pending, setPending] = useState(false);
  const [actionError, setActionError] = useState("");
  const [conflict, setConflict] = useState("");
  const editRef = useRef<HTMLButtonElement>(null);
  const toast = useToast();

  useEffect(() => {
    let current = true;
    security.user(userId).then(
      (loaded) => {
        if (!current) return;
        setUser(loaded);
        setLoadError("");
      },
      (cause) => current && setLoadError(errorMessage(cause)),
    );
    return () => {
      current = false;
    };
  }, [userId, loadToken]);

  function stored(updated: User, text: string) {
    setUser(updated);
    onChanged(updated);
    toast(text);
  }

  /** A write; a stale version reloads and says so, any other refusal is shown as worded. */
  async function write(action: () => Promise<void>) {
    setPending(true);
    setActionError("");
    setConflict("");
    try {
      await action();
      setConfirming(undefined);
    } catch (cause) {
      if (isApiError(cause, "VERSION_CONFLICT")) {
        setConfirming(undefined);
        const current = await security.user(userId).catch(() => undefined);
        if (current) setUser(current);
        setConflict("This person changed while the page was open. They are shown as they are now; choose again.");
      } else {
        setActionError(errorMessage(cause));
      }
    } finally {
      setPending(false);
    }
  }

  if (loadError) return <InlineError message={loadError} onRetry={() => setLoadToken((token) => token + 1)} />;
  if (!user) return <div className="panel-state">Loading person…</div>;

  const signedIn = !user.hasPassword
    ? "Has not set a password yet"
    : user.lastSignInAt
      ? `Last signed in ${formatServerTime(user.lastSignInAt)}`
      : "Never signed in";

  return (
    <div className="model-editor-stack security-detail">
      <header className="model-detail-header security-person-header">
        <span className="account-profile-avatar" aria-hidden="true">
          {initials(user.name)}
        </span>
        <div>
          <p className="eyebrow">Person</p>
          <h2>{user.name}</h2>
          <p>
            {user.username}
            {user.email && ` · ${user.email}`}
          </p>
          <div className="security-pills">
            {user.active ? (
              <StatusPill tone="success">Active</StatusPill>
            ) : (
              <StatusPill tone="neutral">Deactivated</StatusPill>
            )}
            <StatusPill tone={user.hasPassword ? "neutral" : "warning"} marker={false}>
              {signedIn}
            </StatusPill>
          </div>
        </div>
      </header>
      {conflict && (
        <Notice tone="warning" title="Not saved" focusOnMount>
          {conflict}
        </Notice>
      )}
      {actionError && !confirming && (
        <Notice tone="error" title="The action could not be completed">
          {actionError}
        </Notice>
      )}
      <div className="model-actions">
        <button ref={editRef} className="secondary" disabled={pending} onClick={() => setEditing(true)}>
          Edit…
        </button>
        {user.active && (
          <button
            className="secondary"
            disabled={pending}
            onClick={() => void write(async () => onLink(user, await security.passwordLink(user.id)))}
          >
            {user.hasPassword ? "Reset password" : "Make a password link"}
          </button>
        )}
        {user.active && (
          <button className="secondary" disabled={pending} onClick={() => setConfirming("sign-out")}>
            Sign out everywhere
          </button>
        )}
        {user.active ? (
          <button className="danger-ghost" disabled={pending} onClick={() => setConfirming("deactivate")}>
            Deactivate
          </button>
        ) : (
          <button
            className="secondary"
            disabled={pending}
            onClick={() =>
              void write(async () =>
                stored(
                  await security.updateUser(user.id, { expectedVersion: user.version, active: true }),
                  `${user.name} was restored and can sign in again.`,
                ),
              )
            }
          >
            Restore
          </button>
        )}
      </div>
      <GrantsSection
        subject={{ principal: { kind: "user", id: user.id, name: user.name } }}
        load={(cursor) => security.userGrants(user.id, cursor)}
        deps={[user.id]}
        onNavigate={onNavigate}
      />
      <PersonGroups user={user} onNavigate={onNavigate} />
      {editing && (
        <EditPersonDialog
          user={user}
          onClose={() => {
            setEditing(false);
            editRef.current?.focus();
          }}
          onSaved={(updated) => {
            setEditing(false);
            stored(updated, "Saved.");
          }}
          onConflict={(current) => {
            setUser(current);
            onChanged(current);
          }}
        />
      )}
      {confirming === "deactivate" && (
        <ConfirmDialog
          title={`Deactivate ${user.name}?`}
          confirmLabel="Deactivate"
          pending={pending}
          error={actionError}
          onCancel={() => {
            setConfirming(undefined);
            setActionError("");
          }}
          onConfirm={() =>
            void write(async () =>
              stored(
                await security.updateUser(user.id, { expectedVersion: user.version, active: false }),
                `${user.name} was deactivated and signed out everywhere.`,
              ),
            )
          }
        >
          <p>
            {user.name} is signed out everywhere and can no longer sign in. Their roles and groups stay, and history
            keeps their name. You can restore them later.
          </p>
        </ConfirmDialog>
      )}
      {confirming === "sign-out" && (
        <ConfirmDialog
          title={`Sign ${user.name} out everywhere?`}
          confirmLabel="Sign out everywhere"
          pending={pending}
          error={actionError}
          onCancel={() => {
            setConfirming(undefined);
            setActionError("");
          }}
          onConfirm={() =>
            void write(async () => {
              await security.signOutEverywhere(user.id);
              toast(`${user.name} was signed out everywhere.`);
            })
          }
        >
          <p>Every browser where {user.name} is signed in is signed out at its next request. They can sign in again.</p>
        </ConfirmDialog>
      )}
    </div>
  );
}

function EditPersonDialog({
  user,
  onClose,
  onSaved,
  onConflict,
}: {
  user: User;
  onClose: () => void;
  onSaved: (user: User) => void;
  onConflict: (current: User) => void;
}) {
  const [name, setName] = useState(user.name);
  const [email, setEmail] = useState(user.email ?? "");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [conflict, setConflict] = useState("");
  const [refused, setRefused] = useState<Record<string, string>>({});
  const changed = name.trim() !== user.name || email.trim() !== (user.email ?? "");

  async function save() {
    setPending(true);
    setError("");
    setConflict("");
    setRefused({});
    try {
      onSaved(
        await security.updateUser(user.id, {
          expectedVersion: user.version,
          name: name.trim(),
          email: email.trim() || null,
        }),
      );
    } catch (cause) {
      if (isApiError(cause, "VERSION_CONFLICT")) {
        const current = await security.user(user.id).catch(() => undefined);
        if (current) onConflict(current);
        setConflict(
          "Someone changed this person while you were editing. Save again to replace their change with yours.",
        );
      } else {
        setError(errorMessage(cause));
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <Modal title={`Edit ${user.name}`} eyebrow="Person" size="compact" busy={pending} dirty={changed} onClose={onClose}>
      <form
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        <FormField label="Name" error={refused.name}>
          {(control) => (
            <input
              {...control}
              autoFocus
              required
              maxLength={200}
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          )}
        </FormField>
        <FormField label="E-mail (optional)" error={refused.email}>
          {(control) => (
            <input
              {...control}
              type="email"
              maxLength={320}
              value={email}
              onChange={(event) => {
                setEmail(event.target.value);
                setRefused(({ email: _, ...rest }) => rest);
              }}
            />
          )}
        </FormField>
        <p className="admin-hint">The username {user.username} does not change.</p>
        {conflict && (
          <Notice tone="warning" title="Not saved">
            {conflict}
          </Notice>
        )}
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
            {pending ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

/** The person's groups, each linked, with Remove and "Add to a group" (D300). */
function PersonGroups({ user, onNavigate }: { user: User; onNavigate: (route: RouteState) => void }) {
  const feed = useCursorFeed((cursor) => security.groups({ memberId: user.id, cursor, pageSize: 100 }), [user.id]);
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState("");
  const addRef = useRef<HTMLButtonElement>(null);
  const toast = useToast();

  async function remove(group: Group) {
    setError("");
    try {
      await security.removeMember(group.id, user.id);
      feed.setItems((items) => items.filter((item) => item.id !== group.id));
      toast(`${user.name} left ${group.name}. The group's roles no longer apply to them.`);
    } catch (cause) {
      setError(errorMessage(cause));
    }
  }

  return (
    <Section
      title="Groups"
      actions={
        <button ref={addRef} type="button" className="secondary" onClick={() => setAdding(true)}>
          <Icon name="plus" /> Add to a group
        </button>
      }
    >
      {error && (
        <Notice tone="error" title="Not removed from the group">
          {error}
        </Notice>
      )}
      {feed.error ? (
        <InlineError message={feed.error} onRetry={feed.retry} />
      ) : !feed.items.length ? (
        <p className="admin-hint">{feed.loading ? "Loading groups…" : "Not in any group."}</p>
      ) : (
        <ul className="security-chips" aria-label={`${user.name}'s groups`}>
          {feed.items.map((group) => {
            const route: SettingsRoute = { kind: "settings", page: "groups", groupId: group.id };
            return (
              <li key={group.id} className="security-chip">
                <RouteLink href={routePath(route)} onNavigate={() => onNavigate(route)}>
                  {group.name}
                </RouteLink>
                <button type="button" aria-label={`Remove from ${group.name}`} onClick={() => void remove(group)}>
                  <Icon name="close" size={13} />
                </button>
              </li>
            );
          })}
        </ul>
      )}
      {adding && (
        <PickDialog
          title={`Add ${user.name} to a group`}
          label="Group"
          kinds={["group"]}
          confirmLabel="Add to the group"
          onClose={() => {
            setAdding(false);
            addRef.current?.focus();
          }}
          onPicked={async (group) => {
            await security.addMember(group.id, user.id);
            setAdding(false);
            feed.reload();
            toast(`${user.name} is now in ${group.name}.`);
            addRef.current?.focus();
          }}
        />
      )}
    </Section>
  );
}
