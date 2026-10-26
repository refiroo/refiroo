import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import { WebhooksPage } from "@/features/settings/WebhooksPage";
import { capabilitiesFixture } from "@/test/capabilities";
import { testModel } from "@/test/fixtures";
import type { ConsumerApiDefinition, EngineModel, SettingsRoute, Subscription } from "@/types";
import { ToastProvider } from "@/ui/Toast";

vi.mock("@/api/client", async (load) => {
  const actual = await load<typeof import("@/api/client")>();
  return { ...actual, api: Object.fromEntries(Object.keys(actual.api).map((key) => [key, vi.fn()])) };
});

// Two consumer APIs: one declares an event and a filter, the other declares no event. The model
// names them; the page reads each expanded (C18).
const model: EngineModel = {
  ...testModel,
  consumerApis: [
    { key: "codes", name: "Codes", contractVersion: 2 },
    { key: "plain", name: "Plain", contractVersion: 1 },
  ],
};

const definitions: Record<string, ConsumerApiDefinition> = {
  codes: {
    key: "codes",
    name: "Codes",
    contractVersion: 2,
    exposes: ["codelist"],
    publicNames: { codelist: "Codelist" },
    operations: {
      objects: {},
      xref: {},
      resolve: {},
      events: {
        perType: false,
        custom: [
          { key: "lists-changed", objectTypes: ["codelist"], changes: ["created", "deleted"] },
          { key: "lists-renamed", objectTypes: ["codelist"], changes: ["updated"], watch: { fields: ["name"] } },
        ],
      },
    },
    filters: { domain: { under: ["domain"], matchOn: ["id", "code"] } },
  },
  plain: {
    key: "plain",
    name: "Plain",
    contractVersion: 1,
    exposes: ["domain"],
    publicNames: { domain: "Domain" },
    operations: { objects: {}, xref: {}, resolve: {} },
    filters: {},
  },
};

const subscription = (id: string, overrides: Partial<Subscription> = {}): Subscription => ({
  id,
  name: `Receiver ${id}`,
  source: "consumerApi",
  consumerApi: "codes",
  contractVersion: 2,
  workspaceKey: "default",
  events: ["lists-changed"],
  filters: {},
  url: `https://receiver.example.com/${id}`,
  maxEventsPerBatch: 1,
  payload: "full",
  format: "rdm",
  status: "active",
  suspension: null,
  acknowledgedThrough: 120,
  delivery: { lastDeliveredAt: null, pending: null },
  signingKeyCreatedAt: "2026-10-07T08:00:00Z",
  previousSigningKeyExpiresAt: null,
  version: 1,
  createdAt: "2026-10-07T08:00:00Z",
  updatedAt: "2026-10-07T08:00:00Z",
  ...overrides,
});

function enabled() {
  const capabilities = capabilitiesFixture();
  capabilities.consumerSubscriptions = {
    ...capabilities.consumerSubscriptions,
    manageSubscriptions: true,
  };
  return capabilities;
}

/** Navigations that leave the Webhooks page, such as to a record. */
const navigatedAway = vi.fn();

/** The page with its address followed, as the settings area does. */
function Page({ start }: { start: Extract<SettingsRoute, { page: "webhooks" }> }) {
  const [route, setRoute] = useState(start);
  return (
    <WebhooksPage
      route={route}
      model={model}
      onNavigate={(next) => {
        if (next.kind === "settings" && next.page === "webhooks") setRoute(next);
        else navigatedAway(next);
      }}
    />
  );
}

const renderPage = (subscriptionId?: string) =>
  render(
    <ToastProvider>
      <Page start={{ kind: "settings", page: "webhooks", subscriptionId }} />
    </ToastProvider>,
  );

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.capabilities).mockResolvedValue(enabled());
  vi.mocked(api.consumerApiDefinition).mockImplementation(async (key) => definitions[key]);
  vi.mocked(api.subscriptions).mockResolvedValue({ items: [], nextCursor: null });
  vi.mocked(api.workspaces).mockResolvedValue({
    items: [
      { key: "other", label: "Other", status: "active", version: 1, createdAt: "", updatedAt: "" },
      { key: "default", label: "Default", status: "active", version: 1, createdAt: "", updatedAt: "" },
    ],
    nextCursor: null,
  } as never);
  vi.mocked(api.workspaceRuntimeState).mockResolvedValue({ defaultWorkspaceKey: "default", version: 1 } as never);
});

describe("Webhooks", () => {
  it("says how to turn webhooks on when the deployment has them off, and reads no subscription", async () => {
    vi.mocked(api.capabilities).mockResolvedValue(capabilitiesFixture());
    renderPage();
    expect(await screen.findByText(/Webhooks are off in this deployment/)).toHaveTextContent(
      "CONSUMER_SUBSCRIPTIONS_ENABLED=true",
    );
    expect(api.subscriptions).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "New webhook" })).not.toBeInTheDocument();
  });

  it("lists subscriptions with their state, and offers New webhook when there are none", async () => {
    renderPage();
    expect(await screen.findByText(/No webhooks yet/)).toBeInTheDocument();
    vi.mocked(api.subscriptions).mockResolvedValue({
      items: [
        subscription("a"),
        subscription("b", {
          delivery: {
            lastDeliveredAt: null,
            pending: {
              deliveryId: "d1",
              throughPosition: 130,
              attempts: 3,
              failingSince: "2026-10-07T08:00:00Z",
              lastAttemptAt: "2026-10-07T08:01:00Z",
              nextAttemptAt: "2026-10-07T08:02:00Z",
              lastError: { kind: "status", status: 503, message: "busy" },
            },
          },
        }),
        subscription("c", {
          status: "suspended",
          suspension: {
            reason: "SUSPENDED_BY_USER",
            message: "Suspended",
            details: null,
            suspendedAt: "2026-10-07T08:00:00Z",
          },
        }),
      ],
      nextCursor: null,
    });
    renderPage();
    const catalogue = await screen.findByRole("navigation", { name: "Webhook catalogue" });
    await within(catalogue).findByRole("button", { name: /Receiver a/ });
    // Each entry: its name, its URL below, and its state.
    expect(
      within(catalogue).getByRole("button", { name: /Receiver a.*receiver.example.com\/a.*Active/ }),
    ).toBeInTheDocument();
    expect(within(catalogue).getByRole("button", { name: /Receiver b.*Retrying/ })).toBeInTheDocument();
    expect(within(catalogue).getByRole("button", { name: /Receiver c.*Suspended/ })).toBeInTheDocument();
  });

  it("names a workspace-events subscription, which has no consumer API, without failing", async () => {
    vi.mocked(api.subscriptions).mockResolvedValue({
      items: [subscription("w", { source: "workspace", consumerApi: null, contractVersion: 1 })],
      nextCursor: null,
    });
    renderPage("w");
    vi.mocked(api.subscription).mockResolvedValue(
      subscription("w", { source: "workspace", consumerApi: null, contractVersion: 1 }),
    );
    expect((await screen.findAllByText(/Workspace events/)).length).toBeGreaterThan(0);
  });

  it("creates a named webhook with chosen events and an added filter, and shows its signing key once", async () => {
    vi.mocked(api.createSubscription).mockResolvedValue(
      subscription("new", { signingSecret: "rdmwh_secret", name: "Billing", filters: { domain: ["d1", "d2"] } }),
    );
    vi.mocked(api.subscription).mockResolvedValue(
      subscription("new", { name: "Billing", filters: { domain: ["d1", "d2"] } }),
    );
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "New webhook" }));
    const dialog = await screen.findByRole("dialog", { name: "New webhook" });
    // Only the API that declares events is offered, and every event is taken until some are chosen.
    expect(within(dialog).getByRole("combobox", { name: "Consumer API" })).toHaveTextContent("Codes · v2");
    expect(within(dialog).queryByText("Plain · v1")).not.toBeInTheDocument();
    expect(within(dialog).getByRole("radio", { name: "All events (2)" })).toBeChecked();
    await waitFor(() => expect(within(dialog).getByRole("combobox", { name: "Workspace" })).toHaveValue("default"));
    fireEvent.change(within(dialog).getByRole("textbox", { name: "Name" }), { target: { value: "Billing" } });
    fireEvent.change(within(dialog).getByRole("textbox", { name: "URL" }), {
      target: { value: "https://receiver.example.com/hook" },
    });

    // Events: chosen from a searchable list, each with its declaration; shown as chips.
    fireEvent.click(within(dialog).getByRole("radio", { name: "Chosen events" }));
    expect(within(dialog).getByText("No event chosen yet.")).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "Choose events" }));
    const picker = await screen.findByRole("dialog", { name: "Events" });
    expect(within(picker).getByText("An update counts when name change.", { exact: false })).toBeInTheDocument();
    fireEvent.change(within(picker).getByRole("searchbox"), { target: { value: "renamed" } });
    expect(within(picker).queryByRole("option", { name: /lists-changed/ })).not.toBeInTheDocument();
    fireEvent.change(within(picker).getByRole("searchbox"), { target: { value: "" } });
    fireEvent.click(within(picker).getByRole("option", { name: /lists-changed/ }));
    fireEvent.click(within(picker).getByRole("button", { name: "Done" }));
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Events" })).not.toBeInTheDocument());
    expect(within(dialog).getByRole("row", { name: "lists-changed" })).toBeInTheDocument();

    // Filters: added from a menu of the declared parameters, values typed as chips.
    expect(within(dialog).queryByRole("textbox", { name: "domain" })).not.toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "Add filter" }));
    fireEvent.click(await screen.findByRole("menuitem", { name: /domain/ }));
    const values = await within(dialog).findByRole("textbox", { name: "domain" });
    fireEvent.change(values, { target: { value: "d1," } });
    fireEvent.change(values, { target: { value: "d2" } });
    fireEvent.keyDown(values, { key: "Enter" });
    expect(within(dialog).getByRole("row", { name: "d2" })).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Add filter" })).toBeDisabled();

    // Delivery: one event per request by default; the content changed to the notification only.
    expect(within(dialog).getByRole("radio", { name: "One event per request" })).toBeChecked();
    expect(within(dialog).getByRole("radio", { name: "RDM JSON" })).toBeChecked();
    expect(within(dialog).getByText(/For bulk changes, batch them/)).toBeInTheDocument();
    expect(within(dialog).queryByRole("spinbutton", { name: "Up to (events)" })).not.toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("radio", { name: "Notification only" }));
    fireEvent.click(within(dialog).getByRole("button", { name: "Create webhook" }));
    const key = await screen.findByRole("dialog", { name: "Keep the signing key" });
    expect(api.createSubscription).toHaveBeenCalledWith({
      name: "Billing",
      consumerApi: "codes",
      workspaceKey: "default",
      events: ["lists-changed"],
      filters: { domain: ["d1", "d2"] },
      url: "https://receiver.example.com/hook",
      maxEventsPerBatch: 1,
      payload: "identity",
      format: "rdm",
    });
    expect(key).toHaveTextContent("rdmwh_secret");
    expect(key).toHaveTextContent("it is not shown again");
    fireEvent.click(within(key).getByRole("button", { name: "I have stored the key" }));
    expect(await screen.findByRole("heading", { name: "Billing" })).toBeInTheDocument();
    expect(screen.queryByText("rdmwh_secret")).not.toBeInTheDocument();
  });

  it("offers every active workspace, read to the last page (0.9 R-F19)", async () => {
    const workspace = (key: string) => ({
      key,
      label: key,
      status: "active",
      version: 1,
      createdAt: "",
      updatedAt: "",
    });
    vi.mocked(api.workspaces).mockImplementation(
      async (query) =>
        (query?.cursor === "next"
          ? { items: [workspace("later")], nextCursor: null }
          : { items: [workspace("default")], nextCursor: "next" }) as never,
    );
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "New webhook" }));
    const dialog = await screen.findByRole("dialog", { name: "New webhook" });
    const select = within(dialog).getByRole("combobox", { name: "Workspace" });
    await waitFor(() => expect(within(select).getByRole("option", { name: "later (later)" })).toBeInTheDocument());
  });

  it("shows a refusal at the field it names", async () => {
    vi.mocked(api.capabilities).mockResolvedValue(enabled());
    vi.mocked(api.createSubscription).mockRejectedValue(
      new ApiError(400, "INVALID_WEBHOOK_URL", "The webhook URL must use https", { pointer: "/url" }),
    );
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "New webhook" }));
    const dialog = await screen.findByRole("dialog", { name: "New webhook" });
    await waitFor(() => expect(within(dialog).getByRole("combobox", { name: "Workspace" })).toHaveValue("default"));
    fireEvent.change(within(dialog).getByRole("textbox", { name: "Name" }), { target: { value: "X" } });
    const url = within(dialog).getByRole("textbox", { name: "URL" });
    fireEvent.change(url, { target: { value: "http://x.test/hook" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Create webhook" }));
    await waitFor(() => expect(url).toHaveAttribute("aria-invalid", "true"));
    expect(url).toHaveAccessibleDescription(/must use https/);
  });

  it.each([
    [
      "DELIVERY_FAILED",
      { attempts: 40, failingSince: "2026-10-06T08:00:00Z", lastError: { kind: "timeout", message: "" } },
      ["Delivery failed", "No answer in time", "Fix the receiver, then resume"],
    ],
    [
      "EVENTS_EXPIRED",
      { fromPosition: 121, toPosition: 300, publication: { id: "p9", eventSequence: 290 } },
      ["121 to 300", "p9", "Resume with reset, then re-sync"],
    ],
    [
      "MODEL_CHANGED",
      { errors: [{ code: "UNKNOWN_EVENT", message: "No event 'gone'", pointer: "/events/0" }] },
      ["No event 'gone'", "/events/0", "Edit it to fix the findings below"],
    ],
  ] as const)("explains a %s suspension and what fixes it", async (reason, details, texts) => {
    vi.mocked(api.subscription).mockResolvedValue(
      subscription("s", {
        status: "suspended",
        suspension: { reason, message: "Suspended by the engine", details, suspendedAt: "2026-10-07T08:00:00Z" },
      }),
    );
    renderPage("s");
    const notice = (await screen.findByText("Suspended by the engine")).closest(".notice") as HTMLElement;
    for (const text of texts) expect(notice).toHaveTextContent(text);
  });

  it("resumes: a refusal lists what to edit, and expired events choose the reset", async () => {
    vi.mocked(api.subscription).mockResolvedValue(
      subscription("s", {
        status: "suspended",
        version: 4,
        suspension: {
          reason: "SUSPENDED_BY_USER",
          message: "Suspended",
          details: null,
          suspendedAt: "2026-10-07T08:00:00Z",
        },
      }),
    );
    vi.mocked(api.resumeSubscription)
      .mockRejectedValueOnce(
        new ApiError(409, "SUBSCRIPTION_NEEDS_EDIT", "Edit what the details list", {
          errors: [{ code: "FILTER_MATCHES_NOTHING", message: "No domain 'x'", pointer: "/filters/domain" }],
        }),
      )
      .mockRejectedValueOnce(
        new ApiError(409, "EVENTS_EXPIRED", "Events from 121 to 300 expired", { fromPosition: 121, toPosition: 300 }),
      )
      .mockResolvedValueOnce(subscription("s", { version: 5 }));
    renderPage("s");
    fireEvent.click(await screen.findByRole("button", { name: "Resume…" }));
    let dialog = await screen.findByRole("dialog", { name: "Resume this webhook?" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Resume" }));
    expect(await within(dialog).findByText(/No domain 'x'/)).toBeInTheDocument();
    expect(dialog).toHaveTextContent("Edit the subscription to fix these");
    fireEvent.click(within(dialog).getByRole("button", { name: "Resume" }));
    expect(await within(dialog).findByText(/Reset is now chosen/)).toBeInTheDocument();
    expect(within(dialog).getByRole("radio", { name: /Now, with reset/ })).toBeChecked();
    fireEvent.click(within(dialog).getByRole("button", { name: "Reset and resume" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(api.resumeSubscription).toHaveBeenLastCalledWith("s", 4, true);
    dialog = screen.getByRole("heading", { name: "Receiver s" }).closest(".webhook-detail") as HTMLElement;
    expect(within(dialog).getByText("Active")).toBeInTheDocument();
  });

  it("rotates the signing key with an overlap, showing the new key once and who still signs", async () => {
    vi.mocked(api.subscription).mockResolvedValue(subscription("s", { version: 2 }));
    vi.mocked(api.rotateSubscriptionSecret).mockResolvedValue(
      subscription("s", {
        version: 3,
        signingSecret: "rdmwh_newkey",
        previousSigningKeyExpiresAt: "2099-10-08T08:00:00Z",
      }),
    );
    renderPage("s");
    fireEvent.click(await screen.findByRole("button", { name: "Rotate key…" }));
    const dialog = await screen.findByRole("dialog", { name: "Rotate the signing key of Receiver s" });
    expect(within(dialog).getByRole("radio", { name: "24 hours" })).toBeChecked();
    fireEvent.click(within(dialog).getByRole("button", { name: "Make a new key" }));
    await waitFor(() => expect(api.rotateSubscriptionSecret).toHaveBeenCalledWith("s", 2, 24));
    const shown = await screen.findByRole("dialog", { name: "Keep the new signing key" });
    expect(shown).toHaveTextContent("rdmwh_newkey");
    expect(shown).toHaveTextContent("lists two signatures");
    fireEvent.click(within(shown).getByRole("button", { name: "I have stored the key" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    const page = screen.getByRole("heading", { name: "Receiver s" }).closest(".webhook-detail") as HTMLElement;
    expect(page).toHaveTextContent("Previous key signs until");
    expect(page).not.toHaveTextContent("rdmwh_newkey");
  });

  it("rotates a leaked key at once and says the old key stopped", async () => {
    vi.mocked(api.subscription).mockResolvedValue(subscription("s", { version: 2 }));
    vi.mocked(api.rotateSubscriptionSecret)
      .mockRejectedValueOnce(new ApiError(500, "INTERNAL_ERROR", "The key could not be made"))
      .mockResolvedValueOnce(subscription("s", { version: 3, signingSecret: "rdmwh_fresh" }));
    renderPage("s");
    fireEvent.click(await screen.findByRole("button", { name: "Rotate key…" }));
    const dialog = await screen.findByRole("dialog", { name: "Rotate the signing key of Receiver s" });
    fireEvent.click(within(dialog).getByRole("radio", { name: "Stop it now" }));
    expect(dialog).toHaveTextContent("For a key that leaked");
    fireEvent.click(within(dialog).getByRole("button", { name: "Make a new key" }));
    expect(await within(dialog).findByText("The key could not be made")).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "Make a new key" }));
    await waitFor(() => expect(api.rotateSubscriptionSecret).toHaveBeenLastCalledWith("s", 2, 0));
    const shown = await screen.findByRole("dialog", { name: "Keep the new signing key" });
    expect(shown).toHaveTextContent("The old key stopped signing now");
  });

  it("edits only what changed, and a stale suspend reloads and says so", async () => {
    vi.mocked(api.subscription)
      .mockResolvedValueOnce(subscription("s", { version: 2 }))
      .mockResolvedValue(subscription("s", { version: 3, url: "https://receiver.example.com/moved" }));
    vi.mocked(api.updateSubscription).mockResolvedValue(
      subscription("s", { version: 3, maxEventsPerBatch: 50, format: "cloudevents" }),
    );
    renderPage("s");
    const page = (await screen.findByRole("heading", { name: "Receiver s" })).closest(".webhook-detail") as HTMLElement;
    expect(page).toHaveTextContent("One event per request");
    expect(page).toHaveTextContent("With the object");
    expect(page).toHaveTextContent("RDM JSON");
    fireEvent.click(await screen.findByRole("button", { name: "Edit…" }));
    const dialog = await screen.findByRole("dialog", { name: "Edit webhook" });
    expect(within(dialog).getByRole("button", { name: "Save changes" })).toBeDisabled();
    fireEvent.click(within(dialog).getByRole("radio", { name: "Batched" }));
    const size = within(dialog).getByRole("spinbutton", { name: "Up to (events)" });
    expect(size).toHaveValue(100);
    expect(size).toHaveAttribute("max", "1000");
    fireEvent.change(size, { target: { value: "50" } });
    fireEvent.click(within(dialog).getByRole("radio", { name: "CloudEvents 1.0" }));
    expect(within(dialog).getByText(/cloudevents-batch\+json/)).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "Save changes" }));
    await waitFor(() =>
      expect(api.updateSubscription).toHaveBeenCalledWith("s", {
        expectedVersion: 2,
        maxEventsPerBatch: 50,
        format: "cloudevents",
      }),
    );
    expect(await screen.findByText("Batched, up to 50 events")).toBeInTheDocument();
    expect(screen.getByText("CloudEvents 1.0")).toBeInTheDocument();
    vi.mocked(api.suspendSubscription).mockRejectedValue(
      new ApiError(409, "VERSION_CONFLICT", "Stale", { currentVersion: 4 }),
    );
    fireEvent.click(await screen.findByRole("button", { name: "Suspend" }));
    expect(await screen.findByText(/changed while the page was open/)).toBeInTheDocument();
    expect(screen.getByText(/receiver\.example\.com\/moved/)).toBeInTheDocument();
  });

  it("renames a webhook alone, sending only the name", async () => {
    vi.mocked(api.subscription).mockResolvedValue(subscription("s", { version: 2 }));
    vi.mocked(api.updateSubscription).mockResolvedValue(subscription("s", { version: 3, name: "Invoices" }));
    renderPage("s");
    fireEvent.click(await screen.findByRole("button", { name: "Edit…" }));
    const dialog = await screen.findByRole("dialog", { name: "Edit webhook" });
    fireEvent.change(within(dialog).getByRole("textbox", { name: "Name" }), { target: { value: " Invoices " } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Save changes" }));
    await waitFor(() =>
      expect(api.updateSubscription).toHaveBeenCalledWith("s", { expectedVersion: 2, name: "Invoices" }),
    );
    expect(await screen.findByRole("heading", { name: "Invoices" })).toBeInTheDocument();
  });

  it("shows a request in flight as sending, with no answer yet", async () => {
    vi.mocked(api.subscription).mockResolvedValue(subscription("s"));
    vi.mocked(api.deliveries).mockResolvedValue({
      items: [
        {
          deliveryId: "n2",
          eventId: "e-2",
          event: "lists-renamed",
          change: "updated",
          objectType: "Codelist",
          objectId: "o-2",
          position: 40,
          status: "sending",
          attempts: 1,
          responseStatus: null,
          sentAt: "2026-10-07T08:01:00Z",
          nextAttemptAt: null,
          resendOf: null,
        },
      ],
      nextCursor: null,
    });
    renderPage("s");
    fireEvent.click(await screen.findByRole("tab", { name: "Deliveries" }));
    const table = await screen.findByRole("group", { name: "Deliveries" });
    const sending = within(table).getByRole("row", { name: /lists-renamed/ });
    expect(sending).toHaveTextContent("Sending");
    // In flight: one attempt started, no answer yet.
    expect(within(sending).getByText("No answer")).toBeInTheDocument();
  });

  it("lists the deliveries on their tab, and opens an event with its attempts and bodies", async () => {
    vi.mocked(api.subscription).mockResolvedValue(subscription("s"));
    const row = {
      deliveryId: "d1",
      eventId: "e-1234567890abcdef",
      event: "lists-changed",
      change: "created",
      objectType: "Codelist",
      objectId: "o-1234567890abcdef",
      position: 12,
      status: "succeeded" as const,
      attempts: 2,
      responseStatus: 200,
      sentAt: "2026-10-07T08:01:00Z",
      nextAttemptAt: null,
      resendOf: null,
    };
    vi.mocked(api.deliveries).mockResolvedValue({ items: [row], nextCursor: null });
    vi.mocked(api.delivery).mockResolvedValue({
      deliveryId: "d1",
      batchId: "d1",
      status: "succeeded",
      events: [
        {
          eventId: row.eventId,
          event: row.event,
          change: row.change,
          objectType: row.objectType,
          objectId: row.objectId,
          position: 12,
        },
      ],
      requestBody: { deliveryId: "d1", events: [{ eventId: row.eventId, ok: true, n: 3 }] },
      requestBytes: 120,
      createdAt: "2026-10-07T08:00:00Z",
      nextAttemptAt: null,
      resendOf: null,
      attempts: [
        {
          number: 1,
          startedAt: "2026-10-07T08:00:00Z",
          completedAt: "2026-10-07T08:00:01Z",
          durationMs: 1200,
          responseStatus: 503,
          error: { kind: "status", message: "503 Service Unavailable: busy" },
          responseBody: "busy",
        },
        {
          number: 2,
          startedAt: "2026-10-07T08:01:00Z",
          completedAt: "2026-10-07T08:01:00Z",
          durationMs: 40,
          responseStatus: 200,
          error: null,
          responseBody: '{"accepted":true}',
        },
      ],
    });
    renderPage("s");
    fireEvent.click(await screen.findByRole("tab", { name: "Deliveries" }));
    const table = await screen.findByRole("group", { name: "Deliveries" });
    expect(api.deliveries).toHaveBeenCalledWith("s", { cursor: undefined, status: undefined });
    const line = within(table).getByRole("row", { name: /lists-changed/ });
    expect(line).toHaveTextContent("Succeeded");
    expect(line).toHaveTextContent("200");

    // The object's ID opens its record, in the application showing its type and the webhook's workspace.
    fireEvent.click(within(line).getByRole("link", { name: `Open record ${row.objectId}` }));
    expect(navigatedAway).toHaveBeenCalledWith({
      kind: "detail",
      applicationKey: "test-app",
      objectTypeKey: "codelist",
      objectId: row.objectId,
      workspaceKey: "default",
    });

    fireEvent.click(within(line).getByRole("link", { name: /e-1234/ }));
    const opened = await screen.findByRole("dialog", { name: "lists-changed" });
    expect(within(opened).getByRole("link", { name: `Open record ${row.objectId}` })).toBeInTheDocument();
    expect(api.delivery).toHaveBeenCalledWith("s", "d1");
    expect(opened).toHaveTextContent(row.objectId);
    const request = within(opened).getByRole("region", { name: "Request body" });
    expect(request.querySelector(".json-key")).toHaveTextContent('"deliveryId"');
    expect(request.querySelector(".json-literal")).toHaveTextContent("true");
    expect(within(opened).getByRole("region", { name: /Response body/ })).toHaveTextContent('"accepted": true');
    fireEvent.click(within(opened).getByRole("button", { name: "Attempt 1" }));
    expect(within(opened).getByRole("region", { name: /Response body · attempt 1/ })).toHaveTextContent("busy");
    expect(opened).toHaveTextContent("1.2 s");
  });

  it("resends an event by hand: a delivered one after a confirmation, a failed one at once", async () => {
    vi.mocked(api.subscription).mockResolvedValue(subscription("s"));
    const row = (deliveryId: string, status: "succeeded" | "failed") => ({
      deliveryId,
      eventId: `e-${deliveryId}`,
      event: "lists-changed",
      change: status === "failed" ? "deleted" : "updated",
      objectType: "Codelist",
      objectId: "o-1",
      position: 7,
      status,
      attempts: 1,
      responseStatus: status === "succeeded" ? 200 : 500,
      sentAt: "2026-10-07T08:00:00Z",
      nextAttemptAt: null,
      resendOf: null,
    });
    const detail = (deliveryId: string, status: "succeeded" | "failed", resendOf: string | null = null) => ({
      deliveryId,
      batchId: deliveryId,
      status,
      events: [
        {
          eventId: `e-${deliveryId}`,
          event: "lists-changed",
          change: "updated",
          objectType: "Codelist",
          objectId: "o-1",
          position: 7,
        },
      ],
      requestBody: { deliveryId, events: [{ eventId: `e-${deliveryId}` }] },
      requestBytes: 50,
      createdAt: "2026-10-07T08:00:00Z",
      nextAttemptAt: null,
      resendOf,
      attempts: [
        {
          number: 1,
          startedAt: "2026-10-07T08:00:00Z",
          completedAt: "2026-10-07T08:00:00Z",
          durationMs: 5,
          responseStatus: status === "succeeded" ? 200 : 500,
          error: status === "succeeded" ? null : { kind: "status" as const, message: "500 Internal Server Error" },
          responseBody: null,
        },
      ],
    });
    vi.mocked(api.deliveries).mockResolvedValue({
      items: [row("d1", "succeeded"), row("d2", "failed")],
      nextCursor: null,
    });
    vi.mocked(api.delivery).mockImplementation(async (_id, deliveryId) =>
      detail(deliveryId, deliveryId === "d1" ? "succeeded" : "failed"),
    );
    vi.mocked(api.resendDelivery).mockResolvedValue(detail("r1", "succeeded", "d1"));
    renderPage("s");
    fireEvent.click(await screen.findByRole("tab", { name: "Deliveries" }));
    const table = await screen.findByRole("group", { name: "Deliveries" });

    // Delivered: Resend asks first; declining sends nothing.
    fireEvent.click(within(table).getByRole("link", { name: "e-d1" }));
    let opened = await screen.findByRole("dialog", { name: "lists-changed" });
    fireEvent.click(await within(opened).findByRole("button", { name: "Resend" }));
    let confirm = await screen.findByRole("alertdialog", { name: "Resend a delivered event?" });
    expect(confirm).toHaveTextContent("already acknowledged");
    fireEvent.click(within(confirm).getByRole("button", { name: "Don't resend" }));
    expect(api.resendDelivery).not.toHaveBeenCalled();
    fireEvent.click(within(opened).getByRole("button", { name: "Resend" }));
    confirm = await screen.findByRole("alertdialog", { name: "Resend a delivered event?" });
    fireEvent.click(within(confirm).getByRole("button", { name: "Resend event" }));
    await waitFor(() => expect(api.resendDelivery).toHaveBeenCalledWith("s", "d1", "e-d1"));
    expect(await within(opened).findByText("Resent")).toBeInTheDocument();
    expect(api.deliveries).toHaveBeenCalledTimes(2);
    fireEvent.click(within(opened).getByRole("button", { name: "Close" }));

    // Failed: Resend sends at once, without asking.
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "lists-changed" })).not.toBeInTheDocument());
    // A deleted record has no record to open.
    const deleted = within(table).getByRole("row", { name: /e-d2/ });
    expect(within(deleted).queryByRole("link", { name: /Open record/ })).not.toBeInTheDocument();
    fireEvent.click(within(table).getByRole("link", { name: "e-d2" }));
    opened = await screen.findByRole("dialog", { name: "lists-changed" });
    fireEvent.click(await within(opened).findByRole("button", { name: "Resend" }));
    await waitFor(() => expect(api.resendDelivery).toHaveBeenLastCalledWith("s", "d2", "e-d2"));
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  });

  it("offers no resend for a request never sent", async () => {
    vi.mocked(api.subscription).mockResolvedValue(subscription("s"));
    vi.mocked(api.deliveries).mockResolvedValue({
      items: [
        {
          deliveryId: "q1",
          eventId: "e-q1",
          event: "lists-changed",
          change: "updated",
          objectType: "Codelist",
          objectId: "o-1",
          position: 3,
          status: "queued",
          attempts: 0,
          responseStatus: null,
          sentAt: null,
          nextAttemptAt: null,
          resendOf: null,
        },
      ],
      nextCursor: null,
    });
    vi.mocked(api.delivery).mockResolvedValue({
      deliveryId: "q1",
      batchId: "q1",
      status: "queued",
      events: [
        {
          eventId: "e-q1",
          event: "lists-changed",
          change: "updated",
          objectType: "Codelist",
          objectId: "o-1",
          position: 3,
        },
      ],
      requestBody: null,
      requestBytes: null,
      createdAt: "2026-10-07T08:00:00Z",
      nextAttemptAt: null,
      resendOf: null,
      attempts: [],
    });
    renderPage("s");
    fireEvent.click(await screen.findByRole("tab", { name: "Deliveries" }));
    fireEvent.click(
      within(await screen.findByRole("group", { name: "Deliveries" })).getByRole("link", { name: "e-q1" }),
    );
    const opened = await screen.findByRole("dialog", { name: "lists-changed" });
    const resend = await within(opened).findByRole("button", { name: "Resend" });
    expect(resend).toBeDisabled();
    expect(resend).toHaveAccessibleDescription(/nothing to resend/);
  });
});
