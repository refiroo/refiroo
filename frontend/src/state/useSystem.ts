import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { cachedRead } from "@/state/cachedRead";
import type { CapabilitiesResponse, SystemConfiguration, SystemResponse } from "@/types";

/** One read a settings page shows (`load` must be stable, such as an `api` call), with its error and a retry. */
export function useSettingsRead<T>(load: () => Promise<T>) {
  const [data, setData] = useState<T>();
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    load()
      .then((loaded) => active && setData(loaded))
      .catch((cause) => active && setError(errorMessage(cause)));
    return () => {
      active = false;
    };
    // `load` is a module-level API call, so only a retry reads again.
  }, [attempt, load]);
  return {
    data,
    error,
    retry: () => {
      setError("");
      setAttempt((value) => value + 1);
    },
  };
}

/**
 * The parts of `GET /system` that only a new release of the engine changes (its licence and source
 * address, the schema languages a draft may be written in), read once per page load and shared. The
 * parts that can change while the page is open (the active release, the product) are not taken from
 * here: About, the API reference, the AI offers and Consumer APIs read the system fresh.
 */
const staticRead = cachedRead(() => api.system().then(({ engine, schemaLanguages }) => ({ engine, schemaLanguages })));
export const staticSystem = () => staticRead.get();

/** The schema languages a model draft may be written in, from the system's kept static parts. */
export const schemaLanguages = () => staticSystem().then((system) => system.schemaLanguages);

/** `GET /system`, with its error and a retry. */
export function useSystem() {
  const { data, ...read } = useSettingsRead<SystemResponse>(api.system);
  return { system: data, ...read };
}

/** `GET /system/configuration`, with its error and a retry. */
export function useSystemConfiguration() {
  const { data, ...read } = useSettingsRead<SystemConfiguration>(api.systemConfiguration);
  return { configuration: data, ...read };
}

/** `GET /capabilities`, with its error and a retry. */
export function useCapabilities() {
  const { data, ...read } = useSettingsRead<CapabilitiesResponse>(api.capabilities);
  return { capabilities: data, ...read };
}
