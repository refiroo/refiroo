/** Agent access: the assistants that reach the instance, and the calls they made (0.16 AG1). */

import type { Client } from "@/types/security";
import type { PageNavigation } from "@/types/runtime";

/** `GET /agent-access`: the settings as read at start and the last 30 days' calls. */
export interface AgentAccessStatus {
  enabled: boolean;
  /** The address an assistant connects to. */
  url: string;
  ratePerMinute: number;
  openRegistration: boolean;
  redirectHosts: string[];
  callsDays: number;
  calls30Days: number;
  lastCallAt: string | null;
}

export interface AgentClient extends Client {
  calls30Days: number;
  lastCallAt: string | null;
}

export interface AgentClientPage extends PageNavigation {
  items: AgentClient[];
}

/** An assistant people sign in with. */
export interface AgentApplication {
  /** Its OAuth client_id. */
  id: string;
  /** What the assistant says of itself. */
  name: string;
  source: "registered" | "administrator";
  /** Where a sign-in may return, in a person's words. */
  returnsTo: string[];
  blocked: boolean;
  /** People with an open session for it. */
  signedIn: number;
  createdAt: string;
  lastUsedAt: string | null;
}

export interface AgentApplicationPage extends PageNavigation {
  items: AgentApplication[];
}

export type AgentCallOutcome = "answered" | "refused" | "limited" | "failed";

/** One tool call; the names of its arguments, never their values. */
export interface AgentCall {
  id: string;
  occurredAt: string;
  principal: string;
  principalKind: "user" | "client";
  principalId: string;
  /** The assistant; null for a client's own calls. */
  application: string | null;
  tool: string;
  arguments: string[];
  outcome: AgentCallOutcome;
  durationMs: number;
  requestId: string | null;
}

export interface AgentCallPage extends PageNavigation {
  items: AgentCall[];
}
