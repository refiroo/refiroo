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

/** A role as a grant or a permission names it (0.12 Z1). */
export interface RoleRef {
  key: string;
  name: string;
}

/** A role given to a person, client or group, at the instance or in one workspace (0.12 Z1). */
export interface Grant {
  id: string;
  principal: { kind: "user" | "client" | "group"; id: string; name: string };
  role: RoleRef;
  scope: {
    instance: boolean;
    workspaceKey: string | null;
    applications: string[];
    recordTypes: string[];
    applicationNames: string[];
    recordTypeNames: string[];
  };
  createdAt: string;
}

/** What the caller holds in one workspace: the roles that apply there and their action groups. */
export interface MyPermissions {
  workspaceKey: string;
  workspaceLabel: string;
  roles: RoleRef[];
  actionGroups: {
    key: string;
    name: string;
    applications: string[];
    recordTypes: string[];
    sources: {
      grantId: string;
      role: RoleRef;
      scope: "workspace" | "instance";
      group: { id: string; name: string } | null;
    }[];
  }[];
}
