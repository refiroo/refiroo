import type { CSSProperties, KeyboardEvent, PointerEvent } from "react";

export function ResizeHandle({
  label,
  value,
  min,
  max,
  direction = 1,
  onChange,
  onReset,
  start,
  className = "",
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  direction?: 1 | -1;
  onChange: (value: number) => void;
  onReset?: () => void;
  /** The size a drag or key starts from, when the drawn size can differ from `value` (a table column). */
  start?: () => number;
  className?: string;
}) {
  const clamp = (next: number) => Math.min(max, Math.max(min, Math.round(next)));
  function keyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Enter" && onReset) {
      event.preventDefault();
      onReset();
      return;
    }
    const step = event.shiftKey ? 40 : 10;
    const current = start?.() ?? value;
    let next: number | undefined;
    if (event.key === "ArrowLeft") next = current - step * direction;
    if (event.key === "ArrowRight") next = current + step * direction;
    if (event.key === "Home") next = min;
    if (event.key === "End") next = max;
    if (next === undefined) return;
    event.preventDefault();
    onChange(clamp(next));
  }
  function pointerDown(event: PointerEvent<HTMLDivElement>) {
    event.preventDefault();
    const origin = event.clientX;
    const initial = start?.() ?? value;
    event.currentTarget.setPointerCapture(event.pointerId);
    const target = event.currentTarget;
    const move = (moveEvent: globalThis.PointerEvent) =>
      onChange(clamp(initial + (moveEvent.clientX - origin) * direction));
    const finish = () => {
      target.removeEventListener("pointermove", move);
      target.removeEventListener("pointerup", finish);
      target.removeEventListener("pointercancel", finish);
    };
    target.addEventListener("pointermove", move);
    target.addEventListener("pointerup", finish);
    target.addEventListener("pointercancel", finish);
  }
  return (
    <div
      className={`resize-handle ${className}`}
      role="separator"
      aria-label={label}
      aria-orientation="vertical"
      aria-valuemin={min}
      aria-valuemax={max}
      aria-valuenow={value}
      tabIndex={0}
      onKeyDown={keyDown}
      onPointerDown={pointerDown}
      onDoubleClick={onReset}
      title={
        onReset
          ? `${label}. Drag or use arrow keys. Double-click or press Enter to reset.`
          : `${label}. Drag or use arrow keys.`
      }
      style={{ "--resize-position": `${value}px` } as CSSProperties}
    />
  );
}
