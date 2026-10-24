/** The caller and their sessions, as the account menu and Settings › Account show them (0.12 I2). */

import type { PageNavigation } from "@/types/runtime";

/** Who is signed in: a person (or, through the API, a client). */
export interface Me {
  id: string;
  kind: "user" | "client";
  name: string;
  username: string | null;
  email: string | null;
  lastSignInAt: string | null;
  signedInWith: string | null;
  sessionId: string | null;
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
  aggregateType: "user" | "group" | "role" | "grant" | "client" | "token-signing-key" | "sign-in";
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
  role: string;
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
  username: string;
  name: string;
  email: string | null;
  active: boolean;
  hasPassword: boolean;
  version: number;
  createdAt: string;
  updatedAt: string;
  lastSignInAt: string | null;
  roles: UserRole[];
}

export interface UserPage extends PageNavigation {
  items: User[];
}

/** A one-time link that sets a person's password, answered once (D272). */
export interface PasswordResetLink {
  url: string;
  expiresAt: string;
}

/** A local group of people (0.12 Z1). */
export interface Group {
  id: string;
  name: string;
  description: string | null;
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
  username: string;
  name: string;
  active: boolean;
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
