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
import type { CourseModel, CourseMutation } from "./types";

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

function jsonResponse(body: unknown, status = 200) {
  return new Response(status === 204 ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function installCourseApi(initialCourses: CourseModel[] = []) {
  let courses = initialCourses.map((course) => ({ ...course }));
  return vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? "GET";

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

  it("shows active and archived course cards and opens placeholder tabs", async () => {
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
      screen.getByRole("heading", { name: "Notes are coming next" }),
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
});
