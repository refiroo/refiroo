import { api } from "@/api/client";
import { everyPage } from "@/lib/everyPage";

/**
 * Every workspace the caller may list, page by page to the end (ADR-042: few, but never cut at a
 * page). `status` defaults to the engine's "active"; `holding` keeps those where the caller holds
 * the action group. A failed page rejects the read; each caller says its own failure.
 */
export const allWorkspaces = (options: { status?: "active" | "retired" | "all"; holding?: string } = {}) =>
  everyPage((cursor) => api.workspaces({ ...options, cursor }));
