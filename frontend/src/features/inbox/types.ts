export type MailTlsMode = "implicit_tls" | "starttls";
export type MailConnectionState = "connected" | "reconnect_required" | "error";

export interface MailConnectionStatus {
  connected: boolean;
  status: MailConnectionState | null;
  host: string | null;
  port: number | null;
  tls_mode: MailTlsMode | null;
  mailbox: string | null;
  username: string | null;
  last_checked_at: string | null;
  last_success_at: string | null;
  next_check_at: string | null;
  safe_error_code: string | null;
  safe_error: string | null;
  source_warning: string | null;
  quarantined_count: number;
}

export interface MailConnectionInput {
  host: string;
  port: number;
  tls_mode: MailTlsMode;
  mailbox: string;
  username: string;
  password: string;
}

export interface MailCheckResult {
  imported_count: number;
  skipped_count: number;
  quarantined_count: number;
  status: MailConnectionStatus;
}

export interface MailListItem {
  id: string;
  subject: string;
  sender_name: string | null;
  sender_address: string;
  recipients: string[];
  source_date: string | null;
  ingested_at: string;
  attachment_count: number;
  omitted_attachment_count: number;
  is_read: boolean;
  is_archived: boolean;
  forwarded_unverified: boolean;
  source_label: "Mail";
}

export interface MailAddress {
  kind: "from" | "reply_to" | "to" | "cc";
  display_name: string | null;
  address: string;
  position: number;
}

export interface MailAttachment {
  id: string;
  original_filename: string;
  mime_type: string;
  file_size: number;
  status: "stored" | "omitted" | "cleanup_failed";
  omission_reason: string | null;
}

export interface MailMessage extends MailListItem {
  message_id: string | null;
  in_reply_to: string | null;
  thread_references: string[];
  body_text: string;
  body_html: string | null;
  addresses: MailAddress[];
  attachments: MailAttachment[];
}
