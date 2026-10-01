export interface AiModelOption {
  id: string;
  label: string;
}

export interface AiModelList {
  default_model: string;
  models: AiModelOption[];
}

export interface AiAuthStatus {
  authenticated: boolean;
  auth_type: "chatgpt" | "api_key" | null;
  email: string | null;
  plan_type: string | null;
}

export interface AiDeviceLogin {
  login_id: string;
  verification_url: string;
  user_code: string;
  status: "pending" | "completed" | "failed";
  safe_error: string | null;
}

export interface DiagnosticExplanation {
  error_id: string;
  request_id: string;
  model: string;
  explained_at: string;
  plain_explanation: string;
  likely_cause: string;
  input_fixes: string[];
  application_improvements: string[];
  retry_is_safe: boolean;
}
