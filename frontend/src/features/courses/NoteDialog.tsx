import { useState, type FormEvent } from "react";

import { Icon } from "../../components/Icon";
import { useModalDialog } from "../../hooks/useModalDialog";
import { MarkdownNoteEditor } from "./MarkdownNoteEditor";
import type {
  CourseNote,
  CourseSource,
  NoteMutation,
  SlideReference,
} from "./types";

interface EditableReference {
  localId: string;
  sourceId: string;
  startSlide: string;
  endSlide: string;
  label: string;
}

let referenceSequence = 0;

function editableReference(reference?: SlideReference): EditableReference {
  referenceSequence += 1;
  return {
    localId: reference?.id ?? `new-reference-${referenceSequence}`,
    sourceId: reference?.source_id ?? "",
    startSlide: reference?.start_slide?.toString() ?? "",
    endSlide: reference?.end_slide?.toString() ?? "",
    label: reference?.label ?? "",
  };
}

export function NoteDialog({
  note,
  slideSources,
  onClose,
  onSave,
}: {
  note: CourseNote | null;
  slideSources: CourseSource[];
  onClose: () => void;
  onSave: (
    payload: NoteMutation,
    existingNote: CourseNote | null,
  ) => Promise<void>;
}) {
  const [title, setTitle] = useState(note?.title ?? "");
  const [body, setBody] = useState(note?.body ?? "");
  const [references, setReferences] = useState<EditableReference[]>(
    note?.slide_references.map(editableReference) ?? [],
  );
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dialogRef = useModalDialog(onClose);

  function updateReference(
    localId: string,
    changes: Partial<EditableReference>,
  ) {
    setReferences((current) =>
      current.map((reference) =>
        reference.localId === localId
          ? { ...reference, ...changes }
          : reference,
      ),
    );
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (!title.trim()) {
      setError("Add a title for the note.");
      return;
    }

    const identities = new Set<string>();
    for (const [index, reference] of references.entries()) {
      if (!reference.sourceId) {
        setError(`Choose a slide deck for reference ${index + 1}.`);
        return;
      }
      const hasStart = reference.startSlide !== "";
      const hasEnd = reference.endSlide !== "";
      if (hasStart !== hasEnd) {
        setError(
          `Reference ${index + 1} needs both a start and end slide, or neither.`,
        );
        return;
      }
      if (
        hasStart &&
        Number(reference.endSlide) < Number(reference.startSlide)
      ) {
        setError(
          `Reference ${index + 1} must end on or after its start slide.`,
        );
        return;
      }
      const identity = `${reference.sourceId}:${reference.startSlide}:${reference.endSlide}`;
      if (identities.has(identity)) {
        setError("The same slide range cannot be linked more than once.");
        return;
      }
      identities.add(identity);
    }

    setIsSaving(true);
    try {
      await onSave(
        {
          title: title.trim(),
          body,
          slide_references: references.map((reference) => ({
            source_id: reference.sourceId,
            start_slide:
              reference.startSlide === "" ? null : Number(reference.startSlide),
            end_slide:
              reference.endSlide === "" ? null : Number(reference.endSlide),
            label: reference.label.trim() || null,
          })),
        },
        note,
      );
    } catch (saveError) {
      setError(
        saveError instanceof Error
          ? saveError.message
          : "The note could not be saved.",
      );
      setIsSaving(false);
    }
  }

  return (
    <div className="dialog-backdrop" role="presentation">
      <section
        aria-labelledby="note-dialog-title"
        aria-modal="true"
        className="event-dialog note-dialog"
        ref={dialogRef}
        role="dialog"
      >
        <header className="dialog-header">
          <div>
            <p className="eyebrow">{note ? "Edit course note" : "New note"}</p>
            <h2 id="note-dialog-title">
              {note ? "Update note" : "Create note"}
            </h2>
          </div>
          <button
            aria-label="Close note dialog"
            className="icon-button"
            onClick={onClose}
            type="button"
          >
            <Icon name="x" size={19} />
          </button>
        </header>

        <form className="note-editor-form" onSubmit={handleSubmit}>
          <label className="field">
            <span>Note title</span>
            <input
              data-dialog-autofocus="true"
              maxLength={240}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="e.g. Transaction isolation"
              required
              value={title}
            />
          </label>

          <div className="field">
            <label htmlFor="note-body">Note body</label>
            <MarkdownNoteEditor onChange={setBody} value={body} />
          </div>
          <p className="note-format-hint">
            Use the toolbar or type Markdown directly. Syntax characters remain
            visible and are stored exactly as written. Raw HTML is displayed as
            text, never executed.
          </p>

          <section
            aria-labelledby="slide-references-title"
            className="note-reference-editor"
          >
            <header>
              <div>
                <h3 id="slide-references-title">Slide references</h3>
                <p>
                  Optional. Leave both slide numbers blank to link the whole
                  deck.
                </p>
              </div>
              <button
                className="quiet-button"
                disabled={slideSources.length === 0 || isSaving}
                onClick={() =>
                  setReferences((current) => [...current, editableReference()])
                }
                type="button"
              >
                <Icon name="plus" size={14} /> Add reference
              </button>
            </header>

            {slideSources.length === 0 && (
              <p className="note-reference-empty">
                No slide decks are available. You can save this note now and add
                slides from the Materials tab later.
              </p>
            )}

            {references.map((reference, index) => (
              <fieldset className="note-reference-row" key={reference.localId}>
                <legend>Reference {index + 1}</legend>
                <label className="field note-reference-deck">
                  <span>Slide deck</span>
                  <select
                    aria-label={`Slide deck ${index + 1}`}
                    onChange={(event) =>
                      updateReference(reference.localId, {
                        sourceId: event.target.value,
                      })
                    }
                    required
                    value={reference.sourceId}
                  >
                    <option value="">Choose a deck</option>
                    {slideSources.map((source) => (
                      <option key={source.id} value={source.id}>
                        {source.display_name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field">
                  <span>Start slide</span>
                  <input
                    aria-label={`Start slide ${index + 1}`}
                    min={1}
                    onChange={(event) =>
                      updateReference(reference.localId, {
                        startSlide: event.target.value,
                      })
                    }
                    placeholder="Whole deck"
                    type="number"
                    value={reference.startSlide}
                  />
                </label>
                <label className="field">
                  <span>End slide</span>
                  <input
                    aria-label={`End slide ${index + 1}`}
                    min={1}
                    onChange={(event) =>
                      updateReference(reference.localId, {
                        endSlide: event.target.value,
                      })
                    }
                    placeholder="Whole deck"
                    type="number"
                    value={reference.endSlide}
                  />
                </label>
                <label className="field note-reference-label">
                  <span>Label</span>
                  <input
                    aria-label={`Reference label ${index + 1}`}
                    maxLength={240}
                    onChange={(event) =>
                      updateReference(reference.localId, {
                        label: event.target.value,
                      })
                    }
                    placeholder="Optional context"
                    value={reference.label}
                  />
                </label>
                <button
                  aria-label={`Remove reference ${index + 1}`}
                  className="note-reference-remove"
                  disabled={isSaving}
                  onClick={() =>
                    setReferences((current) =>
                      current.filter(
                        (item) => item.localId !== reference.localId,
                      ),
                    )
                  }
                  type="button"
                >
                  <Icon name="x" size={14} /> Remove
                </button>
              </fieldset>
            ))}
          </section>

          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}

          <footer className="dialog-footer">
            <span />
            <div>
              <button
                className="quiet-button"
                disabled={isSaving}
                onClick={onClose}
                type="button"
              >
                Cancel
              </button>
              <button
                className="primary-button"
                disabled={isSaving}
                type="submit"
              >
                {isSaving ? "Saving…" : note ? "Save changes" : "Create note"}
              </button>
            </div>
          </footer>
        </form>
      </section>
    </div>
  );
}
