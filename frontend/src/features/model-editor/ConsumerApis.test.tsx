import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { ConsumerApiPanel } from "@/features/model-editor/ConsumerApis";
import { consumerDefinitionFixture, outlineFixture } from "@/test/draftOutline";
import { ToastProvider } from "@/ui/Toast";

vi.mock("@/api/client", async (load) => {
  const actual = await load<typeof import("@/api/client")>();
  return { ...actual, api: Object.fromEntries(Object.keys(actual.api).map((key) => [key, vi.fn()])) };
});

function show(tab: "fields" | "types" | "operations", parent: unknown) {
  const definition = consumerDefinitionFixture();
  const object = definition.object as Record<string, unknown>;
  object.parent = parent;
  object.related = {
    bins: { via: "stores", fields: { binName: "name" } },
    notes: { via: "stores", fields: { note: "name" }, served: "onRequest" },
  };
  vi.mocked(api.modelDraftConsumerApi).mockResolvedValue({ version: 4, valid: false, definition });
  render(
    <ToastProvider>
      <ConsumerApiPanel
        draftId="d1"
        outline={outlineFixture()}
        selection={{ show: "consumerApi", key: "shop-feed", tab }}
        onSelect={vi.fn()}
        menuOpen={false}
        onMenuOpenChange={vi.fn()}
        onOperation={vi.fn()}
        run={vi.fn()}
      />
    </ToastProvider>,
  );
}

beforeEach(() => vi.clearAllMocks());

describe("a consumer API's parent and the blocks served on request (0.17 CA1)", () => {
  it("shows the parent's fields and related blocks with their Served, as the object's blocks have theirs", async () => {
    show("fields", {
      output: "category",
      fields: { objectType: "objectType", id: "id", shelfCode: "shelf-code" },
      related: { areaBins: { via: "stores", fields: { binName: "name" }, served: "onRequest" } },
    });
    const section = await screen.findByRole("region", { name: "Parent" });
    expect(within(section).getByText("category")).toBeInTheDocument();
    expect(within(section).getByText("objectType, id, shelfCode=shelf-code")).toBeInTheDocument();
    expect(within(section).getByText(/the attributes of the parent types \(Area\)/)).toBeInTheDocument();
    const block = within(section).getByRole("table", { name: /Related records of the parent/ });
    expect(within(block).getByText("areaBins")).toBeInTheDocument();
    expect(within(block).getByText("On request")).toBeInTheDocument();
    expect(within(section).getByRole("button", { name: /Add related/ })).toBeInTheDocument();
    expect(within(section).getByText(/the parent has no parent of its own/)).toBeInTheDocument();
  });

  it("shows no Parent section for a definition that serves none", async () => {
    show("fields", undefined);
    await screen.findByText(/Parent, path and hierarchy are not served/);
    expect(screen.queryByRole("region", { name: "Parent" })).not.toBeInTheDocument();
  });

  it("has a Served column on the object's blocks", async () => {
    show("types", ["objectType", "id", "code", "name"]);
    const table = await screen.findByRole("table", { name: /Related records Shop feed serves/ });
    expect(within(table).getByRole("columnheader", { name: "Served" })).toBeInTheDocument();
    expect(within(table).getByText("Always")).toBeInTheDocument();
    expect(within(table).getByText("On request")).toBeInTheDocument();
  });

  it("lists the names include accepts, from the Served column", async () => {
    show("operations", {
      output: "parent",
      fields: { id: "id" },
      related: { areaBins: { via: "stores", fields: { binName: "name" }, served: "onRequest" } },
    });
    const section = await screen.findByRole("region", { name: "Include" });
    await waitFor(() => expect(within(section).getAllByRole("listitem")).toHaveLength(2));
    expect(within(section).getByText("notes")).toBeInTheDocument();
    expect(within(section).getByText("parent.areaBins")).toBeInTheDocument();
  });
});

describe("editing the fields of a related block of the parent (0.17 CA1)", () => {
  const block = { via: "stores", fields: { name: "name", externalId: "external-id" } };
  const target = (pointer: string) =>
    ({
      on: "consumerItem",
      consumerApi: "shop-feed",
      pointer,
      label: "related block",
      index: 0,
      count: 1,
      value: block,
      definition: consumerDefinitionFixture(),
    }) as never;

  async function edit(pointer: string, change: () => void) {
    const { OperationDialog } = await import("@/features/model-editor/OperationDialog");
    const { operationById } = await import("@/features/model-editor/operations");
    const run = vi.fn().mockResolvedValue(undefined);
    render(
      <OperationDialog
        operation={operationById("consumer-related-fields")!}
        target={target(pointer)}
        outline={outlineFixture()}
        run={run}
        onClose={vi.fn()}
      />,
    );
    change();
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(run).toHaveBeenCalled());
    return run.mock.calls[0][0];
  }

  it.each(["/object/parent/related/systemVariants", "/object/related/systemVariants"])(
    "sends the block's fields with an existing output renamed (%s)",
    async (pointer) => {
      const sent = await edit(pointer, () =>
        fireEvent.change(screen.getByLabelText("Output name 2"), { target: { value: "extId" } }),
      );
      expect(sent).toEqual([
        {
          kind: "setConsumerApiPart",
          consumerApi: "shop-feed",
          pointer: `${pointer}/fields`,
          value: { name: "name", extId: "external-id" },
        },
      ]);
    },
  );

  it("sends an existing output's source changed, with a field added", async () => {
    const sent = await edit("/object/parent/related/systemVariants", () => {
      fireEvent.change(screen.getByLabelText("Output name 1"), { target: { value: "label" } });
      // An output that follows its source's name follows the new source.
      fireEvent.change(screen.getByLabelText("Source of externalId"), { target: { value: "id" } });
      fireEvent.click(screen.getByRole("button", { name: /Add a field/ }));
    });
    expect(Object.entries(sent[0].value).slice(0, 2)).toEqual([
      ["label", "name"],
      ["id", "id"],
    ]);
    expect(Object.keys(sent[0].value)).toHaveLength(3);
  });
});
