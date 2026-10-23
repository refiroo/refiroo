/** The caller and their sessions, as the account menu and Settings › Account show them (0.12 I2). */

import type { PageNavigation } from "@/types/runtime";

/** Who is signed in: a person (or, through the API, a client). */
export interface Me {
  id: string;
  kind: "user" | "client";
  name: string;
  username: string | null;
  email: string | null;
  lastSignInAt: string | null;
  signedInWith: string | null;
  sessionId: string | null;
}

/** One of the person's open browser sessions. */
export interface SignInSession {
  id: string;
  current: boolean;
  signedInWith: string;
  userAgent: string | null;
  createdAt: string;
  lastUsedAt: string;
  endsAt: string;
}

export interface SignInSessionPage extends PageNavigation {
  items: SignInSession[];
}
