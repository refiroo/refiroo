import { describe, expect, it } from "vitest";
import { outlineFixture } from "@/test/draftOutline";
import type { DraftOperation } from "@/types/modelAdmin";
import type { EngineModel } from "@/types/model";
import type { JobRow } from "@/types/integration";
import type {
  DraftProfileDocument,
  DryRun,
  JoinCandidates,
  ProfileSource,
  SourceColumn,
  SourceSheet,
} from "@/types/sources";
import {
  CARD_WIDTH,
  cardHeight,
  cardsOf,
  chosenColumns,
  containOperations,
  filterOperations,
  groupOperations,
  joinBinding,
  joinOperations,
  joinRequest,
  linesOf,
  loadFigures,
  nameColumnOf,
  nudged,
  pickJoin,
  placed,
  closeUp,
  reasonOf,
  relateOperations,
  relatePlan,
  tableViewOf,
  tidy,
  framesOf,
  fieldOffset,
  withApplication,
  wrongValuesOf,
  sheetAsListOperations,
  sameSheetJoin,
  columnAsListOperations,
  dropPlace,
  freshCardOf,
  BOARD_EDGE,
} from "./canvasModel";
import { columnDropOperations, niceName } from "@/features/model-editor/columnDrop";
import {
  addedColumns,
  commonValueType,
  fillDownOperations,
  headingOperations,
  readingsOf,
  unpivotDefaults,
  unpivotOperations,
} from "@/features/model-editor/readings";

const outline = outlineFixture();

const shelves: ProfileSource = {
  id: "shelves-shelf",
  sheet: "Shelves",
  headerRow: 1,
  applicationKey: "shop",
  objectTypeKey: "shelf",
  block: { firstColumn: "A", lastColumn: "F", lastRow: 40 },
  columns: [
    { column: "Shelf", field: "name" },
    { column: "Code", attributeTypeKey: "code" },
    { column: "Area", parent: { objectTypeKey: "area", matchBy: { field: "name" } } },
    { column: "Note", ignore: true },
  ],
};
const areas: ProfileSource = {
  id: "areas-area",
  sheet: "Areas",
  headerRow: 2,
  applicationKey: "shop",
  objectTypeKey: "area",
  key: { attributeTypeKey: "code" },
  columns: [
    { column: "Area name", field: "name" },
    { column: "Area code", attributeTypeKey: "code" },
  ],
};
const profile: DraftProfileDocument = { key: "p", name: "p", sources: [shelves, areas], valueMaps: {} };

const column = (part: Partial<SourceColumn>): SourceColumn => ({
  sheet: "Shelves",
  letter: "A",
  header: "Width",
  block: 0,
  rows: 10,
  filled: 10,
  distinct: 10,
  valueTypes: { text: 10 },
  candidateKey: false,
  delimiters: [],
  placeholders: [],
  overlaps: [],
  ...part,
});

describe("the cards on the board (0.17 PL3b)", () => {
  it("draws a list for every type the draft adds or a sheet loads, with the columns that fill each field", () => {
    const cards = cardsOf(outline, profile);
    expect(cards.map((card) => card.typeKey).sort()).toEqual(["area", "bin", "shelf"]);
    const shelf = cards.find((card) => card.typeKey === "shelf")!;
    expect(shelf.sheets).toEqual(["Shelves"]);
    expect(shelf.fields.find((field) => field.id === "name")?.columns.map((item) => item.header)).toEqual(["Shelf"]);
    expect(shelf.fields.find((field) => field.id === "parent:area")?.columns[0].header).toBe("Area");
    expect(shelf.fields.some((field) => field.kind === "relation" && field.farType === "bin")).toBe(true);
  });

  it("marks a card, a field and a column Proposed while nobody has touched them", () => {
    const proposed = new Set(["objectType:shelf", "attributeType:depth", "column:shelves-shelf/Code"]);
    const shelf = cardsOf(outline, profile, proposed).find((card) => card.typeKey === "shelf")!;
    expect(shelf.proposed).toBe(true);
    expect(shelf.fields.find((field) => field.id === "attribute:depth")?.proposed).toBe(true);
    expect(shelf.fields.find((field) => field.id === "attribute:code")?.proposed).toBe(true);
    expect(shelf.fields.find((field) => field.id === "name")?.proposed).toBe(false);
  });

  it("lists the filters of the list's table view by the attribute's name", () => {
    const model = {
      applications: [
        {
          key: "shop",
          objectTypeKeys: ["shelf"],
          details: [],
          views: [
            {
              key: "shelves",
              type: "table",
              objectTypeKey: "shelf",
              config: { filterFields: ["depth", "name"], columns: [] },
            },
          ],
        },
      ],
    } as unknown as EngineModel;
    const shelf = cardsOf(outline, profile, new Set(), model).find((card) => card.typeKey === "shelf")!;
    expect(shelf.filters).toEqual([
      { key: "depth", label: "Depth" },
      { key: "name", label: "Name" },
    ]);
    expect(tableViewOf(model, "shelf")?.view.key).toBe("shelves");
    expect(tableViewOf(undefined, "shelf")).toBeUndefined();
  });
});

describe("the lines between the cards", () => {
  it("draws a solid line for a parent and a dashed one for a relationship", () => {
    const lines = linesOf(outline, cardsOf(outline, profile));
    expect(lines.map((line) => [line.kind, line.from, line.to])).toEqual(
      expect.arrayContaining([
        ["contains", "area", "shelf"],
        ["relates", "shelf", "bin"],
      ]),
    );
  });

  it("draws no line for a list that contains itself, or relates to itself", () => {
    const own = structuredClone(outline);
    own.objectTypes.find((type) => type.key === "area")!.parents.push("area");
    own.relations.push({
      relationType: "stores",
      from: "bin",
      to: "bin",
      required: false,
      containment: false,
      mark: "new",
    });
    const lines = linesOf(own, cardsOf(own, profile));
    expect(lines.some((line) => line.from === line.to)).toBe(false);
    expect(lines.length).toBe(2);
  });
});

describe("tidy and placed", () => {
  const cards = cardsOf(outline, profile);
  const lines = linesOf(outline, cards);

  it("uses the board's width before its height and keeps a parent beside its children", () => {
    const wide = tidy(cards, lines, 1200);
    expect(Object.keys(wide).sort()).toEqual(["area", "bin", "shelf"]);
    expect(new Set(Object.values(wide).map((position) => position.x)).size).toBe(3);
    const narrow = tidy(cards, lines, 360);
    expect(new Set(Object.values(narrow).map((position) => position.x)).size).toBe(1);
    // One column: no card overlaps the next.
    const ys = cards.map((card) => narrow[card.typeKey].y).sort((a, b) => a - b);
    expect(ys[1] - ys[0]).toBeGreaterThanOrEqual(cardHeight(cards[0]));
  });

  it("keeps stored places and puts a card with none beside them", () => {
    const stored = { area: { x: 40, y: 80 }, shelf: { x: 400, y: 80 } };
    const result = placed(cards, lines, stored, 1200);
    expect(result.area).toEqual({ x: 40, y: 80 });
    expect(result.shelf).toEqual({ x: 400, y: 80 });
    expect(result.bin.y).toBeGreaterThan(80);
    expect(placed(cards, lines, {}, 1200)).toEqual(tidy(cards, lines, 1200));
  });

  it("reads a stored place above or left of the board inside it", () => {
    const result = placed(
      cards,
      lines,
      { area: { x: -40, y: -18 }, shelf: { x: 400, y: 80 }, bin: { x: 760, y: 3 } },
      1200,
    );
    expect(result.area).toEqual(BOARD_EDGE);
    expect(result.bin).toEqual({ x: 760, y: BOARD_EDGE.y });
    expect(result.shelf).toEqual({ x: 400, y: 80 });
  });

  it("moves a card that overlaps another down below it, keeping its x, in reading order", () => {
    const h = cardHeight(cards.find((card) => card.typeKey === "area")!);
    const stored = { area: { x: 40, y: 80 }, shelf: { x: 60, y: 80 + h - 10 }, bin: { x: 70, y: 80 + h } };
    const result = placed(cards, lines, stored, 1200);
    const box = (key: string) => ({
      ...result[key],
      bottom: result[key].y + cardHeight(cards.find((c) => c.typeKey === key)!),
    });
    expect(result.area).toEqual({ x: 40, y: 80 });
    expect(result.shelf.x).toBe(60);
    expect(result.shelf.y).toBe(80 + h + 28);
    expect(result.bin.x).toBe(70);
    for (const a of Object.keys(result))
      for (const b of Object.keys(result)) {
        if (a >= b) continue;
        const [p, q] = [box(a), box(b)];
        const sideBySide = Math.abs(p.x - q.x) >= CARD_WIDTH;
        expect(sideBySide || p.bottom <= q.y || q.bottom <= p.y).toBe(true);
      }
  });

  it("leaves cards that only stand side by side or one above the other as they are", () => {
    const h = cardHeight(cards.find((card) => card.typeKey === "area")!);
    const stored = { area: { x: 40, y: 80 }, shelf: { x: 360, y: 80 }, bin: { x: 40, y: 80 + h } };
    expect(placed(cards, lines, stored, 1200)).toEqual(stored);
  });

  it("is as wide as a card", () => {
    expect(CARD_WIDTH).toBe(320);
  });
});

describe("the figures", () => {
  const dryRun = (summary: unknown, state = "completed") => ({ state, summary }) as unknown as DryRun;

  it("counts every row of every list and the reasons rows were refused", () => {
    const figures = loadFigures(
      dryRun({
        rows: { total: 120 },
        sources: [
          {
            source: 0,
            objectTypeKey: "shelf",
            records: { created: 90, updated: 0, unchanged: 10 },
            rejections: [{ code: "REFERENCE_NOT_FOUND", rows: 20 }],
          },
        ],
      }),
    );
    expect(figures).toMatchObject({ state: "checked", total: 120, loads: 100, refused: 20 });
    expect(figures.byType.shelf.reasons).toEqual([{ code: "REFERENCE_NOT_FOUND", rows: 20, source: 0 }]);
  });

  it("reads checking, failed and none apart", () => {
    expect(loadFigures(undefined).state).toBe("none");
    expect(loadFigures(dryRun(undefined, "checking")).state).toBe("checking");
    expect(loadFigures(dryRun(undefined, "failed")).state).toBe("failed");
  });
});

describe("a column dropped on a list or a field", () => {
  it("fills the field it is dropped on and makes a new field of a header dropped on the card", () => {
    const onName = columnDropOperations(
      "Shelves",
      "Title",
      { on: "field", typeKey: "shelf", field: cardsOf(outline, profile)[1].fields[0] },
      profile,
      outline,
    );
    expect(onName).toEqual([
      { kind: "mapColumn", source: "shelves-shelf", column: "Title", binding: { field: "name" } },
    ]);
    const onCard = columnDropOperations(
      "Shelves",
      "SHELF_DEPTH?",
      { on: "card", typeKey: "shelf" },
      profile,
      outline,
      column({ valueTypes: { text: 10, decimal: 10 } }),
    );
    expect(onCard.map((item) => item.kind)).toEqual(["addAttributeType", "attachAttribute", "mapColumn"]);
    expect(onCard[0]).toMatchObject({ name: "Shelf depth", valueType: "decimal" });
  });

  it("does not make a column that fills a field of the list a second field, and takes a left-out column back into its own", () => {
    expect(columnDropOperations("Shelves", "Code", { on: "card", typeKey: "shelf" }, profile, outline)).toEqual([]);
    const leftOut: DraftProfileDocument = {
      ...profile,
      sources: [
        {
          ...shelves,
          columns: shelves.columns.map((binding) =>
            binding.column === "Code" ? { column: "Code", ignore: true } : binding,
          ),
        },
        areas,
      ],
    };
    const back = columnDropOperations("Shelves", "Code", { on: "card", typeKey: "shelf" }, leftOut, outline);
    expect(back.map((item) => item.kind)).toEqual(["mapColumn"]);
    expect(back[0]).toMatchObject({ column: "Code", binding: { attributeTypeKey: "code" } });
  });

  it("names a header as a field's name", () => {
    expect(niceName("COUNTRY_CODE")).toBe("Country code");
    expect(niceName("RBStopCategory")).toBe("Rb stop category");
    expect(niceName("Shelf depth")).toBe("Shelf depth");
  });
});

describe("Connect: parent, relationship and the join over every row (PP-D8)", () => {
  it("puts the dragged list under the one it is dropped on", () => {
    const [operation] = containOperations("bin", "area", outline);
    expect(operation).toMatchObject({ kind: "setContainment", objectType: "bin", parent: { objectTypes: ["area"] } });
  });

  it("makes a relationship with the key its binding will name", () => {
    const plan = relatePlan("bin", "area", outline);
    expect(plan.operations.map((item) => item.kind)).toEqual(["addRelationType", "allowRelation"]);
    expect(plan.operations[0].key).toBe(plan.relationType);
    expect(relateOperations("bin", "area", outline)).toEqual(plan.operations);
  });

  it("finds the other list's name column, else the column of its key", () => {
    expect(nameColumnOf(profile, "area")).toMatchObject({ header: "Area name", matchBy: { field: "name" } });
    const keyed = structuredClone(profile);
    keyed.sources[1].columns = [{ column: "Area code", attributeTypeKey: "code" }];
    expect(nameColumnOf(keyed, "area")).toMatchObject({ header: "Area code", matchBy: { attributeTypeKey: "code" } });
    expect(nameColumnOf(profile, "bin")).toBeUndefined();
  });

  it("asks the join route about the other list's column against the starting list's table", () => {
    const other = nameColumnOf(profile, "area")!;
    expect(joinRequest(other, shelves)).toEqual({
      column: { sheet: "Areas", column: "Area name", headerRow: 2 },
      against: { sheet: "Shelves", headerRow: 1, block: { firstColumn: "A", lastColumn: "F", lastRow: 40 } },
    });
  });

  const answer = (candidates: Partial<JoinCandidates["candidates"][number]>[]): JoinCandidates =>
    ({
      column: { sheet: "Areas", letter: "A", header: "Area name", rows: 10, distinct: 10 },
      candidates: candidates.map((item, index) => ({
        sheet: "Shelves",
        letter: "CDEFG"[index],
        header: `H${index}`,
        rows: 10,
        distinct: 10,
        matchedValues: 10,
        matchedRows: 10,
        share: 1,
        unique: false,
        ...item,
      })),
      best: null,
      tie: false,
      tied: [],
    }) as JoinCandidates;

  it("takes the best column and asks when two are tied", () => {
    expect(
      pickJoin(
        answer([
          { header: "Region", matchedRows: 10 },
          { header: "Other", matchedRows: 4 },
        ]),
        shelves,
      ).best?.header,
    ).toBe("Region");
    const tied = pickJoin(answer([{ header: "Region" }, { header: "Area copy" }]), shelves);
    expect(tied.best).toBeUndefined();
    expect(tied.tied.map((item) => item.header)).toEqual(["Region", "Area copy"]);
  });

  it("leaves out a column the source already reads as something else and one that matched nothing", () => {
    const result = pickJoin(
      answer([
        { header: "Shelf", matchedRows: 10 },
        { header: "Zero", matchedRows: 0 },
        { header: "Region", matchedRows: 3 },
      ]),
      shelves,
    );
    expect(result.best?.header).toBe("Region");
    expect(pickJoin(answer([{ header: "Shelf" }]), shelves)).toEqual({ tied: [] });
  });

  it("binds the join column by name and creating, or by the unique attribute without creating", () => {
    expect(joinBinding("parent", { typeKey: "area", matchBy: { field: "name" } })).toEqual({
      parent: { objectTypeKey: "area", matchBy: { field: "name" }, missing: "create" },
    });
    const bound = joinBinding("relation", { typeKey: "bin", matchBy: { attributeTypeKey: "code" } }, "shelf-bin");
    expect(bound).toEqual({
      relation: { relationTypeKey: "shelf-bin", objectTypeKey: "bin", matchBy: { attributeTypeKey: "code" } },
    });
    expect(joinOperations("parent", shelves, "Region", { typeKey: "area", matchBy: { field: "name" } })).toEqual([
      {
        kind: "mapColumn",
        source: "shelves-shelf",
        column: "Region",
        binding: { parent: { objectTypeKey: "area", matchBy: { field: "name" }, missing: "create" } },
      },
    ]);
  });
});

describe("several columns onto one field (PP-D6)", () => {
  const wide = ["2022", "2023", "2024"];

  it("suggests Year for years, Period for quarters and a name that is free", () => {
    expect(unpivotDefaults(wide, new Set())).toEqual({ nameColumn: "Year", valueColumn: "Value" });
    expect(unpivotDefaults(["Q1", "Q2"], new Set())).toEqual({ nameColumn: "Period", valueColumn: "Value" });
    expect(unpivotDefaults(wide, new Set(["Year", "Value"]))).toEqual({ nameColumn: "Year 2", valueColumn: "Value 2" });
  });

  it("takes the common value type and falls back to text", () => {
    const numbers = (count: number) => column({ valueTypes: { text: count, integer: count } });
    expect(commonValueType([numbers(3), numbers(5)])).toBe("integer");
    expect(commonValueType([numbers(3), column({ valueTypes: { text: 5 } })])).toBe("text");
    // A column of numbers with one word in it is text: every filled cell must read as the type.
    expect(commonValueType([column({ valueTypes: { text: 25, integer: 24 } })])).toBe("text");
  });

  it("onto a card reads the columns as rows and adds the two new columns as new fields, in one request", () => {
    const operations = unpivotOperations(
      {
        sheet: "Shelves",
        columns: wide,
        nameColumn: "Year",
        valueColumn: "Value",
        drop: { on: "card", typeKey: "shelf" },
      },
      profile,
      outline,
      () => column({ valueTypes: { text: 5, integer: 5 } }),
    );
    expect(operations.map((item) => item.kind)).toEqual([
      "setUnpivot",
      "addAttributeType",
      "attachAttribute",
      "mapColumn",
      "addAttributeType",
      "attachAttribute",
      "mapColumn",
    ]);
    expect(operations[0]).toEqual({
      kind: "setUnpivot",
      source: "shelves-shelf",
      columns: wide,
      nameColumn: "Year",
      valueColumn: "Value",
    });
    expect(operations[3]).toMatchObject({ column: "Year" });
    expect(operations[1]).toMatchObject({ valueType: "text" });
    expect(operations[4]).toMatchObject({ valueType: "integer" });
  });

  it("onto an attribute fills it with the cells; onto the parent or name field the headers find the record", () => {
    const shelf = cardsOf(outline, profile).find((card) => card.typeKey === "shelf")!;
    const depth = shelf.fields.find((field) => field.id === "attribute:depth")!;
    const cells = unpivotOperations(
      {
        sheet: "Shelves",
        columns: wide,
        nameColumn: "Year",
        valueColumn: "Value",
        drop: { on: "field", typeKey: "shelf", field: depth },
      },
      profile,
      outline,
      () => undefined,
    );
    expect(cells.find((item) => item.kind === "mapColumn" && item.column === "Value")).toMatchObject({
      binding: { attributeTypeKey: "depth" },
    });
    const parent = shelf.fields.find((field) => field.kind === "parent")!;
    const headers = unpivotOperations(
      {
        sheet: "Shelves",
        columns: wide,
        nameColumn: "Area",
        valueColumn: "Value",
        drop: { on: "field", typeKey: "shelf", field: parent },
      },
      profile,
      outline,
      () => undefined,
    );
    expect(headers.find((item) => item.kind === "mapColumn" && item.column === "Area")).toMatchObject({
      binding: { parent: { objectTypeKey: "area", matchBy: { field: "name" }, missing: "create" } },
    });
  });

  it("starts a source for a list no source on the sheet loads and unmaps a wide column it read otherwise", () => {
    const fresh = unpivotOperations(
      { sheet: "Sales", columns: wide, nameColumn: "Year", valueColumn: "Value", drop: { on: "card", typeKey: "bin" } },
      profile,
      outline,
      () => undefined,
    );
    expect(fresh[0]).toMatchObject({ kind: "addSource", sheet: "Sales", objectType: "bin" });
    expect(fresh.filter((item) => item.kind === "addSource")).toHaveLength(1);
    const reread = structuredClone(profile);
    reread.sources[0].columns.push({ column: "2023", attributeTypeKey: "depth" });
    const unmapped = unpivotOperations(
      {
        sheet: "Shelves",
        columns: wide,
        nameColumn: "Year",
        valueColumn: "Value",
        drop: { on: "card", typeKey: "shelf" },
      },
      reread,
      outline,
      () => undefined,
    );
    expect(unmapped[0]).toEqual({ kind: "unmapColumn", source: "shelves-shelf", column: "2023" });
  });
});

describe("the readings of a sheet (PP-D7)", () => {
  const reading: DraftProfileDocument = {
    ...profile,
    sources: [
      {
        ...shelves,
        fillDown: ["Area"],
        headings: { column: "Shelf", into: "Group" },
        unpivot: { columns: ["2022", "2023"], nameColumn: "Year", valueColumn: "Value" },
      },
    ],
  };

  it("says which reading is on a column and which columns the readings add", () => {
    expect(readingsOf(reading, "Shelves", "Area").map((item) => item.kind)).toEqual(["fillDown"]);
    expect(readingsOf(reading, "Shelves", "2022").map((item) => item.kind)).toEqual(["unpivot"]);
    expect(readingsOf(reading, "Shelves", "Shelf").map((item) => item.kind)).toEqual(["headings"]);
    expect(addedColumns(reading, "Shelves").map((item) => item.header)).toEqual(["Year", "Value", "Group"]);
  });

  it("turns fill down on and off, clearing it when no column is left", () => {
    expect(fillDownOperations(shelves, "Area", true)).toEqual([
      { kind: "setFillDown", source: "shelves-shelf", columns: ["Area"] },
    ]);
    expect(fillDownOperations(reading.sources[0], "Area", false)).toEqual([
      { kind: "clearFillDown", source: "shelves-shelf" },
    ]);
  });

  it("reads headings, makes the parent a new list and binds the new column as the parent", () => {
    const operations = headingOperations(
      { sheet: "Shelves", column: "Shelf", into: "Zone", rowType: "shelf", parent: { newName: "Zone" } },
      profile,
      outline,
    );
    expect(operations.map((item) => item.kind)).toEqual([
      "setHeadingRows",
      "addObjectType",
      "setContainment",
      "mapColumn",
    ]);
    expect(operations[3]).toMatchObject({
      column: "Zone",
      binding: { parent: { objectTypeKey: "zone", matchBy: { field: "name" }, missing: "create" } },
    });
    // Under an existing parent the list already sits under, no containment is added.
    const existing = headingOperations(
      { sheet: "Shelves", column: "Shelf", into: "Zone", rowType: "shelf", parent: { typeKey: "area" } },
      profile,
      outline,
    );
    expect(existing.map((item) => item.kind)).toEqual(["setHeadingRows", "mapColumn"]);
  });
});

describe("a column onto a list's filters", () => {
  const model = (filterFields: string[]) =>
    ({
      applications: [
        {
          key: "shop",
          objectTypeKeys: ["shelf"],
          details: [],
          views: [{ key: "shelves", type: "table", objectTypeKey: "shelf", config: { filterFields, columns: [] } }],
        },
      ],
    }) as unknown as EngineModel;
  const where = { sheet: "Shelves", header: "Colour", typeKey: "shelf" };

  it("adds a filterable attribute and maps the column in one request: attaching it places it in the filters", () => {
    const { operations } = filterOperations(where, profile, outline, model([]), column({ header: "Colour" }));
    expect(operations.map((item) => item.kind)).toEqual(["addAttributeType", "attachAttribute", "mapColumn"]);
    expect(operations[0]).toMatchObject({ features: { filterable: true } });
  });

  it("makes an attribute the column fills filterable when it is not, then filters by it", () => {
    const { operations } = filterOperations({ ...where, header: "Code" }, profile, outline, model([]));
    expect(operations.map((item) => item.kind)).toEqual(["setAttributeTypeFeatures", "insertViewItem"]);
    expect(operations[0]).toMatchObject({
      attributeType: "code",
      features: { filterable: true, unique: true, searchable: false, sortable: false },
    });
  });

  it("says why nothing is built: no table view to hold the filter, or the list already filters by it", () => {
    expect(filterOperations(where, profile, outline, undefined).problem).toBe("noView");
    expect(filterOperations({ ...where, header: "Code" }, profile, outline, model(["code"])).problem).toBe("already");
  });
});

describe("choosing columns and moving cards from the keyboard", () => {
  const order = ["A", "B", "C", "D", "E"];

  it("chooses one by a press, adds with Ctrl, and takes a range with Shift", () => {
    expect(chosenColumns([], order, "B", {})).toEqual(["B"]);
    expect(chosenColumns(["B"], order, "B", {})).toEqual([]);
    expect(chosenColumns(["B"], order, "D", { toggle: true })).toEqual(["B", "D"]);
    expect(chosenColumns(["B", "D"], order, "D", { toggle: true })).toEqual(["B"]);
    expect(chosenColumns(["B"], order, "D", { shift: true }, "B")).toEqual(["B", "C", "D"]);
    expect(chosenColumns(["D"], order, "B", { shift: true }, "D")).toEqual(["B", "C", "D"]);
  });

  it("moves a card sixteen pixels an arrow press and never off the board", () => {
    expect(nudged({ x: 100, y: 100 }, "ArrowRight")).toEqual({ x: 116, y: 100 });
    expect(nudged({ x: 100, y: 100 }, "ArrowUp")).toEqual({ x: 100, y: 84 });
    // Never nearer the corner than the board's edge, so the frame and its label stay on the board.
    expect(nudged({ x: 30, y: 60 }, "ArrowLeft")).toEqual(BOARD_EDGE.x === 24 ? { x: 24, y: 60 } : undefined);
    expect(nudged({ x: 4, y: 4 }, "Enter")).toBeUndefined();
  });
});

describe("refused rows (PP-D4)", () => {
  const row = (message: string, column = "Area", code = "REFERENCE_NOT_FOUND"): JobRow =>
    ({
      ref: "r",
      sheet: "Shelves",
      row: 2,
      status: "rejected",
      actions: { created: 0, updated: 0, unchanged: 0, deleted: 0 },
      outcomes: [{ index: 0, ref: null, status: "rejected", error: { code, message, details: { column } } }],
    }) as unknown as JobRow;

  it("reads the wrong values of a column from the refusals, most rows first", () => {
    const found = wrongValuesOf([
      row('No area record matches "Nord" in column Area'),
      row('No area record matches "Nord" in column Area'),
      row('No area record matches "Süd \\"X\\"" in column Area'),
      row("No shelf record has the key 7"),
    ]);
    expect(found).toEqual([
      {
        column: "Area",
        values: [
          { text: "Nord", rows: 2 },
          { text: 'Süd "X"', rows: 1 },
        ],
      },
    ]);
  });

  it("names a reason in the engine's words, from the first row", () => {
    expect(reasonOf([row('No area record matches "x" in column Area')])).toContain("No area record");
    expect(reasonOf([])).toBeUndefined();
  });
});

describe("a draft with no application (a workbook nothing was read from)", () => {
  const empty = { ...outlineFixture(), applications: [], objectTypes: [], attributeTypes: [], relationTypes: [] };
  const newList = {
    kind: "addObjectType",
    key: "stock",
    name: "Stock",
    parent: null,
  } as unknown as DraftOperation;

  it("gets an application named for the draft, with the new lists and nested null application keys placed in it", () => {
    const nested = {
      kind: "mapColumn",
      source: "s",
      column: "Area",
      binding: { parent: { applicationKey: null, objectTypeKey: "area" } },
    } as unknown as DraftOperation;
    const sent = withApplication([newList, nested], empty, "Office supplies");
    expect(sent[0]).toEqual({ kind: "addApplication", key: "office-supplies", name: "Office supplies" });
    expect(sent[1]).toMatchObject({ kind: "addObjectType", key: "stock", applicationKey: "office-supplies" });
    expect(JSON.stringify(sent[2])).toContain('"applicationKey":"office-supplies"');
    expect(JSON.stringify(sent[2])).not.toContain("null");
  });

  it("passes through when the draft has an application, or the request adds no list", () => {
    const ops = [newList];
    expect(withApplication(ops, outlineFixture(), "Office supplies")).toBe(ops);
    const mapOnly = [{ kind: "ignoreColumn", source: "s", column: "A" }] as DraftOperation[];
    expect(withApplication(mapOnly, empty, "Office supplies")).toBe(mapOnly);
  });
});

describe("a sheet dropped on the empty board", () => {
  const sheet: SourceSheet = {
    index: 0,
    name: "Stock items",
    rows: 30,
    headerRow: 2,
    blocks: [{ index: 0, range: "A2:D32", firstColumn: "A", lastColumn: "D", headerRow: 2, lastRow: 32, rows: 30 }],
  };
  const columns = [
    column({ header: "Region", distinct: 3 }),
    column({ header: "Item", distinct: 30 }),
    column({ header: "Price", distinct: 12, valueTypes: { text: 30, decimal: 30 } }),
    column({ header: "Colour", distinct: 5 }),
  ];
  const noApplication = { ...outlineFixture(), applications: [] };

  it("makes a list named for the sheet, named by the text column with the most different values, and the rest fields", () => {
    const ops = sheetAsListOperations(sheet, columns, null, noApplication);
    expect(ops[0]).toMatchObject({ kind: "addObjectType", key: "stock-items", name: "Stock items", parent: null });
    expect(ops[0]).not.toHaveProperty("applicationKey");
    expect(ops[1]).toMatchObject({ kind: "addSource", sheet: "Stock items", objectType: "stock-items", headerRow: 2 });
    const source = (ops[1] as unknown as { id: string }).id;
    expect(ops[2]).toEqual({ kind: "mapColumn", source, column: "Item", binding: { field: "name" } });
    const attributes = ops.filter((op) => op.kind === "addAttributeType");
    expect(attributes.map((op) => [op.name, op.valueType])).toEqual([
      ["Region", "text"],
      ["Price", "decimal"],
      ["Colour", "text"],
    ]);
    expect(ops.filter((op) => op.kind === "attachAttribute")).toHaveLength(3);
    expect(ops.filter((op) => op.kind === "mapColumn")).toHaveLength(4);
  });

  it("names the record by a text column whose cells are all different before the one with most distinct values", () => {
    const keyed = [{ ...columns[0], candidateKey: true }, ...columns.slice(1)];
    const ops = sheetAsListOperations(sheet, keyed, null, noApplication);
    expect(ops[2]).toMatchObject({ kind: "mapColumn", column: "Region", binding: { field: "name" } });
  });

  it("puts the list in the draft's application when it has one, and makes nothing of an empty sheet", () => {
    const ops = sheetAsListOperations(sheet, columns, null, outlineFixture());
    expect(ops[0]).toMatchObject({ applicationKey: "shop" });
    expect(sheetAsListOperations(sheet, [], null, outlineFixture())).toEqual([]);
    expect(sheetAsListOperations(sheet, [column({ header: null as never })], null, outlineFixture())).toEqual([]);
  });
});

describe("a column dropped on the empty board", () => {
  const sheet: SourceSheet = {
    index: 0,
    name: "Shelves",
    rows: 40,
    headerRow: 1,
    blocks: [{ index: 0, range: "A1:E40", firstColumn: "A", lastColumn: "E", headerRow: 1, lastRow: 40, rows: 39 }],
  };

  it("makes a list named for the column, a relationship from the sheet's list and the binding that creates its records, in one request", () => {
    const ops = columnAsListOperations(sheet, "Region", profile, outline);
    expect(ops.map((op) => op.kind)).toEqual([
      "addObjectType",
      "addRelationType",
      "allowRelation",
      "mapColumn",
      "addSource",
      "mapColumn",
    ]);
    expect(ops[0]).toMatchObject({ key: "region", name: "Region", applicationKey: "shop", parent: null });
    expect(ops[2]).toMatchObject({ from: "shelf", to: "region" });
    // The list reads the column itself, so it has a source and the join can find its parent's column.
    expect(ops[4]).toMatchObject({ kind: "addSource", objectType: "region", key: { field: "name" } });
    expect(ops[5]).toMatchObject({ column: "Region", binding: { field: "name" } });
    expect(ops[3]).toMatchObject({
      source: "shelves-shelf",
      column: "Region",
      binding: {
        relation: {
          relationTypeKey: (ops[1] as unknown as { key: string }).key,
          objectTypeKey: "region",
          matchBy: { field: "name" },
          missing: "create",
        },
      },
    });
  });

  it("turns a column already read as an attribute into the list instead", () => {
    const ops = columnAsListOperations(sheet, "Code", profile, outline);
    expect(ops.map((op) => op.kind)).toEqual(["convertAttributeToListType", "addSource", "mapColumn"]);
    expect(ops[1]).toMatchObject({ objectType: (ops[0] as unknown as { key: string }).key, key: { field: "name" } });
    expect(ops[2]).toMatchObject({ column: "Code", binding: { field: "name" } });
    expect(ops[0]).toMatchObject({
      kind: "convertAttributeToListType",
      objectType: "shelf",
      attributeType: "code",
      name: "Code",
    });
  });

  it("says nothing can be built for a column read as the name, a parent or a relationship", () => {
    expect(columnAsListOperations(sheet, "Shelf", profile, outline)).toEqual([]);
    expect(columnAsListOperations(sheet, "Area", profile, outline)).toEqual([]);
  });

  it("reads the column as the new list's own name when no list reads the sheet", () => {
    const ops = columnAsListOperations({ ...sheet, name: "Other" }, "Region", profile, outline);
    expect(ops.map((op) => op.kind)).toEqual(["addObjectType", "addSource", "mapColumn"]);
    expect(ops[1]).toMatchObject({ sheet: "Other", objectType: "region", headerRow: 1 });
    expect(ops[2]).toMatchObject({ column: "Region", binding: { field: "name" } });
  });

  it("keeps a drop inside the board's edge, where its frame and label stay on the board", () => {
    expect(dropPlace({ x: 3, y: -12 })).toEqual(BOARD_EDGE);
    expect(dropPlace({ x: 240, y: 90 })).toEqual({ x: 240, y: 90 });
  });
});

describe("two lists that read the same sheet", () => {
  const other = (sheet: string) => ({
    source: { ...areas, sheet },
    header: "Area name",
    matchBy: { field: "name" as const },
  });

  it("join by the other list's own column in the same row, unless the starting list reads it otherwise", () => {
    expect(sameSheetJoin({ ...shelves, sheet: "Areas" }, other("Areas"))).toBe("Area name");
    expect(sameSheetJoin(shelves, other("Areas"))).toBeUndefined();
    const reading = { ...shelves, sheet: "Areas", columns: [{ column: "Area name", attributeTypeKey: "code" }] };
    expect(sameSheetJoin(reading, other("Areas"))).toBeUndefined();
    expect(sameSheetJoin(areas, { ...other("Areas"), source: areas })).toBeUndefined();
  });
});

describe("the whole model on the board (0.17 CE1)", () => {
  it("shows every list in the whole model, the changed ones and their parents when narrowed, a sheet's lists in the workbook's", () => {
    const keys = (scope: "model" | "changed" | "workbook", prof = profile) =>
      cardsOf(outline, prof, new Set(), undefined, { scope })
        .map((card) => card.typeKey)
        .sort();
    expect(keys("model", { ...profile, sources: [] })).toEqual(["area", "bin", "shelf"]);
    // Changed: the new list and the changed one; the released shelf is neither, and no changed list stands under it.
    expect(keys("changed")).toEqual(["area", "bin"]);
    expect(keys("workbook")).toEqual(["area", "bin", "shelf"]);
  });

  it("draws a released list nothing changed and no sheet loads quieter, and carries each list's mark", () => {
    const cards = cardsOf(outline, { ...profile, sources: [] }, new Set(), undefined, { scope: "model" });
    expect(cards.find((card) => card.typeKey === "shelf")).toMatchObject({ mark: "released", quiet: true });
    expect(cards.find((card) => card.typeKey === "bin")).toMatchObject({ mark: "new", quiet: false });
    // A sheet that loads it, or a proposal that is still the engine's, brings it forward.
    expect(
      cardsOf(outline, profile, new Set(), undefined, { scope: "model" }).find((c) => c.typeKey === "shelf")?.quiet,
    ).toBe(false);
    expect(
      cardsOf(outline, { ...profile, sources: [] }, new Set(["objectType:shelf"]), undefined, { scope: "model" }).find(
        (c) => c.typeKey === "shelf",
      )?.quiet,
    ).toBe(false);
  });

  it("draws a folded card as its top bar, so the lines and Tidy agree with it", () => {
    const cards = cardsOf(outline, profile, new Set(), undefined, { folded: new Set(["shelf"]) });
    const shelf = cards.find((card) => card.typeKey === "shelf")!;
    expect(shelf.folded).toBe(true);
    expect(cardHeight(shelf)).toBeLessThan(cardHeight({ ...shelf, folded: false }));
    expect(fieldOffset(shelf, shelf.fields[1].id)).toBe(22);
  });

  it("lays each application's lists in a frame of their own and keeps lists apart across frames", () => {
    const cards = [
      ...cardsOf(outline, profile).map((card) => ({ ...card, applicationKey: "shop" })),
      { ...cardsOf(outline, profile)[0], typeKey: "other", name: "Other", applicationKey: "stock", fields: [] },
    ];
    const lines = linesOf(outline, cards);
    const laid = tidy(cards, lines, 1500);
    const frames = framesOf(cards, (card) => laid[card.typeKey], outline);
    expect(frames.map((frame) => frame.applicationKey).sort()).toEqual(["shop", "stock"]);
    const [shop, stock] = [
      frames.find((f) => f.applicationKey === "shop")!,
      frames.find((f) => f.applicationKey === "stock")!,
    ];
    // A list stands inside its own frame, and the two frames do not overlap.
    for (const card of cards) {
      const frame = card.applicationKey === "shop" ? shop : stock;
      expect(laid[card.typeKey].x).toBeGreaterThanOrEqual(frame.x);
      expect(laid[card.typeKey].x + CARD_WIDTH).toBeLessThanOrEqual(frame.x + frame.width);
      expect(laid[card.typeKey].y).toBeGreaterThanOrEqual(frame.y);
    }
    const apart =
      shop.x + shop.width <= stock.x ||
      stock.x + stock.width <= shop.x ||
      shop.y + shop.height <= stock.y ||
      stock.y + stock.height <= shop.y;
    expect(apart).toBe(true);
  });

  it("wraps frames to the board's width", () => {
    const cards = ["a", "b", "c"].map((key) => ({
      ...cardsOf(outline, profile)[0],
      typeKey: key,
      name: key,
      applicationKey: key,
      fields: [],
    }));
    const wide = tidy(cards, [], 1500);
    const narrow = tidy(cards, [], 500);
    expect(new Set(Object.values(wide).map((place) => place.y)).size).toBe(1);
    expect(new Set(Object.values(narrow).map((place) => place.y)).size).toBe(3);
  });

  it("closes up the column under a folded card, in its own application only, and opens it again on unfold", () => {
    const base = { ...cardsOf(outline, profile)[0], fields: cardsOf(outline, profile)[0].fields };
    const cards = [
      { ...base, typeKey: "top", name: "Top", applicationKey: "a" },
      { ...base, typeKey: "below", name: "Below", applicationKey: "a" },
      { ...base, typeKey: "beside", name: "Beside", applicationKey: "a" },
      { ...base, typeKey: "other", name: "Other", applicationKey: "b" },
    ];
    const at = {
      top: { x: 44, y: 60 },
      below: { x: 44, y: 600 },
      beside: { x: 440, y: 600 },
      other: { x: 44, y: 1400 },
    };
    const lost = cardHeight({ ...base, folded: false }) - cardHeight({ ...base, folded: true });
    expect(closeUp(cards, at, "top", true)).toEqual({ below: { x: 44, y: 600 - lost } });
    expect(closeUp(cards, at, "top", false)).toEqual({ below: { x: 44, y: 600 + lost } });
  });

  it("puts applications side by side when they fit, instead of one frame taking the whole row", () => {
    const base = cardsOf(outline, profile)[0];
    const cards = ["a1", "a2", "a3", "a4", "b1", "b2", "b3"].map((key) => ({
      ...base,
      typeKey: key,
      name: key,
      applicationKey: key[0],
      fields: [],
    }));
    const laid = tidy(cards, [], 900);
    const frames = framesOf(cards, (card) => laid[card.typeKey], outline);
    const [a, b] = ["a", "b"].map((key) => frames.find((frame) => frame.applicationKey === key)!);
    expect(a.y).toBe(b.y);
    expect(a.x + a.width).toBeLessThanOrEqual(b.x);
    expect(b.x + b.width).toBeLessThanOrEqual(900);
  });
});

describe("groupOperations (0.17 NG1)", () => {
  const outline = outlineFixture();

  it("places a list or a view of any kind through the same operation, in a group or a new one", () => {
    expect(groupOperations("shelf", "shop", { key: "lists" }, outline)).toEqual([
      { kind: "placeCollection", applicationKey: "shop", collection: "shelf", group: "lists" },
    ]);
    expect(groupOperations({ view: "bins" }, "shop", { key: "lists" }, outline)).toEqual([
      { kind: "placeCollection", applicationKey: "shop", view: "bins", group: "lists" },
    ]);
    const [add, place] = groupOperations({ view: "bins" }, "shop", { label: "Fresh" }, outline);
    expect(add).toMatchObject({ kind: "addNavigationGroup", label: "Fresh" });
    expect(place).toMatchObject({ kind: "placeCollection", view: "bins" });
  });

  it("sends nothing for an entry dropped where it already stands", () => {
    const base = outlineFixture();
    const outline = {
      ...base,
      applications: base.applications.map((application) =>
        application.key === "shop"
          ? {
              ...application,
              navigation: {
                ...application.navigation,
                groups: [
                  {
                    key: "lists",
                    label: "Lists",
                    collapsed: false,
                    collections: ["shelf", "bin"],
                    entries: [{ collection: "shelf" }, { collection: "bin" }],
                    mark: "none",
                  },
                ],
              },
            }
          : application,
      ),
    } as unknown as typeof base;
    // Last in its group: a placement without a position would put it there again.
    expect(groupOperations("bin", "shop", { key: "lists" }, outline)).toEqual([]);
    // Not last: the drop moves it to the end, which is a change.
    expect(groupOperations("shelf", "shop", { key: "lists" }, outline)).toHaveLength(1);
    // In no group and dropped on the ungrouped part.
    expect(groupOperations("area", "shop", null, outline)).toEqual([]);
    expect(groupOperations("bin", "shop", null, outline)).toHaveLength(1);
  });
});

describe("freshCardOf (a menu drop's card)", () => {
  const card = (typeKey: string) => ({ typeKey }) as never;

  it("is the card the step added, not a card of a laid-out board that has no kept place", () => {
    const before = new Set(["area", "shelf"]);
    // Nothing is stored for any card; the drop adds "bin".
    expect(freshCardOf([card("area"), card("shelf"), card("bin")], before)?.typeKey).toBe("bin");
    // The step has not added its card yet: no card is chosen.
    expect(freshCardOf([card("area"), card("shelf")], before)).toBeUndefined();
  });
});
