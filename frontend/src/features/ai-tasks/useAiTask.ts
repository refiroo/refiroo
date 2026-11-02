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
import { useJobStream } from "@/features/jobs/useJobStream";
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
}

const shared = new Map<string, Shared>();

function sharedOf(taskId: string): Shared {
  let entry = shared.get(taskId);
  if (!entry) {
    entry = { latest: 0, listeners: new Set() };
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
  useJobStream(waiting && task.state !== "loading" ? (task.jobId ?? undefined) : undefined, () => void reload());
  useEffect(() => {
    if (!waiting) return;
    const timer = setInterval(() => void reload(), 2000);
    return () => clearInterval(timer);
  }, [waiting, reload]);

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
