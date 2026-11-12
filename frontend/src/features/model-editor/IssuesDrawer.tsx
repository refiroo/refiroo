/**
 * The draft's issues and history drawer (0.10 A4a, shared in 0.17 CE1): the bar that counts the issues and steps
 * and opens the drawer, and the drawer holding Issues, History and, with a workbook, the dry run. The model editor
 * and the canvas both show this one drawer (PP-D3); each page says where an issue's link goes.
 */

import { useState } from "react";
import { DryRunPanel, dryRunLabel } from "@/features/model-editor/DryRunPanel";
import { historySteps } from "@/features/model-editor/history";
import { IssuesAndHistory, type IssueTarget } from "@/features/model-editor/IssuesAndHistory";
import { removePanel } from "@/features/model-editor/layout";
import type { DraftEditing } from "@/features/model-editor/useDraftEditing";
import type { DraftSource } from "@/features/model-editor/useDraftSource";
import type { SourceDialogs } from "@/features/model-editor/useSourceDialogs";
import { readLocalPreference, writeLocalPreference } from "@/lib/localPreference";
import type { CursorFeed } from "@/lib/hooks/useCursorFeed";
import type { DraftProfile, ModelDraftOperationEntry, ModelDraftOutline } from "@/types";
import { Icon } from "@/ui/Icon";
import { StatusPill } from "@/ui/StatusPill";

const OPEN_KEY = "rdm:model-editor:issues-history-open:v2";

/** The drawer's open state: the bar's toggle is the reader's choice and is remembered; `show` opens it for now. */
export function useIssuesDrawer() {
  const [open, setOpen] = useState(() =>
    readLocalPreference(OPEN_KEY, false, (value): value is boolean => typeof value === "boolean"),
  );
  return {
    open,
    toggle: (next: boolean) => {
      setOpen(next);
      writeLocalPreference(OPEN_KEY, next);
    },
    show: () => setOpen(true),
  };
}

/** The issues the drawer counts: the draft's diagnostics and, with a profile, its warnings. */
export function issueCountOf(outline: ModelDraftOutline, profile: DraftProfile | undefined): number {
  return outline.diagnostics.length + (profile?.profile ? profile.diagnostics.length : 0);
}

export function IssuesDrawer({
  editing,
  outline,
  history,
  source,
  sourceDialogs,
  proposing,
  tab,
  onTab,
  open,
  onToggle,
  onSelect,
  onGoToProfileKey,
  inTab = false,
}: {
  editing: DraftEditing;
  outline: ModelDraftOutline;
  history: CursorFeed<ModelDraftOperationEntry>;
  source: DraftSource;
  sourceDialogs: SourceDialogs;
  proposing: boolean;
  tab: string;
  onTab: (tab: string) => void;
  open: boolean;
  onToggle: (open: boolean) => void;
  /** An issue's link: the page shows its element. */
  onSelect: IssueTarget;
  /** Moves to the profile key's field, where the page has one. */
  onGoToProfileKey?: () => void;
  /** Shown as a tab's content (the editor on a phone): no bar, always open. */
  inTab?: boolean;
}) {
  const hasSource = Boolean(source.profile?.sourceFile);
  const issueCount = issueCountOf(outline, source.profile);
  const errors = outline.diagnostics.filter((item) => item.severity === "error").length;
  // Steps are numbered one by one, so the newest one's number is how many the draft has, though
  // only its latest operations are read (a proposal can hold dozens; 0.10 A8c's TODO, fixed in R).
  const stepCount = historySteps(history.items).reduce((most, step) => Math.max(most, step.step), 0);
  const name = hasSource ? "Issues, history and dry run" : "Issues and history";
  const issuesAndHistory = (
    <IssuesAndHistory
      outline={outline}
      tab={tab}
      onTab={onTab}
      history={history}
      onSelect={onSelect}
      onUndoStep={(value) => void editing.undo([value])}
      profile={source.profile}
      onUseProfileKey={proposing ? undefined : (key) => void editing.runGuarded([{ kind: "setProfile", key }])}
      onGoToProfileKey={onGoToProfileKey}
      onRemovePanel={
        proposing
          ? undefined
          : ({ applicationKey, detail, panel }) =>
              void editing.runGuarded(removePanel({ applicationKey, objectTypeKey: detail }, panel))
      }
      dryRun={
        hasSource
          ? {
              label: `Dry run · ${dryRunLabel(source.dryRun)}`,
              content: (
                <DryRunPanel
                  dryRun={source.dryRun}
                  error={source.dryRunError}
                  onRetry={source.retry}
                  outline={outline}
                  onRows={sourceDialogs.openRows}
                />
              ),
            }
          : undefined
      }
    />
  );
  // On a desktop the pane is a drawer at the bottom, closed until the reader opens it; nothing else
  // opens or closes it (the user, 2026-10-11). On a phone it is the Issues tab.
  if (inTab)
    return (
      <section className="model-editor-bottom" aria-label={name}>
        {issuesAndHistory}
      </section>
    );
  return (
    <section className={`model-editor-bottom${open ? " open" : ""}`} aria-label={name}>
      <button
        type="button"
        className="model-editor-bottom-toggle"
        aria-expanded={open}
        aria-controls="model-editor-issues-history"
        onClick={() => onToggle(!open)}
      >
        <Icon name={open ? "chevron-down" : "chevron-right"} size={14} />
        <span>{name}</span>
        <StatusPill tone={errors ? "error" : issueCount ? "warning" : "success"}>
          {issueCount ? `${issueCount} ${issueCount === 1 ? "issue" : "issues"}` : "No issues"}
        </StatusPill>
        <span className="muted">
          {stepCount ? `${stepCount} ${stepCount === 1 ? "step" : "steps"}` : "No steps yet"}
        </span>
        {hasSource && <span className="muted">Dry run: {dryRunLabel(source.dryRun)}</span>}
      </button>
      <div id="model-editor-issues-history" className="model-editor-bottom-body" hidden={!open}>
        {open && issuesAndHistory}
      </div>
    </section>
  );
}
