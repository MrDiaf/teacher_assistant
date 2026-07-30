import { useEffect, useState } from "react";

import { Icon } from "../../components/Icon";
import { courseApi } from "./api";
import type {
  CourseMaterialType,
  CourseModel,
  CourseSource,
  ExtractionStatus,
} from "./types";

const SOURCE_SECTIONS: {
  type: CourseMaterialType;
  title: string;
  description: string;
}[] = [
  {
    type: "literature",
    title: "Literature",
    description: "Books, articles, reading lists, and reference documents.",
  },
  {
    type: "slides",
    title: "Slides",
    description: "Lecture decks, handouts, and presentation notes.",
  },
];

const STATUS_LABELS: Record<ExtractionStatus, string> = {
  not_started: "Stored",
  queued: "Queued",
  processing: "Extracting",
  completed: "Ready",
  failed: "Extraction failed",
  unsupported: "Stored · extraction unavailable",
};

function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function extractedUnit(source: CourseSource) {
  if (source.mime_type === "application/pdf") return "page";
  if (
    source.mime_type ===
    "application/vnd.openxmlformats-officedocument.presentationml.presentation"
  ) {
    return "slide";
  }
  return "text section";
}

function SourceCard({
  busy,
  confirmingDelete,
  source,
  onCancelDelete,
  onConfirmDelete,
  onRequestDelete,
  onRetry,
}: {
  busy: boolean;
  confirmingDelete: boolean;
  source: CourseSource;
  onCancelDelete: () => void;
  onConfirmDelete: () => void;
  onRequestDelete: () => void;
  onRetry: () => void;
}) {
  const unit = extractedUnit(source);
  const count = source.extracted_text_count;

  return (
    <article className="course-source-card">
      <div className="course-source-mark" aria-hidden="true">
        <Icon
          name={source.source_type === "slides" ? "presentation" : "file"}
        />
      </div>
      <div className="course-source-main">
        <div className="course-source-heading">
          <div>
            <h4>{source.display_name}</h4>
            <p>
              {source.original_filename} · {formatFileSize(source.file_size)}
            </p>
          </div>
          <span className={`course-source-status ${source.extraction_status}`}>
            {STATUS_LABELS[source.extraction_status]}
          </span>
        </div>

        {source.extraction_status === "completed" && (
          <p className="course-source-note success">
            {count} {unit}
            {count === 1 ? "" : "s"} extracted and ready for future course
            features.
          </p>
        )}
        {source.extraction_status === "unsupported" && (
          <p className="course-source-note">
            This file is stored safely. Automatic text extraction is not
            available for its format.
          </p>
        )}
        {source.extraction_status === "failed" && (
          <p className="course-source-note error">
            {source.extraction_error ??
              "Text extraction failed. The original file is still stored."}
          </p>
        )}

        {confirmingDelete ? (
          <div className="course-source-delete-confirm" role="alert">
            <p>
              Delete <strong>{source.display_name}</strong>? Only this{" "}
              {source.source_type} file and its extracted text will be removed.
              {source.source_type === "slides"
                ? " References to it are removed from notes, while the notes remain."
                : ""}{" "}
              Other course materials are unaffected.
            </p>
            <div>
              <button
                className="quiet-button"
                disabled={busy}
                onClick={onCancelDelete}
                type="button"
              >
                Keep file
              </button>
              <button
                className="danger-button"
                disabled={busy}
                onClick={onConfirmDelete}
                type="button"
              >
                {busy ? "Deleting…" : "Delete this file"}
              </button>
            </div>
          </div>
        ) : (
          <div className="course-source-actions">
            {source.extraction_status === "failed" && (
              <button
                className="quiet-button"
                disabled={busy}
                onClick={onRetry}
                type="button"
              >
                <Icon name="refresh" size={14} />
                {busy ? "Retrying…" : "Retry extraction"}
              </button>
            )}
            <button
              className="course-source-delete"
              disabled={busy}
              onClick={onRequestDelete}
              type="button"
            >
              <Icon name="trash" size={14} /> Delete
            </button>
          </div>
        )}
      </div>
    </article>
  );
}

export function CourseMaterials({
  course,
  onSourceCountChange,
}: {
  course: CourseModel;
  onSourceCountChange: (count: number) => void;
}) {
  const [sources, setSources] = useState<CourseSource[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [hasLoadedSources, setHasLoadedSources] = useState(false);
  const [uploadingType, setUploadingType] = useState<CourseMaterialType | null>(
    null,
  );
  const [busySourceId, setBusySourceId] = useState<string | null>(null);
  const [confirmSourceId, setConfirmSourceId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    async function loadSources() {
      setIsLoading(true);
      setHasLoadedSources(false);
      setError(null);
      try {
        const loaded = await courseApi.listSources(
          course.id,
          controller.signal,
        );
        setSources(loaded);
        setHasLoadedSources(true);
      } catch (loadError) {
        if (!controller.signal.aborted) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Course materials could not be loaded.",
          );
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false);
      }
    }
    void loadSources();
    return () => controller.abort();
  }, [course.id, onSourceCountChange]);

  useEffect(() => {
    if (hasLoadedSources) onSourceCountChange(sources.length);
  }, [hasLoadedSources, onSourceCountChange, sources.length]);

  async function upload(sourceType: CourseMaterialType, file: File) {
    setUploadingType(sourceType);
    setError(null);
    try {
      const source = await courseApi.uploadSource(course.id, sourceType, file);
      setSources((current) => [source, ...current]);
    } catch (uploadError) {
      setError(
        uploadError instanceof Error
          ? uploadError.message
          : "The course material could not be uploaded.",
      );
    } finally {
      setUploadingType(null);
    }
  }

  async function retry(source: CourseSource) {
    setBusySourceId(source.id);
    setError(null);
    try {
      const updated = await courseApi.retrySourceExtraction(source.id);
      setSources((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
    } catch (retryError) {
      setError(
        retryError instanceof Error
          ? retryError.message
          : "Text extraction could not be retried.",
      );
    } finally {
      setBusySourceId(null);
    }
  }

  async function remove(source: CourseSource) {
    setBusySourceId(source.id);
    setError(null);
    try {
      await courseApi.deleteSource(source.id);
      setSources((current) => current.filter((item) => item.id !== source.id));
      setConfirmSourceId(null);
    } catch (deleteError) {
      setError(
        deleteError instanceof Error
          ? deleteError.message
          : "The course material could not be deleted.",
      );
    } finally {
      setBusySourceId(null);
    }
  }

  return (
    <div className="course-materials">
      <header className="course-materials-header">
        <div>
          <p className="eyebrow">Course source library</p>
          <h2>Materials</h2>
          <p>
            Upload up to 25 MB per file. PDF, PowerPoint, TXT, and Markdown are
            extracted automatically; other formats are stored without text
            extraction.
          </p>
        </div>
        <span>{sources.length} files</span>
      </header>

      {error && (
        <div className="course-materials-error" role="alert">
          {error}
        </div>
      )}

      {isLoading ? (
        <div className="course-materials-loading" role="status">
          Loading course materials…
        </div>
      ) : (
        <div className="course-material-sections">
          {SOURCE_SECTIONS.map((section) => {
            const sectionSources = sources.filter(
              (source) => source.source_type === section.type,
            );
            const isUploading = uploadingType === section.type;
            return (
              <section
                className={`course-material-section ${section.type}`}
                key={section.type}
              >
                <header>
                  <div>
                    <p className="eyebrow">
                      {sectionSources.length}{" "}
                      {sectionSources.length === 1 ? "file" : "files"}
                    </p>
                    <h3>{section.title}</h3>
                    <p>{section.description}</p>
                  </div>
                  <label
                    className={`course-material-upload${
                      isUploading ? " disabled" : ""
                    }`}
                  >
                    <Icon name="upload" size={15} />
                    {isUploading ? "Uploading…" : `Add ${section.title}`}
                    <input
                      aria-label={`Upload ${section.title.toLowerCase()}`}
                      disabled={uploadingType !== null}
                      onChange={(event) => {
                        const file = event.currentTarget.files?.[0];
                        event.currentTarget.value = "";
                        if (file) void upload(section.type, file);
                      }}
                      type="file"
                    />
                  </label>
                </header>

                {sectionSources.length ? (
                  <div className="course-source-list">
                    {sectionSources.map((source) => (
                      <SourceCard
                        busy={busySourceId === source.id}
                        confirmingDelete={confirmSourceId === source.id}
                        key={source.id}
                        onCancelDelete={() => setConfirmSourceId(null)}
                        onConfirmDelete={() => void remove(source)}
                        onRequestDelete={() => setConfirmSourceId(source.id)}
                        onRetry={() => void retry(source)}
                        source={source}
                      />
                    ))}
                  </div>
                ) : (
                  <p className="course-material-empty">
                    No {section.title.toLowerCase()} uploaded yet.
                  </p>
                )}
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}
