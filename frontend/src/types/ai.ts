/** The assistant and the AI provider the application asks for proposals, and the calls it made (0.16 AP1). */

import type { PageNavigation } from "@/types/pagination";

/** What may leave the process: names and types, also sample values, also the values a feature needs. */
export type AiSendLevel = "structure" | "samples" | "values";
/** `workbookLoad` is kept for the call rows recorded by older versions; it is no longer a feature. */
export type AiPurpose =
  | "connectionTest"
  | "mappingTarget"
  | "queryTranslation"
  | "impactSummary"
  | "historyAccount"
  | "workbookLoad"
  | "assistantSession";
export type AiFailureKind =
  | "unreachable"
  | "unauthorized"
  | "rateLimited"
  | "declined"
  | "malformed"
  | "failed"
  | "timeout"
  | "cancelled"
  | "interrupted";

/** What `GET /system` tells every signed-in person about the provider. */
export interface AiSystemInfo {
  configured: boolean;
  provider: string | null;
  /** The model the provider answers with, when it names one. */
  model?: string | null;
  sendLevel: AiSendLevel;
  /** The assistant's session can run here (`AI_AGENT_COMMAND`, whatever the provider); without it Import stays the ordinary dialog. */
  assistant?: boolean;
}

export interface AiFeature {
  purpose: AiPurpose;
  name: string;
  needs: AiSendLevel;
  available: boolean;
}

export interface AiCall {
  id: string;
  /** The purpose it was made for; `modelNames` (removed in 0.16) stays on the calls recorded before. */
  purpose: AiPurpose | "modelNames";
  provider: string;
  model: string | null;
  sendLevel: AiSendLevel;
  promptVersion: string;
  requestedBy: { kind: "user" | "client"; id: string; name: string } | null;
  jobId: string | null;
  startedAt: string;
  durationMs: number;
  bytesIn: number;
  bytesOut: number;
  tokensIn: number | null;
  tokensOut: number | null;
  /** What a session's turn cost, as it reported it; none from a provider or a run that stopped. */
  costUsd?: number | null;
  /** The task a session's turn belongs to. */
  taskId?: string | null;
  outcome: "answered" | "failed";
  failureKind: AiFailureKind | null;
  failure: string | null;
  /** Kept only where the deployment keeps content (AI_LOG_CONTENT). */
  content: { instructions: unknown; context: unknown; answer: unknown } | null;
}

export interface AiStatus {
  configured: boolean;
  /** The assistant's session can run (`AI_AGENT_COMMAND`, AP-D38); it needs no provider. */
  assistant: boolean;
  provider: string | null;
  model: string | null;
  endpoint: string | null;
  keySet: boolean;
  sendLevel: AiSendLevel;
  sampleValues: number;
  minConfidence: number;
  logContent: boolean;
  logContentDays: number;
  timeoutSeconds: number;
  features: AiFeature[];
  lastCall: AiCall | null;
  totals: {
    days: number;
    calls: number;
    failed: number;
    tokensIn: number;
    tokensOut: number;
    bytesIn: number;
    bytesOut: number;
    costUsd: number;
  };
}

export interface AiCallPage extends PageNavigation {
  items: AiCall[];
}

/** Where an AI proposal came from: carried in its evidence and in an applied step's origin. */
export interface AiOrigin {
  kind: "ai";
  provider: string;
  model: string | null;
  promptVersion: string;
  /** A provider's proposal says how sure it is and why; a session's changes do not (0.16 AP9). */
  confidence?: number | null;
  reason?: string | null;
}

/** A mapping target or a published change the AI proposed (0.16 AP2): who answered, how sure, why, and who asked. */
export interface ProposalOrigin extends AiOrigin {
  /** The person or client that asked for it; a public ID. */
  proposedBy?: string | null;
  /** Their name as it is now (0.16 AP9). */
  proposedByName?: string | null;
  /** Who edited it after it was proposed, by public ID and name (AP-D5). */
  editedBy?: string | null;
  editedByName?: string | null;
  /** The assistant's task that made it. */
  taskId?: string | null;
}

/** A change an outside assistant (an MCP client) prepared: its own name, who asked and who edited (0.16 AG3, AG-D29). */
export interface AgentOrigin {
  kind: "agent";
  /** The name the assistant gave itself; not verified. */
  application: string;
  proposedBy?: string | null;
  proposedByName?: string | null;
  editedBy?: string | null;
  editedByName?: string | null;
}

/** What a history entry, a change set row or a mapping target says made the change. */
export type ChangeOrigin = ProposalOrigin | AgentOrigin;

/** `POST /workspaces/{key}/mapping-proposals`: the grid's narrowing, and exactly one of the change set choices. */
export interface MappingProposalRequest {
  applicationKey: string;
  viewKey: string;
  search?: string;
  parentObjectId?: string;
  changeSetId?: string;
  expectedChangeSetVersion?: number;
  changeSetName?: string;
}

/** What an `aiProposal` job did as far as it has run. */
export interface AiProposalTally {
  proposed: number;
  unmatched: number;
  changed: number;
  refused: number;
  notAnswered: number;
  changeSetId: string;
  warnings: string[];
}

/** `POST /workspaces/{key}/query-translations`: a question about a table view, in a change set or publication when one is named (0.16 AG4). */
export interface QueryTranslationRequest {
  applicationKey: string;
  viewKey: string;
  question: string;
  changeSetId?: string;
  publicationId?: string;
}

/** What a question became: the list's own filters and search, and the parts no filter can say. Applied only when nothing is left out. */
export interface QueryTranslation {
  filters: { field: string; operator: string; value: string }[];
  search: string;
  notExpressed: { part: string; reason: string }[];
  applied: boolean;
}

/** `POST /model-releases/{id}/impact-summary` and `POST /model-drafts/{id}/impact-summary`: the workspace the change is for (0.16 AO1). */
export interface ImpactSummaryRequest {
  workspaceKey: string;
  /** A draft's version, which the account is of; the release's route takes none. */
  expectedVersion?: number;
  language?: string;
}

/** One fact of a model change, written by the engine; its `id` is what a statement cites. */
export interface ImpactFact {
  id: string;
  kind: "blocked" | "data" | "contract" | "change" | "records";
  text: string;
  path: string | null;
  count: number | null;
}

/** The account of a model change: every fact, and the statements that word them (empty when the provider failed). */
export interface ImpactSummary {
  facts: ImpactFact[];
  /** Each cites the facts it rests on: a fact's id, or `more-<kind>` for the facts of a kind the provider was not sent. */
  statements: { text: string; factIds: string[] }[];
  /** Statements dropped because they cited no fact that exists. */
  removedStatements: number;
  failure: string | null;
  cached: boolean;
  callId: string | null;
}

/** `POST /workspaces/{key}/history/account` and `POST /objects/{type}/{id}/history/account` (0.16 AO2). */
export interface HistoryAccountRequest {
  /** Included. */
  since: string;
  /** Not included. */
  until: string;
  /** An IANA name: where a day begins. */
  timeZone?: string;
  language?: string;
}

/** Where a fact leads: the changes it counted (`query` narrows `GET /changes`, or a record's history), a change set or a job. */
export interface HistoryFactLink {
  kind: "changes" | "history" | "changeSet" | "job" | "publication";
  id: string | null;
  query: {
    kind?: string[] | string;
    objectTypeKey?: string;
    relationTypeKey?: string;
    causeId?: string;
    action?: string;
    attributeKey?: string;
    live?: boolean;
  } | null;
}

/** One fact of an account of history, counted by the engine over every live change of the period. */
export interface HistoryFact {
  id: string;
  kind: "records" | "fields" | "relationships" | "source" | "people" | "changeSet" | "publication" | "model";
  text: string;
  count: number | null;
  keys: Record<string, unknown>;
  link: HistoryFactLink | null;
}

/** The account of what changed in a period: every fact, and the statements that word them (empty when the provider failed). */
export interface HistoryAccount {
  scope: "workspace" | "record";
  since: string;
  until: string;
  timeZone: string;
  facts: HistoryFact[];
  statements: { text: string; factIds: string[] }[];
  removedStatements: number;
  failure: string | null;
  cached: boolean;
  callId: string | null;
}
