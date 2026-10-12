/**
 * The draft's source file as the editor needs it (0.10 A5b): the draft's profile, read again after
 * every step (its warnings follow the model's, A5a); the file's profiling, followed until it is
 * stored; its sheets, and each sheet's columns once opened; and the draft's latest dry run,
 * followed while it checks (D79). Jobs are followed over their event streams, never polled.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import type { DraftProfile, DryRun, SourceColumn, SourceFile, SourceSheet } from "@/types";
import { isFinal, useJobStream } from "@/features/jobs/useJobStream";

export interface DraftSource {
  /** The draft's profile and its file; undefined until first read. */
  profile?: DraftProfile;
  /** The file, read while its profiling runs, for its job. */
  file?: SourceFile;
  sheets: SourceSheet[];
  columns: (sheet: string) => SourceColumn[] | undefined;
  loadColumns: (sheet: string) => void;
  dryRun?: DryRun;
  /** Why the dry run cannot be read (not why there is none yet). */
  dryRunError: string;
  error: string;
  /** A step answered with a queued dry run: follow it. */
  dryRunQueued: (jobId: string) => void;
  /** A file was uploaded: read the profile again and follow its profiling. */
  uploaded: (file: SourceFile) => void;
  /** Read the profile and the dry run again, after an error. */
  retry: () => void;
}

export function useDraftSource(draftId: string, version: number | undefined): DraftSource {
  const [profile, setProfile] = useState<DraftProfile>();
  const [file, setFile] = useState<SourceFile>();
  // Read for one file: a newer file's sheets and columns replace them.
  const [sheetsRead, setSheets] = useState<{ file: string; items: SourceSheet[] }>();
  const [columnsRead, setColumns] = useState<{ file: string; bySheet: Record<string, SourceColumn[]> }>();
  const [dryRun, setDryRun] = useState<DryRun>();
  const [dryRunError, setDryRunError] = useState("");
  const [followDryRun, setFollowDryRun] = useState<string>();
  const [error, setError] = useState("");
  const fileId = profile?.sourceFile?.id;
  const profiled = profile?.sourceFile?.profile === "completed";
  const sheets = profiled && sheetsRead && sheetsRead.file === fileId ? sheetsRead.items : [];
  const columns = useMemo(
    () => (profiled && columnsRead && columnsRead.file === fileId ? columnsRead.bySheet : {}),
    [profiled, columnsRead, fileId],
  );

  const readProfile = useCallback(
    () =>
      api
        .modelDraftProfile(draftId)
        .then((next) => {
          setProfile(next);
          setError("");
        })
        .catch((cause) => setError(errorMessage(cause))),
    [draftId],
  );

  const readDryRun = useCallback(
    () =>
      api
        .modelDraftDryRun(draftId)
        .then((next) => {
          setDryRun(next);
          setDryRunError("");
          if (next.state === "checking") setFollowDryRun(next.jobId);
        })
        .catch((cause) => {
          if (isApiError(cause, "DRY_RUN_NOT_FOUND")) setDryRun(undefined);
          else setDryRunError(errorMessage(cause));
        }),
    [draftId],
  );

  // The profile after every step: the model kinds change it too (D78).
  useEffect(() => {
    if (version !== undefined) void readProfile();
  }, [readProfile, version]);

  // Only a draft with a workbook has a dry run to read.
  useEffect(() => {
    if (fileId) void readDryRun();
  }, [readDryRun, fileId]);

  // A file still profiling: read it for its job, and follow that job.
  useEffect(() => {
    if (!fileId || profiled) return;
    let cancelled = false;
    api
      .sourceFile(fileId)
      .then((next) => {
        if (!cancelled) setFile(next);
      })
      .catch((cause) => {
        if (!cancelled) setError(errorMessage(cause));
      });
    return () => {
      cancelled = true;
    };
  }, [fileId, profiled]);
  useJobStream(file && !profiled ? (file.profile.jobId ?? undefined) : undefined, (job) => {
    if (!isFinal(job)) return;
    void readProfile();
    // The first upload runs the dry run after profiling (D79).
    void readDryRun();
  });

  // The sheets, once the file is profiled.
  useEffect(() => {
    if (!fileId || !profiled) return;
    let cancelled = false;
    api
      .sourceSheets(fileId)
      .then((page) => {
        if (!cancelled) setSheets({ file: fileId, items: page.items });
      })
      .catch((cause) => {
        if (!cancelled) setError(errorMessage(cause));
      });
    return () => {
      cancelled = true;
    };
  }, [fileId, profiled]);

  const loadColumns = useCallback(
    (sheet: string) => {
      if (!fileId || columns[sheet]) return;
      api
        .sourceColumns(fileId, sheet)
        .then((page) =>
          setColumns((current) => ({
            file: fileId,
            bySheet: { ...(current?.file === fileId ? current.bySheet : {}), [sheet]: page.items },
          })),
        )
        .catch((cause) => setError(errorMessage(cause)));
    },
    [fileId, columns],
  );

  useJobStream(followDryRun, (job) => {
    if (!isFinal(job)) return;
    setFollowDryRun(undefined);
    void readDryRun();
  });

  const dryRunQueued = useCallback((jobId: string) => {
    setDryRun((current) => (current ? { ...current, state: "checking", jobId } : current));
    setFollowDryRun(jobId);
  }, []);
  const uploaded = useCallback(
    (next: SourceFile) => {
      setFile(next);
      void readProfile();
    },
    [readProfile],
  );

  return {
    profile,
    file,
    sheets,
    columns: (sheet) => columns[sheet],
    loadColumns,
    dryRun,
    dryRunError,
    error,
    dryRunQueued,
    uploaded,
    retry: () => {
      void readProfile();
      if (fileId) void readDryRun();
    },
  };
}
