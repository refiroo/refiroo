import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { useCapabilities } from "@/state/useSystem";
import { resetPermissionsForTests } from "@/state/permissions";
import { heldAnywhereFixture } from "@/test/permissions";
import { ConsumerContracts, useKeptContracts } from "@/ui/ActivationParts";
import type { ModelDiagnostic, ModelDraftOutline } from "@/types";

vi.mock("@/api/client", () => ({
  api: {
    myActionGroups: vi.fn(),
    subscriptions: vi.fn(() =>
      Promise.resolve({
        items: [
          { name: "Timetable sync", consumerApi: "stops", contractVersion: 2 },
          { name: "Other version", consumerApi: "stops", contractVersion: 1 },
        ],
        nextCursor: null,
      }),
    ),
  },
}));

vi.mock("@/state/useSystem", () => ({ useCapabilities: vi.fn() }));

function holding(groups: string[]) {
  vi.mocked(useCapabilities).mockReturnValue({
    capabilities: { consumerSubscriptions: { manageSubscriptions: true } },
  } as never);
  vi.mocked(api.myActionGroups).mockResolvedValue(heldAnywhereFixture(groups));
}

const outline = {
  consumerApis: [{ key: "stops", name: "Stops API", contractVersion: 2 }],
} as unknown as ModelDraftOutline;
const diagnostics: ModelDiagnostic[] = [
  {
    severity: "error",
    code: "CONSUMER_CONTRACT_VERSION_REQUIRED",
    path: "/consumerApis/stops/object/fields/isPrimary",
    message: "Consumer API 'stops' field 'isPrimary' changes type; raise contractVersion above 2 to release it",
  },
];

function Section({
  run = vi.fn(() => Promise.resolve()),
  items = diagnostics,
}: {
  run?: () => Promise<unknown>;
  items?: ModelDiagnostic[];
}) {
  const contracts = useKeptContracts(items, "north");
  return (
    <>
      <ConsumerContracts outline={outline} diagnostics={items} run={run} pending={false} contracts={contracts} />
      <output>{contracts.blocked ? "blocked" : "ready"}</output>
      <output>{contracts.keeping ? "keeping" : "not keeping"}</output>
    </>
  );
}

afterEach(resetPermissionsForTests);

describe("ConsumerContracts", () => {
  it("offers Raise and Keep on a break and blocks until one is chosen", async () => {
    holding(["model-release"]);
    render(<Section />);
    expect(screen.getByRole("button", { name: "Raise to v3" })).toBeTruthy();
    expect(await screen.findByRole("button", { name: "Keep v2, break its readers" })).toBeTruthy();
    expect(screen.getByText(/unless you keep its version/)).toBeTruthy();
    expect(screen.getByText("blocked")).toBeTruthy();
  });

  it("shows the kept box with the breaking changes and the webhooks bound to the version", async () => {
    holding(["model-release", "integration-admin"]);
    const run = vi.fn(() => Promise.resolve());
    render(<Section run={run} />);
    fireEvent.click(await screen.findByRole("button", { name: "Keep v2, break its readers" }));
    expect(await screen.findByText("Stays v2, changed in place")).toBeTruthy();
    expect(screen.getByText("Consumer API 'stops' field 'isPrimary' changes type")).toBeTruthy();
    expect(await screen.findByText("Webhooks bound to v2: Timetable sync")).toBeTruthy();
    expect(screen.getByText("ready")).toBeTruthy();
    expect(screen.getByText("keeping")).toBeTruthy();
    expect(screen.queryByText(/unless you keep/)).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Raise to v3 instead" }));
    expect(run).toHaveBeenCalledWith([{ kind: "raiseConsumerApiVersion", consumerApi: "stops" }]);
    expect(screen.getByText("not keeping")).toBeTruthy();
  });

  it("hides Keep from a person who may not install a release", async () => {
    holding(["browse"]);
    render(<Section />);
    await screen.findByText("blocked");
    expect(screen.queryByRole("button", { name: /Keep v2/ })).toBeNull();
    expect(
      screen.getByText("Activation is refused while a consumer API needs a higher contract version."),
    ).toBeTruthy();
  });

  it("does not offer Keep for a changed earlier version", async () => {
    holding(["model-release"]);
    render(
      <Section
        items={[
          ...diagnostics,
          {
            severity: "error",
            code: "CONSUMER_KEPT_VERSION_CHANGED",
            path: "/consumerApis/stops/earlierVersions/0",
            message: "version 1 would read differently",
          },
        ]}
      />,
    );
    await screen.findByText("blocked");
    expect(screen.queryByRole("button", { name: /Keep v2/ })).toBeNull();
  });
});
