export type CourseStatus = "active" | "archived";
export type CourseSourceType = "manual";
export type CourseTab = "overview" | "notes" | "materials" | "calendar";

export interface CourseModel {
  id: string;
  name: string;
  course_code: string | null;
  description: string | null;
  term: string | null;
  color: string;
  status: CourseStatus;
  source_type: CourseSourceType;
  created_at: string;
  updated_at: string;
}

export interface CourseMutation {
  name: string;
  course_code: string | null;
  description: string | null;
  term: string | null;
  color: string;
}
