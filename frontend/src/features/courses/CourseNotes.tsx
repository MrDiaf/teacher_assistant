import { useEffect, useState } from "react";

import { Icon } from "../../components/Icon";
import { AiModelSelector } from "../ai/AiModelSelector";
import { useAiModelSelection } from "../ai/useAiModelSelection";
import { NoteDialog } from "./NoteDialog";
import { SafeMarkdown } from "./SafeMarkdown";
import { courseApi } from "./api";
import type {
  CourseModel,
  CourseNote,
  CourseSource,
  NoteMutation,
  NoteSummary,
  SlideReference,
  SummaryOrigin,
  SummarySourceReference,
} from "./types";

function referenceRange(reference: SlideReference) {
  if (reference.start_slide === null || reference.end_slide === null) {
    return "Entire deck";
  }
  if (reference.start_slide === reference.end_slide) {
    return `Slide ${reference.start_slide}`;
  }
  return `Slides ${reference.start_slide}–${reference.end_slide}`;
}

const ORIGIN_LABELS: Record<SummaryOrigin, string> = {
  note: "From note",
  slide: "From slides",
  mixed: "From note + slides",
};

function summaryReferenceLabel(
  note: CourseNote,
  reference: SummarySourceReference,
) {
  if (reference.note_id === note.id) return "This note";
  const slideReference = note.slide_references.find(
    (item) => item.source_id === reference.source_id,
  );
  if (slideReference && reference.slide !== null) {
    return `${slideReference.source_display_name}, slide ${reference.slide}`;
  }
  return reference.slide === null
    ? "Linked source"
    : `Linked slide ${reference.slide}`;
}

function summaryInputsChanged(before: CourseNote, after: CourseNote) {
  const references = (note: CourseNote) =>
    note.slide_references.map((reference) => ({
      source_id: reference.source_id,
      start_slide: reference.start_slide,
      end_slide: reference.end_slide,
    }));
  return (
    before.body !== after.body ||
    JSON.stringify(references(before)) !== JSON.stringify(references(after))
  );
}

function NoteCard({
  busy,
  canSummarize,
  confirmingDelete,
  note,
  onCancelDelete,
  onConfirmDelete,
  onEdit,
  onGenerateSummary,
  onRequestDelete,
  onRetrySummary,
  summary,
  summaryBusy,
}: {
  busy: boolean;
  canSummarize: boolean;
  confirmingDelete: boolean;
  note: CourseNote;
  onCancelDelete: () => void;
  onConfirmDelete: () => void;
  onEdit: () => void;
  onGenerateSummary: () => void;
  onRequestDelete: () => void;
  onRetrySummary: () => void;
  summary: NoteSummary | null;
  summaryBusy: boolean;
}) {
  return (
    <article className="course-note-card">
      <header>
        <div>
          <p className="eyebrow">
            Updated{" "}
            {new Intl.DateTimeFormat(undefined, {
              dateStyle: "medium",
            }).format(new Date(note.updated_at))}
          </p>
          <h3>{note.title}</h3>
        </div>
        <div className="course-note-actions">
          <button
            className="quiet-button"
            disabled={busy}
            onClick={onEdit}
            type="button"
          >
            Edit
          </button>
          <button
            className="course-note-delete"
            disabled={busy}
            onClick={onRequestDelete}
            type="button"
          >
            <Icon name="trash" size={14} /> Delete
          </button>
        </div>
      </header>

      {note.body ? (
        <SafeMarkdown className="course-note-body" source={note.body} />
      ) : (
        <p className="course-note-body empty">This note has no body yet.</p>
      )}

      <div className="course-note-references">
        <p>
          {note.slide_references.length} slide{" "}
          {note.slide_references.length === 1 ? "reference" : "references"}
        </p>
        {note.slide_references.length > 0 && (
          <ul>
            {note.slide_references.map((reference) => (
              <li key={reference.id}>
                <Icon name="presentation" size={14} />
                <span>
                  <strong>{reference.source_display_name}</strong>
                  {reference.label && ` · ${reference.label}`}
                  <small>{referenceRange(reference)}</small>
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <section
        aria-label={`AI summary for ${note.title}`}
        className="note-summary"
      >
        <header>
          <div>
            <p className="eyebrow">AI study summary</p>
            <span>
              {summary
                ? `${summary.model}${summary.is_stale ? " · sources changed" : ""}`
                : "Uses only this note and its linked slides"}
            </span>
          </div>
          {summary?.status === "failed" ? (
            <button
              className="quiet-button"
              disabled={summaryBusy}
              onClick={onRetrySummary}
              type="button"
            >
              {summaryBusy ? "Retrying…" : "Retry safely"}
            </button>
          ) : (
            <button
              className="quiet-button"
              disabled={summaryBusy || !canSummarize}
              onClick={onGenerateSummary}
              type="button"
            >
              {summaryBusy
                ? "Summarizing…"
                : summary?.is_stale
                  ? "Regenerate"
                  : summary?.status === "completed"
                    ? "Generate again"
                    : "Generate summary"}
            </button>
          )}
        </header>

        {summary?.is_stale && (
          <p className="note-summary-stale" role="status">
            This summary is stale because the note or linked slide text changed.
          </p>
        )}
        {summary?.status === "failed" && (
          <div className="note-summary-error" role="alert">
            <strong>Summary failed safely</strong>
            <span>{summary.safe_error}</span>
            {summary.safe_error_code && (
              <small>Error code: {summary.safe_error_code}</small>
            )}
          </div>
        )}
        {summary?.status === "completed" && summary.summary_json && (
          <ul className="note-summary-bullets">
            {summary.summary_json.bullets.map((bullet, index) => (
              <li
                className={`origin-${bullet.origin}`}
                key={`${bullet.text}-${index}`}
              >
                <span className="note-summary-origin">
                  {ORIGIN_LABELS[bullet.origin]}
                </span>
                <p>{bullet.text}</p>
                <small>
                  {bullet.source_references
                    .map((reference) => summaryReferenceLabel(note, reference))
                    .join(" · ")}
                </small>
              </li>
            ))}
          </ul>
        )}
        {!summary && (
          <p className="note-summary-empty">
            Generate concise bullets with visible note and slide provenance.
          </p>
        )}
      </section>

      {confirmingDelete && (
        <div className="course-note-delete-confirm" role="alert">
          <p>
            Delete <strong>{note.title}</strong>? The note and its slide
            references will be removed. Slide files are unaffected.
          </p>
          <div>
            <button
              className="quiet-button"
              disabled={busy}
              onClick={onCancelDelete}
              type="button"
            >
              Keep note
            </button>
            <button
              className="danger-button"
              disabled={busy}
              onClick={onConfirmDelete}
              type="button"
            >
              {busy ? "Deleting…" : "Delete note"}
            </button>
          </div>
        </div>
      )}
    </article>
  );
}

export function CourseNotes({ course }: { course: CourseModel }) {
  const { modelList, selectedModel, setSelectedModel, modelError } =
    useAiModelSelection();
  const [notes, setNotes] = useState<CourseNote[]>([]);
  const [summaries, setSummaries] = useState<
    Record<string, NoteSummary | null>
  >({});
  const [slideSources, setSlideSources] = useState<CourseSource[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [dialogNote, setDialogNote] = useState<CourseNote | null | undefined>(
    undefined,
  );
  const [confirmNoteId, setConfirmNoteId] = useState<string | null>(null);
  const [busyNoteId, setBusyNoteId] = useState<string | null>(null);
  const [summaryBusyId, setSummaryBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    async function loadNotes() {
      setIsLoading(true);
      setError(null);
      try {
        const [loadedNotes, loadedSources] = await Promise.all([
          courseApi.listNotes(course.id, controller.signal),
          courseApi.listSources(course.id, controller.signal, "slides"),
        ]);
        const loadedSummaries = await Promise.all(
          loadedNotes.map((note) =>
            courseApi.getNoteSummary(note.id, controller.signal),
          ),
        );
        setNotes(loadedNotes);
        setSlideSources(loadedSources);
        setSummaries(
          Object.fromEntries(
            loadedNotes.map((note, index) => [note.id, loadedSummaries[index]]),
          ),
        );
      } catch (loadError) {
        if (!controller.signal.aborted) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Course notes could not be loaded.",
          );
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false);
      }
    }
    void loadNotes();
    return () => controller.abort();
  }, [course.id]);

  async function saveNote(
    payload: NoteMutation,
    existingNote: CourseNote | null,
  ) {
    const saved = existingNote
      ? await courseApi.updateNote(existingNote.id, payload)
      : await courseApi.createNote(course.id, payload);
    setNotes((current) =>
      existingNote
        ? current.map((note) => (note.id === saved.id ? saved : note))
        : [saved, ...current],
    );
    setSummaries((current) => ({
      ...current,
      [saved.id]: existingNote
        ? current[saved.id]
          ? {
              ...current[saved.id]!,
              is_stale:
                current[saved.id]!.is_stale ||
                summaryInputsChanged(existingNote, saved),
            }
          : null
        : null,
    }));
    setDialogNote(undefined);
  }

  async function deleteNote(note: CourseNote) {
    setBusyNoteId(note.id);
    setError(null);
    try {
      await courseApi.deleteNote(note.id);
      setNotes((current) => current.filter((item) => item.id !== note.id));
      setSummaries((current) => {
        const next = { ...current };
        delete next[note.id];
        return next;
      });
      setConfirmNoteId(null);
    } catch (deleteError) {
      setError(
        deleteError instanceof Error
          ? deleteError.message
          : "The course note could not be deleted.",
      );
    } finally {
      setBusyNoteId(null);
    }
  }

  async function generateSummary(note: CourseNote) {
    if (!selectedModel || summaryBusyId) return;
    setSummaryBusyId(note.id);
    setError(null);
    try {
      const summary = await courseApi.generateNoteSummary(
        note.id,
        selectedModel,
      );
      setSummaries((current) => ({ ...current, [note.id]: summary }));
    } catch (summaryError) {
      setError(
        summaryError instanceof Error
          ? summaryError.message
          : "The note summary could not be generated safely.",
      );
    } finally {
      setSummaryBusyId(null);
    }
  }

  async function retrySummary(note: CourseNote, summary: NoteSummary) {
    if (summaryBusyId) return;
    setSummaryBusyId(note.id);
    setError(null);
    try {
      const retried = await courseApi.retryNoteSummary(summary.id);
      setSummaries((current) => ({ ...current, [note.id]: retried }));
    } catch (summaryError) {
      setError(
        summaryError instanceof Error
          ? summaryError.message
          : "The note summary retry failed safely.",
      );
    } finally {
      setSummaryBusyId(null);
    }
  }

  return (
    <div className="course-notes">
      <header className="course-notes-header">
        <div>
          <p className="eyebrow">Private course notebook</p>
          <h2>Notes</h2>
          <p>
            Capture ideas in plain text or Markdown and optionally connect them
            to one or more slide ranges.
          </p>
        </div>
        <div className="course-notes-header-actions">
          <AiModelSelector
            label="Summary model"
            modelList={modelList}
            onChange={setSelectedModel}
            value={selectedModel}
          />
          <button
            className="primary-button"
            onClick={() => setDialogNote(null)}
            type="button"
          >
            <Icon name="plus" size={16} /> Create note
          </button>
        </div>
      </header>

      {modelError && (
        <div className="course-materials-error" role="alert">
          {modelError}
        </div>
      )}
      {error && (
        <div className="course-materials-error" role="alert">
          {error}
        </div>
      )}

      {isLoading ? (
        <div className="course-materials-loading" role="status">
          Loading course notes…
        </div>
      ) : notes.length === 0 ? (
        <section className="course-notes-empty">
          <span aria-hidden="true">
            <Icon name="file" size={25} />
          </span>
          <p className="eyebrow">No notes yet</p>
          <h3>Start your course notebook</h3>
          <p>
            Notes work on their own. Slide references can be added now or
            whenever a deck becomes available.
          </p>
          <button
            className="primary-button"
            onClick={() => setDialogNote(null)}
            type="button"
          >
            Create note
          </button>
        </section>
      ) : (
        <div className="course-note-grid">
          {notes.map((note) => (
            <NoteCard
              busy={busyNoteId === note.id}
              canSummarize={Boolean(selectedModel)}
              confirmingDelete={confirmNoteId === note.id}
              key={note.id}
              note={note}
              onCancelDelete={() => setConfirmNoteId(null)}
              onConfirmDelete={() => void deleteNote(note)}
              onEdit={() => setDialogNote(note)}
              onGenerateSummary={() => void generateSummary(note)}
              onRequestDelete={() => setConfirmNoteId(note.id)}
              onRetrySummary={() => {
                const summary = summaries[note.id];
                if (summary) void retrySummary(note, summary);
              }}
              summary={summaries[note.id] ?? null}
              summaryBusy={summaryBusyId === note.id}
            />
          ))}
        </div>
      )}

      {dialogNote !== undefined && (
        <NoteDialog
          note={dialogNote}
          onClose={() => setDialogNote(undefined)}
          onSave={saveNote}
          slideSources={slideSources}
        />
      )}
    </div>
  );
}
