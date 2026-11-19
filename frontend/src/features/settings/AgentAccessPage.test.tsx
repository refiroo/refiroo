import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { agentAccess } from "@/api/agentAccessClient";
import { ApiError } from "@/api/errors";
import { security } from "@/api/securityClient";
import { AgentAccessPage } from "@/features/settings/AgentAccessPage";
import { navigationFor } from "@/ui/settingsNavigation";
import type { AgentAccessStatus, AgentApplication, AgentCall, AgentClient, ClientWithSecret } from "@/types";
import { ToastProvider } from "@/ui/Toast";

vi.mock("@/api/agentAccessClient", () => ({
  agentAccess: {
    status: vi.fn(),
    clients: vi.fn(),
    applications: vi.fn(),
    calls: vi.fn(),
    register: vi.fn(),
    block: vi.fn(),
    restore: vi.fn(),
    setSessionLimits: vi.fn(),
  },
}));
vi.mock("@/api/securityClient", () => ({ security: { createClient: vi.fn() } }));

// What the person holds anywhere; the page offers a change only with Security administration.
let held: { key: string }[] | undefined = [];
vi.mock("@/state/permissions", async (original) => ({
  ...(await original<typeof import("@/state/permissions")>()),
  useHeldAnywhere: () => held,
}));

const status: AgentAccessStatus = {
  enabled: true,
  url: "https://refiroo.example.org/mcp",
  ratePerMinute: 120,
  openRegistration: true,
  redirectHosts: [],
  callsDays: 90,
  calls30Days: 3,
  lastCallAt: "2026-10-30T14:02:00Z",
  sessionIdleDays: 30,
  sessionDays: 90,
  sessionLimitsVersion: 1,
  browserSessionIdleHours: 12,
  browserSessionDays: 14,
};

const client = (overrides: Partial<AgentClient>): AgentClient => ({
  id: "c1",
  name: "Reporting assistant",
  active: true,
  kind: "agent",
  version: 1,
  createdAt: "2026-10-01T09:00:00Z",
  updatedAt: "2026-10-01T09:00:00Z",
  lastUsedAt: null,
  secrets: [],
  roles: [],
  consumerApis: [],
  createdBy: null,
  calls30Days: 0,
  lastCallAt: null,
  ...overrides,
});

const application = (overrides: Partial<AgentApplication>): AgentApplication => ({
  id: "a1",
  name: "Claude Code",
  source: "registered",
  returnsTo: ["This computer (localhost)"],
  blocked: false,
  signedIn: 3,
  createdAt: "2026-10-01T09:00:00Z",
  lastUsedAt: null,
  ...overrides,
});

const call = (overrides: Partial<AgentCall>): AgentCall => ({
  id: "k1",
  occurredAt: "2026-10-30T14:02:37Z",
  principal: "Ana Ferreira",
  principalKind: "user",
  principalId: "u1",
  application: "Claude Code",
  tool: "list_workspaces",
  arguments: [],
  outcome: "answered",
  durationMs: 12,
  requestId: null,
  ...overrides,
});

function open(
  options: {
    status?: AgentAccessStatus;
    clients?: AgentClient[];
    applications?: AgentApplication[];
    calls?: AgentCall[];
  } = {},
) {
  vi.mocked(agentAccess.status).mockResolvedValue(options.status ?? status);
  vi.mocked(agentAccess.clients).mockResolvedValue({ items: options.clients ?? [], nextCursor: null });
  vi.mocked(agentAccess.applications).mockResolvedValue({ items: options.applications ?? [], nextCursor: null });
  vi.mocked(agentAccess.calls).mockResolvedValue({ items: options.calls ?? [], nextCursor: null });
  render(
    <ToastProvider>
      <AgentAccessPage onNavigate={vi.fn()} />
    </ToastProvider>,
  );
}

describe("Settings › Security › Agent access (0.16 AG1)", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    held = [{ key: "security-admin" }];
    window.history.replaceState(null, "", "/");
  });

  it("says agent access is off and lists nothing", async () => {
    open({ status: { ...status, enabled: false } });
    await screen.findByText("Agent access is off");
    expect(screen.queryByRole("button", { name: "New agent client" })).toBeNull();
    expect(agentAccess.clients).not.toHaveBeenCalled();
    expect(agentAccess.calls).not.toHaveBeenCalled();
  });

  it("shows how to connect, the clients, the assistants and the calls", async () => {
    open({
      clients: [
        client({ calls30Days: 1284, lastCallAt: "2026-10-30T14:02:00Z" }),
        client({ id: "c2", name: "Service desk" }),
      ],
      applications: [application({}), application({ id: "a2", name: "Other", blocked: true, signedIn: 0 })],
      calls: [
        call({}),
        call({ id: "k2", application: null, tool: "describe_access", arguments: ["cursor"], outcome: "limited" }),
      ],
    });
    await screen.findByText("claude mcp add --transport http refiroo https://refiroo.example.org/mcp");
    expect(screen.getByText("120 calls a minute for each person or client")).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "Reporting assistant" })).toHaveAttribute(
      "href",
      "/settings/clients/c1",
    );
    expect(screen.getByText("1,284")).toBeInTheDocument();
    expect(screen.getAllByText("No access yet", { selector: "td" })).toHaveLength(2);
    expect(await screen.findByText("3 people")).toBeInTheDocument();
    expect(screen.getByText("Blocked")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "Calls" }));
    const rows = await screen.findAllByRole("row");
    const limited = rows.find((row) => within(row).queryByText("describe_access"))!;
    expect(within(limited).getByText("Its own client")).toBeInTheDocument();
    expect(within(limited).getByText("cursor")).toBeInTheDocument();
    expect(within(limited).getByText("Limit reached")).toBeInTheDocument();
    const answered = rows.find((row) => within(row).queryByText("list_workspaces"))!;
    expect(within(answered).getByText("None")).toBeInTheDocument();
    expect(within(answered).getByText("Answered")).toBeInTheDocument();
  });

  it("creates an agent client and shows its secret once", async () => {
    open();
    vi.mocked(security.createClient).mockResolvedValue({
      ...client({ id: "c9", name: "Planner" }),
      secretId: "s1",
      secret: "the-secret-value",
    } as ClientWithSecret);
    fireEvent.click(await screen.findByRole("button", { name: "New agent client" }));
    const dialog = await screen.findByRole("dialog", { name: "New agent client" });
    fireEvent.change(within(dialog).getByLabelText("Name"), { target: { value: "Planner" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Add agent client" }));
    await screen.findByText("the-secret-value");
    expect(security.createClient).toHaveBeenCalledWith({ name: "Planner", kind: "agent" });
    await waitFor(() => expect(agentAccess.clients).toHaveBeenCalledTimes(2));
  });

  it("blocks an assistant only after confirming, and restores one at once", async () => {
    open({ applications: [application({}), application({ id: "a2", name: "Other", blocked: true })] });
    vi.mocked(agentAccess.block).mockResolvedValue(application({ blocked: true }));
    vi.mocked(agentAccess.restore).mockResolvedValue(application({ id: "a2", name: "Other" }));
    fireEvent.click(await screen.findByRole("button", { name: "Block Claude Code" }));
    expect(agentAccess.block).not.toHaveBeenCalled();
    const dialog = await screen.findByRole("alertdialog", { name: "Block Claude Code?" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Block" }));
    await waitFor(() => expect(agentAccess.block).toHaveBeenCalledWith("a1"));
    fireEvent.click(await screen.findByRole("button", { name: "Restore Other" }));
    await waitFor(() => expect(agentAccess.restore).toHaveBeenCalledWith("a2"));
  });

  it("registers an assistant with one return address per line, and shows a refusal", async () => {
    open();
    vi.mocked(agentAccess.register).mockRejectedValueOnce(
      new ApiError(422, "AGENT_APPLICATION_INVALID", "http://assistant.example.com is not an allowed return address."),
    );
    fireEvent.click(await screen.findByRole("button", { name: "New assistant" }));
    const dialog = await screen.findByRole("dialog", { name: "New assistant" });
    fireEvent.change(within(dialog).getByLabelText("Name"), { target: { value: "Helper" } });
    fireEvent.change(within(dialog).getByLabelText("Return addresses"), {
      target: { value: "http://assistant.example.com\n\nhttps://ok.example.com/cb" },
    });
    fireEvent.click(within(dialog).getByRole("button", { name: "Add assistant" }));
    await within(dialog).findByText("http://assistant.example.com is not an allowed return address.");
    expect(agentAccess.register).toHaveBeenCalledWith({
      name: "Helper",
      redirectUris: ["http://assistant.example.com", "https://ok.example.com/cb"],
    });
  });

  it("shows how long assistants stay signed in beside the browser's limits", async () => {
    open();
    const section = await screen.findByRole("region", { name: "Sign-ins" });
    expect(within(section).getByText("30 days")).toBeInTheDocument();
    expect(within(section).getByText("90 days, then the person signs in again")).toBeInTheDocument();
    expect(
      within(section).getByText("12 hours without use, 14 days in all (set in the server's environment)"),
    ).toBeInTheDocument();
  });

  it("offers Change… and New assistant only to someone who may change agent access", async () => {
    open({ applications: [application({}), application({ id: "a2", name: "Other", blocked: true })] });
    await screen.findByRole("button", { name: "Change…" });
    expect(screen.getByRole("button", { name: "New assistant" })).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Block Claude Code" })).toBeInTheDocument();
    cleanup();

    for (const none of [[], undefined]) {
      held = none;
      open({ applications: [application({})] });
      await screen.findByRole("region", { name: "Sign-ins" });
      await screen.findByText("Claude Code");
      expect(screen.queryByRole("button", { name: "Change…" })).toBeNull();
      expect(screen.queryByRole("button", { name: "New assistant" })).toBeNull();
      expect(screen.queryByRole("button", { name: /^Block / })).toBeNull();
      cleanup();
    }
  });

  it("changes the limits in a dialog, refuses what is out of range, and shows the saved values", async () => {
    open();
    vi.mocked(agentAccess.setSessionLimits).mockResolvedValue({
      ...status,
      sessionIdleDays: 10,
      sessionDays: 20,
      sessionLimitsVersion: 2,
    });
    fireEvent.click(await screen.findByRole("button", { name: "Change…" }));
    const dialog = await screen.findByRole("dialog", { name: "Assistant sign-ins" });
    const idle = within(dialog).getByLabelText("Signed out after no use for");
    const all = within(dialog).getByLabelText("Signed out in all after");
    expect(idle).toHaveValue(30);
    expect(all).toHaveValue(90);
    fireEvent.change(idle, { target: { value: "0" } });
    expect(within(dialog).getByText("Enter a whole number of days from 1 to 365.")).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Save" })).toBeDisabled();
    fireEvent.change(idle, { target: { value: "100" } });
    expect(within(dialog).getByText("Must be at least the days without use.")).toBeInTheDocument();
    fireEvent.change(idle, { target: { value: "10" } });
    fireEvent.change(all, { target: { value: "20" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    await waitFor(() =>
      expect(agentAccess.setSessionLimits).toHaveBeenCalledWith({
        sessionIdleDays: 10,
        sessionDays: 20,
        expectedVersion: 1,
      }),
    );
    const section = await screen.findByRole("region", { name: "Sign-ins" });
    await within(section).findByText("10 days");
    expect(within(section).getByText("20 days, then the person signs in again")).toBeInTheDocument();
  });

  it("shows the API's words when the limits are refused", async () => {
    open();
    vi.mocked(agentAccess.setSessionLimits).mockRejectedValueOnce(
      new ApiError(409, "VERSION_CONFLICT", "The sign-in limits have changed"),
    );
    fireEvent.click(await screen.findByRole("button", { name: "Change…" }));
    const dialog = await screen.findByRole("dialog", { name: "Assistant sign-ins" });
    fireEvent.change(within(dialog).getByLabelText("Signed out in all after"), { target: { value: "60" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    await within(dialog).findByText("The sign-in limits have changed");
  });

  it("is listed under Security only to security administrators", () => {
    const labels = (keys: string[]) =>
      navigationFor(keys.map((key) => ({ key })))
        .flatMap((group) => group.pages)
        .map((item) => item.label);
    expect(labels(["security-admin"])).toContain("Agent access");
    expect(labels(["operations"])).not.toContain("Agent access");
  });
});
