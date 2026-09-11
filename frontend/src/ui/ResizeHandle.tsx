import type { CSSProperties, KeyboardEvent, PointerEvent } from "react";

export function ResizeHandle({
  label,
  value,
  min,
  max,
  direction = 1,
  onChange,
  onReset,
  className = "",
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  direction?: 1 | -1;
  onChange: (value: number) => void;
  onReset?: () => void;
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
    let next: number | undefined;
    if (event.key === "ArrowLeft") next = value - step * direction;
    if (event.key === "ArrowRight") next = value + step * direction;
    if (event.key === "Home") next = min;
    if (event.key === "End") next = max;
    if (next === undefined) return;
    event.preventDefault();
    onChange(clamp(next));
  }
  function pointerDown(event: PointerEvent<HTMLDivElement>) {
    event.preventDefault();
    const start = event.clientX;
    const initial = value;
    event.currentTarget.setPointerCapture(event.pointerId);
    const target = event.currentTarget;
    const move = (moveEvent: globalThis.PointerEvent) =>
      onChange(clamp(initial + (moveEvent.clientX - start) * direction));
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
