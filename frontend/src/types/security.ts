/** The caller and their sessions, as the account menu and Settings › Account show them (0.12 I2). */

import type { PageNavigation } from "@/types/pagination";

/** Who is signed in: a person (or, through the API, a client). */
export interface Me {
  id: string;
  kind: "user" | "client";
  name: string;
  email: string | null;
  lastSignInAt: string | null;
  /** `password`, or a sign-in provider's key (0.12 I3). */
  signedInWith: string | null;
  /** The provider this session came from; null for a password. */
  signInProvider?: SignInProviderRef | null;
  sessionId: string | null;
  /** An administrator manages this person's sign-in: they change no own password, second factor,
   * passkey or other session (`403 SIGN_IN_MANAGED`, 0.17 SA1). Always false for a client. */
  signInManaged: boolean;
}

/** A sign-in provider as other reads name it (0.12 I3). */
export interface SignInProviderRef {
  key: string;
  name: string;
}

/** A person or a client as a read names them now (0.12 Z4, D237). */
export interface Principal {
  kind: "user" | "client";
  id: string;
  name: string;
}

/** Who made a change (0.12 Z4, D313): a person, a client or the engine; null before sign-in. */
export type Actor = Principal | { kind: "engine" };

/** A change to access, or a sign-in (0.12 Z4, D317, D318); `details` never holds a secret. */
export interface SecurityEvent {
  id: string;
  aggregateType:
    | "user"
    | "group"
    | "role"
    | "grant"
    | "client"
    | "token-signing-key"
    | "sign-in"
    | "sign-in-provider"
    | "mail-settings"
    | "approval-policy";
  aggregateId: string;
  action: string;
  version: number;
  occurredAt: string;
  actor: Actor | null;
  details: Record<string, unknown>;
}

export interface SecurityEventPage extends PageNavigation {
  items: SecurityEvent[];
}

/** One of the person's open browser sessions. */
export interface SignInSession {
  id: string;
  current: boolean;
  signedInWith: string;
  /** The assistant this session was opened for; null for a browser (0.16 AG1). */
  application: string | null;
  userAgent: string | null;
  createdAt: string;
  lastUsedAt: string;
  endsAt: string;
}

export interface SignInSessionPage extends PageNavigation {
  items: SignInSession[];
}

/** A role as a grant or a permission names it (0.12 Z1). */
export interface RoleRef {
  key: string;
  name: string;
}

/** A role given to a person, client or group, at the instance or in one workspace (0.12 Z1). */
export interface Grant {
  id: string;
  principal: { kind: "user" | "client" | "group"; id: string; name: string };
  /** Null for a consumer API grant (0.12 Z3, D306). */
  role: RoleRef | null;
  /** Instead of a role, read of this consumer API in the grant's workspace; its name is null when
   * the workspace's model no longer declares it (D306). */
  consumerApi?: { key: string; name: string | null } | null;
  scope: {
    instance: boolean;
    workspaceKey: string | null;
    applications: string[];
    recordTypes: string[];
    applicationNames: string[];
    recordTypeNames: string[];
    /** Narrowed-to keys the workspace's model no longer has (D296). */
    missingApplications?: string[];
    missingRecordTypes?: string[];
  };
  /** The narrowing names something the model no longer has; that part allows nothing (D296). */
  stale?: boolean;
  createdAt: string;
}

export interface GrantPage extends PageNavigation {
  items: Grant[];
}

/** What a grant names: a principal, a role and where (0.12 Z1). */
export interface GrantCreate {
  principal: { kind: "user" | "client" | "group"; id: string };
  /** A role, or instead a consumer API read in one workspace (0.12 Z3, D306). */
  role?: string;
  consumerApi?: string;
  scope: { instance: true } | { workspaceKey: string; applications?: string[]; recordTypes?: string[] };
}

/** A role a person holds, directly or through a group, and where (0.12 SP1, D298). */
export interface UserRole {
  key: string;
  name: string;
  instance: boolean;
  workspaces: { key: string; label: string }[];
}

/** A person, as Settings › Security › People shows them (0.12 I1, SP1). */
export interface User {
  id: string;
  name: string;
  /** The name a person signs in with; null only for a deactivated person (0.17 EM1). */
  email: string | null;
  active: boolean;
  hasPassword: boolean;
  version: number;
  createdAt: string;
  updatedAt: string;
  lastSignInAt: string | null;
  roles: UserRole[];
  /** The sign-in providers the person signs in with (0.12 I3, D363). */
  identities: { provider: SignInProviderRef; subject: string }[];
  /** Signs in with a password while local sign-in is off (D365). */
  localKept: boolean;
  /** The authenticator app they sign in with after their password; null without one (I4b). */
  secondFactor: { method: "authenticator-app"; confirmedAt: string; recoveryCodesLeft: number } | null;
  /** How many passkeys they have (I4c). */
  passkeys: number;
  /** An administrator manages their sign-in (0.17 SA1); see `Me.signInManaged`. */
  signInManaged: boolean;
}

/** A passkey by the name its person gave it; never the credential (0.12 I4c, D394). */
export interface Passkey {
  id: string;
  name: string;
  createdAt: string;
  lastUsedAt: string | null;
}

export interface PasskeyPage extends PageNavigation {
  items: Passkey[];
}

export interface UserPage extends PageNavigation {
  items: User[];
}

/** A one-time link that sets a person's password, answered once (D272). */
export interface PasswordResetLink {
  url: string;
  expiresAt: string;
  /** The address the link was also mailed to, when asked (SP3). */
  sentTo?: string | null;
}

/** A group of people (0.12 Z1): local, or from a sign-in provider (I3, D364). */
export interface Group {
  id: string;
  name: string;
  description: string | null;
  /** A provider group's provider and claim value; its members come from sign-ins. */
  source: { provider: SignInProviderRef; claimValue: string } | null;
  members: number;
  version: number;
  createdAt: string;
  updatedAt: string;
}

export interface GroupPage extends PageNavigation {
  items: Group[];
}

export interface GroupMember {
  id: string;
  email: string | null;
  name: string;
  active: boolean;
  /** A provider group's member: when a sign-in last named them in it. */
  seenAt?: string | null;
}

/** What adding or removing one of several people did, or would do (0.12 SP1b, D401, D402). */
export interface GroupMemberOutcome {
  /** The person's ID, or the e-mail address as sent. */
  input: string;
  outcome: "added" | "toAdd" | "alreadyMember" | "deactivated" | "notFound" | "removed" | "notMember";
  member: GroupMember | null;
}

export interface GroupMembersResult {
  items: GroupMemberOutcome[];
  /** How many people were added or removed. */
  changed: number;
}

export interface GroupMemberPage extends PageNavigation {
  items: GroupMember[];
}

/** A role: predefined (read-only) or custom, made of action groups (0.12 Z1). */
export interface Role {
  key: string;
  name: string;
  description: string | null;
  predefined: boolean;
  actionGroups: string[];
  /** How many grants give it. */
  grants: number;
  version: number;
  createdAt: string;
  updatedAt: string;
}

export interface RolePage extends PageNavigation {
  items: Role[];
}

/** One of the catalogue's action groups, which roles are made of. */
export interface ActionGroup {
  key: string;
  name: string;
  description: string;
  /** `instance`: held only for the whole instance (D302). */
  grantableAt: "workspace" | "instance";
  /** Whether a grant's applications and record types narrow it (writes only). */
  narrowable: boolean;
}

/** An OAuth client as a grant's "Who" finds it (0.12 I1). */
export interface ClientSummary {
  id: string;
  name: string;
  active: boolean;
}

export interface ClientSummaryPage extends PageNavigation {
  items: ClientSummary[];
}

/** One of a client's valid secrets, never its value after it was answered (0.12 I1, SP2). */
export interface ClientSecret {
  id: string;
  createdAt: string;
  /** The end of its overlap after a rotation; null while it has no end. */
  expiresAt: string | null;
  lastUsedAt: string | null;
  /** Its last four characters; null for a secret made before SP2 (D350). */
  hint: string | null;
}

/** An OAuth client as Settings › Security › Clients shows it (0.12 I1, SP2). */
export interface Client extends ClientSummary {
  /** `agent`: holds only agent tokens, for the assistants' address (0.16 AG1). */
  kind: "api" | "agent";
  version: number;
  createdAt: string;
  updatedAt: string;
  /** When it last obtained a token. */
  lastUsedAt: string | null;
  secrets: ClientSecret[];
  roles: UserRole[];
  /** The consumer APIs it is granted, by key, with their workspaces (D348). */
  consumerApis: { key: string; workspaces: { key: string; label: string }[] }[];
  /** Null when made on the server or before Z4 (D349). */
  createdBy: Principal | null;
}

/** A client with the secret just made, answered this once. */
export interface ClientWithSecret extends Client {
  secretId: string;
  secret: string;
}

export interface ClientPage extends PageNavigation {
  items: Client[];
}

/** What a grant in a workspace can name, from its model (0.12 SP2, D355). */
export interface GrantOptions {
  applications: { key: string; name: string }[];
  recordTypes: { key: string; name: string }[];
  consumerApis: { key: string; name: string }[];
}

/** A token signing key, without its private half (0.12 I1). */
export interface SigningKey {
  kid: string;
  state: "current" | "verifying" | "retired";
  createdAt: string;
  rotatedAt: string | null;
  /** When it stops verifying: in the future while verifying. */
  retiredAt: string | null;
}

export interface SigningKeyPage extends PageNavigation {
  items: SigningKey[];
}

/** An OpenID Connect provider people sign in with (0.12 I3, D366); never its secret. */
export interface SignInProvider {
  key: string;
  name: string;
  issuer: string;
  clientId: string;
  clientSecretSet: boolean;
  groupsClaim: string | null;
  enabled: boolean;
  /** Signing out of the engine signs the person out of the provider too (I4a, D379). */
  signOutOfProvider: boolean;
  /** Its e-mail addresses are taken as sent; off: only with `email_verified: true` (R17-F20). */
  emailsTrusted: boolean;
  /** The address to register with the provider. */
  redirectUri: string;
  /** The address to register for returning from the provider's sign-out (I4a). */
  signedOutUri: string;
  people: number;
  lastSignInAt: string | null;
  version: number;
  createdAt: string;
  updatedAt: string;
}

export interface SignInProviderPage extends PageNavigation {
  items: SignInProvider[];
}

export interface SignInProviderCreate {
  key: string;
  name: string;
  issuer: string;
  clientId: string;
  clientSecret: string;
  groupsClaim?: string | null;
  enabled?: boolean;
  signOutOfProvider?: boolean;
  emailsTrusted?: boolean;
}

/** Whether people sign in with a password (D365). */
export interface LocalSignIn {
  enabled: boolean;
  /** A password needs an authenticator app; set up on the sign-in page when there is none (I4b). */
  secondFactorRequired: boolean;
  keptPeople: number;
  version: number;
  updatedAt: string;
}

/** Whether the caller is e-mailed when something arrives in their inbox (0.12 M2). `available` is
 * false where it cannot work: the switch is then not offered. */
export interface NoticeMail {
  enabled: boolean;
  available: boolean;
  reason: "mail-not-set-up" | "no-email" | "not-a-person" | null;
  email: string | null;
  /** Every kind of notice with the engine's label, and how it is mailed (D434, AO-D33). */
  kinds: NoticeMailKind[];
  /** How often the digest comes, once chosen (0.16 AO3). */
  digest: NoticeDigest | null;
}

/** How a kind of notice reaches the person: one mail at once, in the digest, or no mail. */
export type NoticeDelivery = "now" | "digest" | "off";

export interface NoticeMailKind {
  kind: string;
  label: string;
  delivery: NoticeDelivery;
}

/** The digest: every morning or on Mondays at 07:00 in the time zone, and when the next is due. */
export interface NoticeDigest {
  every: "daily" | "weekly";
  timeZone: string;
  /** The next send time while mail is on, else null. */
  nextAt: string | null;
}

/** The caller's second factor (0.12 I4b). */
export interface MySecondFactor {
  enabled: boolean;
  confirmedAt: string | null;
  recoveryCodesLeft: number;
  /** How many passkeys the caller has (I4c). */
  passkeys: number;
  /** The instance requires one with a password: the last one cannot be removed. */
  required: boolean;
}

/** What setting an authenticator app up needs, answered once (D386). */
export interface SecondFactorEnrolment {
  secret: string;
  otpauthUri: string;
  qrSvg: string;
}

/** What the caller holds in one workspace: the roles that apply there and their action groups. */
export interface MyPermissions {
  workspaceKey: string;
  workspaceLabel: string;
  roles: RoleRef[];
  actionGroups: {
    key: string;
    name: string;
    applications: string[];
    recordTypes: string[];
    sources: {
      grantId: string;
      role: RoleRef;
      scope: "workspace" | "instance";
      group: { id: string; name: string } | null;
    }[];
  }[];
}

/** An action group the caller holds somewhere: at the instance, or in these workspaces (0.12 Z5). */
export interface HeldAnywhere {
  key: string;
  name: string;
  instance: boolean;
  workspaces: { key: string; label: string }[];
}

export interface HeldAnywhereList {
  items: HeldAnywhere[];
}
