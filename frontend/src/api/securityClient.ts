/**
 * The Security administration routes the Security pages read and write (0.12 I1, I2, Z1, SP1):
 * people, groups and their members, roles, the action groups' catalogue and grants. Every write
 * that changes a stored entry carries the version it was based on.
 */

import { request, type PageSelector } from "@/api/client";
import type {
  PasskeyPage,
  ActionGroup,
  Client,
  ClientPage,
  ClientSummaryPage,
  ClientWithSecret,
  Grant,
  GrantCreate,
  GrantOptions,
  GrantPage,
  Group,
  GroupMemberPage,
  GroupMembersResult,
  GroupPage,
  LocalSignIn,
  PasswordResetLink,
  Role,
  RolePage,
  SecurityEvent,
  SecurityEventPage,
  SignInProvider,
  SignInProviderCreate,
  SignInProviderPage,
  SigningKey,
  SigningKeyPage,
  SubscriptionPage,
  User,
  UserPage,
} from "@/types";

const id = encodeURIComponent;

function query(params: Record<string, string | number | boolean | undefined>) {
  const search = new URLSearchParams();
  for (const [name, value] of Object.entries(params))
    if (value !== undefined && value !== "") search.set(name, String(value));
  const text = search.toString();
  return text ? `?${text}` : "";
}

/** A page selector as query parameters: a cursor, a row position, the end, or a seek (ADR-030). */
function selecting(selector: PageSelector) {
  return {
    cursor: selector.cursor,
    position: selector.position,
    from: selector.fromEnd ? "end" : undefined,
    seek: selector.seek,
    includeTotal: selector.includeTotal || undefined,
  };
}

const json = (method: string, body: unknown): RequestInit => ({ method, body: JSON.stringify(body) });

export const security = {
  /** People as created, each with their roles (D298); `includeTotal` counts the filter's matches. */
  users: (options: PageSelector & { q?: string; active?: boolean; pageSize?: number } = {}) =>
    request<UserPage>(
      `/api/v1/users${query({
        q: options.q,
        active: options.active,
        pageSize: options.pageSize ?? 50,
        ...selecting(options),
      })}`,
    ),
  user: (userId: string) => request<User>(`/api/v1/users/${id(userId)}`),
  createUser: (body: { username: string; name: string; email?: string }) =>
    request<User>("/api/v1/users", json("POST", body)),
  updateUser: (
    userId: string,
    body: { expectedVersion: number; name?: string; email?: string | null; active?: boolean; localKept?: boolean },
  ) => request<User>(`/api/v1/users/${id(userId)}`, json("PATCH", body)),
  /** Move the provider identities and provider-group memberships of `fromUserId` onto this person;
   * the other person is deactivated (I4a, D377, D378). */
  linkIdentity: (userId: string, body: { expectedVersion: number; fromUserId: string }) =>
    request<User>(`/api/v1/users/${id(userId)}/identities`, json("POST", body)),
  /** An administrator removes a person's second factor, for one who lost the phone and the codes
   * (I4b, D387). */
  removeSecondFactor: (userId: string) =>
    request<void>(`/api/v1/users/${id(userId)}/second-factor`, { method: "DELETE" }),
  /** A person's passkeys, as they named them (I4c, D394); an administrator removes one for someone
   * who lost the device. */
  userPasskeys: (userId: string, cursor?: string) =>
    request<PasskeyPage>(`/api/v1/users/${id(userId)}/passkeys${query({ cursor, pageSize: 100 })}`),
  removeUserPasskey: (userId: string, passkeyId: string) =>
    request<void>(`/api/v1/users/${id(userId)}/passkeys/${id(passkeyId)}`, { method: "DELETE" }),
  unlinkIdentity: (userId: string, providerKey: string) =>
    request<void>(`/api/v1/users/${id(userId)}/identities/${id(providerKey)}`, { method: "DELETE" }),
  /** A new one-time link; it replaces an earlier one (D272). With `send` it is also mailed to the person (SP3). */
  passwordLink: (userId: string, send = false) =>
    request<PasswordResetLink>(`/api/v1/users/${id(userId)}/password-reset`, {
      method: "POST",
      ...(send ? { body: JSON.stringify({ send: true }) } : {}),
    }),
  signOutEverywhere: (userId: string) => request<void>(`/api/v1/users/${id(userId)}/sessions`, { method: "DELETE" }),
  /** Security events newest first: those a person or client made or that are about them (0.12 Z4,
   * D317, D319). */
  /** What was done to or by a principal, newest first; `aggregateTypes` keeps those kinds (0.12 RA1). */
  securityEvents: (
    principalId: string,
    cursor?: string,
    pageSize = 20,
    aggregateTypes: readonly SecurityEvent["aggregateType"][] = [],
  ) =>
    request<SecurityEventPage>(
      `/api/v1/security-events${query({ principalId, cursor, pageSize })}${aggregateTypes
        .map((type) => `&aggregateType=${encodeURIComponent(type)}`)
        .join("")}`,
    ),
  /** A person's grants, direct and through their groups (D299). */
  userGrants: (userId: string, cursor?: string) =>
    request<GrantPage>(`/api/v1/users/${id(userId)}/grants${query({ cursor, pageSize: 100 })}`),

  groups: (options: PageSelector & { q?: string; memberId?: string; pageSize?: number } = {}) =>
    request<GroupPage>(
      `/api/v1/groups${query({ q: options.q, memberId: options.memberId, pageSize: options.pageSize ?? 50, ...selecting(options) })}`,
    ),
  group: (groupId: string) => request<Group>(`/api/v1/groups/${id(groupId)}`),
  /** A local group, or with `source` a provider group made ahead of its members' sign-ins (I3, D364). */
  createGroup: (body: { name: string; description?: string; source?: { provider: string; claimValue: string } }) =>
    request<Group>("/api/v1/groups", json("POST", body)),
  updateGroup: (groupId: string, body: { expectedVersion: number; name?: string; description?: string | null }) =>
    request<Group>(`/api/v1/groups/${id(groupId)}`, json("PATCH", body)),
  deleteGroup: (groupId: string) => request<void>(`/api/v1/groups/${id(groupId)}`, { method: "DELETE" }),
  members: (groupId: string, cursor?: string) =>
    request<GroupMemberPage>(`/api/v1/groups/${id(groupId)}/members${query({ cursor, pageSize: 100 })}`),
  addMember: (groupId: string, userId: string) =>
    request<unknown>(`/api/v1/groups/${id(groupId)}/members`, json("POST", { userId })),
  /** Several people at once, by ID or by usernames and e-mail addresses; `dryRun` changes nothing (SP1b). */
  addMembers: (groupId: string, body: { userIds?: string[]; identifiers?: string[]; dryRun?: boolean }) =>
    request<GroupMembersResult>(`/api/v1/groups/${id(groupId)}/members/batch`, json("POST", body)),
  /** Several people taken out at once (SP1b, D402). */
  removeMembers: (groupId: string, userIds: string[]) =>
    request<GroupMembersResult>(`/api/v1/groups/${id(groupId)}/members/removal`, json("POST", { userIds })),
  removeMember: (groupId: string, userId: string) =>
    request<void>(`/api/v1/groups/${id(groupId)}/members/${id(userId)}`, { method: "DELETE" }),

  clients: (options: { q?: string; pageSize?: number } = {}) =>
    request<ClientSummaryPage>(
      `/api/v1/clients${query({ q: options.q, active: true, pageSize: options.pageSize ?? 20 })}`,
    ),
  /** Clients as created, each with its access and creator (SP2, D348, D349). */
  clientPage: (options: PageSelector & { q?: string; active?: boolean; pageSize?: number } = {}) =>
    request<ClientPage>(
      `/api/v1/clients${query({
        q: options.q,
        active: options.active,
        pageSize: options.pageSize ?? 50,
        ...selecting(options),
      })}`,
    ),
  client: (clientId: string) => request<Client>(`/api/v1/clients/${id(clientId)}`),
  /** A client and its first secret, answered this once. */
  createClient: (body: { name: string; kind?: "api" | "agent" }) =>
    request<ClientWithSecret>("/api/v1/clients", json("POST", body)),
  updateClient: (clientId: string, body: { expectedVersion: number; name?: string; active?: boolean }) =>
    request<Client>(`/api/v1/clients/${id(clientId)}`, json("PATCH", body)),
  /** A new secret, answered once; the others keep working for `overlapHours` (0 stops them now). */
  rotateSecret: (clientId: string, body: { expectedVersion: number; overlapHours: number }) =>
    request<ClientWithSecret>(`/api/v1/clients/${id(clientId)}/secrets`, json("POST", body)),
  endSecret: (clientId: string, secretId: string) =>
    request<Client>(`/api/v1/clients/${id(clientId)}/secrets/${id(secretId)}`, { method: "DELETE" }),
  /** The webhooks a person or client created, in the workspaces the caller administers (D353). */
  subscriptionsOf: (ownerId: string, cursor?: string) =>
    request<SubscriptionPage>(`/api/v1/consumer-subscriptions${query({ ownerId, cursor, pageSize: 50 })}`),

  /** Token signing keys, newest first (I1). */
  signingKeys: (cursor?: string) =>
    request<SigningKeyPage>(`/api/v1/token-signing-keys${query({ cursor, pageSize: 50 })}`),
  /** A new key; `immediate` retires the current one at once instead of after its tokens expire. */
  rotateSigningKey: (immediate: boolean) =>
    request<SigningKey>("/api/v1/token-signing-keys/rotation", json("POST", { immediate })),

  /** Sign-in providers as created (I3, D366). */
  signInProviders: (cursor?: string) =>
    request<SignInProviderPage>(`/api/v1/sign-in-providers${query({ cursor, pageSize: 100 })}`),
  signInProvider: (key: string) => request<SignInProvider>(`/api/v1/sign-in-providers/${id(key)}`),
  /** An enabled provider is read when saved (`422 SIGN_IN_PROVIDER_UNREACHABLE` with the reason). */
  createSignInProvider: (body: SignInProviderCreate) =>
    request<SignInProvider>("/api/v1/sign-in-providers", json("POST", body)),
  updateSignInProvider: (key: string, body: { expectedVersion: number } & Partial<Omit<SignInProviderCreate, "key">>) =>
    request<SignInProvider>(`/api/v1/sign-in-providers/${id(key)}`, json("PATCH", body)),
  deleteSignInProvider: (key: string) => request<void>(`/api/v1/sign-in-providers/${id(key)}`, { method: "DELETE" }),
  localSignIn: () => request<LocalSignIn>("/api/v1/sign-in-providers/local"),
  /** Off only once a provider has signed someone in (`409 NO_WORKING_PROVIDER`, D365). */
  setLocalSignIn: (body: { expectedVersion: number; enabled?: boolean; secondFactorRequired?: boolean }) =>
    request<LocalSignIn>("/api/v1/sign-in-providers/local", json("PATCH", body)),

  /** The catalogue every role is made of. */
  actionGroups: () => request<{ items: ActionGroup[] }>("/api/v1/action-groups").then((list) => list.items),
  roles: (cursor?: string) => request<RolePage>(`/api/v1/roles${query({ cursor, pageSize: 500 })}`),
  createRole: (body: { name: string; description?: string; copiedFrom?: string; actionGroups?: string[] }) =>
    request<Role>("/api/v1/roles", json("POST", body)),
  updateRole: (
    roleKey: string,
    body: { expectedVersion: number; name?: string; description?: string | null; actionGroups?: string[] },
  ) => request<Role>(`/api/v1/roles/${id(roleKey)}`, json("PATCH", body)),
  deleteRole: (roleKey: string) => request<void>(`/api/v1/roles/${id(roleKey)}`, { method: "DELETE" }),

  /** Grants made to a principal (a group's, on its page). */
  grantsOf: (principalId: string, cursor?: string) =>
    request<GrantPage>(`/api/v1/grants${query({ principalId, cursor, pageSize: 100 })}`),
  createGrant: (body: GrantCreate) => request<Grant>("/api/v1/grants", json("POST", body)),
  deleteGrant: (grantId: string) => request<void>(`/api/v1/grants/${id(grantId)}`, { method: "DELETE" }),
  /** What a grant in a workspace can name, without Browse there (SP2, D355). */
  grantOptions: (workspaceKey: string) => request<GrantOptions>(`/api/v1/workspaces/${id(workspaceKey)}/grant-options`),
  /** Every grant that applies in a workspace: made there or at the instance (J40.7). */
  access: (workspaceKey: string, cursor?: string) =>
    request<GrantPage>(`/api/v1/workspaces/${id(workspaceKey)}/access${query({ cursor, pageSize: 100 })}`),
};
