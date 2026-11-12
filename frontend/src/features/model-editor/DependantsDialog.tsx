import { ConfirmDialog } from "@/ui/ConfirmDialog";

/**
 * An undo the engine refused because later steps use what it created or re-keyed
 * (`OPERATION_HAS_DEPENDANTS`): which steps depend on which, and the choice to undo them together.
 * One dialog for the model editor and the workbook canvas.
 */
export function DependantsDialog({
  steps,
  dependants,
  pending,
  onCancel,
  onConfirm,
}: {
  steps: number[];
  dependants: number[];
  pending: boolean;
  onCancel: () => void;
  /** The steps to undo together: the ones asked for and those that depend on them. */
  onConfirm: (together: number[]) => void;
}) {
  const together = [...steps, ...dependants].sort((a, b) => a - b);
  return (
    <ConfirmDialog
      title="Undo the steps that depend on it too?"
      confirmLabel={`Undo steps ${together.join(", ")}`}
      pending={pending}
      onCancel={onCancel}
      onConfirm={() => onConfirm([...steps, ...dependants])}
    >
      <p>
        Step {dependants.join(", ")} uses what step {steps.join(", ")} created or re-keyed, so it cannot be undone
        alone.
      </p>
    </ConfirmDialog>
  );
}

/** The steps an `OPERATION_HAS_DEPENDANTS` refusal names, as the engine gives them in its details. */
export function dependantsOf(details: unknown): { steps: number[]; dependants: number[] } {
  const found = (details ?? {}) as { steps?: number[]; dependants?: number[] };
  return { steps: found.steps ?? [], dependants: found.dependants ?? [] };
}
