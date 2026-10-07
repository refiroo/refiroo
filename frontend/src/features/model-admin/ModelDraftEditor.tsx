import { useEffect, useRef, useState } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import type { ModelCompilation, ModelDraft, ModelValidation } from "@/types";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { Notice } from "@/ui/Notice";
import { downloadJson } from "@/lib/download";
import { ModelDiagnostics } from "@/features/model-admin/ModelDiagnostics";
import { ModelDiff } from "@/features/model-admin/ModelDiff";
import { ModelSummary } from "@/features/model-admin/ModelSummary";

function pretty(model: Record<string, unknown>) {
  return JSON.stringify(model, null, 2);
}

function parseDocument(text: string): Record<string, unknown> {
  const value: unknown = JSON.parse(text);
  if (!value || typeof value !== "object" || Array.isArray(value))
    throw new Error("The model document must be a JSON object.");
  return value as Record<string, unknown>;
}

export function ModelDraftEditor({
  draft,
  canInstall,
  onSaved,
  onReload,
  onInstalled,
  onDeleted,
}: {
  draft: ModelDraft;
  canInstall: boolean;
  onSaved: (draft: ModelDraft) => void;
  onReload: () => Promise<void>;
  onInstalled: (releaseId: string) => void;
  onDeleted: () => void;
}) {
  const [name, setName] = useState(draft.name);
  const [text, setText] = useState(() => pretty(draft.model));
  const [syntaxError, setSyntaxError] = useState("");
  const [validation, setValidation] = useState<ModelValidation>();
  const [compilation, setCompilation] = useState<ModelCompilation>();
  const [pending, setPending] = useState("");
  const [error, setError] = useState("");
  const [conflict, setConflict] = useState(false);
  const [confirm, setConfirm] = useState<"install" | "delete">();
  const editorRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    setName(draft.name);
    setText(pretty(draft.model));
    setCompilation(undefined);
    setConflict(false);
    setError("");
  }, [draft.id, draft.version]);

  useEffect(() => {
    let cancelled = false;
    const timeout = window.setTimeout(() => {
      try {
        const model = parseDocument(text);
        setSyntaxError("");
        api
          .validateModel(model)
          .then((result) => {
            if (!cancelled) setValidation(result);
          })
          .catch((cause) => {
            if (!cancelled) setError(errorMessage(cause));
          });
      } catch (cause) {
        setSyntaxError(errorMessage(cause));
        setValidation(undefined);
      }
    }, 350);
    return () => {
      cancelled = true;
      window.clearTimeout(timeout);
    };
  }, [text]);

  function changed() {
    return name !== draft.name || text !== pretty(draft.model);
  }

  async function save() {
    setError("");
    setConflict(false);
    let model: Record<string, unknown>;
    try {
      model = parseDocument(text);
    } catch (cause) {
      setSyntaxError(errorMessage(cause));
      return;
    }
    setPending("save");
    try {
      const saved = await api.updateModelDraft(draft.id, { expectedVersion: draft.version, name, model });
      onSaved(saved);
      setCompilation(undefined);
    } catch (cause) {
      setError(errorMessage(cause));
      setConflict(isApiError(cause, "VERSION_CONFLICT"));
    } finally {
      setPending("");
    }
  }

  async function compile() {
    setPending("compile");
    setError("");
    try {
      setCompilation(await api.compileModelDraft(draft.id, draft.version));
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setPending("");
    }
  }

  async function install() {
    setPending("install");
    setError("");
    try {
      const release = await api.installModelDraft(draft.id, draft.version);
      setConfirm(undefined);
      onInstalled(release.id);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setPending("");
    }
  }

  async function remove() {
    setPending("delete");
    setError("");
    try {
      await api.deleteModelDraft(draft.id, draft.version);
      setConfirm(undefined);
      onDeleted();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setPending("");
    }
  }

  function goToPath(path: string) {
    const editor = editorRef.current;
    if (!editor) return;
    const segments = path
      .split("/")
      .filter(Boolean)
      .reverse()
      .map((segment) => segment.replaceAll("~1", "/").replaceAll("~0", "~"));
    const key = segments.find((segment) => !/^\d+$/.test(segment) && text.includes(`"${segment}"`));
    editor.focus();
    if (!key) return;
    const match = text.indexOf(`"${key}"`);
    editor.setSelectionRange(match, match + key.length + 2);
  }

  async function copyLocal() {
    setError("");
    try {
      if (!navigator.clipboard)
        throw new Error("Clipboard access is unavailable. Select and copy the editor content manually.");
      await navigator.clipboard.writeText(text);
    } catch (cause) {
      setError(errorMessage(cause));
    }
  }

  async function reload() {
    setPending("reload");
    setError("");
    try {
      await onReload();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setPending("");
    }
  }

  const parsed = !syntaxError
    ? (() => {
        try {
          return parseDocument(text);
        } catch {
          return undefined;
        }
      })()
    : undefined;
  return (
    <div className="model-editor-stack">
      <header className="model-detail-header">
        <div>
          <p className="eyebrow">Editable draft · version {draft.version}</p>
          <h2>{draft.name}</h2>
        </div>
        <button className="danger-outline" onClick={() => setConfirm("delete")}>
          Delete draft
        </button>
      </header>
      <label className="model-name-field">
        Draft name
        <input
          maxLength={300}
          value={name}
          onChange={(event) => {
            setName(event.target.value);
            setCompilation(undefined);
          }}
        />
      </label>
      <label className="model-json-field">
        JSON model
        <textarea
          ref={editorRef}
          spellCheck={false}
          value={text}
          onChange={(event) => {
            setText(event.target.value);
            setValidation(undefined);
            setCompilation(undefined);
          }}
        />
      </label>
      {syntaxError && <Notice tone="error">JSON syntax: {syntaxError}</Notice>}
      {!syntaxError && validation && (
        <section className="model-result">
          <h3>Authoritative validation</h3>
          <ModelDiagnostics diagnostics={validation.diagnostics} onPath={goToPath} />
        </section>
      )}
      {parsed && <ModelSummary model={parsed} />}
      {error && <Notice tone="error">{error}</Notice>}
      {conflict && (
        <div className="conflict-actions">
          <strong>A newer draft version exists. Your local JSON is preserved.</strong>
          <button className="secondary" disabled={pending !== ""} onClick={() => void reload()}>
            {pending === "reload" ? "Reloading…" : "Reload saved version"}
          </button>
          <button className="secondary" disabled={pending !== ""} onClick={copyLocal}>
            Copy local JSON
          </button>
        </div>
      )}
      <div className="model-actions">
        <button
          className="primary"
          disabled={pending !== "" || !!syntaxError || !changed() || !name.trim()}
          onClick={save}
        >
          {pending === "save" ? "Saving…" : "Save draft"}
        </button>
        <button className="secondary" disabled={pending !== "" || changed()} onClick={compile}>
          {pending === "compile" ? "Compiling…" : "Compile and compare"}
        </button>
        <button className="secondary" onClick={() => downloadJson(`${draft.name}.json`, text)}>
          Export JSON
        </button>
      </div>
      {compilation && (
        <section className="model-result">
          <div className="model-result-heading">
            <div>
              <p className="eyebrow">Canonical model</p>
              <h3>{compilation.valid ? "Ready for review" : "Invalid"}</h3>
            </div>
            {compilation.modelHash && <code className="model-hash">{compilation.modelHash}</code>}
          </div>
          <ModelDiagnostics diagnostics={compilation.diagnostics} onPath={goToPath} />
          {compilation.valid && <ModelDiff changes={compilation.changes} compatibility={compilation.compatibility} />}
          {canInstall && compilation.valid && compilation.modelHash && (
            <button className="primary install-action" onClick={() => setConfirm("install")}>
              Install immutable release…
            </button>
          )}
        </section>
      )}
      {confirm === "install" && (
        <ConfirmDialog
          title="Install this model release?"
          confirmLabel="Install release"
          pending={pending === "install"}
          error={error}
          onCancel={() => setConfirm(undefined)}
          onConfirm={install}
        >
          <p>
            Installation creates an immutable inactive release. It does not activate the model or change runtime
            behavior.
          </p>
          {compilation?.compatibility.classification === "migration_required" && (
            <Notice tone="warning">
              The release may be installed, but activation is blocked until its compatibility diagnostics are resolved.
            </Notice>
          )}
        </ConfirmDialog>
      )}
      {confirm === "delete" && (
        <ConfirmDialog
          title="Delete this draft?"
          confirmLabel="Delete draft"
          pending={pending === "delete"}
          error={error}
          onCancel={() => setConfirm(undefined)}
          onConfirm={remove}
        >
          <p>This removes only the editable draft. Installed releases are not changed.</p>
        </ConfirmDialog>
      )}
    </div>
  );
}
