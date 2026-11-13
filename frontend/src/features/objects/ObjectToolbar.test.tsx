import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ai } from "@/api/aiClient";
import { ApiError } from "@/api/errors";
import { ObjectToolbar } from "@/features/objects/ObjectToolbar";
import { testModel } from "@/test/fixtures";
import type { CollectionQueryState, QueryTranslation, TableViewDefinition } from "@/types";

const offer = vi.hoisted(() => ({ on: true }));
vi.mock("@/state/useWorkspaceAiOffer", () => ({
  useQueryTranslationOffer: () =>
    offer.on ? { configured: true, provider: "fake", sendLevel: "structure" } : undefined,
}));

afterEach(() => {
  vi.restoreAllMocks();
  offer.on = true;
});

const view = {
  key: "codelists",
  name: "Codelists",
  type: "table",
  objectTypeKey: "codelist",
  config: { columns: ["name"], filterFields: ["code"], sortFields: ["name"], defaultSort: "name", pageSize: 20 },
} as unknown as TableViewDefinition;
const query: CollectionQueryState = { search: "", sort: "name", pageSize: 20, filters: [] };

function toolbar(onChange = vi.fn()) {
  render(
    <ObjectToolbar
      model={testModel}
      view={view}
      query={query}
      placeholder="Search codelists"
      onChange={onChange}
      display={null}
      workspaceKey="default"
      applicationKey="test-app"
      noun={["Codelist", "Codelists"]}
      countDraft={async () => 1}
    />,
  );
  return onChange;
}

const answer = (more: Partial<QueryTranslation>): QueryTranslation => ({
  filters: [],
  search: "",
  notExpressed: [],
  applied: true,
  ...more,
});

describe("asking a list in words (0.16 AG4)", () => {
  it("draws no switch where the question is not offered", () => {
    offer.on = false;
    toolbar();
    expect(screen.queryByRole("radio", { name: "Ask" })).toBeNull();
    expect(screen.getByRole("textbox", { name: "Search" })).toBeInTheDocument();
  });

  it("sends the question on Enter only, then puts the filters on the list with the line that explains them", async () => {
    let finish: (value: QueryTranslation) => void = () => undefined;
    const translate = vi.spyOn(ai, "translateQuery").mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    const onChange = toolbar();
    fireEvent.click(screen.getByRole("radio", { name: "Ask" }));
    const box = screen.getByRole("textbox", { name: "Ask in words" });
    fireEvent.change(box, { target: { value: "codelists with CL in the code" } });
    expect(translate).not.toHaveBeenCalled();
    fireEvent.keyDown(box, { key: "Enter" });
    expect(await screen.findByText("Asking…")).toBeInTheDocument();
    expect(translate).toHaveBeenCalledTimes(1);
    expect(translate.mock.calls[0][1]).toEqual({
      applicationKey: "test-app",
      viewKey: "codelists",
      question: "codelists with CL in the code",
    });
    finish(answer({ filters: [{ field: "code", operator: "contains", value: "CL" }], search: "alpha" }));
    await waitFor(() =>
      expect(onChange).toHaveBeenCalledWith({
        ...query,
        filters: [{ field: "code", operator: "contains", value: "CL" }],
        search: "alpha",
      }),
    );
  });

  it("can be cancelled while it waits, which aborts the request and applies nothing", async () => {
    let signal: AbortSignal | undefined;
    vi.spyOn(ai, "translateQuery").mockImplementation(
      (_workspace, _body, given) =>
        new Promise((_resolve, reject) => {
          signal = given;
          given?.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
        }),
    );
    const onChange = toolbar();
    fireEvent.click(screen.getByRole("radio", { name: "Ask" }));
    const box = screen.getByRole("textbox", { name: "Ask in words" });
    fireEvent.change(box, { target: { value: "anything" } });
    fireEvent.keyDown(box, { key: "Enter" });
    fireEvent.click(await screen.findByRole("button", { name: "Cancel" }));
    expect(signal?.aborted).toBe(true);
    expect(screen.queryByText("Asking…")).toBeNull();
    expect(onChange).not.toHaveBeenCalled();
    expect(box).toHaveValue("anything");
  });

  it("holds back an answer with a part it cannot express: the part, dashed pills and Use these filters", async () => {
    vi.spyOn(ai, "translateQuery").mockResolvedValue(
      answer({
        applied: false,
        filters: [{ field: "code", operator: "contains", value: "CL" }],
        notExpressed: [{ part: "by Anna", reason: "This list has no filter for who changed a record." }],
      }),
    );
    const onChange = toolbar();
    fireEvent.click(screen.getByRole("radio", { name: "Ask" }));
    const box = screen.getByRole("textbox", { name: "Ask in words" });
    fireEvent.change(box, { target: { value: "codelists by Anna" } });
    fireEvent.keyDown(box, { key: "Enter" });
    const panel = await screen.findByText("This list cannot answer all of that, so nothing was applied.");
    expect(onChange).not.toHaveBeenCalled();
    const region = panel.closest("[role=status]") as HTMLElement;
    expect(within(region).getByText("by Anna")).toBeInTheDocument();
    expect(within(region).getByText("Code contains")).toBeInTheDocument();
    expect(within(region).queryByRole("button", { name: /Code contains/ })).toBeNull();
    fireEvent.click(within(region).getByRole("button", { name: "Use these filters" }));
    expect(onChange).toHaveBeenCalledWith({
      ...query,
      filters: [{ field: "code", operator: "contains", value: "CL" }],
      search: "",
    });
  });

  it("says a failure in one sentence, keeps the words, and leaves search working", async () => {
    vi.spyOn(ai, "translateQuery").mockRejectedValue(
      new ApiError(502, "QUERY_TRANSLATION_FAILED", "The question could not be turned into filters: no."),
    );
    toolbar();
    fireEvent.click(screen.getByRole("radio", { name: "Ask" }));
    const box = screen.getByRole("textbox", { name: "Ask in words" });
    fireEvent.change(box, { target: { value: "garbled" } });
    fireEvent.keyDown(box, { key: "Enter" });
    expect(await screen.findByText(/The question could not be turned into filters/)).toBeInTheDocument();
    expect(box).toHaveValue("garbled");
    fireEvent.click(screen.getByRole("radio", { name: "Search" }));
    expect(screen.getByRole("textbox", { name: "Search" })).toBeInTheDocument();
    expect(screen.queryByText(/could not be turned/)).toBeNull();
  });
});
