import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CoursesPage } from "./CoursesPage";
import type {
  CourseModel,
  CourseMutation,
  CourseNote,
  CourseSource,
  NoteMutation,
  NoteSummary,
  SlideReference,
} from "./types";

vi.mock("../ai/api", () => ({
  getAiModels: vi.fn(async () => ({
    default_model: "gpt-5.6-sol",
    models: [
      { id: "gpt-5.6-sol", label: "GPT-5.6 Sol · flagship" },
      { id: "gpt-5.6-terra", label: "GPT-5.6 Terra · balanced" },
    ],
  })),
}));

const now = new Date().toISOString();
const activeCourse: CourseModel = {
  id: "course-active",
  name: "Database Systems",
  course_code: "DAT101",
  description: "Relational data and query design",
  term: "Autumn 2026",
  color: "#29584c",
  status: "active",
  source_type: "manual",
  source_count: 0,
  calendar_count: 0,
  created_at: now,
  updated_at: now,
};
const archivedCourse: CourseModel = {
  ...activeCourse,
  id: "course-archived",
  name: "Introduction to Networks",
  course_code: "NET100",
  status: "archived",
};
const slideSource: CourseSource = {
  id: "slides-source",
  course_id: activeCourse.id,
  source_type: "slides",
  display_name: "Transactions deck",
  original_filename: "transactions.pptx",
  stored_filename: "original.pptx",
  mime_type:
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  file_size: 4096,
  external_id: null,
  extraction_status: "completed",
  extraction_error: null,
  extracted_text_count: 12,
  created_at: now,
  updated_at: now,
};
const literaturePdfSource: CourseSource = {
  ...slideSource,
  id: "literature-pdf-source",
  source_type: "literature",
  display_name: "Week one reading",
  original_filename: "week-one-reading.pdf",
  stored_filename: "original.pdf",
  mime_type: "application/pdf",
  file_size: 81920,
  extracted_text_count: 3,
};
const slidesPdfSource: CourseSource = {
  ...literaturePdfSource,
  id: "slides-pdf-source",
  source_type: "slides",
  display_name: "Lecture two handout",
  original_filename: "lecture-two-handout.pdf",
  extracted_text_count: 5,
};

function jsonResponse(body: unknown, status = 200) {
  return new Response(status === 204 ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function installCourseApi(
  initialCourses: CourseModel[] = [],
  initialSources: CourseSource[] = [],
  initialNotes: CourseNote[] = [],
) {
  let courses = initialCourses.map((course) => ({ ...course }));
  let sources = initialSources.map((source) => ({ ...source }));
  let notes = initialNotes.map((note) => ({
    ...note,
    slide_references: note.slide_references.map((reference) => ({
      ...reference,
    })),
  }));
  let summaries: Record<string, NoteSummary | null> = {};
  return vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    const parsedUrl = new URL(url, "http://teacher-assistant.test");

    if (url.endsWith("/api/v1/courses") && method === "GET") {
      return jsonResponse(courses);
    }
    if (url.endsWith("/api/v1/courses") && method === "POST") {
      const payload = JSON.parse(String(init?.body)) as CourseMutation;
      const created: CourseModel = {
        ...payload,
        id: "course-created",
        status: "active",
        source_type: "manual",
        source_count: 0,
        calendar_count: 0,
        created_at: now,
        updated_at: now,
      };
      courses = [created, ...courses];
      return jsonResponse(created, 201);
    }
    if (url.endsWith("/archive") && method === "POST") {
      const id = url.split("/").at(-2);
      const updated = { ...courses.find((course) => course.id === id)! };
      updated.status = "archived";
      courses = courses.map((course) => (course.id === id ? updated : course));
      return jsonResponse(updated);
    }
    if (url.endsWith("/restore") && method === "POST") {
      const id = url.split("/").at(-2);
      const updated = { ...courses.find((course) => course.id === id)! };
      updated.status = "active";
      courses = courses.map((course) => (course.id === id ? updated : course));
      return jsonResponse(updated);
    }

    if (
      parsedUrl.pathname.endsWith("/sources") &&
      parsedUrl.pathname.includes("/api/v1/courses/") &&
      method === "GET"
    ) {
      const courseId = parsedUrl.pathname.split("/").at(-2);
      return jsonResponse(
        sources.filter((source) => source.course_id === courseId),
      );
    }
    if (
      parsedUrl.pathname.endsWith("/sources") &&
      parsedUrl.pathname.includes("/api/v1/courses/") &&
      method === "POST"
    ) {
      const courseId = parsedUrl.pathname.split("/").at(-2)!;
      const file = init?.body as File;
      const sourceType = parsedUrl.searchParams.get("source_type") as
        | "literature"
        | "slides";
      const supported = !file.name.endsWith(".zip");
      const created: CourseSource = {
        id: `source-${sources.length + 1}`,
        course_id: courseId,
        source_type: sourceType,
        display_name: file.name.replace(/\.[^.]+$/, ""),
        original_filename: file.name,
        stored_filename: supported ? "original.txt" : "original.zip",
        mime_type: supported ? "text/plain" : "application/octet-stream",
        file_size: file.size,
        external_id: null,
        extraction_status: supported ? "completed" : "unsupported",
        extraction_error: supported
          ? null
          : "Text extraction is unavailable for this file type.",
        extracted_text_count: supported ? 1 : 0,
        created_at: now,
        updated_at: now,
      };
      sources = [created, ...sources];
      return jsonResponse(created, 201);
    }
    if (
      parsedUrl.pathname.includes("/api/v1/course-sources/") &&
      parsedUrl.pathname.endsWith("/retry-extraction") &&
      method === "POST"
    ) {
      const sourceId = parsedUrl.pathname.split("/").at(-2);
      const current = sources.find((source) => source.id === sourceId)!;
      const updated: CourseSource = {
        ...current,
        extraction_status: "completed",
        extraction_error: null,
        extracted_text_count: 1,
      };
      sources = sources.map((source) =>
        source.id === sourceId ? updated : source,
      );
      return jsonResponse(updated);
    }
    if (
      parsedUrl.pathname.includes("/api/v1/course-sources/") &&
      parsedUrl.pathname.endsWith("/content") &&
      method === "GET"
    ) {
      return new Response(new Uint8Array([0x25]), {
        status: 206,
        headers: {
          "Content-Type": "application/pdf",
          "Content-Range": "bytes 0-0/81920",
        },
      });
    }
    if (
      parsedUrl.pathname.includes("/api/v1/course-sources/") &&
      method === "DELETE"
    ) {
      const sourceId = parsedUrl.pathname.split("/").at(-1);
      sources = sources.filter((source) => source.id !== sourceId);
      return jsonResponse(undefined, 204);
    }

    if (
      parsedUrl.pathname.endsWith("/notes") &&
      parsedUrl.pathname.includes("/api/v1/courses/") &&
      method === "GET"
    ) {
      const courseId = parsedUrl.pathname.split("/").at(-2);
      return jsonResponse(notes.filter((note) => note.course_id === courseId));
    }
    if (
      parsedUrl.pathname.endsWith("/notes") &&
      parsedUrl.pathname.includes("/api/v1/courses/") &&
      method === "POST"
    ) {
      const courseId = parsedUrl.pathname.split("/").at(-2)!;
      const payload = JSON.parse(String(init?.body)) as NoteMutation;
      const created: CourseNote = {
        ...payload,
        id: `note-${notes.length + 1}`,
        course_id: courseId,
        slide_references: payload.slide_references.map(
          (reference, index): SlideReference => {
            const source = sources.find(
              (item) => item.id === reference.source_id,
            )!;
            return {
              ...reference,
              id: `reference-${notes.length + 1}-${index + 1}`,
              source_display_name: source.display_name,
              original_filename: source.original_filename,
              created_at: now,
            };
          },
        ),
        created_at: now,
        updated_at: now,
      };
      notes = [created, ...notes];
      return jsonResponse(created, 201);
    }
    if (
      parsedUrl.pathname.endsWith("/summary") &&
      parsedUrl.pathname.includes("/api/v1/notes/") &&
      method === "GET"
    ) {
      const noteId = parsedUrl.pathname.split("/").at(-2)!;
      return jsonResponse(summaries[noteId] ?? null);
    }
    if (
      parsedUrl.pathname.endsWith("/summaries") &&
      parsedUrl.pathname.includes("/api/v1/notes/") &&
      method === "POST"
    ) {
      const noteId = parsedUrl.pathname.split("/").at(-2)!;
      const note = notes.find((item) => item.id === noteId)!;
      const payload = JSON.parse(String(init?.body)) as { model: string };
      const slide = note.slide_references[0];
      const created: NoteSummary = {
        id: `summary-${noteId}`,
        note_id: noteId,
        model: payload.model,
        status: "completed",
        summary_json: {
          bullets: [
            {
              text: "The note connects atomicity with reliable transactions.",
              origin: slide ? "mixed" : "note",
              source_references: [
                {
                  note_id: noteId,
                  source_id: null,
                  slide: null,
                },
                ...(slide
                  ? [
                      {
                        note_id: null,
                        source_id: slide.source_id,
                        slide: slide.start_slide ?? 1,
                      },
                    ]
                  : []),
              ],
            },
          ],
        },
        note_content_hash: "a".repeat(64),
        slide_content_hash: "b".repeat(64),
        is_stale: false,
        safe_error: null,
        safe_error_code: null,
        created_at: now,
        updated_at: now,
      };
      summaries[noteId] = created;
      return jsonResponse(created, 201);
    }
    if (
      parsedUrl.pathname.includes("/api/v1/note-summaries/") &&
      parsedUrl.pathname.endsWith("/retry") &&
      method === "POST"
    ) {
      const summaryId = parsedUrl.pathname.split("/").at(-2);
      const summary = Object.values(summaries).find(
        (item) => item?.id === summaryId,
      )!;
      const completed = {
        ...summary,
        status: "completed" as const,
        safe_error: null,
        safe_error_code: null,
      };
      summaries[completed.note_id] = completed;
      return jsonResponse(completed);
    }
    if (parsedUrl.pathname.includes("/api/v1/notes/") && method === "PATCH") {
      const noteId = parsedUrl.pathname.split("/").at(-1);
      const payload = JSON.parse(String(init?.body)) as NoteMutation;
      const current = notes.find((note) => note.id === noteId)!;
      const updated: CourseNote = {
        ...current,
        ...payload,
        slide_references: payload.slide_references.map(
          (reference, index): SlideReference => {
            const source = sources.find(
              (item) => item.id === reference.source_id,
            )!;
            return {
              ...reference,
              id: `updated-reference-${index + 1}`,
              source_display_name: source.display_name,
              original_filename: source.original_filename,
              created_at: now,
            };
          },
        ),
        updated_at: now,
      };
      notes = notes.map((note) => (note.id === noteId ? updated : note));
      if (summaries[noteId!]) {
        summaries[noteId!] = { ...summaries[noteId!]!, is_stale: true };
      }
      return jsonResponse(updated);
    }
    if (parsedUrl.pathname.includes("/api/v1/notes/") && method === "DELETE") {
      const noteId = parsedUrl.pathname.split("/").at(-1);
      notes = notes.filter((note) => note.id !== noteId);
      delete summaries[noteId!];
      return jsonResponse(undefined, 204);
    }

    const courseId = url.split("/").at(-1);
    if (url.includes("/api/v1/courses/") && method === "PATCH") {
      const payload = JSON.parse(String(init?.body)) as CourseMutation;
      const updated = {
        ...courses.find((course) => course.id === courseId)!,
        ...payload,
        updated_at: now,
      };
      courses = courses.map((course) =>
        course.id === courseId ? updated : course,
      );
      return jsonResponse(updated);
    }
    if (url.includes("/api/v1/courses/") && method === "DELETE") {
      courses = courses.filter((course) => course.id !== courseId);
      notes = notes.filter((note) => note.course_id !== courseId);
      return jsonResponse(undefined, 204);
    }
    throw new Error(`Unhandled request: ${method} ${url}`);
  });
}

describe("CoursesPage", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", installCourseApi());
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("shows active and archived course cards and opens course tabs", async () => {
    vi.stubGlobal("fetch", installCourseApi([activeCourse, archivedCourse]));
    render(<CoursesPage />);

    expect(
      await screen.findByRole("heading", { name: "Active courses" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Archived courses" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Database Systems")).toBeInTheDocument();
    expect(screen.getByText("Introduction to Networks")).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: "Open Database Systems" }),
    );
    expect(
      screen.getByRole("heading", { name: "Database Systems" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Created manually")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "Notes" }));
    expect(
      await screen.findByRole("heading", {
        name: "Start your course notebook",
      }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Back to courses" }));
    expect(
      screen.getByRole("heading", { name: "Active courses" }),
    ).toBeInTheDocument();
  });

  it("shows an empty state and creates a manual course", async () => {
    const fetchMock = installCourseApi();
    vi.stubGlobal("fetch", fetchMock);
    render(<CoursesPage />);

    expect(
      await screen.findByRole("heading", { name: "Create your first course" }),
    ).toBeInTheDocument();
    fireEvent.click(
      screen.getAllByRole("button", { name: "Create course" })[0],
    );
    const dialog = screen.getByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Course name"), {
      target: { value: "Operating Systems" },
    });
    fireEvent.change(within(dialog).getByLabelText("Course code"), {
      target: { value: "OS201" },
    });
    fireEvent.change(within(dialog).getByLabelText("Term"), {
      target: { value: "Spring 2027" },
    });
    fireEvent.click(
      within(dialog).getByRole("button", { name: "Create course" }),
    );

    expect(
      await screen.findByRole("heading", { name: "Operating Systems" }),
    ).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/courses",
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining('"course_code":"OS201"'),
      }),
    );
  });

  it("edits, archives, restores, and explicitly deletes a course", async () => {
    const fetchMock = installCourseApi([activeCourse]);
    vi.stubGlobal("fetch", fetchMock);
    render(<CoursesPage />);
    await screen.findByText("Database Systems");

    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    const editDialog = screen.getByRole("dialog");
    fireEvent.change(within(editDialog).getByLabelText("Course name"), {
      target: { value: "Advanced Databases" },
    });
    fireEvent.click(
      within(editDialog).getByRole("button", { name: "Save changes" }),
    );
    expect(await screen.findByText("Advanced Databases")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Archive" }));
    await waitFor(() =>
      expect(
        within(
          screen
            .getByRole("heading", { name: "Archived courses" })
            .closest("section")!,
        ).getByText("Advanced Databases"),
      ).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByRole("button", { name: "Restore" }));
    await waitFor(() =>
      expect(
        within(
          screen
            .getByRole("heading", { name: "Active courses" })
            .closest("section")!,
        ).getByText("Advanced Databases"),
      ).toBeInTheDocument(),
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Open Advanced Databases" }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    const deleteDialog = screen.getByRole("alertdialog");
    expect(
      within(deleteDialog).getByText(
        /Calendars and calendar events are never deleted/,
      ),
    ).toBeInTheDocument();
    fireEvent.click(
      within(deleteDialog).getByRole("button", { name: "Delete course" }),
    );

    expect(
      await screen.findByRole("heading", { name: "Create your first course" }),
    ).toBeInTheDocument();
    expect(
      fetchMock.mock.calls.some(
        ([url, init]) =>
          String(url).endsWith("/api/v1/courses/course-active") &&
          init?.method === "DELETE",
      ),
    ).toBe(true);
  });

  it("shows a load error and retries safely", async () => {
    const successfulFetch = installCourseApi([activeCourse]);
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new Error("The server is unavailable."))
      .mockImplementation(successfulFetch);
    vi.stubGlobal("fetch", fetchMock);
    render(<CoursesPage />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The server is unavailable.",
    );
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Database Systems")).toBeInTheDocument();
  });

  it("uploads distinct material types and deletes only the confirmed source", async () => {
    const fetchMock = installCourseApi([activeCourse]);
    vi.stubGlobal("fetch", fetchMock);
    render(<CoursesPage />);

    await screen.findByText("Database Systems");
    fireEvent.click(
      screen.getByRole("button", { name: "Open Database Systems" }),
    );
    fireEvent.click(screen.getByRole("tab", { name: "Materials" }));

    expect(
      await screen.findByText("No literature uploaded yet."),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Upload literature"), {
      target: {
        files: [
          new File(["Normalization and indexes"], "database-notes.txt", {
            type: "text/plain",
          }),
        ],
      },
    });

    const literature = await screen.findByText("database-notes");
    const literatureCard = literature.closest("article")!;
    expect(within(literatureCard).getByText("Ready")).toBeInTheDocument();
    expect(
      within(literatureCard).getByText(/1 text section extracted/),
    ).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Upload slides"), {
      target: {
        files: [
          new File(["archive"], "lecture-assets.zip", {
            type: "application/zip",
          }),
        ],
      },
    });
    const slides = await screen.findByText("lecture-assets");
    const slidesCard = slides.closest("article")!;
    expect(
      within(slidesCard).getByText("Stored · extraction unavailable"),
    ).toBeInTheDocument();

    fireEvent.click(
      within(literatureCard).getByRole("button", { name: "Delete" }),
    );
    expect(
      within(literatureCard).getByText(/Other course materials are unaffected/),
    ).toBeInTheDocument();
    fireEvent.click(
      within(literatureCard).getByRole("button", {
        name: "Delete this file",
      }),
    );

    await waitFor(() =>
      expect(screen.queryByText("database-notes")).not.toBeInTheDocument(),
    );
    expect(screen.getByText("lecture-assets")).toBeInTheDocument();
  });

  it("opens Literature and Slides PDFs accessibly and restores focus", async () => {
    const successfulFetch = installCourseApi(
      [activeCourse],
      [literaturePdfSource, slidesPdfSource, slideSource],
    );
    let completeFirstProbe: ((response: Response) => void) | undefined;
    let firstProbe = true;
    const fetchMock = vi.fn(
      async (input: string | URL | Request, init?: RequestInit) => {
        if (
          String(input).endsWith(
            `/api/v1/course-sources/${literaturePdfSource.id}/content`,
          ) &&
          firstProbe
        ) {
          firstProbe = false;
          return await new Promise<Response>((resolve) => {
            completeFirstProbe = resolve;
          });
        }
        return successfulFetch(input, init);
      },
    );
    vi.stubGlobal("fetch", fetchMock);
    render(<CoursesPage />);

    await screen.findByText("Database Systems");
    fireEvent.click(
      screen.getByRole("button", { name: "Open Database Systems" }),
    );
    fireEvent.click(screen.getByRole("tab", { name: "Materials" }));

    const literatureCard = (
      await screen.findByText("Week one reading")
    ).closest("article")!;
    const openLiterature = within(literatureCard).getByRole("button", {
      name: "Open Week one reading PDF",
    });
    const directWindowLink = within(literatureCard).getByRole("link", {
      name: "Open Week one reading PDF in new window",
    });
    expect(directWindowLink).toHaveAttribute(
      "href",
      `/api/v1/course-sources/${literaturePdfSource.id}/content`,
    );
    expect(directWindowLink).toHaveAttribute("target", "_blank");
    expect(directWindowLink).toHaveAttribute(
      "rel",
      expect.stringContaining("noopener"),
    );
    expect(directWindowLink).toHaveAttribute(
      "rel",
      expect.stringContaining("noreferrer"),
    );

    openLiterature.focus();
    fireEvent.click(openLiterature);
    let dialog = screen.getByRole("dialog");
    expect(within(dialog).getByRole("status")).toHaveTextContent("Opening PDF");
    completeFirstProbe?.(
      new Response(new Uint8Array([0x25]), {
        status: 206,
        headers: { "Content-Type": "application/pdf" },
      }),
    );
    expect(
      await within(dialog).findByTitle("PDF viewer for Week one reading"),
    ).toHaveAttribute(
      "data",
      `/api/v1/course-sources/${literaturePdfSource.id}/content`,
    );
    expect(
      within(dialog).getByText("This browser cannot embed PDFs."),
    ).toBeInTheDocument();

    fireEvent.click(
      within(dialog).getByRole("button", { name: "Close PDF viewer" }),
    );
    await waitFor(() => expect(openLiterature).toHaveFocus());

    const slidesCard = screen
      .getByText("Lecture two handout")
      .closest("article")!;
    fireEvent.click(
      within(slidesCard).getByRole("button", {
        name: "Open Lecture two handout PDF",
      }),
    );
    dialog = screen.getByRole("dialog");
    expect(
      await within(dialog).findByTitle("PDF viewer for Lecture two handout"),
    ).toBeInTheDocument();

    const nonPdfCard = screen
      .getByText("Transactions deck")
      .closest("article")!;
    expect(
      within(nonPdfCard).queryByRole("button", { name: /Open .* PDF/ }),
    ).not.toBeInTheDocument();
    expect(
      within(nonPdfCard).queryByRole("link", { name: /new window/ }),
    ).not.toBeInTheDocument();
  });

  it("shows a safe PDF API error and can retry the viewer", async () => {
    const successfulFetch = installCourseApi(
      [activeCourse],
      [literaturePdfSource],
    );
    let probeAttempts = 0;
    const fetchMock = vi.fn(
      async (input: string | URL | Request, init?: RequestInit) => {
        if (
          String(input).endsWith(
            `/api/v1/course-sources/${literaturePdfSource.id}/content`,
          ) &&
          probeAttempts++ === 0
        ) {
          return jsonResponse(
            {
              code: "course_source_content_unavailable",
              message:
                "The stored PDF is missing, unreadable, or no longer matches its source record.",
            },
            409,
          );
        }
        return successfulFetch(input, init);
      },
    );
    vi.stubGlobal("fetch", fetchMock);
    render(<CoursesPage />);

    await screen.findByText("Database Systems");
    fireEvent.click(
      screen.getByRole("button", { name: "Open Database Systems" }),
    );
    fireEvent.click(screen.getByRole("tab", { name: "Materials" }));
    const card = (await screen.findByText("Week one reading")).closest(
      "article",
    )!;
    fireEvent.click(
      within(card).getByRole("button", { name: "Open Week one reading PDF" }),
    );

    const dialog = screen.getByRole("dialog");
    expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      "The stored PDF is missing, unreadable, or no longer matches its source record.",
    );
    fireEvent.click(within(dialog).getByRole("button", { name: "Try again" }));
    expect(
      await within(dialog).findByTitle("PDF viewer for Week one reading"),
    ).toBeInTheDocument();
  });

  it("asks the Assistant to explain a sanitized material error", async () => {
    const successfulFetch = installCourseApi([activeCourse]);
    const fetchMock = vi.fn(
      async (input: string | URL | Request, init?: RequestInit) => {
        const url = String(input);
        const method = init?.method ?? "GET";
        if (
          url.includes(`/api/v1/courses/${activeCourse.id}/sources?`) &&
          method === "POST"
        ) {
          return jsonResponse(
            {
              error_id: "diagnostic-error-1",
              code: "course_source_file_too_large",
              message: "The course file exceeds the 25 MB upload limit.",
              details: {
                file_type: "application/pdf",
                maximum_size_mb: 25,
              },
              request_id: "request-1",
            },
            413,
          );
        }
        if (
          url.endsWith("/api/v1/assistant/errors/diagnostic-error-1/explain") &&
          method === "POST"
        ) {
          return jsonResponse({
            error_id: "diagnostic-error-1",
            request_id: "request-1",
            model: "gpt-5.6-sol",
            explained_at: now,
            plain_explanation:
              "The selected file is larger than the upload limit.",
            likely_cause: "Its size exceeds 25 MB.",
            input_fixes: ["Choose a smaller or compressed PDF."],
            application_improvements: [
              "Show the file-size limit beside the picker.",
            ],
            retry_is_safe: true,
          });
        }
        return successfulFetch(input, init);
      },
    );
    vi.stubGlobal("fetch", fetchMock);
    render(<CoursesPage />);

    await screen.findByText("Database Systems");
    fireEvent.click(
      screen.getByRole("button", { name: "Open Database Systems" }),
    );
    fireEvent.click(screen.getByRole("tab", { name: "Materials" }));
    await screen.findByText("No literature uploaded yet.");
    fireEvent.change(screen.getByLabelText("Upload literature"), {
      target: {
        files: [
          new File(["too large"], "oversized.pdf", {
            type: "application/pdf",
          }),
        ],
      },
    });

    expect(
      await screen.findByText(
        "The course file exceeds the 25 MB upload limit.",
      ),
    ).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", {
        name: "Ask Assistant about this error",
      }),
    );

    expect(
      await screen.findByRole("region", {
        name: "Assistant error explanation",
      }),
    ).toHaveTextContent("Choose a smaller or compressed PDF.");
    expect(
      screen.getByText("Possible application improvements"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Show the file-size limit beside the picker."),
    ).toBeInTheDocument();
    const explainCall = fetchMock.mock.calls.find(([url]) =>
      String(url).endsWith(
        "/api/v1/assistant/errors/diagnostic-error-1/explain",
      ),
    );
    expect(JSON.parse(String(explainCall?.[1]?.body))).toEqual({});
  });

  it("creates, edits, links, and explicitly deletes a course note", async () => {
    const markdown = [
      "# Serializable",
      "",
      "Avoid **write skew**, _dirty reads_, and `unsafe defaults`.",
      "",
      "> Confirm the isolation level.",
      "",
      "<script>window.noteXss = true</script>",
    ].join("\n");
    const fetchMock = installCourseApi([activeCourse], [slideSource]);
    vi.stubGlobal("fetch", fetchMock);
    render(<CoursesPage />);

    await screen.findByText("Database Systems");
    fireEvent.click(
      screen.getByRole("button", { name: "Open Database Systems" }),
    );
    fireEvent.click(screen.getByRole("tab", { name: "Notes" }));
    await screen.findByRole("heading", { name: "Start your course notebook" });

    fireEvent.click(screen.getAllByRole("button", { name: "Create note" })[0]);
    let dialog = screen.getByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Note title"), {
      target: { value: "Isolation levels" },
    });
    fireEvent.change(within(dialog).getByLabelText("Note body"), {
      target: { value: markdown },
    });
    fireEvent.click(
      within(dialog).getByRole("button", { name: "Add reference" }),
    );
    fireEvent.change(within(dialog).getByLabelText("Slide deck 1"), {
      target: { value: slideSource.id },
    });
    fireEvent.change(within(dialog).getByLabelText("Start slide 1"), {
      target: { value: "2" },
    });
    fireEvent.change(within(dialog).getByLabelText("End slide 1"), {
      target: { value: "4" },
    });
    fireEvent.change(within(dialog).getByLabelText("Reference label 1"), {
      target: { value: "Key concepts" },
    });
    fireEvent.click(
      within(dialog).getByRole("button", { name: "Create note" }),
    );

    const title = await screen.findByRole("heading", {
      name: "Isolation levels",
    });
    let noteCard = title.closest("article")!;
    expect(
      within(noteCard).getByRole("heading", {
        level: 4,
        name: "Serializable",
      }),
    ).toBeInTheDocument();
    expect(within(noteCard).getByText("write skew").tagName).toBe("STRONG");
    expect(within(noteCard).getByText("dirty reads").tagName).toBe("EM");
    expect(noteCard.querySelector("script")).toBeNull();
    expect(noteCard).toHaveTextContent(
      "<script>window.noteXss = true</script>",
    );
    expect(within(noteCard).getByText(/Transactions deck/)).toBeInTheDocument();
    expect(within(noteCard).getByText("Slides 2–4")).toBeInTheDocument();
    expect(within(noteCard).getByText(/Key concepts/)).toBeInTheDocument();

    fireEvent.click(within(noteCard).getByRole("button", { name: "Edit" }));
    dialog = screen.getByRole("dialog");
    expect(within(dialog).getByLabelText("Note body")).toHaveValue(markdown);
    fireEvent.change(within(dialog).getByLabelText("Note title"), {
      target: { value: "Serializable isolation" },
    });
    fireEvent.click(
      within(dialog).getByRole("button", { name: "Remove reference 1" }),
    );
    fireEvent.click(
      within(dialog).getByRole("button", { name: "Save changes" }),
    );

    const updatedTitle = await screen.findByRole("heading", {
      name: "Serializable isolation",
    });
    noteCard = updatedTitle.closest("article")!;
    expect(
      within(noteCard).getByText("0 slide references"),
    ).toBeInTheDocument();

    fireEvent.click(within(noteCard).getByRole("button", { name: "Delete" }));
    expect(
      within(noteCard).getByText(/Slide files are unaffected/),
    ).toBeInTheDocument();
    fireEvent.click(
      within(noteCard).getByRole("button", { name: "Delete note" }),
    );
    expect(
      await screen.findByRole("heading", {
        name: "Start your course notebook",
      }),
    ).toBeInTheDocument();
  });

  it("selects an allowed model and shows accessible summary provenance and staleness", async () => {
    const linkedReference: SlideReference = {
      id: "reference-summary",
      source_id: slideSource.id,
      source_display_name: slideSource.display_name,
      original_filename: slideSource.original_filename,
      start_slide: 2,
      end_slide: 4,
      label: "Core concepts",
      created_at: now,
    };
    const note: CourseNote = {
      id: "note-summary",
      course_id: activeCourse.id,
      title: "Transaction notes",
      body: "Atomicity keeps transaction changes together.",
      slide_references: [linkedReference],
      created_at: now,
      updated_at: now,
    };
    const fetchMock = installCourseApi([activeCourse], [slideSource], [note]);
    vi.stubGlobal("fetch", fetchMock);
    render(<CoursesPage />);

    await screen.findByText("Database Systems");
    fireEvent.click(
      screen.getByRole("button", { name: "Open Database Systems" }),
    );
    fireEvent.click(screen.getByRole("tab", { name: "Notes" }));
    const summaryRegion = await screen.findByRole("region", {
      name: "AI summary for Transaction notes",
    });

    fireEvent.change(screen.getByLabelText("Summary model"), {
      target: { value: "gpt-5.6-terra" },
    });
    fireEvent.click(
      within(summaryRegion).getByRole("button", {
        name: "Generate summary",
      }),
    );

    expect(
      await within(summaryRegion).findByText("From note + slides"),
    ).toBeInTheDocument();
    expect(
      within(summaryRegion).getByText(
        "The note connects atomicity with reliable transactions.",
      ),
    ).toBeInTheDocument();
    expect(
      within(summaryRegion).getByText(/Transactions deck, slide 2/),
    ).toBeInTheDocument();
    const summaryCall = fetchMock.mock.calls.find(
      ([url, init]) =>
        String(url).endsWith("/api/v1/notes/note-summary/summaries") &&
        init?.method === "POST",
    );
    expect(JSON.parse(String(summaryCall?.[1]?.body))).toEqual({
      model: "gpt-5.6-terra",
    });

    fireEvent.click(
      within(summaryRegion.closest("article")!).getByRole("button", {
        name: "Edit",
      }),
    );
    const dialog = screen.getByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Note body"), {
      target: { value: "Changed transaction notes." },
    });
    fireEvent.click(
      within(dialog).getByRole("button", { name: "Save changes" }),
    );
    expect(
      await screen.findByText(
        "This summary is stale because the note or linked slide text changed.",
      ),
    ).toBeInTheDocument();
  });
});
