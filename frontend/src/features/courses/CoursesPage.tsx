import { useCallback, useEffect, useMemo, useState } from "react";

import { Icon } from "../../components/Icon";
import {
  clearCourseSelection,
  getCourseSelection,
  pruneCourseCalendars,
  removeCourseCalendarPreference,
  setCourseSelection,
} from "../../persistence/uiState";
import { CourseCalendar } from "./CourseCalendar";
import { CourseDialog } from "./CourseDialog";
import { CourseMaterials } from "./CourseMaterials";
import { CourseNotes } from "./CourseNotes";
import { DeleteCourseDialog } from "./DeleteCourseDialog";
import { courseApi } from "./api";
import type { CourseModel, CourseMutation, CourseTab } from "./types";

const TABS: { id: CourseTab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "notes", label: "Notes" },
  { id: "materials", label: "Materials" },
  { id: "calendar", label: "Calendar" },
];

function CourseCard({
  busy,
  course,
  onArchive,
  onEdit,
  onOpen,
  onRestore,
}: {
  busy: boolean;
  course: CourseModel;
  onArchive: (course: CourseModel) => void;
  onEdit: (course: CourseModel) => void;
  onOpen: (course: CourseModel) => void;
  onRestore: (course: CourseModel) => void;
}) {
  return (
    <article className={`course-card ${course.status}`}>
      <span
        aria-hidden="true"
        className="course-card-color"
        style={{ backgroundColor: course.color }}
      />
      <button
        aria-label={`Open ${course.name}`}
        className="course-card-open"
        onClick={() => onOpen(course)}
        type="button"
      >
        <span className="course-card-meta">
          {course.course_code && <strong>{course.course_code}</strong>}
          <span>{course.term ?? "Term not set"}</span>
        </span>
        <h3>{course.name}</h3>
        <p>
          {course.description ??
            "Add a short description to make this course easier to recognize."}
        </p>
        <span className="course-card-link">
          Open course <Icon name="chevron-right" size={15} />
        </span>
      </button>
      <footer className="course-card-actions">
        <span>
          {course.source_count}{" "}
          {course.source_count === 1 ? "material" : "materials"} ·{" "}
          {course.calendar_count}{" "}
          {course.calendar_count === 1 ? "calendar" : "calendars"}
        </span>
        <div>
          <button disabled={busy} onClick={() => onEdit(course)} type="button">
            Edit
          </button>
          {course.status === "active" ? (
            <button
              disabled={busy}
              onClick={() => onArchive(course)}
              type="button"
            >
              Archive
            </button>
          ) : (
            <button
              disabled={busy}
              onClick={() => onRestore(course)}
              type="button"
            >
              Restore
            </button>
          )}
        </div>
      </footer>
    </article>
  );
}

function CourseCollection({
  busyCourseId,
  courses,
  emptyCopy,
  title,
  onArchive,
  onEdit,
  onOpen,
  onRestore,
}: {
  busyCourseId: string | null;
  courses: CourseModel[];
  emptyCopy: string;
  title: string;
  onArchive: (course: CourseModel) => void;
  onEdit: (course: CourseModel) => void;
  onOpen: (course: CourseModel) => void;
  onRestore: (course: CourseModel) => void;
}) {
  const headingId = `${title.toLowerCase().replaceAll(" ", "-")}-heading`;
  return (
    <section className="course-collection" aria-labelledby={headingId}>
      <header>
        <h2 id={headingId}>{title}</h2>
        <span>{courses.length}</span>
      </header>
      {courses.length ? (
        <div className="course-card-grid">
          {courses.map((course) => (
            <CourseCard
              busy={busyCourseId === course.id}
              course={course}
              key={course.id}
              onArchive={onArchive}
              onEdit={onEdit}
              onOpen={onOpen}
              onRestore={onRestore}
            />
          ))}
        </div>
      ) : (
        <p className="course-collection-empty">{emptyCopy}</p>
      )}
    </section>
  );
}

function CourseDetail({
  activeTab,
  busy,
  course,
  onArchive,
  onBack,
  onDelete,
  onEdit,
  onRestore,
  onTabChange,
  onCalendarCountChange,
  onSourceCountChange,
}: {
  activeTab: CourseTab;
  busy: boolean;
  course: CourseModel;
  onArchive: () => void;
  onBack: () => void;
  onDelete: () => void;
  onEdit: () => void;
  onRestore: () => void;
  onTabChange: (tab: CourseTab) => void;
  onCalendarCountChange: (count: number) => void;
  onSourceCountChange: (count: number) => void;
}) {
  return (
    <main className="course-detail-page" aria-labelledby="course-detail-title">
      <button className="course-back-button" onClick={onBack} type="button">
        <Icon name="chevron-left" size={17} /> Back to courses
      </button>

      <header className="course-detail-hero">
        <span
          aria-hidden="true"
          className="course-detail-color"
          style={{ backgroundColor: course.color }}
        />
        <div>
          <p className="eyebrow">
            {course.course_code ?? "Manual course"}
            {course.term ? ` · ${course.term}` : ""}
          </p>
          <h1 id="course-detail-title">{course.name}</h1>
          <p>
            {course.description ??
              "Add a description to introduce this course workspace."}
          </p>
        </div>
        <div className="course-detail-actions">
          <button
            className="quiet-button"
            disabled={busy}
            onClick={onEdit}
            type="button"
          >
            Edit course
          </button>
          <button
            className="quiet-button"
            disabled={busy}
            onClick={course.status === "active" ? onArchive : onRestore}
            type="button"
          >
            {course.status === "active" ? "Archive" : "Restore"}
          </button>
          <button
            className="danger-button"
            disabled={busy}
            onClick={onDelete}
            type="button"
          >
            <Icon name="trash" size={16} /> Delete
          </button>
        </div>
      </header>

      <nav className="course-tabs" aria-label="Course sections" role="tablist">
        {TABS.map((tab) => (
          <button
            aria-controls={`course-panel-${tab.id}`}
            aria-selected={activeTab === tab.id}
            id={`course-tab-${tab.id}`}
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            role="tab"
            type="button"
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <section
        aria-labelledby={`course-tab-${activeTab}`}
        className="course-tab-panel"
        id={`course-panel-${activeTab}`}
        role="tabpanel"
      >
        {activeTab === "overview" ? (
          <div className="course-overview-grid">
            <article>
              <p className="eyebrow">Course information</p>
              <h2>At a glance</h2>
              <dl>
                <div>
                  <dt>Course code</dt>
                  <dd>{course.course_code ?? "Not set"}</dd>
                </div>
                <div>
                  <dt>Term</dt>
                  <dd>{course.term ?? "Not set"}</dd>
                </div>
                <div>
                  <dt>Status</dt>
                  <dd className={`course-status ${course.status}`}>
                    {course.status}
                  </dd>
                </div>
                <div>
                  <dt>Source</dt>
                  <dd>Created manually</dd>
                </div>
                <div>
                  <dt>Materials</dt>
                  <dd>{course.source_count}</dd>
                </div>
                <div>
                  <dt>Linked calendars</dt>
                  <dd>{course.calendar_count}</dd>
                </div>
              </dl>
            </article>
            <article className="course-next-steps">
              <p className="eyebrow">Course workspace</p>
              <h2>Build a useful source library</h2>
              <p>
                Literature, slides, private course notes, and linked calendars
                are ready in this course workspace.
              </p>
            </article>
          </div>
        ) : activeTab === "notes" ? (
          <CourseNotes course={course} />
        ) : activeTab === "materials" ? (
          <CourseMaterials
            course={course}
            onSourceCountChange={onSourceCountChange}
          />
        ) : activeTab === "calendar" ? (
          <CourseCalendar
            course={course}
            onCalendarCountChange={onCalendarCountChange}
          />
        ) : (
          <div className="course-tab-placeholder">
            <span>
              <Icon name="courses" />
            </span>
            <p className="eyebrow">Planned section</p>
            <h2>Planned section</h2>
            <p>This course section is not available yet.</p>
          </div>
        )}
      </section>
    </main>
  );
}

export function CoursesPage() {
  const [initialSelection] = useState(getCourseSelection);
  const [courses, setCourses] = useState<CourseModel[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadVersion, setLoadVersion] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [selectedCourseId, setSelectedCourseId] = useState<string | null>(
    initialSelection?.courseId ?? null,
  );
  const [activeCourseTab, setActiveCourseTab] = useState<CourseTab>(
    initialSelection?.tab ?? "overview",
  );
  const [dialogCourse, setDialogCourse] = useState<
    CourseModel | null | undefined
  >(undefined);
  const [deleteCourse, setDeleteCourse] = useState<CourseModel | null>(null);
  const [busyCourseId, setBusyCourseId] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    async function loadCourses() {
      setIsLoading(true);
      setError(null);
      try {
        const loaded = await courseApi.list(controller.signal);
        if (controller.signal.aborted) return;
        setCourses(loaded);
        const loadedIds = loaded.map((course) => course.id);
        pruneCourseCalendars(loadedIds);
        setSelectedCourseId((current) => {
          if (current && !loadedIds.includes(current)) {
            clearCourseSelection();
            removeCourseCalendarPreference(current);
            return null;
          }
          return current;
        });
      } catch (loadError) {
        if (!controller.signal.aborted) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Courses could not be loaded.",
          );
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false);
      }
    }
    void loadCourses();
    return () => controller.abort();
  }, [loadVersion]);

  const activeCourses = useMemo(
    () => courses.filter((course) => course.status === "active"),
    [courses],
  );
  const archivedCourses = useMemo(
    () => courses.filter((course) => course.status === "archived"),
    [courses],
  );
  const selectedCourse =
    courses.find((course) => course.id === selectedCourseId) ?? null;
  const updateSelectedCourseSourceCount = useCallback(
    (count: number) => {
      setCourses((current) => {
        let changed = false;
        const next = current.map((course) => {
          if (course.id !== selectedCourseId || course.source_count === count) {
            return course;
          }
          changed = true;
          return { ...course, source_count: count };
        });
        return changed ? next : current;
      });
    },
    [selectedCourseId],
  );
  const updateSelectedCourseCalendarCount = useCallback(
    (count: number) => {
      setCourses((current) => {
        let changed = false;
        const next = current.map((course) => {
          if (
            course.id !== selectedCourseId ||
            course.calendar_count === count
          ) {
            return course;
          }
          changed = true;
          return { ...course, calendar_count: count };
        });
        return changed ? next : current;
      });
    },
    [selectedCourseId],
  );

  function replaceCourse(course: CourseModel) {
    setCourses((current) =>
      current.map((item) => (item.id === course.id ? course : item)),
    );
  }

  function openCourse(course: CourseModel) {
    setSelectedCourseId(course.id);
    setActiveCourseTab("overview");
    setCourseSelection({ courseId: course.id, tab: "overview" });
  }

  function changeCourseTab(tab: CourseTab) {
    if (!selectedCourseId) return;
    setActiveCourseTab(tab);
    setCourseSelection({ courseId: selectedCourseId, tab });
  }

  function closeCourse() {
    setSelectedCourseId(null);
    setActiveCourseTab("overview");
    clearCourseSelection();
  }

  async function handleSave(
    payload: CourseMutation,
    existingCourse: CourseModel | null,
  ) {
    const saved = existingCourse
      ? await courseApi.update(existingCourse.id, payload)
      : await courseApi.create(payload);
    if (existingCourse) {
      replaceCourse(saved);
    } else {
      setCourses((current) => [saved, ...current]);
    }
    setDialogCourse(undefined);
  }

  async function changeStatus(
    course: CourseModel,
    action: "archive" | "restore",
  ) {
    setBusyCourseId(course.id);
    setError(null);
    try {
      replaceCourse(
        action === "archive"
          ? await courseApi.archive(course.id)
          : await courseApi.restore(course.id),
      );
    } catch (actionError) {
      setError(
        actionError instanceof Error
          ? actionError.message
          : "The course status could not be changed.",
      );
    } finally {
      setBusyCourseId(null);
    }
  }

  async function handleDelete(course: CourseModel) {
    await courseApi.delete(course.id);
    setCourses((current) => current.filter((item) => item.id !== course.id));
    removeCourseCalendarPreference(course.id);
    if (selectedCourseId === course.id) closeCourse();
    setDeleteCourse(null);
  }

  if (selectedCourse) {
    return (
      <>
        {error && (
          <div className="course-detail-error" role="alert">
            {error}
          </div>
        )}
        <CourseDetail
          activeTab={activeCourseTab}
          busy={busyCourseId === selectedCourse.id}
          course={selectedCourse}
          onArchive={() => void changeStatus(selectedCourse, "archive")}
          onBack={closeCourse}
          onDelete={() => setDeleteCourse(selectedCourse)}
          onEdit={() => setDialogCourse(selectedCourse)}
          onRestore={() => void changeStatus(selectedCourse, "restore")}
          onTabChange={changeCourseTab}
          onCalendarCountChange={updateSelectedCourseCalendarCount}
          onSourceCountChange={updateSelectedCourseSourceCount}
        />
        {dialogCourse !== undefined && (
          <CourseDialog
            course={dialogCourse}
            onClose={() => setDialogCourse(undefined)}
            onSave={handleSave}
          />
        )}
        {deleteCourse && (
          <DeleteCourseDialog
            course={deleteCourse}
            onClose={() => setDeleteCourse(null)}
            onDelete={handleDelete}
          />
        )}
      </>
    );
  }

  return (
    <main className="courses-page" aria-labelledby="courses-title">
      <header className="courses-page-header">
        <div>
          <p className="eyebrow">Course workspace</p>
          <h1 id="courses-title">Courses</h1>
          <p>
            Create a clear home for each course before adding notes and
            materials.
          </p>
        </div>
        <button
          className="primary-button create-course-button"
          onClick={() => setDialogCourse(null)}
          type="button"
        >
          <Icon name="plus" size={18} /> Create course
        </button>
      </header>

      {error && (
        <div className="courses-error" role="alert">
          <div>
            <strong>Courses are unavailable</strong>
            <span>{error}</span>
          </div>
          <button
            className="quiet-button"
            onClick={() => setLoadVersion((version) => version + 1)}
            type="button"
          >
            Try again
          </button>
        </div>
      )}

      {isLoading ? (
        <div className="courses-loading" role="status">
          <span className="sr-only">Loading courses</span>
          <i />
          <i />
          <i />
        </div>
      ) : courses.length === 0 && !error ? (
        <section className="courses-empty-state">
          <span aria-hidden="true">
            <Icon name="courses" size={28} />
          </span>
          <p className="eyebrow">Your course shelf is empty</p>
          <h2>Create your first course</h2>
          <p>
            Start with its name, code, term, and color. You can edit or archive
            it at any time.
          </p>
          <button
            className="primary-button"
            onClick={() => setDialogCourse(null)}
            type="button"
          >
            <Icon name="plus" size={17} /> Create course
          </button>
        </section>
      ) : (
        <div className="course-sections">
          <CourseCollection
            busyCourseId={busyCourseId}
            courses={activeCourses}
            emptyCopy="No active courses. Restore an archived course or create a new one."
            onArchive={(course) => void changeStatus(course, "archive")}
            onEdit={setDialogCourse}
            onOpen={openCourse}
            onRestore={(course) => void changeStatus(course, "restore")}
            title="Active courses"
          />
          <CourseCollection
            busyCourseId={busyCourseId}
            courses={archivedCourses}
            emptyCopy="Archived courses will stay here until you restore or delete them."
            onArchive={(course) => void changeStatus(course, "archive")}
            onEdit={setDialogCourse}
            onOpen={openCourse}
            onRestore={(course) => void changeStatus(course, "restore")}
            title="Archived courses"
          />
        </div>
      )}

      {dialogCourse !== undefined && (
        <CourseDialog
          course={dialogCourse}
          onClose={() => setDialogCourse(undefined)}
          onSave={handleSave}
        />
      )}
    </main>
  );
}
