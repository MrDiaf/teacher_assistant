import { useState, type FormEvent } from "react";

import { Icon } from "../../components/Icon";
import { useModalDialog } from "../../hooks/useModalDialog";
import type { CourseModel, CourseMutation } from "./types";

const DEFAULT_COLOR = "#29584c";

interface CourseDialogProps {
  course: CourseModel | null;
  onClose: () => void;
  onSave: (
    payload: CourseMutation,
    course: CourseModel | null,
  ) => Promise<void>;
}

export function CourseDialog({ course, onClose, onSave }: CourseDialogProps) {
  const [name, setName] = useState(course?.name ?? "");
  const [courseCode, setCourseCode] = useState(course?.course_code ?? "");
  const [term, setTerm] = useState(course?.term ?? "");
  const [description, setDescription] = useState(course?.description ?? "");
  const [color, setColor] = useState(course?.color ?? DEFAULT_COLOR);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dialogRef = useModalDialog(onClose);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (!name.trim()) {
      setError("Add a name for the course.");
      return;
    }
    setIsSaving(true);
    try {
      await onSave(
        {
          name: name.trim(),
          course_code: courseCode.trim() || null,
          description: description.trim() || null,
          term: term.trim() || null,
          color,
        },
        course,
      );
    } catch (saveError) {
      setError(
        saveError instanceof Error
          ? saveError.message
          : "The course could not be saved.",
      );
      setIsSaving(false);
    }
  }

  return (
    <div className="dialog-backdrop" role="presentation">
      <section
        aria-labelledby="course-dialog-title"
        aria-modal="true"
        className="event-dialog course-dialog"
        ref={dialogRef}
        role="dialog"
      >
        <header className="dialog-header">
          <div>
            <p className="eyebrow">
              {course ? "Course settings" : "New course"}
            </p>
            <h2 id="course-dialog-title">
              {course ? "Edit course" : "Create course"}
            </h2>
          </div>
          <button
            aria-label="Close course dialog"
            className="icon-button"
            onClick={onClose}
            type="button"
          >
            <Icon name="x" size={19} />
          </button>
        </header>

        <form className="event-form" onSubmit={handleSubmit}>
          <label className="field field-wide">
            <span>Course name</span>
            <input
              data-dialog-autofocus="true"
              maxLength={160}
              onChange={(input) => setName(input.target.value)}
              placeholder="e.g. Database Systems"
              required
              value={name}
            />
          </label>

          <label className="field">
            <span>Course code</span>
            <input
              maxLength={64}
              onChange={(input) => setCourseCode(input.target.value)}
              placeholder="e.g. DAT101"
              value={courseCode}
            />
          </label>

          <label className="field">
            <span>Term</span>
            <input
              maxLength={120}
              onChange={(input) => setTerm(input.target.value)}
              placeholder="e.g. Autumn 2026"
              value={term}
            />
          </label>

          <label className="field field-wide">
            <span>Description</span>
            <textarea
              maxLength={5000}
              onChange={(input) => setDescription(input.target.value)}
              placeholder="What will you learn in this course?"
              rows={4}
              value={description}
            />
          </label>

          <label className="field">
            <span>Course color</span>
            <input
              aria-label="Course color"
              onChange={(input) => setColor(input.target.value)}
              type="color"
              value={color}
            />
          </label>

          <p className="course-form-note">
            You can add notes, materials, and calendars in later milestones.
          </p>

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
                {isSaving
                  ? "Saving…"
                  : course
                    ? "Save changes"
                    : "Create course"}
              </button>
            </div>
          </footer>
        </form>
      </section>
    </div>
  );
}
