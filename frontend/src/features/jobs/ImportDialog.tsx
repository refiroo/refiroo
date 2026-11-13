/**
 * Start an import (0.9 J4, J27.13). From a collection the file loads into the page's data: its
 * workspace's live data or the change set shown (D89). From Settings › Jobs a workspace and its
 * live data or one of its change sets are chosen. The user picks a file, a stored profile or none,
 * the policy and what happens to records the file finds (D92); the import is always previewed
 * (D90), and the caller opens its job page (D91).
 */

import { useEffect, useRef, useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { everyPage } from "@/lib/everyPage";
import type {
  ChangeSet,
  EngineModel,
  ImportOnExisting,
  ImportPolicy,
  ImportProfile,
  Job,
  OtherWorkspaceIds,
} from "@/types";
import { Choice } from "@/ui/Choice";
import { FileField } from "@/ui/FileField";
import { FormField } from "@/ui/FormField";
import { WorkspaceField } from "@/ui/WorkspaceField";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { bytes } from "@/ui/limits";
import { useCapabilities } from "@/state/useSystem";
import {
  defaultOnExisting,
  importField,
  importRequest,
  keyless,
  newIdempotencyKey,
  profileProblems,
  profileSummary,
  type ImportContext,
  type ImportField,
} from "@/model/importRequest";

export interface ImportStart {
  /** The page's data; none lets the user choose a workspace and its data. */
  context?: ImportContext;
  /** A file already chosen, where the person came from the AI assistant's dialog (0.16 AP6a). */
  file?: File;
}

const ACCEPT = ".xlsx,.csv,.jsonl,.ndjson";
const LIVE = "live";

const OTHER_WORKSPACE: readonly (readonly [OtherWorkspaceIds, string])[] = [
  ["counterparts", "Load them as this workspace's own"],
  ["refuse", "Refuse them"],
];

const POLICIES: readonly (readonly [ImportPolicy, string])[] = [
  ["independent", "Load the rows that can load"],
  ["atomic", "Load nothing unless every row loads"],
];

/**
 * The profiles that can read this file for this workspace's model: those still valid under the
 * workspace's release (the server checks each, so another model's profiles are not among them). A
 * JSON Lines file is batch items and needs none; a CSV file is one table, read by a profile that
 * says so or has a single source; a workbook by any.
 */
export function profilesFor(profiles: readonly ImportProfile[], file: File | undefined): ImportProfile[] {
  if (!file) return [];
  const name = file.name.toLowerCase();
  if (name.endsWith(".jsonl") || name.endsWith(".ndjson")) return [];
  const valid = profiles.filter((item) => item.valid);
  if (name.endsWith(".csv")) return valid.filter((item) => item.csv || item.sources.length === 1);
  return valid;
}

export function ImportDialog({
  model,
  start,
  onClose,
  onStarted,
}: {
  model: EngineModel;
  start: ImportStart;
  onClose: () => void;
  onStarted: (job: Job) => void;
}) {
  const { capabilities } = useCapabilities();
  const [file, setFile] = useState<File | undefined>(start.file);
  const [profiles, setProfiles] = useState<ImportProfile[]>();
  // Undefined until the person chooses a profile or none: until then the file chooses for them.
  const [picked, setPicked] = useState<string>();
  const [policy, setPolicy] = useState<ImportPolicy>("independent");
  const [pickedOnExisting, setOnExisting] = useState<ImportOnExisting>();
  const [otherWorkspace, setOtherWorkspace] = useState<OtherWorkspaceIds>("counterparts");
  const [workspaceKey, setWorkspaceKey] = useState(start.context?.workspaceKey ?? "");
  const [changeSets, setChangeSets] = useState<ChangeSet[]>();
  const [data, setData] = useState(LIVE);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<{ field: ImportField; message: string; problems: string[] }>();
  // One key per distinct request, so a retried submission answers with the job the first created.
  const attempt = useRef<{ signature: string; key: string }>(undefined);

  useEffect(() => {
    let current = true;
    // Valid or not under the release of the workspace the file loads into (0.13 DOC11).
    everyPage((cursor) => api.importProfiles(cursor, workspaceKey || undefined))
      .then((items) => current && setProfiles(items))
      .catch((cause) => current && setError({ field: "profile", message: errorMessage(cause), problems: [] }));
    return () => {
      current = false;
    };
  }, [workspaceKey]);

  useEffect(() => {
    if (start.context || !workspaceKey) return;
    let current = true;
    everyPage((cursor) => api.changeSets(workspaceKey, cursor))
      .then((items) => current && setChangeSets(items))
      .catch((cause) => current && setError({ field: "form", message: errorMessage(cause), problems: [] }));
    return () => {
      current = false;
    };
  }, [start.context, workspaceKey]);

  const chosenChangeSet = changeSets?.find((item) => item.id === data);
  const context: ImportContext | undefined =
    start.context ??
    (workspaceKey
      ? {
          workspaceKey,
          ...(chosenChangeSet
            ? { changeSet: { id: chosenChangeSet.id, name: chosenChangeSet.name, version: chosenChangeSet.version } }
            : {}),
        }
      : undefined);
  const matching = profilesFor(profiles ?? [], file);
  // One profile fits the file: it is chosen for the person; none or several leave the choice to them.
  const autoKey = matching.length === 1 ? matching[0].key : "";
  // A choice the new file no longer allows gives way to what the file fits.
  const stillFits = picked !== undefined && (picked === "" || matching.some((item) => item.key === picked));
  const profileKey = stillFits ? picked : autoKey;
  const profile = matching.find((item) => item.key === profileKey);
  // The default follows the file's kind: a profile's file carries no versions (D92).
  const onExisting = pickedOnExisting ?? defaultOnExisting(profileKey || null);

  function chooseProfile(key: string) {
    setPicked(key);
    setOnExisting(undefined);
  }

  async function submit() {
    if (!file || !context) return;
    const body = importRequest(context, profileKey || null, policy, onExisting, otherWorkspace);
    const signature = JSON.stringify([body, file.name, file.size, file.lastModified]);
    if (attempt.current?.signature !== signature) attempt.current = { signature, key: newIdempotencyKey() };
    setPending(true);
    setError(undefined);
    try {
      onStarted(await api.startImport(file, body, attempt.current.key));
    } catch (cause) {
      setError({ field: importField(cause), message: errorMessage(cause), problems: profileProblems(cause) });
    } finally {
      setPending(false);
    }
  }

  const fieldError = (field: ImportField) =>
    error?.field === field ? (
      <>
        {error.message}
        {error.problems.length > 0 && (
          <ul className="field-problems">
            {error.problems.map((problem) => (
              <li key={problem}>{problem}</li>
            ))}
          </ul>
        )}
      </>
    ) : undefined;
  const limit = capabilities ? `, up to ${bytes(capabilities.integrationJobs.limits.importMaxBytes)}` : "";
  const where = !context
    ? ""
    : context.changeSet
      ? `the change set “${context.changeSet.name ?? "Unnamed"}”`
      : "the workspace’s live data";

  return (
    <Modal title="Import" size="wide" busy={pending} onClose={onClose}>
      <form
        className="dialog-form"
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <section className="dialog-form-section" aria-labelledby="import-file">
          <h3 id="import-file">The file</h3>
          {!start.context && (
            <>
              <WorkspaceField
                holding="bulk"
                value={workspaceKey}
                onChange={(key) => {
                  // Only another workspace reads its change sets; the same one keeps those read.
                  if (key === workspaceKey) return;
                  setWorkspaceKey(key);
                  setChangeSets(undefined);
                  setData(LIVE);
                }}
                onError={(message) => setError({ field: "form", message, problems: [] })}
              />
              <FormField
                label="Load into"
                help="A change set keeps the import apart from live data until it is published."
              >
                {(control) => (
                  <select
                    {...control}
                    value={data}
                    disabled={!changeSets}
                    onChange={(event) => setData(event.target.value)}
                  >
                    <option value={LIVE}>Live data</option>
                    {(changeSets ?? []).map((changeSet) => (
                      <option key={changeSet.id} value={changeSet.id}>
                        Change set “{changeSet.name ?? "Unnamed"}”
                      </option>
                    ))}
                  </select>
                )}
              </FormField>
            </>
          )}
          <FormField
            label="File"
            help={`XLSX, CSV or JSON Lines${limit}. Loads into ${where || "the data chosen above"}.`}
            error={fieldError("file")}
          >
            {(control) => <FileField control={control} accept={ACCEPT} onFile={setFile} disabled={pending} />}
          </FormField>
          {(file || error?.field === "profile") && (
            <FormField
              label="Profile"
              help={
                profile
                  ? `${profile.key === autoKey ? "Chosen because it fits this file. " : ""}Reads ${profileSummary(model, profile)}.`
                  : "Without a profile: a workbook exported for people, read as it was written; a JSON Lines file of batch items; or a table an export wrote."
              }
              error={fieldError("profile")}
            >
              {(control) => (
                <select
                  {...control}
                  value={profileKey}
                  disabled={!profiles}
                  onChange={(event) => chooseProfile(event.target.value)}
                >
                  <option value="">None</option>
                  {matching.map((item) => (
                    <option key={item.key} value={item.key}>
                      {item.name}
                    </option>
                  ))}
                </select>
              )}
            </FormField>
          )}
          {profile && keyless(profile) && (
            <Notice tone="warning" title="This profile has no key">
              Rows are not matched to records already there, so sending the file twice creates its records twice.
            </Notice>
          )}
        </section>

        <details className="dialog-form-section plain-import-options">
          <summary>Options</summary>
          <FormField label="Rows that cannot load" group>
            {() => <Choice name="import-policy" value={policy} options={POLICIES} onChange={setPolicy} />}
          </FormField>
          <FormField
            label="Records the file finds"
            help={
              profileKey
                ? "A supplier file carries no versions: updating overwrites the record as it is now."
                : "An exported table carries each record's version: records changed since the export are refused unless updated anyway."
            }
            group
          >
            {() => (
              <Choice
                name="import-existing"
                value={onExisting}
                options={[
                  ["overwrite", profileKey ? "Update them" : "Update them anyway"],
                  ["reject", profileKey ? "Refuse their rows" : "Only if unchanged since the export"],
                ]}
                onChange={setOnExisting}
              />
            )}
          </FormField>
          <FormField
            label="Records of another workspace"
            help="A file may name records of another workspace by their IDs, as its export does. Loaded as this workspace's own, each becomes a record here, found again when the file is sent again."
            group
          >
            {() => (
              <Choice
                name="import-other-workspace"
                value={otherWorkspace}
                options={OTHER_WORKSPACE}
                onChange={setOtherWorkspace}
              />
            )}
          </FormField>
        </details>
        <p className="admin-hint">
          Nothing is written yet: the preview shows what loading would do, then you confirm it.
        </p>

        {error?.field === "form" && (
          <Notice tone="error" title="The import was not started">
            {error.message}
          </Notice>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" disabled={pending} onClick={onClose}>
            Cancel
          </button>
          <button className="primary" disabled={pending || !file || !context}>
            {pending ? "Sending…" : "Preview"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
