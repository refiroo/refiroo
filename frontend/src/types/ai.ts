/** The AI provider the application asks for proposals, and the calls it made (0.16 AP1). */

import type { PageNavigation } from "@/types/runtime";

/** What may leave the process: names and types, also sample values, also the values a feature needs. */
export type AiSendLevel = "structure" | "samples" | "values";
export type AiPurpose = "connectionTest" | "modelNames";
export type AiFailureKind = "unreachable" | "unauthorized" | "rateLimited" | "declined" | "malformed" | "failed";

/** What `GET /system` tells every signed-in person about the provider. */
export interface AiSystemInfo {
  configured: boolean;
  provider: string | null;
  sendLevel: AiSendLevel;
}

export interface AiFeature {
  purpose: AiPurpose;
  name: string;
  needs: AiSendLevel;
  available: boolean;
}

export interface AiCall {
  id: string;
  purpose: AiPurpose;
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
  outcome: "answered" | "failed";
  failureKind: AiFailureKind | null;
  failure: string | null;
  /** Kept only where the deployment keeps content (AI_LOG_CONTENT). */
  content: { instructions: unknown; context: unknown; answer: unknown } | null;
}

export interface AiStatus {
  configured: boolean;
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
  };
}

export interface AiCallPage extends PageNavigation {
  items: AiCall[];
}

/** Where an assistant proposal came from: carried in its evidence and in an applied step's origin. */
export interface AiOrigin {
  kind: "ai";
  provider: string;
  model: string | null;
  promptVersion: string;
  confidence: number;
  reason: string;
}
