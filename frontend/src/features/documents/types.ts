export interface DocumentTagSummary {
  id: string;
  name: string;
  color: string;
}

export interface DocumentTag extends DocumentTagSummary {
  project_count: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentProject {
  id: string;
  title: string;
  tags: DocumentTagSummary[];
  created_at: string;
  updated_at: string;
}
