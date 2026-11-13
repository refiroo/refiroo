/**
 * What Activate and Apply say alike about a workspace's release change (0.11 M5, D26; 0.16 WM1): its open change
 * sets that stay on the release it runs now, and the first reasons the data does not fit.
 */

import { api } from "@/api/client";
import type { ChangeSet, ModelDiagnostic } from "@/types";

/** Every open change set of the workspace, page by page (a workspace holds few). */
export async function openChangeSets(workspaceKey: string): Promise<ChangeSet[]> {
  const found: ChangeSet[] = [];
  let cursor: string | undefined;
  do {
    const page = await api.changeSets(workspaceKey, cursor);
    found.push(...page.items);
    cursor = page.nextCursor ?? undefined;
  } while (cursor);
  return found;
}

/** The candidate releases by model, the workspace's own model first, each newest first (M6). */

/** The workspace's open change sets that stay on the release it runs now (D26). */
export function LeftBehindChangeSets({
  workspaceLabel,
  version,
  changeSets,
}: {
  workspaceLabel: string;
  version: string;
  changeSets: ChangeSet[];
}) {
  return (
    <section aria-labelledby="activate-left-behind" className="activate-left-behind">
      <h3 id="activate-left-behind" className="install-heading">
        Change sets left on {version}
      </h3>
      {changeSets.length ? (
        <>
          <p className="muted">
            These open change sets of {workspaceLabel} stay pinned to the release it runs now. They cannot be published
            until each is moved to the new release or discarded.
          </p>
          <ul>
            {changeSets.map((item) => (
              <li key={item.id}>
                {item.name ?? "Unnamed change set"} · version {item.version}
              </li>
            ))}
          </ul>
        </>
      ) : (
        <p className="muted">None: {workspaceLabel} has no open change set.</p>
      )}
    </section>
  );
}

/** The first reasons the data does not fit, in plain words; the release's page lists every one. */
const REASONS_SHOWN = 5;

export function MigrationReasons({ diagnostics }: { diagnostics: ModelDiagnostic[] }) {
  if (!diagnostics.length) return null;
  const more = diagnostics.length - REASONS_SHOWN;
  return (
    <ul className="migration-reasons">
      {diagnostics.slice(0, REASONS_SHOWN).map((item, index) => (
        <li key={`${item.path}:${index}`}>{item.message}</li>
      ))}
      {more > 0 && (
        <li>
          And {more} more {more === 1 ? "reason" : "reasons"}, listed on the release's page.
        </li>
      )}
    </ul>
  );
}
