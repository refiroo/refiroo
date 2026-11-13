/**
 * A new workspace from a workbook (0.17 PL4): what the sheet asks of the engine, in the order the
 * existing routes need it, and what it shows of the answers. The workbook becomes a model draft (an
 * empty one, with the workbook uploaded, read and its proposals applied), its dry run is read for
 * "What refiroo found", and one route then installs the draft, creates the workspace and loads the
 * workbook. Nothing here decides what a column means: the engine proposes, the dry run counts every row.
 */

import { api } from "@/api/client";
import { emptyDraftModel } from "@/model/emptyDraftModel";
import { nameOfFile } from "@/ui/ProposeFields";
import { holdsAnywhere } from "@/state/permissions";
import type { CapabilitiesResponse, DryRun, DryRunSource, HeldAnywhere, ModelDraft } from "@/types";

/** The workspace's name a file suggests: "office-supplies.xlsx" becomes "Office supplies". */
export const workspaceNameOfFile = (fileName: string): string => nameOfFile(fileName);

/**
 * Whether the person may start a workspace from a workbook: every step the one route makes is theirs
 * (create the draft, install it, create the workspace, load the file), and the deployment lets each
 * step happen. Hidden, never disabled, when not (D323).
 */
export function startsFromWorkbook(
  held: HeldAnywhere[] | undefined,
  capabilities: CapabilitiesResponse | undefined,
): boolean {
  if (!held || !capabilities) return false;
  const instance = (group: string) => held.some((item) => item.key === group && item.instance);
  return (
    capabilities.workspaceAdmin.manageWorkspaces &&
    capabilities.modelAdmin.manageDrafts &&
    capabilities.modelAdmin.install &&
    capabilities.integrationJobs.createJobs &&
    instance("workspace-admin") &&
    holdsAnywhere(held, "model-authoring") &&
    (instance("model-install") || instance("model-release")) &&
    instance("bulk")
  );
}

/** Repeat `read` until `done` accepts its answer; gives up after `limitMs`. */
export async function waitFor<T>(
  read: () => Promise<T>,
  done: (value: T) => boolean,
  { every = 400, limitMs = 180_000 }: { every?: number; limitMs?: number } = {},
): Promise<T> {
  const until = Date.now() + limitMs;
  for (;;) {
    const value = await read();
    if (done(value)) return value;
    if (Date.now() > until) throw new Error("The workbook took too long to read. Try again in a moment.");
    await new Promise((resolve) => setTimeout(resolve, every));
  }
}

/** A draft made from a workbook, read and proposed, with the dry run of its rows. */
export interface LookedAt {
  draft: ModelDraft;
  /** The check of every row; none when refiroo found no list by itself, so nothing was there to check. */
  dryRun?: DryRun;
  /** Why rows were refused: a sentence per refusal code, from the first row refused for it. */
  reasons: Record<string, string>;
  /** The names of the draft's record types, by key. */
  typeNames: Record<string, string>;
}

/**
 * Make the draft the workbook asks for and check it: an empty model named for the workspace, the
 * workbook uploaded and read, the engine's proposals applied, and the dry run (which the applying
 * queues) read to its end. Every row is in the dry run's figures.
 */
export async function lookAtWorkbook(file: File, name: string, onStage: (stage: string) => void): Promise<LookedAt> {
  onStage("Reading the workbook");
  const created = await api.createModelDraft({
    name,
    model: emptyDraftModel(name, (await api.system()).schemaLanguages),
  });
  try {
    const stored = await api.uploadSourceFile(file, { owner: { draftId: created.id } });
    const profiled = await waitFor(
      () => api.sourceFile(stored.id),
      (source) => source.profile.state !== "queued" && source.profile.state !== "running",
    );
    if (profiled.profile.state !== "completed")
      throw new Error(profiled.profile.error?.message ?? "The workbook could not be read.");
    onStage("Finding its lists");
    await api.proposeFromWorkbook(created.id, { mode: "newApplication", applicationName: name });
    const inference = await waitFor(
      () => api.modelDraftInference(created.id, true),
      (found) => found.state !== "checking",
    );
    if (inference.state !== "completed")
      throw new Error(inference.error?.message ?? "refiroo could not find lists in the workbook.");
    // A workbook refiroo reads no list from by itself is not a failure: the draft goes on to the canvas,
    // where a sheet dragged onto the board makes a list of its rows.
    if (!inference.counts.open) {
      const untouched = await api.modelDraft(created.id);
      return { draft: untouched, reasons: {}, typeNames: typeNamesOf(untouched) };
    }
    const step = await api.applyProposals(created.id, (await api.modelDraft(created.id)).version);
    onStage("Checking every row");
    if (step.dryRun)
      await waitFor(
        () => api.modelDraftDryRun(created.id),
        (run) => run.state !== "checking",
      );
    const dryRun = await api.modelDraftDryRun(created.id);
    const draft = await api.modelDraft(created.id);
    return { draft, dryRun, reasons: await reasonsOf(created.id, dryRun), typeNames: typeNamesOf(draft) };
  } catch (cause) {
    // A draft made for a reading that failed is of no use to anyone: it does not stay behind.
    const left = await api.modelDraft(created.id).catch(() => undefined);
    if (left) await api.deleteModelDraft(left.id, left.version).catch(() => undefined);
    throw cause;
  }
}

async function reasonsOf(draftId: string, dryRun: DryRun): Promise<Record<string, string>> {
  const reasons: Record<string, string> = {};
  const codes = new Set(dryRun.summary?.sources.flatMap((source) => source.rejections.map((item) => item.code)));
  for (const code of codes) {
    const page = await api.modelDraftDryRunRows(draftId, { status: "rejected", code, pageSize: 1 });
    const message = page.items[0]?.outcomes.find((outcome) => outcome.error)?.error?.message;
    if (message) reasons[code] = message;
  }
  return reasons;
}

function typeNamesOf(draft: ModelDraft): Record<string, string> {
  const types = (draft.model.objectTypes ?? []) as { key: string; name?: string }[];
  return Object.fromEntries(types.map((type) => [type.key, type.name ?? type.key]));
}

/** What the dry run found in one list of the workbook. */
export interface Finding {
  key: string;
  list: string;
  sheet: string | null;
  rows: number;
  /** Rows that load: every row but the refused and the skipped. */
  loads: number;
  skipped: number;
  refused: { code: string; rows: number; reason?: string }[];
}

/** The lists the dry run found with what each loads and refuses, and the whole file's figures. */
export function findings(
  dryRun: DryRun,
  typeNames: Record<string, string>,
  reasons: Record<string, string> = {},
): { lists: Finding[]; rows: number; loads: number; refused: number } {
  const sources: DryRunSource[] = dryRun.summary?.sources ?? [];
  const lists = sources.map((source) => {
    const refusedRows = source.rejections.reduce((total, item) => total + item.rows, 0);
    const skipped = source.skippedRows ?? 0;
    return {
      key: `${source.source}`,
      list: typeNames[source.objectTypeKey] ?? source.objectTypeKey,
      sheet: source.sheet,
      rows: source.rows,
      loads: Math.max(source.rows - refusedRows - skipped, 0),
      skipped,
      refused: source.rejections.map((item) => ({
        code: item.code,
        rows: item.rows,
        ...(reasons[item.code] ? { reason: reasons[item.code] } : {}),
      })),
    };
  });
  return {
    lists,
    rows: dryRun.summary?.rows.total ?? lists.reduce((total, item) => total + item.rows, 0),
    loads: lists.reduce((total, item) => total + item.loads, 0),
    refused: lists.reduce((total, item) => total + item.refused.reduce((sum, row) => sum + row.rows, 0), 0),
  };
}

/** The load a workspace was just created for, until its page has shown it (kept for this page load). */
const loads = new Map<string, { jobId: string; file: string }>();

export function rememberWorkspaceLoad(workspaceKey: string, jobId: string, file: string): void {
  loads.set(workspaceKey, { jobId, file });
}

export function workspaceLoadOf(workspaceKey: string): { jobId: string; file: string } | undefined {
  return loads.get(workspaceKey);
}

export function forgetWorkspaceLoad(workspaceKey: string): void {
  loads.delete(workspaceKey);
}
