/**
 * The job limits as Settings shows them, on Deployment and on Jobs (one list, U-D14), and the change
 * feed's retention, on Deployment and on Consumer APIs, whose consumers follow the feed.
 */

import { count } from "@/lib/count";
import type { CapabilitiesResponse } from "@/types";
import type { DescriptionItem } from "@/ui/DescriptionList";

export const bytes = (value: number) =>
  value >= 1024 * 1024 && value % (1024 * 1024) === 0 ? `${count(value / (1024 * 1024))} MB` : `${count(value)} bytes`;

export function jobLimitItems(capabilities: CapabilitiesResponse): DescriptionItem[] {
  const jobs = capabilities.integrationJobs.limits;
  return [
    { term: "Inline batch", value: `${count(jobs.batchMaxItems)} items, ${bytes(jobs.batchMaxBytes)}` },
    { term: "Atomic batch", value: `${count(jobs.atomicJobMaxItems)} items` },
    {
      term: "Background batch",
      value: `${count(jobs.backgroundJobMaxItems)} items, ${bytes(jobs.backgroundBatchMaxBytes)}`,
    },
    { term: "Chunk", value: `${count(jobs.chunkItems)} items` },
    { term: "Import file", value: bytes(jobs.importMaxBytes) },
    { term: "Preview", value: `${count(jobs.previewMaxItems)} items` },
    { term: "Jobs kept", value: `${count(jobs.retentionDays)} days` },
  ];
}

export function feedRetentionItem(capabilities: CapabilitiesResponse): DescriptionItem {
  return { term: "Change feed kept", value: `${count(capabilities.changeFeed.retentionDays)} days` };
}
