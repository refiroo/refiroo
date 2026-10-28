/** The AI routes Settings › AI reads and the test request it makes (0.16 AP1). */

import { request } from "@/api/client";
import type { AiCall, AiCallPage, AiStatus } from "@/types";

export const ai = {
  status: () => request<AiStatus>("/api/v1/ai/status"),
  /** The calls made, newest first. */
  calls: (options: { cursor?: string } = {}) => {
    const search = new URLSearchParams({ pageSize: "25" });
    if (options.cursor) search.set("cursor", options.cursor);
    return request<AiCallPage>(`/api/v1/ai/calls?${search}`);
  },
  /** A small request that sends no data of yours; answered or failed, either way it is a call. `409 AI_NOT_CONFIGURED` without a provider. */
  test: () => request<AiCall>("/api/v1/ai/test", { method: "POST", body: JSON.stringify({}) }),
};
