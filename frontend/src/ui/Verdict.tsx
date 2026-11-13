/**
 * What a job would do or did, in one line: a pill for its result and a sentence saying what that
 * means. An import's preview (0.9 J4) and a batch's preview and result (0.9 K2) say it the same way.
 */

import type { ReactNode } from "react";
import type { JobPreview } from "@/types";
import { StatusPill } from "@/ui/StatusPill";

const TONE = { applied: "success", partial: "warning", rejected: "error" } as const;

export function Verdict({
  result,
  label,
  children,
}: {
  result: JobPreview["result"];
  label: string;
  children: ReactNode;
}) {
  return (
    <p className="import-outcome">
      <StatusPill tone={TONE[result]}>{label}</StatusPill>
      <span>{children}</span>
    </p>
  );
}
