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
import { mail } from "@/api/mailClient";
import { security } from "@/api/securityClient";
import { initials } from "@/app/useMe";
import { formatServerTime } from "@/lib/dates";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { useCursorWindow } from "@/lib/hooks/useCursorWindow";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import { routePath } from "@/routing/routes";
import type { Group, Passkey, PasswordResetLink, RouteState, SettingsRoute, SignInProviderRef, User } from "@/types";
import { CatalogueEntry, CatalogueLayout } from "@/ui/CatalogueLayout";
import { CatalogueWindow } from "@/ui/CatalogueWindow";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { FormField } from "@/ui/FormField";
import { Icon } from "@/ui/Icon";
import { InlineError } from "@/ui/InlineError";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { RouteLink } from "@/ui/RouteLink";
import { SearchField } from "@/ui/SearchField";
import { RuledList, RuledListItem } from "@/ui/RuledList";
import { Section } from "@/ui/Section";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { ShownOnceDialog } from "@/ui/ShownOnceDialog";
import { StatusPill } from "@/ui/StatusPill";
import { Switch } from "@/ui/Switch";
import { useToast } from "@/ui/Toast";
import { readsChanges } from "@/features/changes/changeText";
import { GrantsSection } from "./GrantsSection";
import { useHeldAnywhere } from "./permissions";
import { PickDialog } from "./PickDialog";
import { RecentActivity } from "./RecentActivity";
import { PrincipalPicker, type PickedPrincipal } from "./PrincipalPicker";
import { identityNames, linkSentence, personSignInLine, unlinkSentence, userRoleLine } from "./securityText";

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
const CATALOGUE_PAGE = 50;

export function PeoplePage({ route, onNavigate }: { route: PeopleRoute; onNavigate: (route: RouteState) => void }) {
  const [search, setSearch] = useState("");
  const [active, setActive] = useState(true);
  const [counts, setCounts] = useState<{ active?: number; deactivated?: number }>({});
  const [creating, setCreating] = useState(false);
  const [link, setLink] = useState<{ user: User; link: PasswordResetLink; created: boolean }>();
  const newButtonRef = useRef<HTMLButtonElement>(null);
  const q = useDebouncedValue(search.trim());
  const list = useCursorWindow<User>(
    (selector) => security.users({ q, active, ...selector, pageSize: CATALOGUE_PAGE }),
    [q, active],
  );
  const [countToken, setCountToken] = useState(0);
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

  function changed() {
    list.reload();
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
        <CatalogueWindow
          list={list}
          label="People"
          noun={["person", "people"]}
          pageSize={CATALOGUE_PAGE}
          loadingText="Loading people…"
          emptyText={
            q
              ? `No ${active ? "active" : "deactivated"} person matches “${q}”.`
              : `No ${active ? "active" : "deactivated"} people.`
          }
          entry={(user) => (
            <CatalogueEntry
              icon="user"
              title={user.name}
              subtitle={userRoleLine(user.roles)}
              current={route.userId === user.id}
              onSelect={() => onNavigate({ ...PEOPLE, userId: user.id })}
            />
          )}
        />
      </section>
    </nav>
  );

  return (
    <SettingsLayout
      eyebrow="Security"
      title="People"
      description="The people who sign in, the roles they hold and the groups they are in. A person is deactivated, never deleted, so their history keeps their name."
      actions={
        localOn && (
          <button ref={newButtonRef} className="primary" onClick={() => setCreating(true)}>
            <Icon name="plus" /> New person
          </button>
        )
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
            localOn={localOn}
            required={required}
            onNavigate={onNavigate}
            onChanged={changed}
            onLink={(user, made) => setLink({ user, link: made, created: false })}
            onLinked={(target) => {
              list.reload();
              setCountToken((token) => token + 1);
              onNavigate({ ...PEOPLE, userId: target.id });
            }}
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
            list.reload();
            setCountToken((token) => token + 1);
            onNavigate({ ...PEOPLE, userId: user.id });
            if (made) setLink({ user, link: made, created: true });
          }}
        />
      )}
      {link && <PasswordLinkDialog {...link} mailReady={mailReady} onClose={() => setLink(undefined)} />}
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
    const link = await makeLink(user).catch(() => undefined);
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
  localOn,
  required,
  onNavigate,
  onChanged,
  onLink,
  onLinked,
}: {
  userId: string;
  localOn: boolean;
  required: boolean;
  onNavigate: (route: RouteState) => void;
  onChanged: (user: User) => void;
  onLink: (user: User, link: PasswordResetLink) => void;
  onLinked: (target: User) => void;
}) {
  const [user, setUser] = useState<User>();
  const [loadError, setLoadError] = useState("");
  const [loadToken, setLoadToken] = useState(0);
  const [editing, setEditing] = useState(false);
  const [confirming, setConfirming] = useState<"deactivate" | "sign-out" | "keep" | "remove-factor">();
  const [linking, setLinking] = useState(false);
  const [unlinking, setUnlinking] = useState<SignInProviderRef>();
  const linkRef = useRef<HTMLButtonElement>(null);
  const [pending, setPending] = useState(false);
  const [actionError, setActionError] = useState("");
  const [conflict, setConflict] = useState("");
  const editRef = useRef<HTMLButtonElement>(null);
  const toast = useToast();
  const held = useHeldAnywhere();

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

  // What they changed in the workspaces this administrator reads (0.12 Z6, D345).
  const changes: RouteState = { kind: "changes", actorId: user.id, actorName: user.name };
  const signedIn = personSignInLine(user);
  const passwords = user.localKept || localOn;

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
            <StatusPill tone={user.hasPassword || user.identities.length ? "neutral" : "warning"} marker={false}>
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
      {actionError && !confirming && !unlinking && (
        <Notice tone="error" title="The action could not be completed">
          {actionError}
        </Notice>
      )}
      <div className="model-actions">
        <button ref={editRef} className="secondary" disabled={pending} onClick={() => setEditing(true)}>
          Edit…
        </button>
        {readsChanges(held) && (
          <RouteLink className="secondary" href={routePath(changes)} onNavigate={() => onNavigate(changes)}>
            See changes
          </RouteLink>
        )}
        {user.active && user.identities.length > 0 && !user.hasPassword && (
          <button ref={linkRef} className="secondary" disabled={pending} onClick={() => setLinking(true)}>
            Link to an existing person…
          </button>
        )}
        {user.active && passwords && (
          <button
            className="secondary"
            disabled={pending}
            onClick={() => void write(async () => onLink(user, await makeLink(user)))}
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
      {user.active && user.identities.length > 0 && !user.hasPassword && (
        <p className="admin-hint">
          If this person already has an account of their own, link this sign-in to it: they keep their roles and
          history.
        </p>
      )}
      <Section title="Sign-in">
        <RuledList label={`How ${user.name} signs in`}>
          {user.identities.map((identity) => (
            <RuledListItem
              key={identity.provider.key}
              title={identity.provider.name}
              meta={`Subject ${identity.subject}`}
              actions={
                <button className="secondary" disabled={pending} onClick={() => setUnlinking(identity.provider)}>
                  Unlink…
                </button>
              }
            />
          ))}
          {(user.hasPassword || !user.identities.length) && (
            <RuledListItem title="Password" meta={user.hasPassword ? "Set" : "Not set yet"} />
          )}
          {user.secondFactor && (
            <RuledListItem
              title="Second factor: authenticator app"
              meta={`Set up ${formatServerTime(user.secondFactor.confirmedAt)} · ${user.secondFactor.recoveryCodesLeft} of 10 recovery codes left`}
              actions={
                <button className="danger-ghost" disabled={pending} onClick={() => setConfirming("remove-factor")}>
                  Remove second factor…
                </button>
              }
            />
          )}
          {user.passkeys > 0 && (
            <PersonPasskeys user={user} onRemoved={(updated) => stored(updated, "The passkey was removed.")} />
          )}
          <RuledListItem
            title="Keeps local sign-in"
            meta={
              localOn
                ? "Signs in with a password even while local sign-in is off: the way back if the provider fails"
                : "Local sign-in is off: only people who keep it sign in with a password"
            }
            actions={
              <Switch
                label="Keeps local sign-in"
                checked={user.localKept}
                disabled={pending || !user.active}
                onChange={() => setConfirming("keep")}
              />
            }
          />
        </RuledList>
      </Section>
      <GrantsSection
        subject={{ principal: { kind: "user", id: user.id, name: user.name } }}
        load={(cursor) => security.userGrants(user.id, cursor)}
        deps={[user.id]}
        onNavigate={onNavigate}
      />
      <PersonGroups user={user} onNavigate={onNavigate} />
      <RecentActivity principal={user} />
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
      {linking && (
        <LinkIdentityDialog
          user={user}
          onClose={() => {
            setLinking(false);
            linkRef.current?.focus();
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
          title={user.localKept ? `${user.name} stops keeping local sign-in?` : `${user.name} keeps local sign-in?`}
          confirmLabel={user.localKept ? "Stop keeping it" : "Keep local sign-in"}
          pending={pending}
          error={actionError}
          onCancel={() => {
            setConfirming(undefined);
            setActionError("");
          }}
          onConfirm={() =>
            void write(async () =>
              stored(
                await security.updateUser(user.id, { expectedVersion: user.version, localKept: !user.localKept }),
                user.localKept ? `${user.name} no longer keeps local sign-in.` : `${user.name} keeps local sign-in.`,
              ),
            )
          }
        >
          <p>
            {user.localKept
              ? `While local sign-in is off, ${user.name} can no longer sign in with a password; they sign in with a provider. The last person who keeps it cannot stop.`
              : `${user.name} can sign in with a password even while local sign-in is off. Give it to the people who must get in if the provider fails.`}
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
    </div>
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
      eyebrow="Security"
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
function PersonPasskeys({ user, onRemoved }: { user: User; onRemoved: (user: User) => void }) {
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
        <RuledListItem
          key={passkey.id}
          title={`Passkey: ${passkey.name}`}
          meta={`Added ${formatServerTime(passkey.createdAt)} · ${
            passkey.lastUsedAt ? `last used ${formatServerTime(passkey.lastUsedAt)}` : "not used yet"
          }`}
          actions={
            <button
              className="danger-ghost"
              aria-label={`Remove the passkey ${passkey.name}`}
              onClick={() => setRemoving(passkey)}
            >
              Remove passkey…
            </button>
          }
        />
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
