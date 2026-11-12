import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AppearancePage } from "@/features/settings/AppearancePage";

describe("AppearancePage (R13-F24)", () => {
  it("links each group's help text from its radio buttons", () => {
    render(<AppearancePage />);
    for (const [name, help] of [
      ["Current", /colours of the refiroo website/],
      ["Studio", /arrangement of the frame/],
      ["Light", /System follows your device's light or dark setting/],
      ["Compact", /The default for every table/],
      ["A: plum and gold", /The palette that colours each kind of record/],
      ["Always, faintly", /When a record's editable fields show their pencil/],
    ] as const) {
      expect(screen.getByRole("radio", { name })).toHaveAccessibleDescription(help);
    }
  });
});
