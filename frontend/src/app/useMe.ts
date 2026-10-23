import { useEffect, useState } from "react";
import { api } from "@/api/client";
import type { Me } from "@/types";

// Who is signed in, read once per page load: it changes only by signing in again (0.12 I2).
let loading: Promise<Me> | undefined;

/** The signed-in person, or `undefined` while it loads or when it cannot be read. */
export function useMe(): Me | undefined {
  const [me, setMe] = useState<Me>();
  useEffect(() => {
    let active = true;
    loading ??= Promise.resolve().then(() => api.me());
    loading.then(
      (loaded) => active && setMe(loaded),
      () => {
        loading = undefined;
      },
    );
    return () => {
      active = false;
    };
  }, []);
  return me;
}

/** A person's initials for the avatar: the first letters of their first and last names. */
export function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  const letters = words.length > 1 ? [words[0], words[words.length - 1]] : words;
  return letters.map((word) => word[0]?.toUpperCase() ?? "").join("");
}
