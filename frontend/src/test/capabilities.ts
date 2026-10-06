import type { CapabilitiesResponse } from "@/types";

/** A `GET /capabilities` answer with model and workspace administration on or off as asked. */
export function capabilitiesFixture({
  manageModel = false,
  manageWorkspaces = true,
}: { manageModel?: boolean; manageWorkspaces?: boolean } = {}): CapabilitiesResponse {
  return {
    modelAdmin: {
      readReleases: true,
      manageDrafts: manageModel,
      install: manageModel,
      activate: manageModel,
      setting: "MODEL_ADMIN_MUTATIONS_ENABLED",
    },
    workspaceAdmin: { manageWorkspaces, setting: "WORKSPACE_ADMIN_MUTATIONS_ENABLED" },
    integrationJobs: {
      createJobs: true,
      runModes: ["inline", "background"],
      limits: {
        batchMaxItems: 1000,
        batchMaxBytes: 5 * 1024 * 1024,
        atomicJobMaxItems: 10000,
        backgroundJobMaxItems: 1000000,
        backgroundBatchMaxBytes: 50 * 1024 * 1024,
        chunkItems: 500,
        retentionDays: 7,
      },
      setting: "INTEGRATION_JOBS_ENABLED",
    },
    changeFeed: { retentionDays: 30 },
    consumerApi: { resolveMaxItems: 1000, setting: "CONSUMER_RESOLVE_MAX_ITEMS" },
    consumerSubscriptions: {
      manageSubscriptions: false,
      allowedHosts: [],
      delivery: {
        maxEvents: 100,
        maxBytes: 1024 * 1024,
        timeoutSeconds: 10,
        retryWaitsSeconds: [10, 60],
        laterWaitSeconds: 3600,
        retryHours: 72,
      },
      setting: "CONSUMER_SUBSCRIPTIONS_ENABLED",
    },
  };
}
