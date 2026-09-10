"""Public backend entry for Courses-owned routes."""

from app.course_calendars.routes import router as course_calendar_router
from app.course_sources.routes import router as course_source_router
from app.courses.routes import router as course_router
from app.notes.prettify_routes import router as note_prettify_router
from app.notes.routes import router as note_router
from app.notes.summary_routes import router as note_summary_router
from app.platform.modules.backend_contract import BackendModuleEntry, RouterCodeContribution

courses_backend_entry = BackendModuleEntry(
    id="courses",
    routers=(
        RouterCodeContribution(
            id="course-calendars", router=course_calendar_router, tags=("course-calendars",)
        ),
        RouterCodeContribution(
            id="course-materials", router=course_source_router, tags=("course-materials",)
        ),
        RouterCodeContribution(
            id="course-note-prettify",
            router=note_prettify_router,
            tags=("course-note-prettify",),
        ),
        RouterCodeContribution(
            id="course-note-summaries",
            router=note_summary_router,
            tags=("course-note-summaries",),
        ),
        RouterCodeContribution(id="course-notes", router=note_router, tags=("course-notes",)),
        RouterCodeContribution(id="courses", router=course_router, tags=("courses",)),
    ),
)
