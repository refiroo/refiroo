/**
 * A workspace the engine cannot serve (0.12 UW1, D443 to D446): why, in plain words, the other
 * workspaces to continue in and, for someone who may install models, the repair that raises the
 * stored release to the schema language this version reads. One component for the not-opened
 * screen (`page`) and the workspace's Settings page (`banner`); the Workspaces list marks the
 * workspace with `UnavailableBadge`.
 */

import { useEffect, useRef, useState } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import { useHeldAnywhere } from "@/state/permissions";
import { workspaceModelLabel } from "@/ui/WorkspaceSelector";
import { forgetWorkspaceModel, workspaceModel } from "@/model/workspaceModels";
import { defaultRoute } from "@/routing/routes";
import type { ModelReleaseRaising, RouteState, Workspace, WorkspaceAvailability } from "@/types";
import { Card } from "@/ui/Card";
import { DescriptionList } from "@/ui/DescriptionList";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { PageHeader } from "@/ui/PageHeader";
import { StatusPill } from "@/ui/StatusPill";
import { allWorkspaces } from "@/api/allWorkspaces";

type Unavailable = Extract<WorkspaceAvailability, { state: "unavailable" }>;

/** The workspace's availability when the engine cannot serve it. */
export function unavailability(workspace: Workspace | undefined): Unavailable | undefined {
  return workspace?.availability?.state === "unavailable" ? workspace.availability : undefined;
}

/** The mark on a workspace in a list: text, not colour alone. */
export function UnavailableBadge() {
  return <StatusPill tone="warning">Cannot be opened</StatusPill>;
}

/** What happened, by reason. The other workspaces are said to work in each. */
export function unavailableExplanation(workspace: Workspace, availability: Unavailable): string {
  const model = workspaceModelLabel(workspace);
  const supported = availability.supportedSchemaVersions.join(", ");
  switch (availability.reason) {
    case "schemaLeftWindow":
      return `Its model, ${model}, was written in schema language ${availability.schemaVersion}, which this version of refiroo no longer reads (it reads ${supported}). Nothing was lost and nothing was changed. The other workspaces work.`;
    case "schemaAfterWindow":
      return `Its model, ${model}, was written by a newer version of refiroo (schema language ${availability.schemaVersion}). Run that version to open it. Nothing was lost and nothing was changed. The other workspaces work.`;
    default:
      return "Its model release is not valid, so refiroo cannot read it. People who manage models can see why in Settings › Model. The other workspaces work.";
  }
}

/** The workspace's start, under its own model (read afresh when it was just raised). */
async function startRouteOf(workspaceKey: string): Promise<RouteState> {
  return defaultRoute(await workspaceModel(workspaceKey), workspaceKey);
}

export function UnavailableWorkspace({
  workspace,
  form,
  onNavigate,
  onRaised,
}: {
  workspace: Workspace;
  /** `page` replaces the screen; `banner` sits at the top of the workspace's Settings page. */
  form: "page" | "banner";
  onNavigate: (route: RouteState) => void;
  /** Told once the workspace is served again, so the caller reads it afresh. */
  onRaised?: () => void;
}) {
  const [back, setBack] = useState(false);
  const availability = unavailability(workspace);

  if (back) {
    return (
      <div className={form === "page" ? "not-in-model" : undefined}>
        <Notice
          tone="success"
          title={`${workspace.label} is back.`}
          actions={
            <>
              <button
                type="button"
                className="secondary"
                onClick={() => onNavigate({ kind: "settings", page: "model" })}
              >
                Choose another model…
              </button>
              <button
                type="button"
                className="primary"
                onClick={() => void startRouteOf(workspace.key).then(onNavigate)}
              >
                Open {workspace.label}
              </button>
            </>
          }
        >
          It is served again, with its records, history and change sets as they were.
        </Notice>
      </div>
    );
  }
  if (!availability) return null;

  const title = `${workspace.label} cannot be opened`;
  const explanation = unavailableExplanation(workspace, availability);
  const repair =
    availability.reason === "schemaLeftWindow" ? (
      <RepairCard
        workspace={workspace}
        availability={availability}
        onRaised={() => {
          // The shell reads this workspace's model afresh, so opening it works at once.
          forgetWorkspaceModel(workspace.key);
          setBack(true);
          onRaised?.();
        }}
      />
    ) : undefined;

  if (form === "banner") {
    return (
      <div className="unavailable-banner">
        <Notice tone="warning" title={title}>
          {explanation}
        </Notice>
        {repair}
      </div>
    );
  }
  return (
    <section className="not-in-model unavailable-workspace" aria-label={title}>
      <PageHeader variant="plain" focusTitle title={title} description={explanation} />
      <div className="unavailable-cards">
        {repair}
        <ContinueElsewhere excludeKey={workspace.key} onNavigate={onNavigate} />
      </div>
    </section>
  );
}

/** "Bring it up to date": the repair for someone who may install models, a sentence for everyone else. */
function RepairCard({
  workspace,
  availability,
  onRaised,
}: {
  workspace: Workspace;
  availability: Unavailable;
  onRaised: () => void;
}) {
  const held = useHeldAnywhere();
  const [reviewing, setReviewing] = useState(false);
  const mayRaise = Boolean(held?.some((item) => item.key === "model-release" && item.instance));
  const target = availability.supportedSchemaVersions[availability.supportedSchemaVersions.length - 1];
  return (
    <Card title="Bring it up to date" as="section" className="unavailable-card" aria-busy={held === undefined}>
      {held === undefined ? null : !availability.raisable ? (
        <p>This model cannot be brought up to date automatically.</p>
      ) : mayRaise ? (
        <>
          <p>Raise the model to schema {target}. Its records, history and change sets stay as they are.</p>
          <div className="unavailable-actions wrap-row">
            <button type="button" className="primary" onClick={() => setReviewing(true)}>
              Review the change…
            </button>
          </div>
        </>
      ) : (
        <p>Ask someone with the Model administrator role to bring this workspace up to date.</p>
      )}
      {reviewing && (
        <RaiseDialog
          workspace={workspace}
          availability={availability}
          onClose={() => setReviewing(false)}
          onRaised={() => {
            setReviewing(false);
            onRaised();
          }}
        />
      )}
    </Card>
  );
}

/** The error to show for a failed preview or raise. */
function raiseError(cause: unknown): string {
  if (isApiError(cause, "RELEASE_RAISE_REFUSED")) {
    const details = (cause.details ?? {}) as { diagnostics?: unknown[]; collidesWith?: string };
    const lines = (details.diagnostics ?? []).map((item) =>
      typeof item === "string" ? item : String((item as { message?: unknown })?.message ?? ""),
    );
    const collides = details.collidesWith ? [`It would equal the release ${details.collidesWith}.`] : [];
    return [cause.message, ...collides, ...lines.filter(Boolean)].join(" ");
  }
  return errorMessage(cause);
}

/** Review, then raise: the preview changes nothing; the confirmation names the hash it answered. */
function RaiseDialog({
  workspace,
  availability,
  onClose,
  onRaised,
}: {
  workspace: Workspace;
  availability: Unavailable;
  onClose: () => void;
  onRaised: () => void;
}) {
  const [preview, setPreview] = useState<ModelReleaseRaising>();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const cancelRef = useRef<HTMLButtonElement>(null);
  const target = availability.supportedSchemaVersions[availability.supportedSchemaVersions.length - 1];

  // Reading again (after a changed release, or a failed read) is another round of the same preview.
  const [round, setRound] = useState(0);
  function read() {
    setPreview(undefined);
    setRound((value) => value + 1);
  }
  useEffect(() => {
    let active = true;
    api.previewModelReleaseRaising(availability.releaseId).then(
      (answer) => active && setPreview(answer),
      (cause) => active && setError(raiseError(cause)),
    );
    return () => {
      active = false;
    };
  }, [availability.releaseId, round]);

  async function confirm() {
    if (!preview) return;
    setBusy(true);
    setError("");
    try {
      await api.raiseModelRelease(availability.releaseId, preview.modelHash);
      onRaised();
    } catch (cause) {
      if (isApiError(cause, "MODEL_HASH_CHANGED")) {
        setError("The release changed after you looked. Review it again.");
        read();
      } else {
        setError(raiseError(cause));
      }
      setBusy(false);
    }
  }

  return (
    <Modal
      title={`Raise ${workspaceModelLabel(workspace)} to schema ${target}`}
      eyebrow="Review the change"
      size="confirm"
      busy={busy}
      onClose={onClose}
      initialFocusRef={cancelRef}
    >
      <div className="dialog-body">
        {preview ? (
          <>
            <DescriptionList
              items={[
                { term: "Schema language", value: `${preview.schemaFrom} → ${preview.schemaTo}` },
                { term: "Consumer APIs rewritten", value: String(preview.consumerApisRewritten) },
                {
                  term: "Workspaces that return",
                  value: preview.workspaces.map((item) => item.label).join(", ") || workspace.label,
                },
                { term: "Records, change sets, publications", value: "unchanged" },
              ]}
            />
            <p className="admin-hint">This edits the stored release in place (before 1.0 only).</p>
          </>
        ) : error ? null : (
          <p className="muted">Looking at what the change would do…</p>
        )}
        {error && (
          <Notice tone="error" title="The change could not be made">
            {error}
          </Notice>
        )}
      </div>
      <div className="dialog-actions">
        <button ref={cancelRef} type="button" className="secondary" disabled={busy} onClick={onClose}>
          Cancel
        </button>
        {!preview && error && (
          <button
            type="button"
            className="secondary"
            onClick={() => {
              setError("");
              read();
            }}
          >
            Try again
          </button>
        )}
        <button type="button" className="primary" disabled={!preview || busy} onClick={() => void confirm()}>
          {busy ? "Raising…" : "Raise and reopen"}
        </button>
      </div>
    </Modal>
  );
}

/** "Or continue elsewhere": the other workspaces that open, the default first. */
function ContinueElsewhere({
  excludeKey,
  onNavigate,
}: {
  excludeKey: string;
  onNavigate: (route: RouteState) => void;
}) {
  const [others, setOthers] = useState<Workspace[]>();
  useEffect(() => {
    let active = true;
    Promise.all([allWorkspaces({ status: "active" }), api.workspaceRuntimeState().catch(() => undefined)]).then(
      ([items, runtime]) => {
        const open = items.filter((item) => item.key !== excludeKey && item.availability?.state !== "unavailable");
        const first = open.findIndex((item) => item.key === runtime?.defaultWorkspaceKey);
        if (active) setOthers(first > 0 ? [open[first], ...open.slice(0, first), ...open.slice(first + 1)] : open);
      },
      () => active && setOthers([]),
    );
    return () => {
      active = false;
    };
  }, [excludeKey]);
  return (
    <Card title="Or continue elsewhere" as="section" className="unavailable-card">
      {others?.length ? (
        <ul className="unavailable-others">
          {others.map((item) => (
            <li key={item.key}>
              <button type="button" onClick={() => void startRouteOf(item.key).then(onNavigate)}>
                <strong>{item.label}</strong>
                <span>{workspaceModelLabel(item)}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      <div className="unavailable-actions wrap-row">
        <button
          type="button"
          className="secondary"
          onClick={() => onNavigate({ kind: "settings", page: "workspaces" })}
        >
          All workspaces
        </button>
      </div>
    </Card>
  );
}
