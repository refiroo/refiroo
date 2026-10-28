/**
 * Propose targets (0.16 AP2): the AI assistant proposes a target for each unmapped source of a
 * mapping view, into a change set, as ordinary mappings the person can change. The dialog says what
 * it will do (the count, the narrowing, the change set) and what leaves the server, then follows the
 * `aiProposal` job: progress, Stop (what was proposed stays), the result's counts and warnings, and
 * Show proposed. Closing while it runs leaves the job going; its end is announced.
 */

import { useEffect, useState, type FormEvent } from "react";
import { errorMessage, isApiError } from "@/api/errors";
import { ai } from "@/api/aiClient";
import { useJobNotifications } from "@/features/jobs/JobNotifications";
import { isFinal, useJobStream } from "@/features/jobs/useJobStream";
import { cancellable } from "@/features/jobs/jobText";
import { sentForMappingTargets } from "@/features/settings/aiText";
import { count } from "@/features/settings/limits";
import { useDataApi, useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import type { AiSystemInfo, Job, MappingProposalRequest } from "@/types";
import { FormField } from "@/ui/FormField";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";

export interface ProposalScope {
  workspaceKey: string;
  applicationKey: string;
  viewKey: string;
  viewName: string;
  /** The coverage the grid reads, so the count is of the same sources. */
  coverage: {
    relationTypeKey: string;
    fromObjectTypeKey: string;
    toObjectTypeKey: string;
    direction: "outgoing" | "incoming";
  };
  search?: string;
  parentObjectId?: string;
  /** The sources' and targets' names, lower case: "carrier codes", "shipping methods". */
  sources: string;
  targets: string;
  /** What one target is called: "shipping method". */
  targetName: string;
}

type Step = "form" | "starting" | "running" | "result";

export function MappingProposalDialog({
  scope,
  offer,
  onClose,
  onShowProposed,
}: {
  scope: ProposalScope;
  offer: AiSystemInfo;
  onClose: () => void;
  /** Shows the change set's proposals; the grid moves there when it is another. */
  onShowProposed: (changeSetId: string) => void;
}) {
  const api = useDataApi();
  const { changeSet, refresh } = useWorkspaceData();
  const notifications = useJobNotifications();
  const [step, setStep] = useState<Step>("form");
  const [unmapped, setUnmapped] = useState<number | null>(null);
  const [readError, setReadError] = useState("");
  const [floor, setFloor] = useState<number>();
  const [model, setModel] = useState<string | null | undefined>(offer.model);
  const [into, setInto] = useState<"current" | "new">(changeSet ? "current" : "new");
  const [name, setName] = useState(`AI proposals: ${scope.viewName}`);
  const [job, setJob] = useState<Job>();
  const [problem, setProblem] = useState("");
  const [stopping, setStopping] = useState(false);

  // How many sources the request will ask about: the grid's own narrowing, unmapped only.
  useEffect(() => {
    let active = true;
    api
      .mappingCoverage({
        ...scope.coverage,
        workspaceKey: scope.workspaceKey,
        applicationKey: scope.applicationKey,
        viewKey: scope.viewKey,
        changeSetId: changeSet?.id,
        search: scope.search || undefined,
        parentObjectId: scope.parentObjectId,
        state: "unmapped",
        pageSize: 1,
        includeTotal: true,
      })
      .then((page) => active && setUnmapped(page.totalCount ?? page.items.length))
      .catch((cause) => active && setReadError(errorMessage(cause)));
    return () => {
      active = false;
    };
  }, [api, changeSet?.id, scope]);

  // The confidence floor, when the person may read the AI status; otherwise it is not mentioned.
  useEffect(() => {
    let active = true;
    ai.status()
      .then((status) => {
        if (!active) return;
        setFloor(status.minConfidence);
        setModel(status.model ?? offer.model);
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [offer.model]);

  useJobStream(job && !isFinal(job) ? job.id : undefined, (next) => {
    setJob(next);
    if (isFinal(next)) setStep("result");
  });

  const newName = name.trim();
  const toNew = !changeSet || into === "new";

  async function propose(event?: FormEvent) {
    event?.preventDefault();
    if (step !== "form" || (toNew && !newName) || !unmapped) return;
    setProblem("");
    setStep("starting");
    try {
      const body: MappingProposalRequest = {
        applicationKey: scope.applicationKey,
        viewKey: scope.viewKey,
        ...(scope.search ? { search: scope.search } : {}),
        ...(scope.parentObjectId ? { parentObjectId: scope.parentObjectId } : {}),
      };
      if (toNew) body.changeSetName = newName;
      else {
        // The version as it is now: the job checks it, and another person's change since would refuse it.
        const current = refresh ? await refresh() : changeSet!;
        body.changeSetId = current.id;
        body.expectedChangeSetVersion = current.version;
      }
      const started = await api.proposeMappingTargets(scope.workspaceKey, body);
      setJob(started);
      setStep(isFinal(started) ? "result" : "running");
    } catch (cause) {
      setStep("form");
      setProblem(proposeProblem(cause));
    }
  }

  async function stop() {
    if (!job) return;
    setStopping(true);
    try {
      setJob(await api.cancelJob(job.id));
    } catch {
      // A job that ended meanwhile reports its end through the stream.
    } finally {
      setStopping(false);
    }
  }

  /** Leaves the dialog; a job still running goes on and its end is announced. */
  function close() {
    if (job && !isFinal(job)) notifications.follow(job);
    onClose();
  }

  const tally = job?.aiProposal;
  const title =
    step === "running" || step === "starting"
      ? "Proposing targets…"
      : step === "result"
        ? job?.state === "completed"
          ? "Targets proposed"
          : job?.state === "cancelled"
            ? "Proposing stopped"
            : "Proposing failed"
        : "Propose targets";

  return (
    <Modal title={title} size="compact" busy={step === "starting"} onClose={close}>
      {step === "form" || step === "starting" ? (
        <form className="dialog-form" aria-label="Propose targets" onSubmit={(event) => void propose(event)}>
          {readError ? (
            <Notice tone="error">{readError}</Notice>
          ) : unmapped === null ? (
            <p>Counting the unmapped {scope.sources}…</p>
          ) : unmapped === 0 ? (
            <p>
              There are no unmapped {scope.sources} in this view{scope.search ? " for this search" : ""}, so there is
              nothing to propose.
            </p>
          ) : (
            <p className="mapping-proposal-scope">
              The AI assistant proposes a {scope.targetName} for each of the{" "}
              <strong>
                {count(unmapped)} unmapped {scope.sources}
              </strong>{" "}
              in this view.
              {scope.search && ` The search “${scope.search}” applies.`}
              {scope.parentObjectId && " Only those within the parent you narrowed to."} Each proposal lands in a change
              set as an ordinary mapping you can change.
            </p>
          )}
          {unmapped !== null && unmapped > 0 && (
            <>
              <fieldset className="dialog-field">
                <legend>Into change set</legend>
                {changeSet && (
                  <>
                    <label className="checkbox">
                      <input
                        type="radio"
                        name="proposal-change-set"
                        checked={into === "current"}
                        onChange={() => setInto("current")}
                      />
                      {changeSet.name ? `Current: “${changeSet.name}”` : "The current change set"}
                    </label>
                    <label className="checkbox">
                      <input
                        type="radio"
                        name="proposal-change-set"
                        checked={into === "new"}
                        onChange={() => setInto("new")}
                      />
                      New change set
                    </label>
                  </>
                )}
                {toNew && (
                  <FormField label={changeSet ? "New change set name" : "Name of the new change set"}>
                    {(control) => (
                      <input
                        {...control}
                        value={name}
                        maxLength={200}
                        onChange={(event) => setName(event.target.value)}
                      />
                    )}
                  </FormField>
                )}
              </fieldset>
              <p className="admin-hint">
                {sentForMappingTargets({
                  provider: offer.provider,
                  model,
                  sources: scope.sources,
                  targets: scope.targets,
                  floor,
                })}
              </p>
            </>
          )}
          {problem && (
            <Notice tone="error" title="Nothing was proposed" focusOnMount>
              {problem}
            </Notice>
          )}
          <div className="dialog-actions">
            <button type="button" className="ghost" disabled={step === "starting"} onClick={close}>
              {unmapped === 0 ? "Close" : "Cancel"}
            </button>
            {unmapped !== null && unmapped > 0 && (
              <button className="primary" disabled={step === "starting" || (toNew && !newName)}>
                {step === "starting" ? "Starting…" : "Propose"}
              </button>
            )}
          </div>
        </form>
      ) : step === "running" && job ? (
        <form className="dialog-form" onSubmit={(event) => event.preventDefault()} aria-label={title}>
          <div className="job-progress">
            <progress
              value={job.progress.total ? job.progress.processed : undefined}
              max={job.progress.total ?? undefined}
              aria-label="Progress"
            />
            <span role="status">
              {job.progress.total !== null
                ? `${count(job.progress.processed)} of ${count(job.progress.total)} ${scope.sources}`
                : job.state === "queued"
                  ? "Waiting to start"
                  : `${count(job.progress.processed)} ${scope.sources} done`}
            </span>
          </div>
          <p className="admin-hint">
            You can close this: the job goes on and you are told when it ends. Proposals already made stay if you stop.
          </p>
          <div className="dialog-actions">
            {cancellable(job) && (
              <button type="button" className="secondary" disabled={stopping} onClick={() => void stop()}>
                Stop
              </button>
            )}
            <button type="button" className="primary" onClick={close}>
              Close
            </button>
          </div>
        </form>
      ) : job ? (
        <form className="dialog-form" onSubmit={(event) => event.preventDefault()} aria-label={title}>
          {job.error && (
            <Notice tone="error" title={job.state === "failed" ? "Why it failed" : "What stopped it"}>
              {job.error.message}
            </Notice>
          )}
          {job.state === "cancelled" && <p>What was proposed before it stopped stays in the change set.</p>}
          {tally && (
            <dl className="mapping-proposal-counts" aria-label="Result">
              <div>
                <dt>Proposed</dt>
                <dd>{count(tally.proposed)}</dd>
              </div>
              <div>
                <dt>Left unmapped: no likely target</dt>
                <dd>{count(tally.unmatched)}</dd>
              </div>
              <div>
                <dt>Changed meanwhile, not touched</dt>
                <dd>{count(tally.changed)}</dd>
              </div>
              {tally.refused > 0 && (
                <div>
                  <dt>Refused by the model’s rules</dt>
                  <dd>{count(tally.refused)}</dd>
                </div>
              )}
              {tally.notAnswered > 0 && (
                <div>
                  <dt>Not answered, left unmapped</dt>
                  <dd>{count(tally.notAnswered)}</dd>
                </div>
              )}
            </dl>
          )}
          {tally?.warnings.map((warning) => (
            <Notice key={warning} tone="warning">
              {warning}
            </Notice>
          ))}
          <div className="dialog-actions">
            <button type="button" className={tally?.proposed ? "secondary" : "primary"} onClick={close}>
              Close
            </button>
            {tally && tally.proposed > 0 && (
              <button
                type="button"
                className="primary"
                autoFocus
                onClick={() => {
                  onClose();
                  onShowProposed(tally.changeSetId);
                }}
              >
                Show proposed
              </button>
            )}
          </div>
        </form>
      ) : null}
    </Modal>
  );
}

/** What the request's refusals say, in the person's words. */
function proposeProblem(cause: unknown): string {
  if (isApiError(cause, "AI_NOT_CONFIGURED")) return "No AI provider is set up on this deployment any more.";
  if (isApiError(cause, "AI_SEND_LEVEL_TOO_LOW"))
    return "This deployment does not let record names leave the server, so targets cannot be proposed.";
  if (isApiError(cause, "CHANGE_SET_VERSION_CONFLICT"))
    return "Someone changed the change set meanwhile. Propose again to use it as it is now.";
  if (isApiError(cause, "CHANGE_SET_NOT_FOUND")) return "The change set no longer exists.";
  return errorMessage(cause);
}
