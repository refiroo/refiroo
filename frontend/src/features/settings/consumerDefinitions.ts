/**
 * The active model's consumer API definitions, expanded by the server (C18,
 * `GET /model/consumer-apis/{consumerApi}`): one read per definition, kept for the release, whose
 * content never changes, so the Webhooks page reads events, filters and public names without
 * repeating the expansion.
 */

import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import type { ConsumerApiDefinition, EngineModel, Subscription } from "@/types";

/** Where a subscription's events come from: its consumer API, or the workspace's own change-set events. */
export const sourceName = (subscription: Subscription, definition?: ConsumerApiDefinition) =>
  subscription.source === "workspace" || subscription.consumerApi === null
    ? "Workspace events"
    : (definition?.name ?? subscription.consumerApi);

const reads = new Map<string, Promise<ConsumerApiDefinition>>();

function definition(model: EngineModel, consumerApi: string): Promise<ConsumerApiDefinition> {
  const id = `${model.release.key}@${model.release.version}/${consumerApi}`;
  let read = reads.get(id);
  if (!read) {
    read = api.consumerApiDefinition(consumerApi);
    read.catch(() => reads.delete(id));
    reads.set(id, read);
  }
  return read;
}

export function useConsumerDefinitions(model: EngineModel) {
  const [definitions, setDefinitions] = useState<ConsumerApiDefinition[]>();
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const keys = (model.consumerApis ?? []).map((item) => item.key).join(" ");

  useEffect(() => {
    let active = true;
    Promise.all(keys ? keys.split(" ").map((key) => definition(model, key)) : [])
      .then((loaded) => active && setDefinitions(loaded))
      .catch((cause) => active && setError(errorMessage(cause)));
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- the release names the content, the keys what is read
  }, [model.release.key, model.release.version, keys, attempt]);

  const retry = () => {
    setError("");
    setAttempt((value) => value + 1);
  };
  return { definitions, error, retry };
}

/** The definitions a subscription can name: those that declare events. */
export const subscribable = (definitions: ConsumerApiDefinition[]) =>
  definitions.filter((item) => item.operations.events?.custom.length);
