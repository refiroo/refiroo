import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useRef } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import { testModel } from "@/test/fixtures";
import type { AttributeTypeDefinition, EngineModel } from "@/types";
import {
  RelationAttributes,
  RelationConflictNotice,
  relationAttributeTypes,
  relationValuesFromForm,
  useRelationValues,
} from "@/features/objects/relations/RelationAttributes";

vi.mock("@/api/client", () => ({ api: { updateRelation: vi.fn(), relation: vi.fn() } }));

const attributeType = (key: string, name: string, valueType: AttributeTypeDefinition["valueType"]) => ({
  key,
  name,
  valueType,
  features: {},
  validation: {},
  ui: {},
});
const model: EngineModel = structuredClone(testModel);
model.attributeTypes.push(attributeType("weight", "Weight", "integer"), attributeType("flag", "Flagged", "boolean"));
const binding = { attributeTypeKeys: ["weight", "flag", "unknown-key"] };
const attributes = relationAttributeTypes(model, binding);

function Editor({ onValues }: { onValues: (values: Record<string, unknown>) => void }) {
  const form = useRef<HTMLFormElement>(null);
  return (
    <form
      ref={form}
      onSubmit={(event) => (event.preventDefault(), onValues(relationValuesFromForm(form.current!, attributes)))}
    >
      <RelationAttributes attributes={attributes} relation={{ attributes: { weight: 4, flag: true } }} mode="edit" />
      <button>Save</button>
    </form>
  );
}

describe("RelationAttributes (0.13 RV)", () => {
  beforeEach(() => vi.clearAllMocks());

  it("takes the binding's declared attribute types in order and leaves out one the model lacks", () => {
    expect(attributes.map((item) => item.key)).toEqual(["weight", "flag"]);
    expect(relationAttributeTypes(model, undefined)).toEqual([]);
  });

  it("offers the fields in a group named for the relationship and reads them back typed", () => {
    const onValues = vi.fn();
    render(<Editor onValues={onValues} />);
    expect(screen.getByRole("group", { name: "Attributes of the relationship" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Weight"), { target: { value: "9" } });
    fireEvent.click(screen.getByLabelText("Flagged"));
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onValues).toHaveBeenCalledWith({ weight: 9, flag: false });
  });

  it("shows the values formatted, and nothing when the binding declares none", () => {
    const { container, rerender } = render(
      <RelationAttributes attributes={attributes} relation={{ attributes: { weight: 4 } }} mode="display" />,
    );
    expect(screen.getByRole("group", { name: "Attributes of the relationship" })).toHaveTextContent("Weight");
    expect(screen.getByText("4")).toBeInTheDocument();
    rerender(<RelationAttributes attributes={[]} mode="display" />);
    expect(container).toBeEmptyDOMElement();
  });

  function Saver() {
    const edit = useRelationValues({ id: "rel", version: 1 }, "west");
    return (
      <>
        <button onClick={() => void edit.save({ weight: 2 })}>Save values</button>
        <span data-testid="version">{edit.version}</span>
        {edit.error && <p role="alert">{edit.error}</p>}
        {edit.current && <RelationConflictNotice attributes={attributes} current={edit.current as never} />}
      </>
    );
  }

  it("saves against the version, and after a conflict shows the saved relationship and claims its version", async () => {
    vi.mocked(api.updateRelation)
      .mockRejectedValueOnce(
        new ApiError(409, "VERSION_CONFLICT", "Relation version has changed", { currentVersion: 3 }),
      )
      .mockResolvedValueOnce({ id: "rel", version: 4 } as never);
    vi.mocked(api.relation).mockResolvedValue({ id: "rel", version: 3, attributes: { weight: 7 } } as never);
    render(<Saver />);
    fireEvent.click(screen.getByRole("button", { name: "Save values" }));
    expect(await screen.findByText("Current saved relationship (v3)")).toBeInTheDocument();
    expect(screen.getByText("7")).toBeInTheDocument();
    expect(api.updateRelation).toHaveBeenLastCalledWith("rel", { attributes: { weight: 2 }, expectedVersion: 1 });
    expect(screen.getByTestId("version")).toHaveTextContent("3");
    fireEvent.click(screen.getByRole("button", { name: "Save values" }));
    await waitFor(() => expect(screen.getByTestId("version")).toHaveTextContent("4"));
    expect(api.updateRelation).toHaveBeenLastCalledWith("rel", { attributes: { weight: 2 }, expectedVersion: 3 });
    expect(screen.queryByText(/Current saved relationship/)).toBeNull();
  });
});
