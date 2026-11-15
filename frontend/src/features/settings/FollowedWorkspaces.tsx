/**
 * Settings › Notifications › Workspaces I follow (0.16 AO3, AO-D38): the workspaces the person follows,
 * each with Stop following. A change set published in one of them puts a notice in the inbox; it is
 * followed from the workspace's card on Home.
 */

import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { formatLongDay } from "@/lib/dates";
import type { Hue } from "@/model/hues";
import type { FollowedWorkspace } from "@/types";
import { InlineError } from "@/ui/InlineError";
import { Notice } from "@/ui/Notice";
import { SettingRow, SettingsEmpty, SettingsGroup, SettingsPanel, SettingsTile } from "@/ui/SettingsParts";
import { Skeleton } from "@/ui/Skeleton";

const since = (at: string) => `Following since ${formatLongDay(at)}`;

export function FollowedWorkspaces({ hue }: { hue?: Hue }) {
  const [items, setItems] = useState<FollowedWorkspace[]>();
  const [error, setError] = useState("");
  const [problem, setProblem] = useState("");
  const [pending, setPending] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    api.followedWorkspaces().then(
      (loaded) => active && setItems(loaded),
      (cause) => active && setError(errorMessage(cause)),
    );
    return () => {
      active = false;
    };
  }, [attempt]);

  async function stop(item: FollowedWorkspace) {
    setPending(item.workspaceKey);
    setProblem("");
    try {
      await api.unfollowWorkspace(item.workspaceKey);
      setItems((current) => current?.filter((one) => one.workspaceKey !== item.workspaceKey));
    } catch (cause) {
      setProblem(errorMessage(cause));
    } finally {
      setPending("");
    }
  }

  return (
    <SettingsGroup
      title="Workspaces I follow"
      description="When a change set is published in one of these, a notice arrives in your inbox."
    >
      {error ? (
        <InlineError
          message={error}
          onRetry={() => {
            setError("");
            setAttempt((value) => value + 1);
          }}
        />
      ) : !items ? (
        <Skeleton label="Loading the workspaces you follow" lines={2} />
      ) : (
        <SettingsPanel note="Follow a workspace from its card on Home.">
          {items.length === 0 ? (
            <SettingsEmpty icon="workspace" hue={hue}>
              You do not follow a workspace.
            </SettingsEmpty>
          ) : (
            items.map((item) => (
              <SettingRow
                key={item.workspaceKey}
                lead={<SettingsTile icon="workspace" hue={hue} />}
                name={item.label}
                help={since(item.since)}
              >
                <button
                  type="button"
                  className="ghost"
                  disabled={pending === item.workspaceKey}
                  aria-label={`Stop following ${item.label}`}
                  onClick={() => void stop(item)}
                >
                  Stop following
                </button>
              </SettingRow>
            ))
          )}
        </SettingsPanel>
      )}
      {problem && <Notice tone="error">{problem}</Notice>}
    </SettingsGroup>
  );
}
