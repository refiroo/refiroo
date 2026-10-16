import type { ReactNode } from "react";

/**
 * A row, list item or card that opens what it names on a click anywhere in it (0.11 M6). It holds a
 * link to the same place, which the keyboard and assistive technology use; a click on a link, button
 * or field inside it is left to that control.
 */
export function OpenableRow({
  onOpen,
  as: Element = "tr",
  className,
  children,
}: {
  onOpen: () => void;
  as?: "tr" | "li" | "div";
  className?: string;
  children: ReactNode;
}) {
  return (
    <Element
      className={["openable-row", className].filter(Boolean).join(" ")}
      onClick={(event) => {
        if ((event.target as Element).closest("a, button, input, select, textarea, label")) return;
        onOpen();
      }}
    >
      {children}
    </Element>
  );
}
