import { useEffect, useState } from "react";

import { Icon } from "../../components/Icon";
import { NoteDialog } from "./NoteDialog";
import { courseApi } from "./api";
import type {
  CourseModel,
  CourseNote,
  CourseSource,
  NoteMutation,
  SlideReference,
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

function NoteCard({
  busy,
  confirmingDelete,
  note,
  onCancelDelete,
  onConfirmDelete,
  onEdit,
  onRequestDelete,
}: {
  busy: boolean;
  confirmingDelete: boolean;
  note: CourseNote;
  onCancelDelete: () => void;
  onConfirmDelete: () => void;
  onEdit: () => void;
  onRequestDelete: () => void;
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
        <p className="course-note-body">{note.body}</p>
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
  const [notes, setNotes] = useState<CourseNote[]>([]);
  const [slideSources, setSlideSources] = useState<CourseSource[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [dialogNote, setDialogNote] = useState<CourseNote | null | undefined>(
    undefined,
  );
  const [confirmNoteId, setConfirmNoteId] = useState<string | null>(null);
  const [busyNoteId, setBusyNoteId] = useState<string | null>(null);
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
        setNotes(loadedNotes);
        setSlideSources(loadedSources);
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
    setDialogNote(undefined);
  }

  async function deleteNote(note: CourseNote) {
    setBusyNoteId(note.id);
    setError(null);
    try {
      await courseApi.deleteNote(note.id);
      setNotes((current) => current.filter((item) => item.id !== note.id));
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
        <button
          className="primary-button"
          onClick={() => setDialogNote(null)}
          type="button"
        >
          <Icon name="plus" size={16} /> Create note
        </button>
      </header>

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
              confirmingDelete={confirmNoteId === note.id}
              key={note.id}
              note={note}
              onCancelDelete={() => setConfirmNoteId(null)}
              onConfirmDelete={() => void deleteNote(note)}
              onEdit={() => setDialogNote(note)}
              onRequestDelete={() => setConfirmNoteId(note.id)}
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
