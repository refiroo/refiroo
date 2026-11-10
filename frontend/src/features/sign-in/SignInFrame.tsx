/**
 * The frame every screen before a session shares (0.12 I5, I6): the product's mark and welcome
 * words above a card with a title. The sign-in screen and the password-reset pages draw inside it,
 * so the two never keep their own copies of the brand or the card.
 */

import type { ReactNode } from "react";
import { ProductMark } from "@/ui/ProductMark";

export function SignInFrame({
  product,
  named,
  busy,
  title,
  build,
  children,
}: {
  product: string;
  /** The product's name is known; until then a space is held so the default is never swapped in. */
  named: boolean;
  busy: boolean;
  title: string;
  /** The engine's version and build, as a small line under the card; none until it is known. */
  build?: { version: string; commit: string | null; tag: string | null };
  children: ReactNode;
}) {
  return (
    <main className="sign-in-screen" aria-busy={busy}>
      <header className="sign-in-brand">
        {named ? <ProductMark name={product} /> : <span className="sign-in-mark-space" />}
        <p className="sign-in-welcome">
          <strong>Reference data that stays in step.</strong>
          Every code, category and mapping, kept tidy so everything else can trust it.
        </p>
      </header>
      <div className="sign-in-card">
        <h1>{title}</h1>
        {children}
      </div>
      {build && (
        <p className="sign-in-build">
          {product} {build.version}
          {(build.tag || build.commit) && (
            <>
              {" "}
              &middot; build {build.tag && <span className="sign-in-build-ref">{build.tag}</span>}
              {build.tag && build.commit && " "}
              {build.commit && (
                <span className="sign-in-build-ref">{build.tag ? `(${build.commit})` : build.commit}</span>
              )}
            </>
          )}
        </p>
      )}
    </main>
  );
}
