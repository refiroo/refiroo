import { describe, expect, it } from "vitest";
import type { ActionGroup, Grant, SecurityEvent, UserRole } from "@/types";
import {
  clientAccessLine,
  clientUseLine,
  consumerApiSentence,
  grantHeld,
  grantSentence,
  localSignInLine,
  personSignInLine,
  providerUseLine,
  securityEventTitle,
  signingKeyState,
  staleNote,
  turnOffSentence,
  userRoleLine,
} from "./securityText";

const group = (
  key: string,
  name: string,
  grantableAt: ActionGroup["grantableAt"],
  narrowable = false,
): ActionGroup => ({
  key,
  name,
  description: "",
  grantableAt,
  narrowable,
});

const CATALOGUE = [
  group("browse", "Browse", "workspace"),
  group("edit-live", "Edit live", "workspace", true),
  group("change-sets", "Work in change sets", "workspace", true),
  group("model-authoring", "Model authoring", "instance"),
  group("model-release", "Model release", "workspace"),
  group("security-admin", "Security administration", "instance"),
];

const role = (name: string, instance: boolean, ...labels: string[]): UserRole => ({
  key: name.toLowerCase(),
  name,
  instance,
  workspaces: labels.map((label) => ({ key: label.toLowerCase(), label })),
});

describe("userRoleLine (D298)", () => {
  it("names each role with where it applies, an instance role alone", () => {
    expect(userRoleLine([role("Data steward", false, "Herbarium"), role("Reader", false, "Field stations")])).toBe(
      "Data steward · Herbarium; Reader · Field stations",
    );
    expect(userRoleLine([role("Security administrator", true)])).toBe("Security administrator");
    expect(userRoleLine([role("Data owner", false, "Herbarium", "Field stations")])).toBe(
      "Data owner · Herbarium, Field stations",
    );
  });

  it("counts many workspaces and many roles, and says when there are none", () => {
    expect(userRoleLine([role("Reader", false, "A", "B", "C")])).toBe("Reader · 3 workspaces");
    expect(userRoleLine([role("Reader", false, "A"), role("Operator", true), role("Contributor", false, "B")])).toBe(
      "Reader · A; Operator; and 1 more",
    );
    expect(userRoleLine([])).toBe("No roles yet");
  });
});

describe("grantSentence", () => {
  it("says what a narrowed workspace grant allows", () => {
    expect(
      grantSentence({
        who: "Jonah",
        groups: ["browse", "change-sets"],
        catalogue: CATALOGUE,
        where: "Herbarium",
        narrowedTo: ["Collections", "Determination"],
      }),
    ).toBe(
      "Jonah will read everything and change records in change sets in Herbarium, changing only Collections and Determination.",
    );
  });

  it("names the groups a workspace grant leaves out because they are held only at the instance (D302)", () => {
    expect(
      grantSentence({
        who: "Tomás",
        groups: ["model-authoring", "model-release"],
        catalogue: CATALOGUE,
        where: "Herbarium",
        narrowedTo: [],
      }),
    ).toBe(
      "Tomás will install, activate and migrate model releases in Herbarium. Model authoring is held only for the whole instance, so this grant does not give it.",
    );
  });

  it("covers every workspace at the instance and warns of writes without reading", () => {
    expect(grantSentence({ who: "Mei", groups: ["security-admin"], catalogue: CATALOGUE, narrowedTo: [] })).toBe(
      "Mei will manage people, groups, roles and clients across the whole instance.",
    );
    expect(
      grantSentence({ who: "Ana", groups: ["edit-live"], catalogue: CATALOGUE, where: "Herbarium", narrowedTo: [] }),
    ).toBe("Ana will change records live in Herbarium. Without Browse they cannot read the records they change.");
  });
});

describe("a consumer API grant (Z3, D306)", () => {
  const consumer = (name: string | null): Grant => ({
    id: "g1",
    principal: { kind: "client", id: "c1", name: "Catalogue sync" },
    role: null,
    consumerApi: { key: "catalogue", name },
    scope: {
      instance: false,
      workspaceKey: "herbarium",
      applications: [],
      recordTypes: [],
      applicationNames: [],
      recordTypeNames: [],
    },
    stale: name === null,
    createdAt: "2026-10-24T09:00:00Z",
  });

  it("is named by its API, and by its key once the model no longer declares it", () => {
    expect(grantHeld(consumer("Catalogue"))).toBe("Consumer API: Catalogue");
    expect(staleNote(consumer("Catalogue"))).toBe("");
    expect(grantHeld(consumer(null))).toBe("Consumer API: catalogue");
    expect(staleNote(consumer(null))).toBe(
      "Stale: consumer API “catalogue” is no longer in this workspace’s model, and allows nothing.",
    );
  });
});

describe("securityEventTitle", () => {
  const event = (aggregateType: SecurityEvent["aggregateType"], action: string, details = {}): SecurityEvent => ({
    id: `${aggregateType}-${action}`,
    aggregateType,
    aggregateId: "x",
    action,
    version: 1,
    occurredAt: "2026-10-24T09:00:00Z",
    actor: null,
    details,
  });

  it("says what happened to or by a person, never a secret (0.12 Z4, D319)", () => {
    expect(securityEventTitle(event("sign-in", "succeeded", { address: "10.0.4.17" }))).toBe(
      "Signed in from 10.0.4.17",
    );
    expect(securityEventTitle(event("sign-in", "failed", { address: null }))).toBe("Sign-in failed");
    expect(
      securityEventTitle(
        event("grant", "created", { role: { key: "steward", name: "Data steward" }, workspaceKey: "herbarium" }),
      ),
    ).toBe("Granted Data steward in herbarium");
    expect(
      securityEventTitle(
        event("grant", "created", { role: { name: "Reader" }, workspaceKey: "herbarium" }),
        new Map([["herbarium", "Herbarium"]]),
      ),
    ).toBe("Granted Reader in Herbarium");
    expect(
      securityEventTitle(event("grant", "deleted", { role: null, consumerApi: "catalogue", workspaceKey: "w" })),
    ).toBe("Grant removed: Consumer API: catalogue in w");
    expect(securityEventTitle(event("grant", "created", { role: { name: "Operator" }, workspaceKey: null }))).toBe(
      "Granted Operator in every workspace",
    );
    expect(securityEventTitle(event("group", "member-added", { groupName: "Stewards" }))).toBe("Added to Stewards");
    expect(securityEventTitle(event("user", "updated", { changedFields: ["active"], active: false }))).toBe(
      "Deactivated",
    );
    expect(securityEventTitle(event("user", "updated", { changedFields: ["name", "email"] }))).toBe(
      "Changed name, email",
    );
    expect(securityEventTitle(event("user", "password-link-created"))).toBe("One-time password link made");
    expect(securityEventTitle(event("token-signing-key", "rotated"))).toBe("Token signing key rotated");
  });
});

describe("the Clients page's words (SP2)", () => {
  const workspaces = (...labels: string[]) => labels.map((label) => ({ key: label.toLowerCase(), label }));
  const reader = { key: "reader", name: "Reader", instance: false, workspaces: workspaces("Herbarium") };

  it("names a client's consumer APIs, then its roles (D348)", () => {
    expect(
      clientAccessLine({
        consumerApis: [{ key: "specimen-catalogue", workspaces: workspaces("Herbarium", "Field stations") }],
        roles: [reader],
      }),
    ).toBe("specimen-catalogue · Herbarium, Field stations; Reader · Herbarium");
    expect(
      clientAccessLine({
        consumerApis: [],
        roles: [{ key: "operator", name: "Operator", instance: true, workspaces: [] }],
      }),
    ).toBe("Operator");
    expect(clientAccessLine({ consumerApis: [], roles: [] })).toBe("No access yet");
    expect(
      clientAccessLine({
        consumerApis: [{ key: "a", workspaces: workspaces("One", "Two", "Three") }],
        roles: [],
      }),
    ).toBe("a · 3 workspaces");
    expect(
      clientAccessLine({
        consumerApis: ["a", "b", "c", "d"].map((key) => ({ key, workspaces: workspaces("W") })),
        roles: [reader],
      }),
    ).toBe("a · W; b · W; Reader · Herbarium; and 2 more APIs");
  });

  it("says when a client last obtained a token", () => {
    const now = new Date("2026-10-25T10:15:00Z");
    expect(clientUseLine({ active: true, lastUsedAt: "2026-10-25T10:11:00Z" }, now)).toBe("Last token 4 minutes ago");
    expect(clientUseLine({ active: true, lastUsedAt: null }, now)).toBe("No token yet");
    expect(clientUseLine({ active: false, lastUsedAt: "2026-10-25T10:11:00Z" }, now)).toBe("Deactivated");
  });

  it("says what a consumer API grant allows (D354)", () => {
    expect(consumerApiSentence("catalogue-sync", "Specimen catalogue", "Field stations")).toBe(
      "catalogue-sync will read the Specimen catalogue consumer API in Field stations. It changes nothing and opens nothing on the management API.",
    );
  });

  it("names a signing key's state (D356)", () => {
    const key = { kid: "k", createdAt: "2026-10-01T03:00:00Z", rotatedAt: null, retiredAt: null };
    expect(signingKeyState({ ...key, state: "current" })).toBe("Signing");
    expect(signingKeyState({ ...key, state: "retired", retiredAt: "2026-10-01T04:00:00Z" })).toBe("Retired");
    const verifying = signingKeyState(
      { ...key, state: "verifying", retiredAt: "2026-10-25T11:15:00Z" },
      new Date("2026-10-25T10:15:00Z"),
    );
    expect(verifying).toMatch(/^Verifying until today, /);
  });

  it("titles a client's security events", () => {
    const client = (action: string, details: Record<string, unknown> = {}): SecurityEvent => ({
      id: action,
      aggregateType: "client",
      aggregateId: "c1",
      action,
      version: 1,
      occurredAt: "2026-10-25T10:15:00Z",
      actor: null,
      details,
    });
    expect(securityEventTitle(client("created", { name: "Sync" }))).toBe("Client created");
    expect(securityEventTitle(client("secret-added", { overlapHours: 24 }))).toBe(
      "New secret made; the earlier one works 24 more hours",
    );
    expect(securityEventTitle(client("secret-added", { overlapHours: 0 }))).toBe(
      "New secret made; the earlier ones stopped at once",
    );
    expect(securityEventTitle(client("secret-removed"))).toBe("A secret was ended");
    expect(securityEventTitle(client("updated", { changedFields: ["active"], active: true }))).toBe("Restored");
    expect(securityEventTitle(client("updated", { changedFields: ["name"], name: "Sync 2" }))).toBe(
      "Renamed to Sync 2",
    );
  });

  it("says how people sign in (0.12 I3)", () => {
    const now = new Date("2026-10-25T10:15:00Z");
    expect(providerUseLine({ people: 0, lastSignInAt: null }, now)).toBe("Nobody has signed in yet");
    expect(providerUseLine({ people: 1, lastSignInAt: "2026-10-25T10:11:00Z" }, now)).toMatch(
      /^1 person · last sign-in /,
    );
    expect(providerUseLine({ people: 42, lastSignInAt: "2026-10-25T10:11:00Z" }, now)).toMatch(/^42 people · /);
    expect(localSignInLine({ enabled: true, keptPeople: 1 })).toBe("On · people sign in with a username and password");
    expect(localSignInLine({ enabled: false, keptPeople: 1 })).toBe("Off · 1 administrator keeps a password");
    expect(localSignInLine({ enabled: false, keptPeople: 2 })).toBe("Off · 2 administrators keep a password");
    expect(turnOffSentence(["Northfield Entra ID"], 1)).toBe(
      "People sign in with Northfield Entra ID only. Passwords stop working, except for the 1 administrator made on the server, who keeps local sign-in as the way back. Clients are not affected.",
    );
    expect(turnOffSentence(["A", "B", "C"], 2)).toMatch(
      /^People sign in with A, B or C only\. .*2 administrators .* keep local/,
    );
    expect(turnOffSentence(["A"], 0)).toMatch(/nobody keeps local sign-in: make an administrator on the server/);
    const person = { identities: [], hasPassword: true, lastSignInAt: null };
    expect(personSignInLine(person)).toBe("Never signed in");
    expect(personSignInLine({ ...person, hasPassword: false })).toBe("Has not set a password yet");
    const provided = {
      ...person,
      hasPassword: false,
      identities: [{ provider: { key: "entra", name: "Northfield Entra ID" }, subject: "s" }],
    };
    expect(personSignInLine(provided)).toBe("Signs in with Northfield Entra ID");
  });

  it("titles provider sign-ins and the providers' changes", () => {
    const event = (
      aggregateType: SecurityEvent["aggregateType"],
      aggregateId: string,
      action: string,
      details: Record<string, unknown>,
    ): SecurityEvent => ({
      id: action,
      aggregateType,
      aggregateId,
      action,
      version: 1,
      occurredAt: "2026-10-25T10:15:00Z",
      actor: null,
      details,
    });
    expect(securityEventTitle(event("sign-in", "u", "succeeded", { provider: "entra", address: "10.0.0.1" }))).toBe(
      "Signed in with entra from 10.0.0.1",
    );
    expect(securityEventTitle(event("sign-in", "u", "failed", { provider: "entra", reason: "nonce" }))).toBe(
      "Sign-in with entra failed (nonce)",
    );
    expect(securityEventTitle(event("sign-in", "u", "failed", {}))).toBe("Sign-in failed");
    expect(securityEventTitle(event("user", "u", "created", { provider: "entra" }))).toBe(
      "Person created at their first sign-in with entra",
    );
    expect(securityEventTitle(event("sign-in-provider", "local", "updated", { enabled: false }))).toBe(
      "Local sign-in turned off",
    );
    expect(
      securityEventTitle(event("sign-in-provider", "entra", "updated", { changedFields: ["enabled"], enabled: false })),
    ).toBe("Sign-in provider entra disabled");
  });
});
