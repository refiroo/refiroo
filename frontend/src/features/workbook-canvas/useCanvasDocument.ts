/**
 * The draft's canvas document (0.17 CE1, PP-D87): card positions, the folded cards and the chosen scope, read
 * once and written as they change. They belong to the draft's canvas, not to its version or history: a write
 * never changes `expectedVersion`, so opening a model, moving cards, Tidy and folding leave the draft as it is.
 * A place or a fold that could not be kept is only that: the board stays as the person left it on this screen.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/api/client";
import type { CanvasScope } from "@/types/sources";
import type { Position } from "./canvasModel";

export interface CanvasDocument {
  /** False until the document has been read; the board waits so cards do not jump to their stored places. */
  ready: boolean;
  positions: Record<string, Position>;
  folded: ReadonlySet<string>;
  /** The scope the person chose, `undefined` while the default stands. */
  scope?: CanvasScope;
  /** Replaces places in the board's own copy at once (Tidy) without a request. */
  setPositions: (next: Record<string, Position>) => void;
  savePositions: (changed: Record<string, Position | null>) => void;
  fold: (typeKey: string, folded: boolean) => void;
  foldAll: (typeKeys: readonly string[], folded: boolean) => void;
  chooseScope: (scope: CanvasScope) => void;
}

/**
 * The writes of one board go out one after the other, in the order they were made: a later save never lands before
 * an earlier one. A write that could not be kept is only a place or a fold: nothing is said and the screen stays
 * as it is, and the next write still goes.
 */
const useWrites = () => {
  const tail = useRef<Promise<void> | null>(null);
  return useCallback((send: () => Promise<unknown> | undefined) => {
    const run = async () => {
      try {
        await send();
      } catch {
        // Kept on the screen only.
      }
    };
    // With nothing waiting the write goes at once; otherwise it goes when the one before it has answered.
    const next = tail.current ? tail.current.then(run) : run();
    tail.current = next;
    void next.then(() => {
      if (tail.current === next) tail.current = null;
    });
  }, []);
};

export function useCanvasDocument(draftId: string): CanvasDocument {
  const [ready, setReady] = useState(false);
  const [positions, setPositions] = useState<Record<string, Position>>({});
  const [folded, setFolded] = useState<ReadonlySet<string>>(new Set());
  const [scope, setScope] = useState<CanvasScope>();
  const keep = useWrites();

  useEffect(() => {
    let cancelled = false;
    api.modelDraftCanvas(draftId).then(
      (answer) => {
        if (cancelled) return;
        setPositions(answer.positions ?? {});
        setFolded(new Set(answer.folded ?? []));
        setScope(answer.scope ?? undefined);
        setReady(true);
      },
      () => !cancelled && setReady(true),
    );
    return () => {
      cancelled = true;
    };
  }, [draftId]);

  const savePositions = useCallback(
    (changed: Record<string, Position | null>) => {
      setPositions((current) => {
        const next = { ...current };
        for (const [key, value] of Object.entries(changed)) {
          if (value) next[key] = value;
          else delete next[key];
        }
        return next;
      });
      keep(() => api.moveCanvasCards(draftId, changed));
    },
    [draftId, keep],
  );

  const foldAll = useCallback(
    (typeKeys: readonly string[], value: boolean) => {
      if (!typeKeys.length) return;
      setFolded((current) => {
        const next = new Set(current);
        for (const key of typeKeys) {
          if (value) next.add(key);
          else next.delete(key);
        }
        return next;
      });
      keep(() =>
        api.arrangeCanvas(draftId, { folded: Object.fromEntries(typeKeys.map((key) => [key, value ? true : null])) }),
      );
    },
    [draftId, keep],
  );
  const fold = useCallback((typeKey: string, value: boolean) => foldAll([typeKey], value), [foldAll]);

  const chooseScope = useCallback(
    (next: CanvasScope) => {
      setScope(next);
      keep(() => api.arrangeCanvas(draftId, { scope: next }));
    },
    [draftId, keep],
  );

  return { ready, positions, folded, scope, setPositions, savePositions, fold, foldAll, chooseScope };
}
