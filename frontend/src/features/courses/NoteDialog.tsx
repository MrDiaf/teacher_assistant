import { useEffect, useRef, useState, type FormEvent } from "react";

import { AiModelSelector, useAiModelSelection } from "../../platform/ai";
import { Icon, useModalDialog } from "../../platform/ui";
import { courseApi } from "./api";
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

interface PrettifyPreview {
  original: string;
  proposed: string;
  message: string;
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
  const [isPrettifying, setIsPrettifying] = useState(false);
  const [prettifyPreview, setPrettifyPreview] =
    useState<PrettifyPreview | null>(null);
  const [prettifyStatus, setPrettifyStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const prettifyController = useRef<AbortController | null>(null);
  const {
    modelList,
    selectedModel,
    setSelectedModel,
    modelError,
    isModelLoading,
  } = useAiModelSelection();

  function handleClose() {
    prettifyController.current?.abort();
    onClose();
  }

  const dialogRef = useModalDialog(handleClose);

  useEffect(
    () => () => {
      prettifyController.current?.abort();
    },
    [],
  );

  function focusEditor() {
    window.requestAnimationFrame(() => {
      document.getElementById("note-body")?.focus();
    });
  }

  async function handlePrettify() {
    if (isPrettifying || !selectedModel) return;
    const original = body;
    const controller = new AbortController();
    prettifyController.current = controller;
    setError(null);
    setPrettifyStatus(null);
    setPrettifyPreview(null);
    setIsPrettifying(true);
    try {
      const suggestion = await courseApi.prettifyNote(
        original,
        selectedModel,
        controller.signal,
      );
      if (suggestion.has_changes) {
        setPrettifyPreview({
          original,
          proposed: suggestion.proposed_body,
          message: suggestion.message,
        });
      } else {
        setPrettifyStatus(suggestion.message);
        focusEditor();
      }
    } catch (prettifyError) {
      if (
        prettifyError instanceof DOMException &&
        prettifyError.name === "AbortError"
      ) {
        setPrettifyStatus("Prettify cancelled. Your draft is unchanged.");
      } else {
        setError(
          prettifyError instanceof Error
            ? prettifyError.message
            : "The note could not be prettified. Your draft is unchanged.",
        );
      }
    } finally {
      if (prettifyController.current === controller) {
        prettifyController.current = null;
      }
      setIsPrettifying(false);
    }
  }

  function cancelPrettify() {
    prettifyController.current?.abort();
  }

  function keepOriginal() {
    setPrettifyPreview(null);
    setPrettifyStatus("Your original draft is unchanged.");
    focusEditor();
  }

  function usePrettifiedVersion() {
    if (!prettifyPreview) return;
    setBody(prettifyPreview.proposed);
    setPrettifyPreview(null);
    setPrettifyStatus(
      "The prettified text is now in your unsaved draft. Save the note when ready.",
    );
    focusEditor();
  }

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
            onClick={handleClose}
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

          {!prettifyPreview && (
            <div className="field">
              <label htmlFor="note-body">Note body</label>
              <MarkdownNoteEditor
                disabled={isPrettifying}
                onChange={setBody}
                value={body}
              />
            </div>
          )}
          {!prettifyPreview && (
            <p className="note-format-hint">
              Use the toolbar or type Markdown directly. Syntax characters
              remain visible and are stored exactly as written. Raw HTML is
              displayed as text, never executed.
            </p>
          )}

          {prettifyPreview ? (
            <section
              aria-label="Prettify comparison"
              className="note-prettify-preview"
            >
              <header>
                <div>
                  <p className="eyebrow">Suggestion only</p>
                  <h3>Review every change</h3>
                </div>
                <p>{prettifyPreview.message}</p>
              </header>
              <div className="note-prettify-columns">
                <section aria-labelledby="prettify-before-title">
                  <h4 id="prettify-before-title">Your version</h4>
                  <pre tabIndex={0}>{prettifyPreview.original}</pre>
                </section>
                <section aria-labelledby="prettify-after-title">
                  <h4 id="prettify-after-title">Prettified version</h4>
                  <pre tabIndex={0}>{prettifyPreview.proposed}</pre>
                </section>
              </div>
              <div className="note-prettify-actions">
                <button
                  className="quiet-button"
                  onClick={keepOriginal}
                  type="button"
                >
                  Keep my version
                </button>
                <button
                  className="secondary-button"
                  onClick={usePrettifiedVersion}
                  type="button"
                >
                  Use prettified version
                </button>
              </div>
            </section>
          ) : (
            <section className="note-prettify-controls">
              <div>
                <AiModelSelector
                  disabled={isPrettifying || isSaving}
                  label="Prettify model"
                  modelList={modelList}
                  onChange={setSelectedModel}
                  value={selectedModel}
                />
                {modelError && <p className="form-error">{modelError}</p>}
              </div>
              <button
                className="quiet-button note-prettify-button"
                disabled={isSaving || isModelLoading || Boolean(modelError)}
                onClick={isPrettifying ? cancelPrettify : handlePrettify}
                type="button"
              >
                <Icon name={isPrettifying ? "x" : "assistant"} size={14} />
                {isPrettifying ? "Cancel prettify" : "Prettify"}
              </button>
              <p>
                Sends only this current draft to the configured private Codex
                runtime. You review the suggestion, and nothing is saved
                automatically. Maximum 40,000 characters.
              </p>
            </section>
          )}

          {isPrettifying && (
            <p className="note-prettify-working" role="status">
              Checking the draft for clear corrections…
            </p>
          )}
          {prettifyStatus && (
            <p className="note-prettify-status" role="status">
              {prettifyStatus}
            </p>
          )}

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
                disabled={
                  slideSources.length === 0 || isSaving || isPrettifying
                }
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
                    disabled={isPrettifying}
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
                    disabled={isPrettifying}
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
                    disabled={isPrettifying}
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
                    disabled={isPrettifying}
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
                  disabled={isSaving || isPrettifying}
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
                disabled={isSaving || isPrettifying}
                onClick={handleClose}
                type="button"
              >
                Cancel
              </button>
              <button
                className="primary-button"
                disabled={isSaving || isPrettifying || Boolean(prettifyPreview)}
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
