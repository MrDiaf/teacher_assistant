export type CourseStatus = "active" | "archived";
export type CourseOriginType = "manual";
export type CourseMaterialType = "literature" | "slides";
export type ExtractionStatus =
  | "not_started"
  | "queued"
  | "processing"
  | "completed"
  | "failed"
  | "unsupported";
export type CourseTab = "overview" | "notes" | "materials" | "calendar";

export interface CourseModel {
  id: string;
  name: string;
  course_code: string | null;
  description: string | null;
  term: string | null;
  color: string;
  status: CourseStatus;
  source_type: CourseOriginType;
  source_count: number;
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

export interface CourseSource {
  id: string;
  course_id: string;
  source_type: CourseMaterialType;
  display_name: string;
  original_filename: string;
  stored_filename: string;
  mime_type: string;
  file_size: number;
  external_id: string | null;
  extraction_status: ExtractionStatus;
  extraction_error: string | null;
  extracted_text_count: number;
  created_at: string;
  updated_at: string;
}

export interface SlideReferenceMutation {
  source_id: string;
  start_slide: number | null;
  end_slide: number | null;
  label: string | null;
}

export interface SlideReference extends SlideReferenceMutation {
  id: string;
  source_display_name: string;
  original_filename: string;
  created_at: string;
}

export interface CourseNote {
  id: string;
  course_id: string;
  title: string;
  body: string;
  slide_references: SlideReference[];
  created_at: string;
  updated_at: string;
}

export interface NoteMutation {
  title: string;
  body: string;
  slide_references: SlideReferenceMutation[];
}

export type NoteSummaryStatus =
  | "queued"
  | "running"
  | "validating"
  | "completed"
  | "failed";
export type SummaryOrigin = "note" | "slide" | "mixed";

export interface SummarySourceReference {
  note_id: string | null;
  source_id: string | null;
  slide: number | null;
}

export interface SummaryBullet {
  text: string;
  origin: SummaryOrigin;
  source_references: SummarySourceReference[];
}

export interface NoteSummary {
  id: string;
  note_id: string;
  model: string;
  status: NoteSummaryStatus;
  summary_json: { bullets: SummaryBullet[] } | null;
  note_content_hash: string;
  slide_content_hash: string;
  is_stale: boolean;
  safe_error: string | null;
  safe_error_code: string | null;
  created_at: string;
  updated_at: string;
}
