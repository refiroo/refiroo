/**
 * An assistant task as a page needs it (0.16 AP6a): read once, then followed while a job runs. The
 * job's own change is pushed over its event stream; the task is read again at each push and now and
 * then (the phase moves within one job), as the inference's editor does. Every part following one
 * task shares one copy of it (0.16 AP6): the task's page and the journey bar never disagree, as a
 * write's answer or a read reaches both.
 */

import { useCallback, useEffect, useState } from "react";
import { ai } from "@/api/aiClient";
import { errorMessage, isApiError } from "@/api/errors";
import { useFollowedJob } from "@/state/useFollowedJob";
import type { AiTask } from "@/types";
import { running } from "./aiTaskText";

export interface FollowedTask {
  task?: AiTask;
  error: string;
  /** The task is not kept or never existed (`404 AI_TASK_NOT_FOUND`, 0.16 AP13). */
  notFound: boolean;
  /** Replaces the task with an answer a write returned. */
  set: (task: AiTask) => void;
  /** Reads the task again; resolves with what was read. */
  reload: () => Promise<AiTask | undefined>;
  retry: () => void;
}

interface Shared {
  task?: AiTask;
  /** Counts reads and writes: a read still in flight is older than any later one. */
  latest: number;
  listeners: Set<(task: AiTask) => void>;
  /** The one follower that holds the job's stream and the timer; the others read what it publishes. */
  leader?: symbol;
  /** Each follower's way to look again for a leader when the leader lets go. */
  rechecks: Map<symbol, () => void>;
}

const shared = new Map<string, Shared>();

function sharedOf(taskId: string): Shared {
  let entry = shared.get(taskId);
  if (!entry) {
    entry = { latest: 0, listeners: new Set(), rechecks: new Map() };
    shared.set(taskId, entry);
  }
  return entry;
}

function publish(entry: Shared, task: AiTask) {
  entry.task = task;
  entry.listeners.forEach((listener) => listener(task));
}

export function useAiTask(taskId: string): FollowedTask {
  const entry = sharedOf(taskId);
  const [task, setTask] = useState<AiTask | undefined>(entry.task);
  const [error, setError] = useState("");
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    const own = sharedOf(taskId);
    const listener = (next: AiTask) => {
      setTask(next);
      setError("");
      setNotFound(false);
    };
    own.listeners.add(listener);
    return () => {
      own.listeners.delete(listener);
      if (own.listeners.size === 0) shared.delete(taskId);
    };
  }, [taskId]);

  const reload = useCallback(async () => {
    const own = sharedOf(taskId);
    const asked = (own.latest += 1);
    try {
      const read = await ai.task(taskId);
      // A later read (or a write's answer) is newer than one still in flight.
      if (asked === own.latest) publish(own, read);
      return read;
    } catch (cause) {
      if (asked === own.latest) {
        setError(errorMessage(cause));
        setNotFound(isApiError(cause, "AI_TASK_NOT_FOUND"));
      }
      return undefined;
    }
  }, [taskId]);

  // The first read, unless another part following the task has it already.
  useEffect(() => {
    const own = sharedOf(taskId);
    if (own.task !== undefined) return;
    let current = true;
    const asked = own.latest;
    ai.task(taskId)
      .then((read) => current && own.latest === asked && publish(own, read))
      .catch((cause) => {
        if (!current) return;
        setError(errorMessage(cause));
        setNotFound(isApiError(cause, "AI_TASK_NOT_FOUND"));
      });
    return () => {
      current = false;
    };
  }, [taskId]);

  const waiting = task && running(task);
  // One stream and one timer for a task however many parts follow it (the page and the journey bar).
  const [me] = useState(() => Symbol("follower"));
  const [looked, lookAgain] = useState(0);
  const [leading, setLeading] = useState(false);
  useEffect(() => {
    const own = sharedOf(taskId);
    own.rechecks.set(me, () => lookAgain((n) => n + 1));
    return () => {
      own.rechecks.delete(me);
    };
  }, [taskId, me]);
  useEffect(() => {
    const own = sharedOf(taskId);
    if (!waiting || (own.leader !== undefined && own.leader !== me)) return;
    own.leader = me;
    setLeading(true);
    return () => {
      if (own.leader === me) own.leader = undefined;
      setLeading(false);
      own.rechecks.forEach((again, follower) => follower !== me && again());
    };
  }, [taskId, waiting, looked, me]);
  // Only the leader follows: the stream opens once the task has its job, and the timer runs while
  // the task waits, so a change that has not committed yet is read now and then.
  useFollowedJob(leading && waiting && task.state !== "loading" ? (task.jobId ?? undefined) : undefined, {
    keep: false,
    onChange: () => void reload(),
    poll: { every: 2000, enabled: Boolean(waiting && leading), run: () => void reload() },
  });

  const set = useCallback(
    (next: AiTask) => {
      const own = sharedOf(taskId);
      own.latest += 1;
      publish(own, next);
    },
    [taskId],
  );

  return { task, error, notFound, set, reload, retry: () => void reload() };
}
