export type AssistantMessageRole = "owner" | "assistant";
export type AssistantJobStatus =
  | "queued"
  | "preparing_context"
  | "running"
  | "validating"
  | "awaiting_confirmation"
  | "completed"
  | "failed";

export type AssistantProposalStatus =
  | "awaiting_confirmation"
  | "confirmed"
  | "rejected"
  | "executing"
  | "completed"
  | "failed"
  | "expired";

export type ProposalOperation =
  | "create_calendar"
  | "update_calendar"
  | "create_event"
  | "update_event"
  | "delete_event";

export interface AssistantConversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface AssistantMessage {
  id: string;
  conversation_id: string;
  role: AssistantMessageRole;
  content: string;
  job_id: string | null;
  created_at: string;
}

export interface AssistantJob {
  id: string;
  conversation_id: string;
  owner_message_id: string;
  status: AssistantJobStatus;
  safe_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface AssistantConversationDetail extends AssistantConversation {
  messages: AssistantMessage[];
  jobs: AssistantJob[];
  proposals: AssistantProposal[];
}

export interface AssistantTurn {
  conversation: AssistantConversation;
  owner_message: AssistantMessage;
  assistant_message: AssistantMessage | null;
  job: AssistantJob;
  proposal: AssistantProposal | null;
}

export interface ProposalReviewItem {
  operation: ProposalOperation;
  title: string;
  calendar_id: string | null;
  calendar_name: string | null;
  event_id: string | null;
  event_title: string | null;
  previous: Record<string, unknown> | null;
  proposed: Record<string, unknown> | null;
  recurrence_scope: "occurrence" | "series" | null;
  occurrence_start_at: string | null;
  affected_events: number;
  warnings: string[];
}

export interface ProposalActionRecord {
  id: string;
  position: number;
  operation: ProposalOperation;
  target_calendar_id: string | null;
  target_event_id: string | null;
  requested_at: string;
  confirmed_at: string | null;
  executed_at: string | null;
  result: Record<string, unknown> | null;
  safe_error: string | null;
}

export interface AssistantProposal {
  id: string;
  job_id: string;
  conversation_id: string;
  status: AssistantProposalStatus;
  summary: string;
  actions: Array<Record<string, unknown> & { operation: ProposalOperation }>;
  review_items: ProposalReviewItem[];
  warnings: string[];
  affected_events: number;
  expires_at: string;
  confirmed_at: string | null;
  rejected_at: string | null;
  executed_at: string | null;
  result: Record<string, unknown> | null;
  safe_error: string | null;
  created_at: string;
  updated_at: string;
  action_records: ProposalActionRecord[];
}

export interface AssistantAuthStatus {
  authenticated: boolean;
  auth_type: "chatgpt" | "api_key" | null;
  email: string | null;
  plan_type: string | null;
}

export interface AssistantDeviceLogin {
  login_id: string;
  verification_url: string;
  user_code: string;
  status: "pending" | "completed" | "failed";
  safe_error: string | null;
}
