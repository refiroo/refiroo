/**
 * Settings › This instance › E-mail template: the one template every mail the engine sends is set in. Its
 * Markdown (with the placeholders, `{{content}}` exactly once) is edited at the left with a small toolbar,
 * the logo is uploaded under it, and the mail as it would arrive is rendered at the right by the engine
 * (`POST /mail-template/preview`) in a sandboxed frame, so what is shown is what is sent. Until a template
 * is saved the engine's own layout is used; Reset to default deletes the saved one.
 */

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { errorMessage } from "@/api/errors";
import { mailTemplate } from "@/api/mailTemplateClient";
import type { MailTemplate } from "@/types";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { FileField } from "@/ui/FileField";
import { FormField } from "@/ui/FormField";
import { InlineError } from "@/ui/InlineError";
import { Notice } from "@/ui/Notice";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { SettingsGroup, SettingsPanel } from "@/ui/SettingsParts";
import { Skeleton } from "@/ui/Skeleton";
import { Tabs } from "@/ui/Tabs";
import { useToast } from "@/ui/Toast";
import { settingsHead } from "./navigation";

/** The preview is asked for once the person stops typing. */
const PREVIEW_DELAY_MS = 400;

const PLACEHOLDER_WORDS: Record<string, string> = {
  content: "The message's own text (required, once)",
  product_name: "The product's name",
  instance_url: "The address of this instance",
  recipient_name: "The person's name",
  logo: "The logo image",
};

type Paper = "light" | "dark" | "text";

export function MailTemplatePage() {
  const [template, setTemplate] = useState<MailTemplate>();
  const [loadError, setLoadError] = useState("");
  const [draft, setDraft] = useState("");

  function load() {
    mailTemplate.get().then(
      (loaded) => {
        setTemplate(loaded);
        setDraft(loaded.markdown);
        setLoadError("");
      },
      (cause) => setLoadError(errorMessage(cause)),
    );
  }
  useEffect(load, []);

  return (
    <SettingsLayout
      {...settingsHead("mail-template")}
      title="E-mail template"
      description="One template for every mail refiroo sends: invitations, password resets, notices and digests. Write it in Markdown, put the message's own text where {{content}} stands and add a logo. Until you save one, refiroo's own layout is used."
    >
      {loadError ? (
        <InlineError message={loadError} onRetry={load} />
      ) : !template ? (
        <Skeleton label="Loading the e-mail template" lines={8} />
      ) : (
        <Editor
          template={template}
          draft={draft}
          onDraft={setDraft}
          onTemplate={setTemplate}
          onReset={(reset) => {
            setTemplate(reset);
            setDraft(reset.markdown);
          }}
        />
      )}
    </SettingsLayout>
  );
}

function Editor({
  template,
  draft,
  onDraft,
  onTemplate,
  onReset,
}: {
  template: MailTemplate;
  draft: string;
  onDraft: (markdown: string) => void;
  onTemplate: (template: MailTemplate) => void;
  onReset: (template: MailTemplate) => void;
}) {
  const toast = useToast();
  const source = useRef<HTMLTextAreaElement>(null);
  const resetRef = useRef<HTMLButtonElement>(null);
  // Where the selection goes once a toolbar button has changed the text.
  const selection = useRef<[number, number] | null>(null);
  const [error, setError] = useState("");
  const [logoError, setLogoError] = useState("");
  const [testError, setTestError] = useState("");
  const [pending, setPending] = useState<"" | "save" | "test" | "logo" | "reset">("");
  const [confirming, setConfirming] = useState(false);
  const [fileKey, setFileKey] = useState(0);
  const dirty = draft !== template.markdown;

  useLayoutEffect(() => {
    if (!selection.current || !source.current) return;
    source.current.focus();
    source.current.setSelectionRange(...selection.current);
    selection.current = null;
  }, [draft]);

  /** Replaces the selected text with `make(selected)` and selects `inner` of it (the part to type over). */
  function edit(make: (selected: string) => { text: string; select?: [number, number] }) {
    const field = source.current;
    if (!field) return;
    const start = field.selectionStart;
    const end = field.selectionEnd;
    const { text, select } = make(draft.slice(start, end));
    onDraft(draft.slice(0, start) + text + draft.slice(end));
    selection.current = select ? [start + select[0], start + select[1]] : [start + text.length, start + text.length];
  }
  const wrap = (mark: string, fallback: string) =>
    edit((selected) => {
      const inner = selected || fallback;
      return { text: `${mark}${inner}${mark}`, select: [mark.length, mark.length + inner.length] };
    });
  const prefix = (mark: string, fallback: string) =>
    edit((selected) => {
      const inner = selected || fallback;
      return { text: `${mark}${inner}`, select: [mark.length, mark.length + inner.length] };
    });
  const link = () =>
    edit((selected) => {
      const label = selected || "text";
      const address = "https://";
      return {
        text: `[${label}](${address})`,
        select: [label.length + 3, label.length + 3 + address.length],
      };
    });
  const insertPlaceholder = (name: string) => edit(() => ({ text: `{{${name}}}` }));

  async function save() {
    setPending("save");
    setError("");
    try {
      const saved = await mailTemplate.save(draft, template.version);
      onTemplate(saved);
      onDraft(saved.markdown);
      toast("E-mail template saved");
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setPending("");
    }
  }

  async function sendTest() {
    setPending("test");
    setTestError("");
    try {
      const sent = await mailTemplate.sendTest();
      toast(`A test was sent to ${sent.sentTo}`);
    } catch (cause) {
      setTestError(errorMessage(cause));
    } finally {
      setPending("");
    }
  }

  async function chooseLogo(file: File | undefined) {
    if (!file) return;
    setLogoError("");
    if (file.size > template.logoMaxBytes) {
      setLogoError(`The logo is larger than ${Math.round(template.logoMaxBytes / 1024)} KB.`);
      setFileKey((n) => n + 1);
      return;
    }
    setPending("logo");
    try {
      onTemplate(await mailTemplate.uploadLogo(file, template.version));
      toast("Logo uploaded");
    } catch (cause) {
      setLogoError(errorMessage(cause));
    } finally {
      setFileKey((n) => n + 1);
      setPending("");
    }
  }

  async function removeLogo() {
    setPending("logo");
    setLogoError("");
    try {
      onTemplate(await mailTemplate.removeLogo(template.version));
      toast("Logo removed");
    } catch (cause) {
      setLogoError(errorMessage(cause));
    } finally {
      setPending("");
    }
  }

  async function reset() {
    setPending("reset");
    setError("");
    try {
      await mailTemplate.reset();
      onReset(await mailTemplate.get());
      setConfirming(false);
      toast("E-mail template reset to the default");
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setPending("");
    }
  }

  const busy = pending !== "";
  return (
    <>
      <SettingsGroup title="Template" description="Markdown. Raw HTML and images are not carried into the mail.">
        {testError && (
          <Notice tone="error" title="The test could not be sent">
            {testError}
          </Notice>
        )}
        <SettingsPanel
          className="mail-template-panel"
          foot={
            <>
              <span className="settings-panel-state">
                {dirty ? "A test sends the saved template, not this draft." : ""}
              </span>
              {template.saved && (
                <button
                  ref={resetRef}
                  type="button"
                  className="danger-ghost mail-template-reset"
                  disabled={busy}
                  onClick={() => setConfirming(true)}
                >
                  Reset to default…
                </button>
              )}
              <button type="button" className="secondary" disabled={busy} onClick={() => void sendTest()}>
                {pending === "test" ? "Sending…" : "Send a test to me"}
              </button>
              <button type="button" className="primary" disabled={busy || !dirty} onClick={() => void save()}>
                {pending === "save" ? "Saving…" : "Save"}
              </button>
            </>
          }
        >
          <div className="settings-panel-pad">
            <FormField label="Markdown" error={error}>
              {(control) => (
                <>
                  <div className="mail-template-toolbar" role="toolbar" aria-label="Formatting">
                    <button type="button" className="mail-template-bold" onClick={() => wrap("**", "bold")}>
                      Bold
                    </button>
                    <button type="button" className="mail-template-italic" onClick={() => wrap("_", "italic")}>
                      Italic
                    </button>
                    <button type="button" onClick={link}>
                      Link
                    </button>
                    <button type="button" onClick={() => prefix("## ", "Heading")}>
                      Heading
                    </button>
                    <button type="button" onClick={() => prefix("- ", "Item")}>
                      List
                    </button>
                    <select
                      aria-label="Insert placeholder"
                      value=""
                      onChange={(event) => event.target.value && insertPlaceholder(event.target.value)}
                    >
                      <option value="">Insert placeholder…</option>
                      {template.placeholders.map((name) => (
                        <option key={name} value={name}>
                          {`{{${name}}} · ${PLACEHOLDER_WORDS[name] ?? name}`}
                        </option>
                      ))}
                    </select>
                  </div>
                  <textarea
                    {...control}
                    ref={source}
                    className="mail-template-source"
                    spellCheck={false}
                    value={draft}
                    onChange={(event) => onDraft(event.target.value)}
                  />
                </>
              )}
            </FormField>
          </div>
        </SettingsPanel>
      </SettingsGroup>
      <SettingsGroup title="Logo" description="Shown at the top of every mail. Without one, the refiroo mark is used.">
        <SettingsPanel className="settings-panel-pad">
          <div className="mail-template-logo">
            <div className="mail-template-thumbnail">
              {template.logoDataUrl ? (
                <img src={template.logoDataUrl} alt="The logo in use" />
              ) : (
                <span>refiroo mark</span>
              )}
            </div>
            <div className="mail-template-logo-actions">
              <FormField
                label="Upload a logo"
                help={`PNG, JPEG or SVG without script, up to ${Math.round(template.logoMaxBytes / 1024)} KB. Many mail programs do not draw SVG.`}
                error={logoError}
              >
                {(control) => (
                  <FileField
                    key={fileKey}
                    control={control}
                    accept="image/png,image/jpeg,image/svg+xml,.png,.jpg,.jpeg,.svg"
                    disabled={busy}
                    onFile={(file) => void chooseLogo(file)}
                  />
                )}
              </FormField>
              {template.logoDataUrl && (
                <div>
                  <button type="button" className="secondary" disabled={busy} onClick={() => void removeLogo()}>
                    Remove logo
                  </button>
                </div>
              )}
            </div>
          </div>
        </SettingsPanel>
      </SettingsGroup>
      <Preview markdown={draft} logoDataUrl={template.logoDataUrl} />
      {confirming && (
        <ConfirmDialog
          title="Reset the e-mail template?"
          confirmLabel="Reset to default"
          pending={pending === "reset"}
          error={error}
          onCancel={() => {
            setConfirming(false);
            setError("");
            resetRef.current?.focus();
          }}
          onConfirm={() => void reset()}
        >
          <p>The saved Markdown and the logo are deleted and refiroo&apos;s own layout is used for every mail again.</p>
        </ConfirmDialog>
      )}
    </>
  );
}

/** The mail as the engine renders it for the draft, a moment after the last keystroke. */
function Preview({ markdown, logoDataUrl }: { markdown: string; logoDataUrl: string | null }) {
  const [paper, setPaper] = useState<Paper>("light");
  const [html, setHtml] = useState("");
  const [text, setText] = useState("");
  const [problem, setProblem] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => {
      mailTemplate.preview(markdown, controller.signal).then(
        (rendered) => {
          setHtml(rendered.html);
          setText(rendered.text);
          setProblem("");
        },
        (cause) => {
          if (controller.signal.aborted) return;
          // A draft the engine refuses (an unknown placeholder, no {{content}}) says why and keeps the last good preview.
          setProblem(errorMessage(cause));
        },
      );
    }, PREVIEW_DELAY_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
    // The logo is part of the rendered mail.
  }, [markdown, logoDataUrl]);

  const sheet = (scheme: "light" | "dark") => (
    <div className="mail-template-paper" data-paper={scheme}>
      <iframe className="mail-template-frame" title="Preview of the e-mail" sandbox="" srcDoc={html} />
    </div>
  );
  return (
    <SettingsGroup
      stacked
      title="Preview"
      description="The engine renders the draft with sample values; nothing is saved or sent."
    >
      {problem && (
        <Notice tone="warning" title="The draft cannot be previewed">
          {problem}
        </Notice>
      )}
      <SettingsPanel className="settings-panel-pad">
        <Tabs
          label="Preview of the e-mail"
          selected={paper}
          onChange={(id) => setPaper(id as Paper)}
          tabs={[
            { id: "light", label: "Light paper", content: sheet("light") },
            { id: "dark", label: "Dark paper", content: sheet("dark") },
            {
              id: "text",
              label: "Plain text",
              content: <pre className="mail-template-text">{text}</pre>,
            },
          ]}
        />
      </SettingsPanel>
    </SettingsGroup>
  );
}
