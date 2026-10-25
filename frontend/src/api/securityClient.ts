/**
 * The Security administration routes the Security pages read and write (0.12 I1, I2, Z1, SP1):
 * people, groups and their members, roles, the action groups' catalogue and grants. Every write
 * that changes a stored entry carries the version it was based on.
 */

import { request } from "@/api/client";
import type {
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
  GroupPage,
  PasswordResetLink,
  Role,
  RolePage,
  SecurityEventPage,
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

const json = (method: string, body: unknown): RequestInit => ({ method, body: JSON.stringify(body) });

export const security = {
  /** People as created, each with their roles (D298); `includeTotal` counts the filter's matches. */
  users: (options: { q?: string; active?: boolean; cursor?: string; pageSize?: number; includeTotal?: boolean } = {}) =>
    request<UserPage>(
      `/api/v1/users${query({
        q: options.q,
        active: options.active,
        cursor: options.cursor,
        pageSize: options.pageSize ?? 50,
        includeTotal: options.includeTotal || undefined,
      })}`,
    ),
  user: (userId: string) => request<User>(`/api/v1/users/${id(userId)}`),
  createUser: (body: { username: string; name: string; email?: string }) =>
    request<User>("/api/v1/users", json("POST", body)),
  updateUser: (
    userId: string,
    body: { expectedVersion: number; name?: string; email?: string | null; active?: boolean },
  ) => request<User>(`/api/v1/users/${id(userId)}`, json("PATCH", body)),
  /** A new one-time link; it replaces an earlier one (D272). */
  passwordLink: (userId: string) =>
    request<PasswordResetLink>(`/api/v1/users/${id(userId)}/password-reset`, { method: "POST" }),
  signOutEverywhere: (userId: string) => request<void>(`/api/v1/users/${id(userId)}/sessions`, { method: "DELETE" }),
  /** Security events newest first: those a person or client made or that are about them (0.12 Z4,
   * D317, D319). */
  securityEvents: (principalId: string, cursor?: string, pageSize = 20) =>
    request<SecurityEventPage>(`/api/v1/security-events${query({ principalId, cursor, pageSize })}`),
  /** A person's grants, direct and through their groups (D299). */
  userGrants: (userId: string, cursor?: string) =>
    request<GrantPage>(`/api/v1/users/${id(userId)}/grants${query({ cursor, pageSize: 100 })}`),

  groups: (options: { q?: string; memberId?: string; cursor?: string; pageSize?: number } = {}) =>
    request<GroupPage>(
      `/api/v1/groups${query({ q: options.q, memberId: options.memberId, cursor: options.cursor, pageSize: options.pageSize ?? 50 })}`,
    ),
  group: (groupId: string) => request<Group>(`/api/v1/groups/${id(groupId)}`),
  createGroup: (body: { name: string; description?: string }) => request<Group>("/api/v1/groups", json("POST", body)),
  updateGroup: (groupId: string, body: { expectedVersion: number; name?: string; description?: string | null }) =>
    request<Group>(`/api/v1/groups/${id(groupId)}`, json("PATCH", body)),
  deleteGroup: (groupId: string) => request<void>(`/api/v1/groups/${id(groupId)}`, { method: "DELETE" }),
  members: (groupId: string, cursor?: string) =>
    request<GroupMemberPage>(`/api/v1/groups/${id(groupId)}/members${query({ cursor, pageSize: 100 })}`),
  addMember: (groupId: string, userId: string) =>
    request<unknown>(`/api/v1/groups/${id(groupId)}/members`, json("POST", { userId })),
  removeMember: (groupId: string, userId: string) =>
    request<void>(`/api/v1/groups/${id(groupId)}/members/${id(userId)}`, { method: "DELETE" }),

  clients: (options: { q?: string; pageSize?: number } = {}) =>
    request<ClientSummaryPage>(
      `/api/v1/clients${query({ q: options.q, active: true, pageSize: options.pageSize ?? 20 })}`,
    ),
  /** Clients as created, each with its access and creator (SP2, D348, D349). */
  clientPage: (
    options: { q?: string; active?: boolean; cursor?: string; pageSize?: number; includeTotal?: boolean } = {},
  ) =>
    request<ClientPage>(
      `/api/v1/clients${query({
        q: options.q,
        active: options.active,
        cursor: options.cursor,
        pageSize: options.pageSize ?? 50,
        includeTotal: options.includeTotal || undefined,
      })}`,
    ),
  client: (clientId: string) => request<Client>(`/api/v1/clients/${id(clientId)}`),
  /** A client and its first secret, answered this once. */
  createClient: (body: { name: string }) => request<ClientWithSecret>("/api/v1/clients", json("POST", body)),
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
