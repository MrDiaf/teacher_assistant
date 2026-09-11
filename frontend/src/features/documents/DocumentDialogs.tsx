import { useState, type FormEvent } from "react";

import { Icon, useModalDialog } from "../../platform/ui";
import type { DocumentProject } from "./types";

export function ProjectDialog({
  project,
  onClose,
  onSave,
}: {
  project: DocumentProject | null;
  onClose: () => void;
  onSave: (title: string) => Promise<void>;
}) {
  const [title, setTitle] = useState(project?.title ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dialogRef = useModalDialog(onClose);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const normalized = title.trim();
    if (!normalized) {
      setError("Enter a project title.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await onSave(normalized);
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "The project could not be saved.",
      );
      setBusy(false);
    }
  }

  return (
    <div className="dialog-backdrop" role="presentation">
      <section
        aria-labelledby="document-project-dialog-title"
        aria-modal="true"
        className="event-dialog document-dialog"
        ref={dialogRef}
        role="dialog"
      >
        <header className="dialog-header">
          <div>
            <p className="eyebrow">
              {project ? "Project settings" : "New LaTeX project"}
            </p>
            <h2 id="document-project-dialog-title">
              {project ? "Rename project" : "Create document"}
            </h2>
          </div>
          <button
            className="icon-button"
            aria-label="Close project dialog"
            onClick={onClose}
            type="button"
          >
            <Icon name="x" size={19} />
          </button>
        </header>
        <form className="event-form" onSubmit={submit}>
          <label className="field field-wide">
            <span>Project title</span>
            <input
              data-dialog-autofocus="true"
              maxLength={200}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="e.g. Linear algebra notes"
              value={title}
            />
          </label>
          {!project && (
            <p className="document-form-note field-wide">
              A private project folder and valid <code>main.tex</code> will be
              created automatically.
            </p>
          )}
          {error && (
            <p className="form-error field-wide" role="alert">
              {error}
            </p>
          )}
          <footer className="dialog-footer field-wide">
            <span />
            <div>
              <button
                className="quiet-button"
                disabled={busy}
                onClick={onClose}
                type="button"
              >
                Cancel
              </button>
              <button className="primary-button" disabled={busy} type="submit">
                {busy ? "Saving…" : project ? "Save title" : "Create project"}
              </button>
            </div>
          </footer>
        </form>
      </section>
    </div>
  );
}

export function DeleteProjectDialog({
  project,
  onClose,
  onDelete,
}: {
  project: DocumentProject;
  onClose: () => void;
  onDelete: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dialogRef = useModalDialog(onClose);

  async function remove() {
    setBusy(true);
    setError(null);
    try {
      await onDelete();
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "The project could not be deleted.",
      );
      setBusy(false);
    }
  }

  return (
    <div className="dialog-backdrop" role="presentation">
      <section
        aria-labelledby="delete-document-title"
        aria-modal="true"
        className="event-dialog delete-document-dialog"
        ref={dialogRef}
        role="alertdialog"
      >
        <header className="dialog-header">
          <div>
            <p className="eyebrow">Permanent action</p>
            <h2 id="delete-document-title">Delete {project.title}?</h2>
          </div>
          <button
            aria-label="Close delete project dialog"
            className="icon-button"
            onClick={onClose}
            type="button"
          >
            <Icon name="x" size={19} />
          </button>
        </header>
        <div className="delete-document-content">
          <p>
            This permanently removes the project record and its private source
            files, including <code>main.tex</code>. Tags themselves are kept.
          </p>
          <p>The project can only be recovered from a coordinated backup.</p>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <footer className="dialog-footer">
            <button
              className="quiet-button"
              data-dialog-autofocus="true"
              disabled={busy}
              onClick={onClose}
              type="button"
            >
              Keep project
            </button>
            <button
              className="danger-button"
              disabled={busy}
              onClick={remove}
              type="button"
            >
              <Icon name="trash" size={17} />{" "}
              {busy ? "Deleting…" : "Delete project"}
            </button>
          </footer>
        </div>
      </section>
    </div>
  );
}
