import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import type { SystemResponse } from "@/types";

/** `GET /system`, with its error and a retry. */
export function useSystem() {
  const [system, setSystem] = useState<SystemResponse>();
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    api
      .system()
      .then((loaded) => active && setSystem(loaded))
      .catch((cause) => active && setError(errorMessage(cause)));
    return () => {
      active = false;
    };
  }, [attempt]);
  return {
    system,
    error,
    retry: () => {
      setError("");
      setAttempt((value) => value + 1);
    },
  };
}
