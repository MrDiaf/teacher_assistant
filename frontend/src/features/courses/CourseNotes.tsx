import { type Dispatch, type SetStateAction, useEffect, useState } from "react";

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

function summaryStateLabel(summary: NoteSummary | null) {
  if (!summary) return "No summary";
  if (summary.status === "completed" && summary.summary_json) {
    const count = summary.summary_json.bullets.length;
    return count === 0
      ? "Summary empty"
      : `${count} summary ${count === 1 ? "bullet" : "bullets"}`;
  }
  return `Summary ${summary.status}`;
}

function NoteCard({
  busy,
  canSummarize,
  confirmingDelete,
  expanded,
  note,
  onCancelDelete,
  onConfirmDelete,
  onEdit,
  onGenerateSummary,
  onRemoveBullet,
  onRequestDelete,
  onRetrySummary,
  onToggle,
  onToggleSummary,
  removingBulletIds,
  summary,
  summaryBusy,
  summaryError,
  summaryExpanded,
}: {
  busy: boolean;
  canSummarize: boolean;
  confirmingDelete: boolean;
  expanded: boolean;
  note: CourseNote;
  onCancelDelete: () => void;
  onConfirmDelete: () => void;
  onEdit: () => void;
  onGenerateSummary: () => void;
  onRemoveBullet: (bulletId: string) => void;
  onRequestDelete: () => void;
  onRetrySummary: () => void;
  onToggle: () => void;
  onToggleSummary: () => void;
  removingBulletIds: Set<string>;
  summary: NoteSummary | null;
  summaryBusy: boolean;
  summaryError: string | null;
  summaryExpanded: boolean;
}) {
  const noteContentId = `course-note-${note.id}-content`;
  const summaryContentId = `note-summary-${note.id}-content`;
  const bulletCount = summary?.summary_json?.bullets.length ?? 0;

  return (
    <article className="course-note-card">
      <header className="course-note-card-header">
        <div className="course-note-heading">
          <p className="eyebrow">
            Updated{" "}
            {new Intl.DateTimeFormat(undefined, {
              dateStyle: "medium",
            }).format(new Date(note.updated_at))}
          </p>
          <h3>{note.title}</h3>
          <p className="course-note-compact-meta">
            {note.slide_references.length} slide{" "}
            {note.slide_references.length === 1 ? "reference" : "references"}
            <span aria-hidden="true"> · </span>
            {summaryStateLabel(summary)}
            {summary?.is_stale ? " · stale" : ""}
          </p>
        </div>
        <div className="course-note-actions">
          {expanded && (
            <>
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
            </>
          )}
          <button
            aria-controls={noteContentId}
            aria-expanded={expanded}
            className="quiet-button course-note-toggle"
            onClick={onToggle}
            type="button"
          >
            {expanded ? "Minimize note" : "Expand note"}
            <span className="sr-only"> {note.title}</span>
          </button>
        </div>
      </header>

      <div hidden={!expanded} id={noteContentId}>
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
                {summaryStateLabel(summary)}
                {summary ? ` · ${summary.model}` : ""}
                {summary?.is_stale ? " · sources changed" : ""}
                {summary?.status === "completed"
                  ? ` · ${bulletCount} ${bulletCount === 1 ? "bullet" : "bullets"}`
                  : ""}
              </span>
            </div>
            <div className="note-summary-actions">
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
              <button
                aria-controls={summaryContentId}
                aria-expanded={summaryExpanded}
                className="quiet-button"
                onClick={onToggleSummary}
                type="button"
              >
                {summaryExpanded ? "Minimize summary" : "Expand summary"}
                <span className="sr-only"> for {note.title}</span>
              </button>
            </div>
          </header>

          <div hidden={!summaryExpanded} id={summaryContentId}>
            {summaryError && (
              <div className="note-summary-error" role="alert">
                <strong>Bullet was not removed</strong>
                <span>{summaryError}</span>
              </div>
            )}
            {summary?.is_stale && (
              <p className="note-summary-stale" role="status">
                This summary is stale because the note or linked slide text
                changed.
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
            {summary?.status === "completed" &&
              summary.summary_json &&
              (summary.summary_json.bullets.length > 0 ? (
                <ul className="note-summary-bullets">
                  {summary.summary_json.bullets.map((bullet, index) => (
                    <li className={`origin-${bullet.origin}`} key={bullet.id}>
                      <div className="note-summary-bullet-heading">
                        <span className="note-summary-origin">
                          {ORIGIN_LABELS[bullet.origin]}
                        </span>
                        <button
                          aria-label={`Remove summary bullet ${index + 1}`}
                          className="note-summary-remove-bullet"
                          disabled={removingBulletIds.has(bullet.id)}
                          onClick={() => onRemoveBullet(bullet.id)}
                          type="button"
                        >
                          <span aria-hidden="true">
                            {removingBulletIds.has(bullet.id) ? "…" : "×"}
                          </span>
                        </button>
                      </div>
                      <p>{bullet.text}</p>
                      <small>
                        {bullet.source_references
                          .map((reference) =>
                            summaryReferenceLabel(note, reference),
                          )
                          .join(" · ")}
                      </small>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="note-summary-empty-state">
                  <strong>No summary bullets remain.</strong>
                  <p>
                    The source note is unchanged. Use Generate again for a fresh
                    summary.
                  </p>
                </div>
              ))}
            {!summary && (
              <p className="note-summary-empty">
                Generate concise bullets with visible note and slide provenance.
              </p>
            )}
          </div>
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
      </div>
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
  const [expandedNoteIds, setExpandedNoteIds] = useState<Set<string>>(
    () => new Set(),
  );
  const [expandedSummaryNoteIds, setExpandedSummaryNoteIds] = useState<
    Set<string>
  >(() => new Set());
  const [removingBulletIds, setRemovingBulletIds] = useState<Set<string>>(
    () => new Set(),
  );
  const [summaryErrors, setSummaryErrors] = useState<Record<string, string>>(
    {},
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    async function loadNotes() {
      setExpandedNoteIds(new Set());
      setExpandedSummaryNoteIds(new Set());
      setRemovingBulletIds(new Set());
      setSummaryErrors({});
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
      setExpandedNoteIds((current) => {
        const next = new Set(current);
        next.delete(note.id);
        return next;
      });
      setExpandedSummaryNoteIds((current) => {
        const next = new Set(current);
        next.delete(note.id);
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
    setExpandedSummaryNoteIds((current) => {
      const next = new Set(current);
      next.delete(note.id);
      return next;
    });
    setSummaryBusyId(note.id);
    setSummaryErrors((current) => ({ ...current, [note.id]: "" }));
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
    setExpandedSummaryNoteIds((current) => {
      const next = new Set(current);
      next.delete(note.id);
      return next;
    });
    setSummaryBusyId(note.id);
    setSummaryErrors((current) => ({ ...current, [note.id]: "" }));
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

  function toggleExpanded(
    setter: Dispatch<SetStateAction<Set<string>>>,
    noteId: string,
  ) {
    setter((current) => {
      const next = new Set(current);
      if (next.has(noteId)) next.delete(noteId);
      else next.add(noteId);
      return next;
    });
  }

  async function removeSummaryBullet(
    note: CourseNote,
    summary: NoteSummary,
    bulletId: string,
  ) {
    if (removingBulletIds.has(bulletId)) return;
    setRemovingBulletIds((current) => new Set(current).add(bulletId));
    setSummaryErrors((current) => ({ ...current, [note.id]: "" }));
    try {
      const updated = await courseApi.removeNoteSummaryBullet(
        summary.id,
        bulletId,
      );
      setSummaries((current) => ({ ...current, [note.id]: updated }));
    } catch (removeError) {
      setSummaryErrors((current) => ({
        ...current,
        [note.id]:
          removeError instanceof Error
            ? removeError.message
            : "The summary bullet could not be removed.",
      }));
    } finally {
      setRemovingBulletIds((current) => {
        const next = new Set(current);
        next.delete(bulletId);
        return next;
      });
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
              expanded={expandedNoteIds.has(note.id)}
              key={note.id}
              note={note}
              onCancelDelete={() => setConfirmNoteId(null)}
              onConfirmDelete={() => void deleteNote(note)}
              onEdit={() => setDialogNote(note)}
              onGenerateSummary={() => void generateSummary(note)}
              onRemoveBullet={(bulletId) => {
                const summary = summaries[note.id];
                if (summary) {
                  void removeSummaryBullet(note, summary, bulletId);
                }
              }}
              onRequestDelete={() => setConfirmNoteId(note.id)}
              onRetrySummary={() => {
                const summary = summaries[note.id];
                if (summary) void retrySummary(note, summary);
              }}
              onToggle={() => toggleExpanded(setExpandedNoteIds, note.id)}
              onToggleSummary={() =>
                toggleExpanded(setExpandedSummaryNoteIds, note.id)
              }
              removingBulletIds={removingBulletIds}
              summary={summaries[note.id] ?? null}
              summaryBusy={summaryBusyId === note.id}
              summaryError={summaryErrors[note.id] || null}
              summaryExpanded={expandedSummaryNoteIds.has(note.id)}
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
