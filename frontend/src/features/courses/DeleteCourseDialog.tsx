import { useState } from "react";

import { Icon } from "../../components/Icon";
import { useModalDialog } from "../../hooks/useModalDialog";
import type { CourseModel } from "./types";

interface DeleteCourseDialogProps {
  course: CourseModel;
  onClose: () => void;
  onDelete: (course: CourseModel) => Promise<void>;
}

export function DeleteCourseDialog({
  course,
  onClose,
  onDelete,
}: DeleteCourseDialogProps) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dialogRef = useModalDialog(onClose);

  async function handleDelete() {
    setIsDeleting(true);
    setError(null);
    try {
      await onDelete(course);
    } catch (deleteError) {
      setError(
        deleteError instanceof Error
          ? deleteError.message
          : "The course could not be deleted.",
      );
      setIsDeleting(false);
    }
  }

  return (
    <div className="dialog-backdrop" role="presentation">
      <section
        aria-labelledby="delete-course-title"
        aria-modal="true"
        className="event-dialog delete-course-dialog"
        ref={dialogRef}
        role="alertdialog"
      >
        <header className="dialog-header">
          <div>
            <p className="eyebrow">Permanent action</p>
            <h2 id="delete-course-title">Delete {course.name}?</h2>
          </div>
          <button
            aria-label="Close delete course dialog"
            className="icon-button"
            onClick={onClose}
            type="button"
          >
            <Icon name="x" size={19} />
          </button>
        </header>

        <div className="delete-course-content">
          <p>
            This permanently deletes the course details and all of its
            literature, slides, extracted text, notes, and slide references. The
            content cannot be recovered unless you have a backup.
          </p>
          <p>
            Calendars and calendar events are never deleted with a course. This
            action cannot be undone.
          </p>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <footer className="dialog-footer">
            <button
              className="quiet-button"
              data-dialog-autofocus="true"
              disabled={isDeleting}
              onClick={onClose}
              type="button"
            >
              Keep course
            </button>
            <button
              className="danger-button"
              disabled={isDeleting}
              onClick={handleDelete}
              type="button"
            >
              <Icon name="trash" size={17} />
              {isDeleting ? "Deleting…" : "Delete course"}
            </button>
          </footer>
        </div>
      </section>
    </div>
  );
}
