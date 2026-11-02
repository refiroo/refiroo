/**
 * Settings › Notifications › Workspaces I follow (0.16 AO3, AO-D38): the workspaces the person follows,
 * each with Stop following. A change set published in one of them puts a notice in the inbox; it is
 * followed from the workspace's card on Home.
 */

import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import type { FollowedWorkspace } from "@/types";
import { InlineError } from "@/ui/InlineError";
import { Notice } from "@/ui/Notice";
import { Section } from "@/ui/Section";

const since = (at: string) =>
  `Following since ${new Date(at).toLocaleDateString("en-GB", { day: "numeric", month: "long" })}`;

export function FollowedWorkspaces() {
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
    <Section title="Workspaces I follow">
      <div className="account-panel">
        <p className="account-panel-note account-muted">
          When a change set is published in one of these, a notice arrives in your inbox. Follow a workspace from its
          card on Home.
        </p>
        {error ? (
          <InlineError
            message={error}
            onRetry={() => {
              setError("");
              setAttempt((value) => value + 1);
            }}
          />
        ) : !items ? (
          <p className="account-panel-note account-muted">Loading…</p>
        ) : items.length === 0 ? (
          <p className="account-panel-note account-muted">You do not follow a workspace.</p>
        ) : (
          <ul className="account-list">
            {items.map((item) => (
              <li className="account-row" key={item.workspaceKey}>
                <div className="account-row-text">
                  <span>{item.label}</span>
                  <span className="account-muted">{since(item.since)}</span>
                </div>
                <button
                  type="button"
                  className="secondary"
                  disabled={pending === item.workspaceKey}
                  aria-label={`Stop following ${item.label}`}
                  onClick={() => void stop(item)}
                >
                  Stop following
                </button>
              </li>
            ))}
          </ul>
        )}
        {problem && <Notice tone="error">{problem}</Notice>}
      </div>
    </Section>
  );
}
