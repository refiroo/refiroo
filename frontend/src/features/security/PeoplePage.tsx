/**
 * Settings › Security › People (0.12 SP1, U8; 0.17 ST1): the people of the instance as a full-width list,
 * searched by name or e-mail, active or deactivated, each with the roles they hold (D298); a row opens the
 * person as a page of its own (PP-D61). A person's page edits their name and e-mail, makes a
 * one-time password link shown once (D304), signs them out everywhere, deactivates or restores them
 * (never deletes, D237), lists their roles directly and through groups (D299) and their groups.
 * Every write carries the version read; the engine's refusals are shown as it words them.
 */

import { useEffect, useRef, useState } from "react";
import { errorMessage, invalidFields, isApiError, isVersionConflict } from "@/api/errors";
import { mail } from "@/api/mailClient";
import { security } from "@/api/securityClient";
import { plural } from "@/lib/count";
import { formatServerDayTime, formatServerTime } from "@/lib/dates";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import { routePath } from "@/routing/routes";
import type { Hue } from "@/model/hues";
import type {
  Group,
  Passkey,
  PasswordResetLink,
  RouteState,
  SettingsRoute,
  SignInProviderRef,
  User,
  UserRole,
} from "@/types";
import { ActionMenu, type ActionMenuItem } from "@/ui/ActionMenu";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { EntityList } from "@/ui/EntityList";
import { FormField } from "@/ui/FormField";
import { Icon } from "@/ui/Icon";
import { InlineError } from "@/ui/InlineError";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { RouteLink } from "@/ui/RouteLink";
import { SearchField } from "@/ui/SearchField";
import { SettingsLayout } from "@/ui/SettingsLayout";
import {
  FilterChip,
  hueOf,
  ItemHeader,
  NameMark,
  SettingRow,
  SettingsEmpty,
  SettingsGroup,
  SettingsPanel,
  SettingsTile,
  SettingsTools,
} from "@/ui/SettingsParts";
import { ShownOnceDialog } from "@/ui/ShownOnceDialog";
import { Skeleton } from "@/ui/Skeleton";
import { StatusPill } from "@/ui/StatusPill";
import { Switch } from "@/ui/Switch";
import { useToast } from "@/ui/Toast";
import { Trail } from "@/ui/Trail";
import { readsChanges } from "@/ui/changeText";
import { settingsHead } from "@/ui/settingsNavigation";
import { GrantsSection } from "./GrantsSection";
import { useHeldAnywhere } from "@/state/permissions";
import { PickDialog } from "./PickDialog";
import { RecentActivity } from "./RecentActivity";
import { PrincipalPicker, type PickedPrincipal } from "./PrincipalPicker";
import { RoleKeyChip } from "./RoleChip";
import { identityNames, linkSentence, unlinkSentence, personSignInLine } from "./securityText";

type PeopleRoute = Extract<SettingsRoute, { page: "people" }>;

const PEOPLE: PeopleRoute = { kind: "settings", page: "people" };

/**
 * A new one-time link, shown to the administrator to pass on. With `send` it is also mailed to the
 * person (SP3, D418); mail that turned out not to be possible leaves the link to pass on by hand.
 */
async function makeLink(user: Pick<User, "id" | "email">, send = false): Promise<PasswordResetLink> {
  if (!send || !user.email) return security.passwordLink(user.id);
  try {
    return await security.passwordLink(user.id, true);
  } catch (cause) {
    if (isApiError(cause, "MAIL_NOT_SET_UP") || isApiError(cause, "NO_EMAIL")) return security.passwordLink(user.id);
    throw cause;
  }
}

/** People read in a page of this size. */
const LIST_PAGE = 50;

/** Where a role applies, for the chip's tooltip. */
const roleWhere = (role: UserRole) =>
  role.instance ? "Every workspace" : role.workspaces.map((workspace) => workspace.label).join(", ");

/** A person's roles in the list: a few coloured chips, then how many more. */
function RoleChips({ roles }: { roles: readonly UserRole[] }) {
  if (!roles.length) return <span className="muted">No roles yet</span>;
  const shown = roles.slice(0, 2);
  return (
    <>
      {shown.map((role) => (
        <RoleKeyChip key={role.key} roleKey={role.key} title={roleWhere(role)}>
          {role.name}
        </RoleKeyChip>
      ))}
      {roles.length > shown.length && <span className="entity-more">{roles.length - shown.length} more</span>}
    </>
  );
}

export function PeoplePage({ route, onNavigate }: { route: PeopleRoute; onNavigate: (route: RouteState) => void }) {
  const [creating, setCreating] = useState(false);
  const [link, setLink] = useState<{ user: User; link: PasswordResetLink; created: boolean }>();
  const newButtonRef = useRef<HTMLButtonElement>(null);
  // While local sign-in is off, a new person or a password is of no use (I3, D365).
  const [localOn, setLocalOn] = useState(true);
  // With the requirement on, a person without a second factor sets one up at their next sign-in (I4b).
  const [required, setRequired] = useState(false);
  // With mail set up, a link is also sent to a person who has an address (SP3).
  const [mailReady, setMailReady] = useState(false);

  useEffect(() => {
    let current = true;
    mail.settings().then(
      (settings) => current && setMailReady(settings.configured),
      () => undefined,
    );
    security.localSignIn().then(
      (local) => {
        if (!current) return;
        setLocalOn(local.enabled);
        setRequired(local.secondFactorRequired);
      },
      () => undefined,
    );
    return () => {
      current = false;
    };
  }, []);

  return (
    <>
      {route.userId ? (
        <PersonDetail
          key={route.userId}
          userId={route.userId}
          localOn={localOn}
          required={required}
          onNavigate={onNavigate}
          onLink={(user, made) => setLink({ user, link: made, created: false })}
          onLinked={(target) => onNavigate({ ...PEOPLE, userId: target.id })}
        />
      ) : (
        <PeopleList
          localOn={localOn}
          newButtonRef={newButtonRef}
          onNew={() => setCreating(true)}
          onNavigate={onNavigate}
        />
      )}
      {creating && (
        <NewPersonDialog
          onClose={() => {
            setCreating(false);
            newButtonRef.current?.focus();
          }}
          onCreated={(user, made) => {
            setCreating(false);
            onNavigate({ ...PEOPLE, userId: user.id });
            if (made) setLink({ user, link: made, created: true });
          }}
        />
      )}
      {link && <PasswordLinkDialog {...link} mailReady={mailReady} onClose={() => setLink(undefined)} />}
    </>
  );
}

/** The list a person is chosen from: search, Active or Deactivated with their counts, and the rows. */
function PeopleList({
  localOn,
  newButtonRef,
  onNew,
  onNavigate,
}: {
  localOn: boolean;
  newButtonRef: React.RefObject<HTMLButtonElement | null>;
  onNew: () => void;
  onNavigate: (route: RouteState) => void;
}) {
  const [search, setSearch] = useState("");
  const [active, setActive] = useState(true);
  const [counts, setCounts] = useState<{ active?: number; deactivated?: number }>({});
  const q = useDebouncedValue(search.trim());
  const feed = useCursorFeed<User>((cursor) => security.users({ q, active, cursor, pageSize: LIST_PAGE }), [q, active]);

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
  }, []);

  const total = q ? undefined : active ? counts.active : counts.deactivated;
  const shown = feed.items.length;
  const count = total ?? shown;
  return (
    <SettingsLayout
      {...settingsHead("people")}
      title="People"
      description="The people who sign in, the roles they hold and the groups they are in. A person is deactivated, never deleted, so their history keeps their name."
      actions={
        localOn && (
          <button ref={newButtonRef} className="primary" onClick={onNew}>
            <Icon name="plus" /> New person
          </button>
        )
      }
    >
      <SettingsTools
        count={
          feed.loading && !shown
            ? undefined
            : `${count}${total === undefined && feed.hasMore ? "+" : ""} ${plural(count, "person", "people")}`
        }
      >
        <SearchField
          label="Search people"
          placeholder="Name or e-mail"
          value={search}
          onChange={setSearch}
          clearOnEscape
        />
        <span className="filter-chips" role="group" aria-label="Show">
          <FilterChip selected={active} onSelect={() => setActive(true)}>
            Active{counts.active !== undefined && ` · ${counts.active}`}
          </FilterChip>
          <FilterChip selected={!active} onSelect={() => setActive(false)}>
            Deactivated{counts.deactivated !== undefined && ` · ${counts.deactivated}`}
          </FilterChip>
        </span>
      </SettingsTools>
      <SettingsPanel>
        <EntityList
          label="people"
          statusTrack="0px"
          groups={[
            {
              key: "people",
              title: active ? "Active people" : "Deactivated people",
              count,
              loading: feed.loading && !shown,
              error: feed.error && !shown ? feed.error : undefined,
              onRetry: feed.retry,
              onEnd: feed.hasMore ? feed.loadMore : undefined,
              loadingMore: feed.loading && shown > 0,
              rows: feed.items.map((user) => ({
                key: user.id,
                title: user.name,
                subtitle: user.email ?? "No e-mail address",
                lead: <NameMark name={user.name} />,
                facts: [
                  { label: "Roles", value: <RoleChips roles={user.roles} />, width: 38 },
                  {
                    label: "Last signed in",
                    value: user.lastSignInAt ? formatServerDayTime(user.lastSignInAt) : "Never",
                  },
                ],
                onOpen: () => onNavigate({ ...PEOPLE, userId: user.id }),
              })),
            },
          ]}
          empty={
            q
              ? `No ${active ? "active" : "deactivated"} person matches “${q}”.`
              : `No ${active ? "active" : "deactivated"} people.`
          }
        />
      </SettingsPanel>
    </SettingsLayout>
  );
}

/** The one-time password link, shown once (D272, D304). */
function PasswordLinkDialog({
  user,
  link: first,
  created,
  mailReady,
  onClose,
}: {
  user: User;
  link: PasswordResetLink;
  created: boolean;
  mailReady: boolean;
  onClose: () => void;
}) {
  // Mailing makes a newer link (the engine keeps only a link's digest, so this one cannot be sent
  // as it is); it replaces this one and is shown here in its place.
  const [link, setLink] = useState(first);
  const [mailing, setMailing] = useState(false);
  const [failure, setFailure] = useState("");
  async function mailIt() {
    setMailing(true);
    setFailure("");
    try {
      setLink(await security.passwordLink(user.id, true));
    } catch (cause) {
      setFailure(errorMessage(cause));
    } finally {
      setMailing(false);
    }
  }
  return (
    <ShownOnceDialog
      title="Pass on the password link"
      eyebrow={created ? `${user.name} was created` : `Password link for ${user.name}`}
      label="Password link"
      value={link.url}
      confirmLabel="I have copied it"
      onClose={onClose}
      actions={
        mailReady && user.email && !link.sentTo ? (
          <button type="button" className="secondary" disabled={mailing} onClick={() => void mailIt()}>
            {mailing ? "Mailing…" : `Mail it to ${user.email}`}
          </button>
        ) : undefined
      }
    >
      {{
        before: link.sentTo ? (
          <p>
            The link was mailed to {link.sentTo}. It is shown here once more, in case the mail does not arrive: you can
            pass it on yourself, and it is not shown again.
          </p>
        ) : (
          <p>
            {user.name} sets a password with this link. Pass it on yourself, for example in a chat
            {user.email ? "" : " (the person has no e-mail address)"}: the link is not shown again.
            {user.email && !mailReady && " To have it mailed to the person, set up Mail under Settings › Integration."}
          </p>
        ),
        after: (
          <>
            {failure && <Notice tone="error">{failure}</Notice>}
            <p className="admin-hint">
              Works once, until {formatServerTime(link.expiresAt)}. A newer link replaces this one, and using it signs{" "}
              {user.name} out everywhere.
              {created && user.roles.length === 0 && ` ${user.name} has no roles yet: grant one on their page.`}
            </p>
          </>
        ),
      }}
    </ShownOnceDialog>
  );
}

// What a person's fields must be, said where the engine refused one (`422`, by field).
const PERSON_FIELDS: Record<string, string> = {
  name: "A name has 1 to 200 characters.",
  email: "An e-mail address looks like name@example.org.",
};

/** The message under each field the engine refused, in the words above; others as it said them. */
function refusedFields(cause: unknown): Record<string, string> {
  const fields = invalidFields(cause);
  return Object.fromEntries(Object.keys(fields).map((key) => [key, PERSON_FIELDS[key] ?? fields[key]]));
}

/** The person form's one checkbox: an administrator keeps the person's own credentials (0.17 SA1). */
function SignInManagedField({ checked, onChange }: { checked: boolean; onChange: (checked: boolean) => void }) {
  return (
    <label className="checkbox">
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      <span>
        An administrator manages this person’s sign-in
        <small>
          They cannot change their own password, second factor or passkeys, or sign out their other browsers. An
          administrator still sets their password with a link.
        </small>
      </span>
    </label>
  );
}

function NewPersonDialog({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (user: User, link: PasswordResetLink | undefined) => void;
}) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [managed, setManaged] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [refused, setRefused] = useState<Record<string, string>>({});

  async function create() {
    setPending(true);
    setError("");
    setRefused({});
    let user: User;
    try {
      user = await security.createUser({
        name: name.trim(),
        email: email.trim(),
        ...(managed ? { signInManaged: true } : {}),
      });
    } catch (cause) {
      const fields = refusedFields(cause);
      setRefused(fields);
      if (!Object.keys(fields).length) setError(errorMessage(cause));
      setPending(false);
      return;
    }
    // The person exists now; a link that fails is made again from their page.
    const link = await makeLink(user).catch(() => undefined);
    setPending(false);
    onCreated(user, link);
  }

  return (
    <Modal
      title="New person"
      eyebrow="People and access"
      size="compact"
      busy={pending}
      dirty={!!(name || email || managed)}
      onClose={onClose}
    >
      <form
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          void create();
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
        <FormField
          label="E-mail"
          help="What they type to sign in. Another person cannot have the same address."
          error={refused.email}
        >
          {(control) => (
            <input
              {...control}
              type="email"
              required
              autoComplete="off"
              maxLength={320}
              value={email}
              onChange={(event) => {
                setEmail(event.target.value);
                setRefused(({ email: _, ...rest }) => rest);
              }}
            />
          )}
        </FormField>
        <SignInManagedField checked={managed} onChange={setManaged} />
        {error && (
          <Notice tone="error" title="The person was not created">
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" disabled={pending} onClick={onClose}>
            Cancel
          </button>
          <button className="primary" disabled={pending || !email.trim() || !name.trim()}>
            {pending ? "Adding…" : "Add person"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function PersonDetail({
  userId,
  localOn,
  required,
  onNavigate,
  onLink,
  onLinked,
}: {
  userId: string;
  localOn: boolean;
  required: boolean;
  onNavigate: (route: RouteState) => void;
  onLink: (user: User, link: PasswordResetLink) => void;
  onLinked: (target: User) => void;
}) {
  const [user, setUser] = useState<User>();
  const [loadError, setLoadError] = useState("");
  const [loadToken, setLoadToken] = useState(0);
  const [editing, setEditing] = useState<false | "edit" | "restore">(false);
  const [confirming, setConfirming] = useState<"deactivate" | "sign-out" | "keep" | "remove-factor">();
  const [linking, setLinking] = useState(false);
  const [unlinking, setUnlinking] = useState<SignInProviderRef>();
  const [pending, setPending] = useState(false);
  const [actionError, setActionError] = useState("");
  const [conflict, setConflict] = useState("");
  const editRef = useRef<HTMLButtonElement>(null);
  const toast = useToast();
  const held = useHeldAnywhere();
  const head = settingsHead("people");

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

  function stored(updated: User, text: string, undo?: () => Promise<void>) {
    setUser(updated);
    toast(
      text,
      undo
        ? {
            actions: [
              {
                label: "Undo",
                onPress: () => void write(undo),
              },
            ],
          }
        : undefined,
    );
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
      if (isVersionConflict(cause, ["VERSION_CONFLICT"])) {
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

  const trail = <Trail back={{ label: "People", onClick: () => onNavigate(PEOPLE), href: routePath(PEOPLE) }} />;
  if (loadError)
    return (
      <SettingsLayout trail={trail} title="Person">
        <InlineError message={loadError} onRetry={() => setLoadToken((token) => token + 1)} />
      </SettingsLayout>
    );
  if (!user)
    return (
      <SettingsLayout trail={trail} title="Person">
        <Skeleton label="Loading person" lines={4} />
      </SettingsLayout>
    );

  // What they changed in the workspaces this administrator reads (0.12 Z6, D345).
  const changes: RouteState = { kind: "changes", actorId: user.id, actorName: user.name };
  const signedIn = personSignInLine(user);
  const passwords = user.localKept || localOn;
  const canLink = user.active && user.identities.length > 0 && !user.hasPassword;
  const makePassword = user.active && passwords;

  function restore(person: User) {
    // An active person signs in with an e-mail address, so one without is asked for it first.
    if (!person.email) return setEditing("restore");
    void write(async () =>
      stored(
        await security.updateUser(person.id, { expectedVersion: person.version, active: true }),
        `${person.name} was restored and can sign in again.`,
      ),
    );
  }

  // Two actions show; the rest are in the ⋯ menu, what cannot be undone last (PP-D63).
  const menu: ActionMenuItem[] = [
    ...(readsChanges(held)
      ? [{ id: "changes", label: "See changes", onAction: () => onNavigate(changes) } satisfies ActionMenuItem]
      : []),
    ...(canLink
      ? [
          {
            id: "link",
            label: "Link to an existing person…",
            description:
              "If this person already has an account of their own, link this sign-in to it: they keep their roles and history.",
            disabled: pending,
            onAction: () => setLinking(true),
          } satisfies ActionMenuItem,
        ]
      : []),
    ...(user.active
      ? [
          {
            id: "sign-out",
            label: "Sign out everywhere",
            disabled: pending,
            onAction: () => setConfirming("sign-out"),
          } satisfies ActionMenuItem,
          {
            id: "deactivate",
            label: "Deactivate",
            tone: "danger",
            disabled: pending,
            onAction: () => setConfirming("deactivate"),
          } satisfies ActionMenuItem,
        ]
      : []),
  ];

  const actions = (
    <>
      {makePassword && (
        <button
          className="secondary"
          disabled={pending}
          onClick={() => void write(async () => onLink(user, await makeLink(user)))}
        >
          {user.hasPassword ? "Reset password" : "Make a password link"}
        </button>
      )}
      <button ref={editRef} className="secondary" disabled={pending} onClick={() => setEditing("edit")}>
        Edit…
      </button>
      {!user.active && (
        <button className="secondary" disabled={pending} onClick={() => restore(user)}>
          Restore
        </button>
      )}
      {menu.length > 0 && <ActionMenu label="More actions" items={menu} />}
    </>
  );

  return (
    <SettingsLayout
      trail={trail}
      header={
        <ItemHeader
          hue={hueOf(user.name)}
          lead={<NameMark name={user.name} size={64} />}
          title={<h1>{user.name}</h1>}
          meta={
            <>
              <span>{user.email ?? "No e-mail address"}</span>
              {user.active ? (
                <StatusPill tone="success">Active</StatusPill>
              ) : (
                <StatusPill tone="neutral">Deactivated</StatusPill>
              )}
              <span title={user.lastSignInAt ? formatServerTime(user.lastSignInAt) : undefined}>
                <StatusPill tone={user.hasPassword || user.identities.length ? "neutral" : "warning"} marker={false}>
                  {signedIn}
                </StatusPill>
              </span>
            </>
          }
          actions={actions}
        />
      }
    >
      {conflict && (
        <Notice tone="warning" title="Not saved" focusOnMount>
          {conflict}
        </Notice>
      )}
      {actionError && !confirming && !unlinking && (
        <Notice tone="error" title="The action could not be completed">
          {actionError}
        </Notice>
      )}
      <SettingsGroup
        title="Sign-in"
        description="How this person proves who they are. Their own choices are on their Account page."
      >
        <SettingsPanel label={`How ${user.name} signs in`}>
          {user.identities.map((identity) => (
            <SettingRow
              key={identity.provider.key}
              lead={<SettingsTile icon="link" hue={head.hue} />}
              name={identity.provider.name}
              help={`Subject ${identity.subject}`}
            >
              <button className="secondary" disabled={pending} onClick={() => setUnlinking(identity.provider)}>
                Unlink…
              </button>
            </SettingRow>
          ))}
          {(user.hasPassword || !user.identities.length) && (
            <SettingRow lead={<SettingsTile icon="lock" hue={head.hue} />} name="Password">
              <span className="muted">{user.hasPassword ? "Set" : "Not set yet"}</span>
            </SettingRow>
          )}
          {user.secondFactor && (
            <SettingRow
              lead={<SettingsTile icon="shield" hue={head.hue} />}
              name="Second factor: authenticator app"
              help={`Set up ${formatServerTime(user.secondFactor.confirmedAt)} · ${user.secondFactor.recoveryCodesLeft} of 10 recovery codes left`}
            >
              <button className="danger-ghost" disabled={pending} onClick={() => setConfirming("remove-factor")}>
                Remove second factor…
              </button>
            </SettingRow>
          )}
          {user.passkeys > 0 && (
            <PersonPasskeys
              user={user}
              hue={head.hue}
              onRemoved={(updated) => stored(updated, "The passkey was removed.")}
            />
          )}
          <SettingRow
            keep
            lead={<SettingsTile icon="key" hue={head.hue} />}
            name="Keeps local sign-in"
            help={
              localOn
                ? "Signs in with a password even while local sign-in is off: the way back if the provider fails"
                : "Local sign-in is off: only people who keep it sign in with a password"
            }
          >
            <Switch
              label="Keeps local sign-in"
              checked={user.localKept}
              disabled={pending || !user.active}
              onChange={() =>
                // Turning it off takes the password way in away, so that asks first; turning it on only gives.
                user.localKept
                  ? setConfirming("keep")
                  : void write(async () => {
                      const kept = await security.updateUser(user.id, {
                        expectedVersion: user.version,
                        localKept: true,
                      });
                      stored(kept, `${user.name} keeps local sign-in.`, async () =>
                        stored(
                          await security.updateUser(kept.id, { expectedVersion: kept.version, localKept: false }),
                          `${user.name} no longer keeps local sign-in.`,
                        ),
                      );
                    })
              }
            />
          </SettingRow>
        </SettingsPanel>
      </SettingsGroup>
      <GrantsSection
        subject={{ principal: { kind: "user", id: user.id, name: user.name } }}
        description="What this person may do, and where. A role held through a group is changed on the group."
        load={(cursor) => security.userGrants(user.id, cursor)}
        deps={[user.id]}
        onNavigate={onNavigate}
        hue={head.hue}
      />
      <PersonGroups user={user} hue={head.hue} onNavigate={onNavigate} />
      <RecentActivity principal={user} />
      {editing && (
        <EditPersonDialog
          user={user}
          restoring={editing === "restore"}
          onClose={() => {
            setEditing(false);
            editRef.current?.focus();
          }}
          onSaved={(updated) => {
            setEditing(false);
            stored(updated, editing === "restore" ? `${updated.name} was restored and can sign in again.` : "Saved.");
          }}
          onConflict={(current) => {
            setUser(current);
          }}
        />
      )}
      {linking && (
        <LinkIdentityDialog
          user={user}
          onClose={() => {
            setLinking(false);
          }}
          onLinked={(target) => {
            setLinking(false);
            toast(`${target.name} now signs in with ${identityNames(target)}; ${user.name} was deactivated.`);
            onLinked(target);
          }}
        />
      )}
      {unlinking && (
        <ConfirmDialog
          title={`Unlink ${unlinking.name}?`}
          confirmLabel="Unlink"
          pending={pending}
          error={actionError}
          onCancel={() => {
            setUnlinking(undefined);
            setActionError("");
          }}
          onConfirm={() =>
            void write(async () => {
              await security.unlinkIdentity(user.id, unlinking.key);
              stored(await security.user(user.id), `${user.name} no longer signs in with ${unlinking.name}.`);
              setUnlinking(undefined);
            })
          }
        >
          <p>{unlinkSentence(user.name, unlinking.name)}</p>
        </ConfirmDialog>
      )}
      {confirming === "remove-factor" && (
        <ConfirmDialog
          title={`Remove ${user.name}'s second factor?`}
          confirmLabel="Remove second factor"
          pending={pending}
          error={actionError}
          onCancel={() => {
            setConfirming(undefined);
            setActionError("");
          }}
          onConfirm={() =>
            void write(async () => {
              await security.removeSecondFactor(user.id);
              stored(await security.user(user.id), `${user.name}'s second factor was removed.`);
            })
          }
        >
          <p>
            {user.name} signs in with their password alone, and their recovery codes stop working.{" "}
            {required
              ? "The instance requires a second factor, so they set one up again at their next sign-in."
              : "They can set one up again on their Account page."}{" "}
            Use this when they lost the phone and the recovery codes; the change is recorded.
          </p>
        </ConfirmDialog>
      )}
      {confirming === "keep" && (
        <ConfirmDialog
          title={`${user.name} stops keeping local sign-in?`}
          confirmLabel="Stop keeping local sign-in"
          pending={pending}
          error={actionError}
          onCancel={() => {
            setConfirming(undefined);
            setActionError("");
          }}
          onConfirm={() =>
            void write(async () =>
              stored(
                await security.updateUser(user.id, { expectedVersion: user.version, localKept: false }),
                `${user.name} no longer keeps local sign-in.`,
              ),
            )
          }
        >
          <p>
            While local sign-in is off, {user.name} can no longer sign in with a password; they sign in with a provider.
            The last person who keeps it cannot stop.
          </p>
        </ConfirmDialog>
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
    </SettingsLayout>
  );
}

/** Pick the existing person a provider sign-in belongs to; their roles and history carry on (D377). */
function LinkIdentityDialog({
  user,
  onClose,
  onLinked,
}: {
  user: User;
  onClose: () => void;
  onLinked: (target: User) => void;
}) {
  const [picked, setPicked] = useState<PickedPrincipal>();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  async function link(target: PickedPrincipal) {
    setPending(true);
    setError("");
    try {
      const current = await security.user(target.id);
      onLinked(await security.linkIdentity(target.id, { expectedVersion: current.version, fromUserId: user.id }));
    } catch (cause) {
      setError(errorMessage(cause));
      setPending(false);
    }
  }

  return (
    <Modal
      title="Link this sign-in to an existing person"
      eyebrow="People and access"
      size="compact"
      busy={pending}
      onClose={onClose}
    >
      <form
        className="grant-form"
        onSubmit={(event) => {
          event.preventDefault();
          if (picked) void link(picked);
        }}
      >
        <PrincipalPicker label="Person" kinds={["user"]} exclude={user.id} onPick={setPicked} />
        {picked && <p>{linkSentence(user, picked.name)}</p>}
        {error && (
          <Notice tone="error" title="Not linked">
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" disabled={pending} onClick={onClose}>
            Cancel
          </button>
          <button className="primary" disabled={pending || !picked}>
            {pending ? "Linking…" : picked ? `Link to ${picked.name}` : "Link"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

/** A person's passkeys, one row each, with Remove for an administrator (I4c, D394). */
function PersonPasskeys({ user, hue, onRemoved }: { user: User; hue: Hue; onRemoved: (user: User) => void }) {
  const feed = useCursorFeed((cursor) => security.userPasskeys(user.id, cursor), [user.id, user.passkeys]);
  const [removing, setRemoving] = useState<Passkey>();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  async function remove(passkey: Passkey) {
    setPending(true);
    setError("");
    try {
      await security.removeUserPasskey(user.id, passkey.id);
      setRemoving(undefined);
      onRemoved(await security.user(user.id));
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }

  return (
    <>
      {feed.items.map((passkey) => (
        <SettingRow
          key={passkey.id}
          lead={<SettingsTile icon="key" hue={hue} />}
          name={`Passkey: ${passkey.name}`}
          help={`Added ${formatServerTime(passkey.createdAt)} · ${
            passkey.lastUsedAt ? `last used ${formatServerTime(passkey.lastUsedAt)}` : "not used yet"
          }`}
        >
          <button
            className="danger-ghost"
            aria-label={`Remove the passkey ${passkey.name}`}
            onClick={() => setRemoving(passkey)}
          >
            Remove passkey…
          </button>
        </SettingRow>
      ))}
      {removing && (
        <ConfirmDialog
          title={`Remove ${user.name}'s passkey ${removing.name}?`}
          confirmLabel="Remove passkey"
          pending={pending}
          error={error}
          onCancel={() => {
            setRemoving(undefined);
            setError("");
          }}
          onConfirm={() => void remove(removing)}
        >
          <p>
            {user.name} can no longer sign in with {removing.name}. Use this when they lost the device; the change is
            recorded.
          </p>
        </ConfirmDialog>
      )}
    </>
  );
}

function EditPersonDialog({
  user,
  restoring,
  onClose,
  onSaved,
  onConflict,
}: {
  user: User;
  /** A deactivated person is made active again with the address typed here. */
  restoring: boolean;
  onClose: () => void;
  onSaved: (user: User) => void;
  onConflict: (current: User) => void;
}) {
  const [name, setName] = useState(user.name);
  const [email, setEmail] = useState(user.email ?? "");
  const [managed, setManaged] = useState(user.signInManaged);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [conflict, setConflict] = useState("");
  const [refused, setRefused] = useState<Record<string, string>>({});
  const changed =
    restoring || name.trim() !== user.name || email.trim() !== (user.email ?? "") || managed !== user.signInManaged;

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
          ...(restoring ? { active: true } : {}),
          ...(managed !== user.signInManaged ? { signInManaged: managed } : {}),
        }),
      );
    } catch (cause) {
      if (isVersionConflict(cause, ["VERSION_CONFLICT"])) {
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
    <Modal
      title={`${restoring ? "Restore" : "Edit"} ${user.name}`}
      eyebrow="People and access"
      size="compact"
      busy={pending}
      dirty={changed}
      onClose={onClose}
    >
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
        <FormField
          label={user.active || restoring ? "E-mail" : "E-mail (optional)"}
          help={
            user.active || restoring
              ? "The name they sign in with. Another person cannot have the same address."
              : "A deactivated person may have none, which frees the address for someone else."
          }
          error={refused.email}
        >
          {(control) => (
            <input
              {...control}
              type="email"
              required={user.active || restoring}
              maxLength={320}
              value={email}
              onChange={(event) => {
                setEmail(event.target.value);
                setRefused(({ email: _, ...rest }) => rest);
              }}
            />
          )}
        </FormField>
        <SignInManagedField checked={managed} onChange={setManaged} />
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
            {pending ? "Saving…" : restoring ? "Restore" : "Save"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

/** The person's groups, each linked, with Remove and "Add to a group" (D300). */
function PersonGroups({ user, hue, onNavigate }: { user: User; hue: Hue; onNavigate: (route: RouteState) => void }) {
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
    <SettingsGroup
      title="Groups"
      description="A group gives its roles to every member."
      action={
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
        feed.loading ? (
          <Skeleton label="Loading groups" lines={2} />
        ) : (
          <SettingsPanel>
            <SettingsEmpty icon="users" hue={hue}>
              Not in any group.
            </SettingsEmpty>
          </SettingsPanel>
        )
      ) : (
        <SettingsPanel label={`${user.name}'s groups`}>
          {feed.items.map((group) => {
            const route: SettingsRoute = { kind: "settings", page: "groups", groupId: group.id };
            return (
              <SettingRow
                key={group.id}
                lead={<SettingsTile icon="users" hue={hue} />}
                name={
                  <RouteLink href={routePath(route)} onNavigate={() => onNavigate(route)}>
                    {group.name}
                  </RouteLink>
                }
                help={group.description || undefined}
              >
                <button
                  type="button"
                  className="ghost"
                  aria-label={`Remove from ${group.name}`}
                  onClick={() => void remove(group)}
                >
                  Remove
                </button>
              </SettingRow>
            );
          })}
        </SettingsPanel>
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
    </SettingsGroup>
  );
}
