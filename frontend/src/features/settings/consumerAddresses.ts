/**
 * Where a consumer API is reached, from its API index entry: the base URL its routes start with,
 * its OpenAPI document and its source on the reference page (`/docs/api?api=<slug>`, API.md). The
 * index names the document below the engine's root path, so it resolves against the API's origin.
 */

import { API_URL, api } from "@/api/client";
import type { ConsumerApiIndexEntry } from "@/types";

export const openapiUrl = (entry: ConsumerApiIndexEntry) => new URL(entry.openapi, API_URL).href;

export const baseUrl = (entry: ConsumerApiIndexEntry) => openapiUrl(entry).replace(/\/openapi\.json$/, "");

/** The reference page opened on one source: `management`, or `consumer-{consumerApi}-v{version}`. */
export const referenceUrl = (slug: string) => `${API_URL}/docs/api?api=${encodeURIComponent(slug)}`;

/** One operation on the reference page: its source, then the method and the path as the document
 * writes it (Scalar's address for an operation; it opens that source, scrolled to it). */
export const operationUrl = (slug: string, method: string, path: string) =>
  `${API_URL}/docs/api#${slug}/${method.toUpperCase()}${path}`;

export const consumerSlug = (entry: ConsumerApiIndexEntry) => `consumer-${entry.consumerApi}-v${entry.contractVersion}`;

/** Every entry of the API index, page after page. */
export async function allConsumerApis() {
  const entries: ConsumerApiIndexEntry[] = [];
  let cursor: string | undefined;
  do {
    const page = await api.consumerApis(cursor);
    entries.push(...page.items);
    cursor = page.nextCursor ?? undefined;
  } while (cursor);
  return entries;
}
