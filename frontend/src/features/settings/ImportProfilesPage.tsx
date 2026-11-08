/**
 * Settings › Data operations › Import profiles (0.10 A5c, D85): the instance's stored import profiles, and a
 * profile's page for the next version of its workbook (J35). The list names each profile, the types
 * it loads, whether it holds against the active release and its latest file. A profile's page has
 * Upload the next version (the file is profiled, then checked: D83), the check's report, and Load
 * into a change set, whose review lists only what the file changes. A change the report offers
 * (accept a rename, ignore a new column, keep or delete missing records) saves the profile and
 * checks the file again.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import { formatServerTime } from "@/lib/dates";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { objectTypeFor } from "@/model/lookup";
import type {
  EngineModel,
  ImportProfile,
  ImportProfileLastLoad,
  ImportProfileSource,
  ProfileCheck,
  RouteState,
  SettingsRoute,
  SourceFile,
} from "@/types";
import { DescriptionList } from "@/ui/DescriptionList";
import { EmptyState } from "@/ui/EmptyState";
import { InlineError } from "@/ui/InlineError";
import { Notice } from "@/ui/Notice";
import { Section } from "@/ui/Section";
import { CatalogueEntry, CatalogueLayout } from "@/ui/CatalogueLayout";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { Skeleton } from "@/ui/Skeleton";
import { StatusPill } from "@/ui/StatusPill";
import { isFinal, useJobStream } from "@/features/jobs/useJobStream";
import { AddWorkbookDialog } from "@/features/model-editor/AddWorkbookDialog";
import { CheckRowsDialog, differences, loadable, ProfileCheckReport, type CheckRows } from "./ProfileCheckReport";
import { ProfileLoadDialog } from "./ProfileLoadDialog";
import { ignoreColumn, renameColumn, setMissing } from "./profileEdits";
import { count } from "./limits";
import { useCapabilities } from "./useSystem";

const IMPORTS: Extract<SettingsRoute, { page: "import-profiles" }> = { kind: "settings", page: "import-profiles" };

export function ImportProfilesPage({
  model,
  route,
  defaultWorkspace,
  onNavigate,
}: {
  model: EngineModel;
  route: Extract<SettingsRoute, { page: "import-profiles" }>;
  defaultWorkspace: string;
  onNavigate: (route: RouteState) => void;
}) {
  const typeName = (key: string) => objectTypeFor(model, key)?.name ?? key;
  const feed = useCursorFeed((cursor) => api.importProfiles(cursor), []);
  const selected = route.profileKey;
  const empty = !feed.loading && !feed.error && feed.items.length === 0;

  const catalogue = (
    <nav className="model-catalogue" aria-label="Import profiles">
      <section>
        <h2 className="nav-label">
          Profiles <span>{feed.items.length}</span>
        </h2>
        {feed.items.map((profile) => (
          <CatalogueEntry
            key={profile.key}
            icon="document"
            title={profile.name}
            subtitle={
              profile.lastLoad
                ? `Loaded ${formatServerTime(profile.lastLoad.createdAt)} · ${loadOutcome(profile.lastLoad)}`
                : "Not loaded yet"
            }
            current={selected === profile.key}
            onSelect={() => onNavigate({ ...IMPORTS, profileKey: profile.key })}
            pill={
              <StatusPill tone={profile.valid ? "success" : "error"}>
                {profile.valid ? "Valid" : "Needs a fix"}
              </StatusPill>
            }
          />
        ))}
        {feed.loading && !feed.items.length && <p className="explorer-empty">Loading import profiles…</p>}
        {feed.error && (
          <div className="catalogue-error">
            <InlineError message={feed.error} onRetry={feed.retry} />
          </div>
        )}
        {feed.hasMore && (
          <button className="load-more" disabled={feed.loading} onClick={feed.loadMore}>
            Load more profiles
          </button>
        )}
      </section>
    </nav>
  );

  return (
    <SettingsLayout
      eyebrow="Data operations"
      title="Import profiles"
      description="Import profiles say how a workbook's sheets and columns load into the model. Upload the next version of a workbook to its profile to see what changed before loading it."
    >
      {empty ? (
        <EmptyState>
          No import profiles yet. A profile is saved when a model draft holding a workbook is installed from the model
          editor, or with <code>POST /api/v1/import-profiles</code>.
        </EmptyState>
      ) : (
        <CatalogueLayout
          catalogue={catalogue}
          hasSelection={Boolean(selected)}
          backLabel="All import profiles"
          onBack={() => onNavigate(IMPORTS)}
        >
          {selected ? (
            <ProfileDetail
              key={selected}
              profileKey={selected}
              typeName={typeName}
              defaultWorkspace={defaultWorkspace}
              job={(jobId) => onNavigate({ kind: "settings", page: "jobs", jobId })}
              onChanged={(changed) =>
                feed.setItems((items) => items.map((item) => (item.key === changed.key ? changed : item)))
              }
              onOpenReview={({ applicationKey, workspaceKey, changeSetId }) =>
                onNavigate({
                  kind: "changeSetChanges",
                  applicationKey,
                  workspaceKey,
                  changeSetId,
                  tab: "records",
                  changeKinds: [],
                })
              }
            />
          ) : (
            <div className="panel-state">Choose an import profile.</div>
          )}
        </CatalogueLayout>
      )}
    </SettingsLayout>
  );
}

function loads(profile: ImportProfile, typeName: (key: string) => string): string {
  return [...new Set(profile.sources.map((source) => typeName(source.objectTypeKey)))].join(", ");
}

/** What became of a load, in words (0.10 A5c). */
export function loadOutcome(load: ImportProfileLastLoad): string {
  switch (load.outcome) {
    case "live":
      return "loaded into live data";
    case "inChangeSet":
      return "in a change set, not published yet";
    case "published":
      return "published";
    case "discarded":
      return "its change set was discarded: nothing of it is live";
    default:
      return load.state === "failed" ? "the load failed" : `the load is ${load.state}`;
  }
}

/** What the load did with the rows, in words. */
export function loadCounts(load: ImportProfileLastLoad): string {
  const { created, updated, deleted, rejected } = load.counts;
  return [
    `${count(created)} created`,
    `${count(updated)} updated`,
    ...(deleted ? [`${count(deleted)} deleted`] : []),
    `${count(rejected)} refused`,
  ].join(", ");
}

type Dialog = { kind: "upload" } | { kind: "load" } | CheckRows;

function ProfileDetail({
  profileKey,
  typeName,
  defaultWorkspace,
  job,
  onChanged,
  onOpenReview,
}: {
  profileKey: string;
  typeName: (key: string) => string;
  defaultWorkspace: string;
  /** Open a job's page. */
  job: (jobId: string) => void;
  /** The profile changed here: the catalogue shows it too. */
  onChanged: (profile: ImportProfile) => void;
  onOpenReview: (target: { applicationKey: string; workspaceKey: string; changeSetId: string }) => void;
}) {
  const { capabilities } = useCapabilities();
  const canWrite = capabilities?.integrationJobs.createJobs ?? false;
  const [profile, setProfile] = useState<ImportProfile>();
  const [file, setFile] = useState<SourceFile | null>();
  const [check, setCheck] = useState<ProfileCheck | null>();
  const [following, setFollowing] = useState<string>();
  const [error, setError] = useState("");
  const [saveError, setSaveError] = useState("");
  const [saving, setSaving] = useState(false);
  const [dialog, setDialog] = useState<Dialog>();
  const [attempt, setAttempt] = useState(0);

  // Each read of the check, and each change that sets it (a save, an upload), takes the next number;
  // a read answering after a newer one began is dropped. A late answer saying "checking" for a check
  // whose stream had ended left the page checking for good (0.10 R, found by the composed runner).
  const reads = useRef(0);
  // A profile is instance-wide, its files and checks are per workspace (0.12 E1, F5): the check is
  // read in the workspace of the profile's latest file, the page's workspace without one.
  const readCheck = useCallback(
    async (workspaceKey: string) => {
      const read = ++reads.current;
      try {
        const found = await api.profileCheck(profileKey, workspaceKey);
        if (read !== reads.current) return;
        setCheck(found);
        setFollowing(found.state === "checking" ? found.jobId : undefined);
      } catch (cause) {
        if (read !== reads.current) return;
        if (isApiError(cause, "PROFILE_CHECK_NOT_FOUND")) setCheck(null);
        else throw cause;
      }
    },
    [profileKey],
  );

  useEffect(() => {
    let cancelled = false;
    // The profile is read, and later saved, under the workspace the comparison is for: the one of
    // its latest file, the page's without one (0.13 DOC11).
    api
      .latestProfileFile(profileKey)
      .then(async (latest) => {
        const found = await api.importProfile(profileKey, latest?.workspaceKey ?? defaultWorkspace);
        if (cancelled) return;
        setProfile(found);
        setFile(latest ?? null);
        if (latest && !["completed", "failed", "cancelled", "expired"].includes(latest.profile.state)) {
          // Still being profiled: its check follows once it is.
          setFollowing(latest.profile.jobId ?? undefined);
          return;
        }
        await readCheck(latest?.workspaceKey ?? defaultWorkspace);
      })
      .catch((cause) => {
        if (!cancelled) setError(errorMessage(cause));
      });
    return () => {
      cancelled = true;
    };
  }, [profileKey, defaultWorkspace, readCheck, attempt]);

  // The profiling job, then the check's: when one ends, read the file and the check again (the check
  // follows the profiling).
  useJobStream(following, (job) => {
    if (!isFinal(job)) return;
    api
      .latestProfileFile(profileKey)
      .then(async (latest) => {
        setFile(latest ?? null);
        await readCheck(latest?.workspaceKey ?? defaultWorkspace);
      })
      .catch((cause) => setError(errorMessage(cause)));
  });

  async function save(sources: ImportProfileSource[]) {
    if (!profile) return;
    setSaving(true);
    setSaveError("");
    try {
      const saved = await api.updateImportProfile(profile, sources, file?.workspaceKey ?? defaultWorkspace);
      setProfile(saved);
      onChanged(saved);
      const started = await api.runProfileCheck(profileKey, file?.workspaceKey ?? defaultWorkspace);
      reads.current += 1;
      setCheck(started);
      setFollowing(started.jobId);
    } catch (cause) {
      setSaveError(errorMessage(cause));
    } finally {
      setSaving(false);
    }
  }

  if (error)
    return (
      <InlineError
        message={error}
        onRetry={() => {
          setError("");
          setAttempt((value) => value + 1);
        }}
      />
    );
  if (!profile || file === undefined) return <Skeleton label="Loading the import profile" lines={6} />;

  const checking = Boolean(following) || check?.state === "checking";
  const checked = check && check.state === "completed" && check.sourceFileId === file?.id ? check : undefined;
  const found = checked ? differences(checked) : 0;
  const canLoad = Boolean(file && checked && loadable(checked));
  const firstFigures = checked?.dryRun?.sources;
  const summary = firstFigures
    ? `The check found ${firstFigures.reduce((sum, item) => sum + item.records.created, 0)} records to add, ${firstFigures.reduce((sum, item) => sum + item.records.updated, 0)} to change and ${checked?.sources.reduce((sum, item) => sum + item.missingRecords, 0)} missing from the file.`
    : "";
  const description = [
    `Loads ${loads(profile, typeName)}`,
    profile.valid ? "fits the active release" : "needs a fix against the active release",
    ...(file ? [`next version ${file.name}, uploaded ${formatServerTime(file.uploadedAt)}`] : []),
  ].join(" · ");
  const last = profile.lastLoad;

  return (
    <div className="model-editor-stack import-detail">
      <header className="model-detail-header">
        <div>
          <h2>{profile.name}</h2>
          <p>
            <code>{profile.key}</code> · {description}
          </p>
        </div>
        <StatusPill tone={profile.valid ? "success" : "error"}>{profile.valid ? "Valid" : "Needs a fix"}</StatusPill>
      </header>
      {canWrite && (
        <div className="model-actions">
          <button type="button" className="secondary" onClick={() => setDialog({ kind: "upload" })}>
            Upload the next version…
          </button>
          <button
            type="button"
            className="primary"
            disabled={!canLoad || checking}
            onClick={() => setDialog({ kind: "load" })}
          >
            Load into a change set…
          </button>
        </div>
      )}
      <Section
        title="Last load"
        headingLevel={3}
        actions={
          last &&
          (last.outcome === "inChangeSet" && last.changeSetId ? (
            <button
              type="button"
              className="secondary"
              onClick={() =>
                onOpenReview({
                  applicationKey: profile.sources[0].applicationKey,
                  workspaceKey: last.workspaceKey,
                  changeSetId: last.changeSetId!,
                })
              }
            >
              Open the change set review
            </button>
          ) : (
            <button type="button" className="secondary" onClick={() => job(last.jobId)}>
              Open the load's job
            </button>
          ))
        }
      >
        {last ? (
          <DescriptionList
            className="compact"
            items={[
              { term: "File", value: last.fileName ?? "A file sent with the import" },
              {
                term: "Loaded",
                value: `${formatServerTime(last.createdAt)} into ${last.changeSetId ? "a change set" : "live data"} of ${last.workspaceKey}`,
              },
              { term: "Rows", value: loadCounts(last) },
              { term: "Now", value: loadOutcome(last) },
            ]}
          />
        ) : (
          <p className="section-description">
            Not loaded through this profile yet, or the load's job has passed its retention.
          </p>
        )}
      </Section>
      {!file ? (
        <EmptyState>
          {last
            ? `No next version is uploaded yet. When ${last.fileName ?? "the workbook"} changes, upload the new file: it is checked against the profile and what it loaded last before anything is written.`
            : "Upload the workbook this profile loads: it is checked against the profile before anything is written."}
        </EmptyState>
      ) : checking ? (
        <Notice tone="info">
          <span role="status">Checking {file.name}: profiling its sheets, then reading it through the profile…</span>
        </Notice>
      ) : file.profile.state === "failed" ? (
        <Notice tone="error" title="The file could not be read">
          {file.profile.error?.message ?? `${file.name} could not be profiled.`}
        </Notice>
      ) : !checked ? (
        <Notice
          tone={check?.state === "failed" ? "error" : "info"}
          title={check?.state === "failed" ? "The check failed" : undefined}
        >
          {(check?.sourceFileId === file.id && check.error?.message) || `${file.name} has not been checked.`}
        </Notice>
      ) : (
        <Notice tone={found ? "warning" : "success"}>
          {file.name} checked:{" "}
          {found
            ? `${found} ${found === 1 ? "difference needs" : "differences need"} a look before loading.`
            : "it loads as the profile reads it."}{" "}
          Nothing has been written.
          {!loadable(checked) && " Accept or fix the columns and the profile's problems to load it."}
        </Notice>
      )}
      {saveError && (
        <Notice tone="error" title="The profile was not saved">
          {saveError}
        </Notice>
      )}
      {checked && (
        <ProfileCheckReport
          check={checked}
          typeName={typeName}
          busy={saving || !canWrite}
          onRename={(source, from, to) => void save(renameColumn(profile.sources, source.profileSource, from, to))}
          onIgnore={(source, column) => void save(ignoreColumn(profile.sources, source.profileSource, column))}
          onMissing={(source, missing) => void save(setMissing(profile.sources, source.profileSource, missing))}
          onOpen={setDialog}
        />
      )}
      {checked && (
        <p className="section-description">
          Loading opens a new change set; its review shows only these differences. Deleting missing records is the
          profile's choice and happens only in a change set.
        </p>
      )}
      {dialog?.kind === "upload" && (
        <AddWorkbookDialog
          owner={{ profileKey }}
          replaces={file?.name}
          defaultWorkspace={check?.workspaceKey ?? file?.workspaceKey ?? defaultWorkspace}
          title="Upload the next version"
          description="Checked against the profile before anything is written: new, missing and renamed columns, new values, names that drifted and records missing from the file."
          onUploaded={(uploaded) => {
            setFile(uploaded);
            reads.current += 1;
            setCheck(undefined);
            setFollowing(uploaded.profile.jobId ?? undefined);
          }}
          onClose={() => setDialog(undefined)}
        />
      )}
      {dialog?.kind === "load" && file && checked && (
        <ProfileLoadDialog
          profileKey={profileKey}
          file={file}
          defaultWorkspace={checked.workspaceKey}
          summary={summary}
          onOpenReview={({ workspaceKey, changeSetId }) =>
            onOpenReview({ applicationKey: profile.sources[0].applicationKey, workspaceKey, changeSetId })
          }
          onClose={() => {
            setDialog(undefined);
            // The load is the profile's last one now.
            void api.importProfile(profileKey, checked.workspaceKey).then(
              (found) => {
                setProfile(found);
                onChanged(found);
              },
              () => undefined,
            );
          }}
        />
      )}
      {(dialog?.kind === "list" || dialog?.kind === "rows") && (
        <CheckRowsDialog
          profileKey={profileKey}
          workspaceKey={check?.workspaceKey ?? file?.workspaceKey ?? defaultWorkspace}
          rows={dialog}
          onClose={() => setDialog(undefined)}
        />
      )}
    </div>
  );
}
