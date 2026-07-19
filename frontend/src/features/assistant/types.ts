export type AssistantMessageRole = "owner" | "assistant";
export type AssistantJobStatus =
  | "queued"
  | "preparing_context"
  | "running"
  | "validating"
  | "completed"
  | "failed";

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
}

export interface AssistantTurn {
  conversation: AssistantConversation;
  owner_message: AssistantMessage;
  assistant_message: AssistantMessage | null;
  job: AssistantJob;
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
