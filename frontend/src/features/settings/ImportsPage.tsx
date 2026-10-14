/**
 * Settings › Integration › Imports (0.10 A5c, D85): the instance's stored import profiles, and a
 * profile's page for the next version of its workbook (J35). The list names each profile, the types
 * it loads, whether it holds against the active release and its latest file. A profile's page has
 * Upload the next version (the file is profiled, then checked: D83), the check's report, and Load
 * into a change set, whose review lists only what the file changes. A change the report offers
 * (accept a rename, ignore a new column, keep or delete missing records) saves the profile and
 * checks the file again.
 */

import { useCallback, useEffect, useState } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import { formatServerTime } from "@/lib/dates";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { objectTypeFor } from "@/model/lookup";
import { routePath } from "@/routing/routes";
import type {
  EngineModel,
  ImportProfile,
  ImportProfileSource,
  ProfileCheck,
  RouteState,
  SettingsRoute,
  SourceFile,
} from "@/types";
import { EmptyState } from "@/ui/EmptyState";
import { InlineError } from "@/ui/InlineError";
import { Notice } from "@/ui/Notice";
import { RouteLink } from "@/ui/RouteLink";
import { Section } from "@/ui/Section";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { SettingsTable } from "@/ui/SettingsTable";
import { Skeleton } from "@/ui/Skeleton";
import { StatusPill } from "@/ui/StatusPill";
import { isFinal, useJobStream } from "@/features/jobs/useJobStream";
import { AddWorkbookDialog } from "@/features/model-editor/AddWorkbookDialog";
import { CheckRowsDialog, differences, loadable, ProfileCheckReport, type CheckRows } from "./ProfileCheckReport";
import { ProfileLoadDialog } from "./ProfileLoadDialog";
import { ignoreColumn, renameColumn, setMissing } from "./profileEdits";
import { useCapabilities } from "./useSystem";

const IMPORTS: Extract<SettingsRoute, { page: "imports" }> = { kind: "settings", page: "imports" };

export function ImportsPage({
  model,
  route,
  defaultWorkspace,
  onNavigate,
}: {
  model: EngineModel;
  route: Extract<SettingsRoute, { page: "imports" }>;
  defaultWorkspace: string;
  onNavigate: (route: RouteState) => void;
}) {
  const typeName = (key: string) => objectTypeFor(model, key)?.name ?? key;
  if (route.profileKey)
    return (
      <ProfilePage
        key={route.profileKey}
        profileKey={route.profileKey}
        typeName={typeName}
        defaultWorkspace={defaultWorkspace}
        back={{ href: routePath(IMPORTS), onNavigate: () => onNavigate(IMPORTS) }}
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
    );
  return <ProfileList typeName={typeName} onNavigate={onNavigate} />;
}

function loads(profile: ImportProfile, typeName: (key: string) => string): string {
  return [...new Set(profile.sources.map((source) => typeName(source.objectTypeKey)))].join(", ");
}

function ProfileList({
  typeName,
  onNavigate,
}: {
  typeName: (key: string) => string;
  onNavigate: (route: RouteState) => void;
}) {
  const feed = useCursorFeed((cursor) => api.importProfiles(cursor), []);
  return (
    <SettingsLayout
      eyebrow="Integration"
      title="Imports"
      description="Import profiles say how a workbook's sheets and columns load into the model. Upload the next version of a workbook to its profile to see what changed before loading it."
    >
      <Section title="Import profiles">
        {feed.error ? (
          <InlineError message={feed.error} onRetry={feed.retry} />
        ) : feed.loading && feed.items.length === 0 ? (
          <Skeleton label="Loading the import profiles" lines={4} />
        ) : feed.items.length === 0 ? (
          <EmptyState>
            No import profiles yet. A profile is saved when a model draft holding a workbook is installed from the model
            editor, or with <code>POST /api/v1/import-profiles</code>.
          </EmptyState>
        ) : (
          <SettingsTable
            label="Import profiles"
            columns={["Profile", "Loads", "Against the active release", "Latest file"]}
          >
            {feed.items.map((profile) => {
              const next: RouteState = { ...IMPORTS, profileKey: profile.key };
              return (
                <tr key={profile.key}>
                  <th scope="row">
                    <RouteLink className="job-name" href={routePath(next)} onNavigate={() => onNavigate(next)}>
                      {profile.name}
                      <code>{profile.key}</code>
                    </RouteLink>
                  </th>
                  <td data-label="Loads">{loads(profile, typeName)}</td>
                  <td data-label="Against the active release">
                    <StatusPill tone={profile.valid ? "success" : "error"}>
                      {profile.valid ? "Valid" : "Needs a fix"}
                    </StatusPill>
                  </td>
                  <td data-label="Latest file">
                    <LatestFile profileKey={profile.key} />
                  </td>
                </tr>
              );
            })}
          </SettingsTable>
        )}
        {feed.hasMore && !feed.error && (
          <button className="load-more" disabled={feed.loading} onClick={feed.loadMore}>
            Load more profiles
          </button>
        )}
      </Section>
    </SettingsLayout>
  );
}

function LatestFile({ profileKey }: { profileKey: string }) {
  const [file, setFile] = useState<SourceFile | null>();
  useEffect(() => {
    let cancelled = false;
    api
      .latestProfileFile(profileKey)
      .then((found) => {
        if (!cancelled) setFile(found ?? null);
      })
      .catch(() => {
        if (!cancelled) setFile(null);
      });
    return () => {
      cancelled = true;
    };
  }, [profileKey]);
  if (file === undefined) return <span className="muted">…</span>;
  if (file === null) return <span className="muted">None uploaded to the profile</span>;
  return (
    <span>
      {file.name} · {formatServerTime(file.uploadedAt)}
    </span>
  );
}

type Dialog = { kind: "upload" } | { kind: "load" } | CheckRows;

function ProfilePage({
  profileKey,
  typeName,
  defaultWorkspace,
  back,
  onOpenReview,
}: {
  profileKey: string;
  typeName: (key: string) => string;
  defaultWorkspace: string;
  back: { href: string; onNavigate: () => void };
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

  const readCheck = useCallback(async () => {
    try {
      const found = await api.profileCheck(profileKey);
      setCheck(found);
      setFollowing(found.state === "checking" ? found.jobId : undefined);
    } catch (cause) {
      if (isApiError(cause, "PROFILE_CHECK_NOT_FOUND")) setCheck(null);
      else throw cause;
    }
  }, [profileKey]);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.importProfile(profileKey), api.latestProfileFile(profileKey)])
      .then(async ([found, latest]) => {
        if (cancelled) return;
        setProfile(found);
        setFile(latest ?? null);
        if (latest && !["completed", "failed", "cancelled", "expired"].includes(latest.profile.state)) {
          // Still being profiled: its check follows once it is.
          setFollowing(latest.profile.jobId ?? undefined);
          return;
        }
        await readCheck();
      })
      .catch((cause) => {
        if (!cancelled) setError(errorMessage(cause));
      });
    return () => {
      cancelled = true;
    };
  }, [profileKey, readCheck, attempt]);

  // The profiling job, then the check's: when one ends, read the file and the check again (the check
  // follows the profiling).
  useJobStream(following, (job) => {
    if (!isFinal(job)) return;
    Promise.all([api.latestProfileFile(profileKey), readCheck()])
      .then(([latest]) => setFile(latest ?? null))
      .catch((cause) => setError(errorMessage(cause)));
  });

  async function save(sources: ImportProfileSource[]) {
    if (!profile) return;
    setSaving(true);
    setSaveError("");
    try {
      setProfile(await api.updateImportProfile(profile, sources));
      const started = await api.runProfileCheck(profileKey);
      setCheck(started);
      setFollowing(started.jobId);
    } catch (cause) {
      setSaveError(errorMessage(cause));
    } finally {
      setSaving(false);
    }
  }

  const title = profile?.name ?? "Import profile";
  if (error)
    return (
      <SettingsLayout eyebrow={<RouteLink {...back}>Imports</RouteLink>} title={title}>
        <InlineError
          message={error}
          onRetry={() => {
            setError("");
            setAttempt((value) => value + 1);
          }}
        />
      </SettingsLayout>
    );
  if (!profile || file === undefined)
    return (
      <SettingsLayout eyebrow={<RouteLink {...back}>Imports</RouteLink>} title={title}>
        <Skeleton label="Loading the import profile" lines={6} />
      </SettingsLayout>
    );

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
    profile.valid ? "valid against the active release" : "needs a fix against the active release",
    file ? `latest file ${file.name}, uploaded ${formatServerTime(file.uploadedAt)}` : "no file uploaded yet",
  ].join(" · ");

  return (
    <SettingsLayout
      eyebrow={<RouteLink {...back}>Imports</RouteLink>}
      title={
        <>
          {profile.name} <code>{profile.key}</code>
        </>
      }
      description={description}
      actions={
        canWrite && (
          <>
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
          </>
        )
      }
    >
      {!file ? (
        <EmptyState>
          No workbook is uploaded to this profile yet. Upload the next version of the workbook it loads: it is checked
          against the profile before anything is written.
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
          onClose={() => setDialog(undefined)}
        />
      )}
      {(dialog?.kind === "list" || dialog?.kind === "rows") && (
        <CheckRowsDialog profileKey={profileKey} rows={dialog} onClose={() => setDialog(undefined)} />
      )}
    </SettingsLayout>
  );
}
