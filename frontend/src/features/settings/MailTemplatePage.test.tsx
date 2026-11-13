import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/api/errors";
import { mailTemplate } from "@/api/mailTemplateClient";
import { MailTemplatePage } from "@/features/settings/MailTemplatePage";
import { allowNavigation } from "@/routing/navigationGuard";
import { navigationFor } from "@/ui/settingsNavigation";
import type { MailTemplate } from "@/types";
import { ToastProvider } from "@/ui/Toast";

vi.mock("@/api/mailTemplateClient", () => ({
  mailTemplate: {
    get: vi.fn(),
    save: vi.fn(),
    reset: vi.fn(),
    uploadLogo: vi.fn(),
    removeLogo: vi.fn(),
    preview: vi.fn(),
    sendTest: vi.fn(),
  },
}));

const DEFAULT = "{{logo}}\n\nHello {{recipient_name}},\n\n{{content}}\n";
const unsaved: MailTemplate = {
  markdown: DEFAULT,
  defaultMarkdown: DEFAULT,
  saved: false,
  placeholders: ["content", "product_name", "instance_url", "recipient_name", "logo"],
  logoType: null,
  logoDataUrl: null,
  logoMaxBytes: 512 * 1024,
  version: null,
  updatedAt: null,
};
const saved: MailTemplate = {
  ...unsaved,
  markdown: "Dear {{recipient_name}}\n\n{{content}}\n",
  saved: true,
  version: 2,
};

function open(template: MailTemplate) {
  vi.mocked(mailTemplate.get).mockResolvedValue(template);
  vi.mocked(mailTemplate.preview).mockResolvedValue({ html: "<p>Hello Alex Example</p>", text: "Hello Alex Example" });
  render(
    <ToastProvider>
      <MailTemplatePage />
    </ToastProvider>,
  );
}

const markdown = () => screen.findByLabelText("Markdown") as Promise<HTMLTextAreaElement>;

describe("Settings › E-mail template", () => {
  beforeEach(() => vi.resetAllMocks());
  afterEach(cleanup);

  it("loads the template and shows the engine's preview in a sandboxed frame", async () => {
    open(saved);
    expect((await markdown()).value).toBe(saved.markdown);
    await waitFor(() => expect(mailTemplate.preview).toHaveBeenCalledWith(saved.markdown, expect.anything()));
    const frame = (await screen.findByTitle("Preview of the e-mail")) as HTMLIFrameElement;
    await waitFor(() => expect(frame.getAttribute("srcdoc")).toContain("Hello Alex Example"));
    expect(frame.getAttribute("sandbox")).toBe("");
    // Unsaved: nothing to reset. Saved: it can be reset.
    expect(screen.getByRole("button", { name: "Reset to default…" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Save" }).hasAttribute("disabled")).toBe(true);
  });

  it("edits with the toolbar, asks for a preview of the draft and saves it with the saved version", async () => {
    open(saved);
    const field = await markdown();
    fireEvent.change(field, { target: { value: "{{content}}" } });
    field.setSelectionRange(0, 11);
    fireEvent.click(screen.getByRole("button", { name: "Bold" }));
    await waitFor(() => expect(field.value).toBe("**{{content}}**"));
    await waitFor(() => expect(mailTemplate.preview).toHaveBeenCalledWith("**{{content}}**", expect.anything()));
    fireEvent.change(screen.getByLabelText("Insert placeholder"), { target: { value: "product_name" } });
    await waitFor(() => expect(field.value).toContain("{{product_name}}"));

    vi.mocked(mailTemplate.save).mockResolvedValue({ ...saved, markdown: field.value, version: 3 });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(mailTemplate.save).toHaveBeenCalledWith(field.value, 2));
    await screen.findByText("E-mail template saved");
  });

  it("says why a draft the engine refuses cannot be saved", async () => {
    open(unsaved);
    const field = await markdown();
    fireEvent.change(field, { target: { value: "Hello" } });
    vi.mocked(mailTemplate.save).mockRejectedValue(
      new ApiError(422, "MAIL_TEMPLATE_CONTENT_REQUIRED", "The template must hold {{content}} exactly once", {}),
    );
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await screen.findByText(/must hold \{\{content\}\} exactly once/);
    expect(mailTemplate.save).toHaveBeenCalledWith("Hello", null);
    // Unsaved: no reset is offered.
    expect(screen.queryByRole("button", { name: "Reset to default…" })).toBeNull();
  });

  it("uploads and removes the logo, and sends a test to the caller", async () => {
    open(saved);
    await markdown();
    const logo = { ...saved, logoType: "image/png" as const, logoDataUrl: "data:image/png;base64,AAAA", version: 3 };
    vi.mocked(mailTemplate.uploadLogo).mockResolvedValue(logo);
    const file = new File(["x"], "logo.png", { type: "image/png" });
    fireEvent.change(screen.getByLabelText("Upload a logo"), { target: { files: [file] } });
    await waitFor(() => expect(mailTemplate.uploadLogo).toHaveBeenCalledWith(file, 2));
    expect((await screen.findByAltText("The logo in use")).getAttribute("src")).toBe(logo.logoDataUrl);

    vi.mocked(mailTemplate.removeLogo).mockResolvedValue({ ...saved, version: 4 });
    fireEvent.click(screen.getByRole("button", { name: "Remove logo" }));
    await waitFor(() => expect(mailTemplate.removeLogo).toHaveBeenCalledWith(3));
    await waitFor(() => expect(screen.queryByAltText("The logo in use")).toBeNull());

    vi.mocked(mailTemplate.sendTest).mockResolvedValue({ sentTo: "olga@example.org" });
    fireEvent.click(screen.getByRole("button", { name: "Send a test to me" }));
    await screen.findByText("A test was sent to olga@example.org");
  });

  it("resets to the default after one confirmation", async () => {
    open(saved);
    await markdown();
    vi.mocked(mailTemplate.reset).mockResolvedValue(undefined);
    vi.mocked(mailTemplate.get).mockResolvedValue(unsaved);
    fireEvent.click(screen.getByRole("button", { name: "Reset to default…" }));
    fireEvent.click(await screen.findByRole("button", { name: "Reset to default" }));
    await waitFor(() => expect(mailTemplate.reset).toHaveBeenCalledTimes(1));
    await waitFor(() => expect((screen.getByLabelText("Markdown") as HTMLTextAreaElement).value).toBe(DEFAULT));
    expect(screen.queryByRole("button", { name: "Reset to default…" })).toBeNull();
  });

  it("asks before leaving with an unsaved draft, and not once it is saved", async () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    open(saved);
    const field = await markdown();
    expect(allowNavigation()).toBe(true);
    expect(confirm).not.toHaveBeenCalled();
    fireEvent.change(field, { target: { value: "{{content}} changed" } });
    expect(allowNavigation()).toBe(false);
    expect(confirm).toHaveBeenCalledWith("Discard your unsaved changes?");
    confirm.mockRestore();
  });

  it("is listed only to those who hold Operations", () => {
    const labels = (keys: string[]) =>
      navigationFor(keys.map((key) => ({ key })))
        .flatMap((group) => group.pages)
        .map((item) => item.label);
    expect(labels(["operations"])).toContain("E-mail template");
    expect(labels(["security-admin", "browse"])).not.toContain("E-mail template");
  });
});
