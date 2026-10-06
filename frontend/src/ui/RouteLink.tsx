import type { AnchorHTMLAttributes, MouseEvent, ReactNode } from "react";

/**
 * A link to a route of this application: a real `href`, so it opens in a new tab and copies like any
 * link, while a plain click navigates in place through `onNavigate`.
 */
export function RouteLink({
  href,
  onNavigate,
  children,
  ...rest
}: {
  href: string;
  onNavigate: () => void;
  children: ReactNode;
} & Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "href" | "onClick">) {
  return (
    <a
      href={href}
      onClick={(event: MouseEvent<HTMLAnchorElement>) => {
        if (event.defaultPrevented || event.button !== 0) return;
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        onNavigate();
      }}
      {...rest}
    >
      {children}
    </a>
  );
}
