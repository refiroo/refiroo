/** The Agent access routes (0.16 AG1): the settings, agent clients, the assistants people sign in with and the calls. */

import { request } from "@/api/client";
import type {
  AgentAccessStatus,
  AgentApplication,
  AgentApplicationPage,
  AgentCallPage,
  AgentClientPage,
} from "@/types";

const page = (cursor?: string) => {
  const search = new URLSearchParams({ pageSize: "25" });
  if (cursor) search.set("cursor", cursor);
  return `?${search}`;
};
const post = (body: unknown) => ({ method: "POST", body: JSON.stringify(body) });
const application = (id: string) => `/api/v1/agent-access/applications/${encodeURIComponent(id)}`;

export const agentAccess = {
  status: () => request<AgentAccessStatus>("/api/v1/agent-access"),
  clients: (cursor?: string) => request<AgentClientPage>(`/api/v1/agent-access/clients${page(cursor)}`),
  applications: (cursor?: string) => request<AgentApplicationPage>(`/api/v1/agent-access/applications${page(cursor)}`),
  /** `422 AGENT_APPLICATION_INVALID` for a return address that is not allowed. */
  register: (body: { name: string; redirectUris: string[] }) =>
    request<AgentApplication>("/api/v1/agent-access/applications", post(body)),
  block: (id: string) => request<AgentApplication>(`${application(id)}/block`, post({})),
  restore: (id: string) => request<AgentApplication>(`${application(id)}/restore`, post({})),
  /** The calls made, newest first. */
  calls: (cursor?: string) => request<AgentCallPage>(`/api/v1/agent-access/calls${page(cursor)}`),
};
