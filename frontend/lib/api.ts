export const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";
const AUTH_STORAGE_KEY = "omni_auth_session";

export type AuthUser = {
  user_id: string;
  email: string;
  display_name: string;
  role: "user" | "admin" | string;
  role_label: string;
  disabled?: boolean;
};

export type AuthSession = {
  access_token: string;
  token_type: string;
  user: AuthUser;
};

export type LoginResponse = AuthSession;

export type Citation = {
  title: string | null;
  source_url: string;
  document_type: string;
  chunk_id: string | null;
  score: number;
  preview: string;
  snippet?: string | null;
  full_text?: string | null;
  chunk_text_full?: string | null;
  preview_text?: string | null;
  section_heading?: string | null;
  context_before?: string | null;
  context_after?: string | null;
  usage?: "cited" | "supporting" | "retrieval_debug" | string;
  citation_index?: number | null;
  relevance_reason?: string;
  used_in_answer?: boolean;
};

export type RagResponse = {
  answer: string;
  citations: Citation[];
  debug_retrieval?: Citation[];
  retrieval: {
    top_k: number;
    collection: string;
    embedding_model: string;
  };
  metadata: {
    latency_ms: number;
    mode: string;
    memory_items: number;
  };
};

export type AssistantSource = Record<string, any> & {
  title?: string | null;
  source_url?: string;
  document_type?: string;
  chunk_id?: string | null;
  score?: number;
  preview?: string;
  snippet?: string | null;
  full_text?: string | null;
  chunk_text_full?: string | null;
  preview_text?: string | null;
  section_heading?: string | null;
  context_before?: string | null;
  context_after?: string | null;
  type?: string;
  usage?: "cited" | "supporting" | "retrieval_debug" | string;
  citation_index?: number | null;
  relevance_reason?: string;
  used_in_answer?: boolean;
};

export type AssistantChatResponse = {
  answer: string;
  intent: string;
  sources: AssistantSource[];
  actions: string[];
  memory_used: boolean;
  metadata: {
    latency_ms: number;
    route: string[];
    [key: string]: any;
  };
};

export type FeedbackReason =
  | "wrong_answer"
  | "outdated_data"
  | "missing_source"
  | "bad_citation"
  | "bad_asr"
  | "bad_tts"
  | "irrelevant_retrieval"
  | "too_slow"
  | "other";

export type FeedbackRecord = {
  feedback_id: string;
  user_id: string;
  session_id: string | null;
  message_id: string | null;
  query: string;
  answer: string;
  intent: string;
  route: string[];
  sources: AssistantSource[];
  rating: "up" | "down";
  reason: FeedbackReason;
  correction: string | null;
  status: string;
  severity: string;
  created_at: string;
  updated_at: string | null;
  admin_note: string;
  diagnostics: Record<string, any>;
};

export type FeedbackSummary = {
  total: number;
  by_rating: Record<string, number>;
  by_status: Record<string, number>;
  by_reason: Record<string, number>;
  by_severity: Record<string, number>;
  by_intent: Record<string, number>;
  top_problem_sources: Array<Record<string, any>>;
  top_failed_queries: Array<Record<string, any>>;
  recommended_actions: string[];
};

export type JobRecord = {
  job_id: string;
  job_type: string;
  status: string;
  source: string;
  source_id: string | null;
  payload: Record<string, any>;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
  result: Record<string, any>;
};

export type VoiceChatResponse = {
  transcript: string;
  answer: string;
  spoken_answer: string;
  intent: string;
  sources: AssistantSource[];
  actions: string[];
  memory_used: boolean;
  audio_url: string;
  metadata: Record<string, any>;
};

export type FeatureSummary = {
  total_documents: number;
  total_chunks: number;
  chunks_by_document_type: Record<string, number>;
  top_keywords: Record<string, number>;
  top_domains: Record<string, number>;
  average_chunk_length: number;
  empty_or_skipped_count: number;
  skipped_duplicate_exact_sources?: number;
  input_documents?: number;
  source_path?: string;
};

export type QaReports = {
  reports: Record<string, any>;
  available_reports: string[];
};

export type AdminDocument = {
  document_id: string;
  title: string | null;
  document_type: string;
  source_url: string;
  domain?: string;
  source_path: string;
  text_length: number;
  content_hash: string;
  published_date: string | null;
  language: string;
};

export type AdminChunk = {
  chunk_id: string;
  document_id: string;
  title: string | null;
  document_type: string;
  source_url: string;
  domain: string;
  source_path: string | null;
  chunk_index: number | null;
  text: string;
  preview: string;
  chunk_text_full?: string;
  preview_text?: string;
  section_heading?: string;
  context_before?: string;
  context_after?: string;
  text_length: number;
  character_start: number | null;
  character_end: number | null;
  content_hash: string | null;
  keyword_hints: string[];
  features: Record<string, any>;
  metadata: Record<string, any>;
  freshness_score: number | null;
  authority_score: number | null;
  boilerplate_score?: number | null;
  menu_density_score?: number | null;
  content_quality_score?: number | null;
};

export type AdminDocumentDetail = {
  document: AdminDocument & {
    text: string;
    text_preview: string;
    headings: string[];
    links: Array<Record<string, any>>;
    tables: Array<Record<string, any>>;
    metadata: Record<string, any>;
  };
  chunks: AdminChunk[];
  chunk_count: number;
  source_path: string;
  chunks_path: string;
};

export type SourceHealth = {
  domain: string;
  document_count: number;
  chunk_count: number;
  document_types: Record<string, number>;
  stale_or_unknown_documents: number;
  duplicate_content_hashes: number;
  average_freshness_score: number;
  average_authority_score: number;
  status: string;
};

export type MissingKnowledgeIndicator = {
  label: string;
  count: number;
  severity: string;
  action: string;
};

export type AdminSystemSummary = {
  health: {
    status: string;
    qdrant: string;
    llm: string;
    qdrant_points: number;
    collection: string;
  };
  data: {
    total_documents: number;
    total_chunks: number;
    qdrant_points: number;
    chunks_by_document_type: Record<string, number>;
    top_domains: Array<{ domain: string; count: number }>;
    average_chunk_length: number;
    empty_or_skipped_count: number;
    duplicate_content_hash_count: number;
    stale_or_unknown_date_count: number;
    unknown_chunk_count: number;
    source_health: SourceHealth[];
    missing_knowledge_indicators: MissingKnowledgeIndicator[];
  };
  qa: {
    data_quality: Record<string, any>;
    retrieval_eval: Record<string, any>;
    rag_eval: Record<string, any>;
    feedback_eval: Record<string, any>;
  };
  feedback: FeedbackSummary;
  jobs: Record<string, number>;
};

export type DataLayerSummary = {
  layers: Record<string, Record<string, any>>;
  latest_data_version: Record<string, any>;
  schema_registry: Record<string, any>;
  lineage: Record<string, any>;
  data_quality: Record<string, any>;
  file_ingestion?: Record<string, any>;
  source_domain_counts: Record<string, number>;
  document_type_counts: Record<string, number>;
  governance: Record<string, any>;
};

export type MemoryRecord = {
  memory_id: string;
  user_id: string;
  memory_type: string;
  content: string;
  importance: number;
  source: string;
  created_at: string;
  updated_at: string | null;
  metadata: Record<string, any>;
};

export type TaskRecord = {
  task_id: string;
  user_id: string;
  title: string;
  due_date: string | null;
  priority: string;
  status: string;
  source_text: string | null;
  created_at: string;
  updated_at: string | null;
  metadata: Record<string, any>;
};

export type MemorySummary = {
  long_term_memories_count: number;
  tasks_count: number;
  recent_session_count: number;
  storage_mode: Record<string, string>;
  recent_memories: MemoryRecord[];
  upcoming_tasks: TaskRecord[];
};

export type GoogleStatus = {
  credentials_available: boolean;
  google_libraries_available: boolean;
  mode: string;
  client_secret_path: string | null;
  scopes: string[];
  read_only: boolean;
};

export type GoogleLoginStatus = {
  configured: boolean;
  scopes: string[];
  redirect_uri: string;
  message: string;
};

export type GoogleIntegrationStatus = {
  google_login_configured: boolean;
  google_login_email?: string | null;
  gmail_connected: boolean;
  calendar_connected: boolean;
  gmail_account_email?: string | null;
  calendar_account_email?: string | null;
  gmail_account_mismatch?: boolean;
  calendar_account_mismatch?: boolean;
  gmail_last_sync_at?: string | null;
  calendar_last_sync_at?: string | null;
  required_scopes: {
    login: string[];
    gmail_readonly: string[];
    calendar_readonly: string[];
  };
};

export type SyncResponse = {
  user_id: string;
  mode: string;
  raw_path: string;
  processed_path: string;
  features_path: string | null;
  records_synced: number;
  connected: boolean;
  message?: string | null;
  source_mode: string;
  metadata: Record<string, any>;
  calendar_connected?: boolean | null;
  calendar_count?: number | null;
  calendars?: CalendarInfo[] | null;
  events_count?: number | null;
  today_count?: number | null;
  date_range?: Record<string, string> | null;
  events?: Array<Record<string, any>> | null;
};

export type CalendarInfo = {
  id: string;
  summary: string;
  description?: string;
  primary?: boolean;
  selected?: boolean;
  accessRole?: string;
  backgroundColor?: string;
  timeZone?: string;
  is_holiday?: boolean;
  is_classroom?: boolean;
};

export type CalendarListResponse = {
  connected: boolean;
  calendars: CalendarInfo[];
};

export type GmailSummary = {
  user_id: string;
  total?: number;
  total_messages: number;
  unread?: number;
  unread_count: number;
  read?: number;
  read_count?: number;
  important?: number;
  important_count: number;
  noise_ignored?: number;
  noise_count: number;
  top_senders: Record<string, number>;
  recent_messages: Array<Record<string, any>>;
  source_mode: string;
};

export type CalendarToday = {
  user_id: string;
  date: string;
  events: Array<Record<string, any>>;
  source_mode: string;
};

export type DailyBriefing = {
  user_id: string;
  date: string;
  summary: string;
  important_emails: Array<Record<string, any>>;
  ignored_noise_count: number;
  today_events: Array<Record<string, any>>;
  email_summary: GmailSummary;
  extracted_email_tasks: Array<Record<string, any>>;
  tasks: Array<Record<string, any>>;
  task_memory: Array<Record<string, any>>;
  priorities: string[];
  institutional_reminders: Array<Record<string, string>>;
  generated_at: string;
  metadata: Record<string, any>;
};

export type SmartBriefing = {
  briefing_id: string;
  user_id: string;
  generated_at: string;
  headline: string;
  morning_report: string;
  top_priorities: Array<Record<string, any>>;
  upcoming_events: Array<Record<string, any>>;
  important_emails: Array<Record<string, any>>;
  suggested_actions: Array<Record<string, any>>;
  project_updates: Array<Record<string, any>>;
  ignored_noise_count: number;
  sources: Array<Record<string, any>>;
  metadata: Record<string, any>;
};

export type KnowledgeSummary = {
  user_id: string;
  node_count: number;
  edge_count: number;
  node_counts: Record<string, number>;
  edge_counts: Record<string, number>;
  top_people: Array<Record<string, any>>;
  top_projects: Array<Record<string, any>>;
  recent_deadlines: Array<Record<string, any>>;
  metadata: Record<string, any>;
};

export type KnowledgeNode = {
  id: string;
  type: string;
  label: string;
  metadata: Record<string, any>;
  source_count: number;
  node_id?: string;
  node_type?: string;
  properties?: Record<string, any>;
};

export type KnowledgeEdge = {
  id: string;
  source: string;
  target: string;
  type: string;
  weight: number;
  metadata: Record<string, any>;
  edge_id?: string;
  source_id?: string;
  target_id?: string;
  edge_type?: string;
  properties?: Record<string, any>;
};

export type KnowledgeGraph = {
  user_id: string;
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
  summary: KnowledgeSummary & {
    filters?: Record<string, any>;
  };
  metadata: Record<string, any>;
};

export type KnowledgeGraphFilters = {
  nodeType?: string;
  edgeType?: string;
  query?: string;
  limit?: number;
};

export type ActionDraft = {
  draft_id: string;
  user_id: string;
  draft_type: "meeting_prep" | "report" | "slides" | "email_draft" | string;
  title: string;
  content: string;
  format: "markdown" | "text" | "json" | string;
  sources: Array<Record<string, any>>;
  created_at: string;
  metadata: Record<string, any>;
};

export async function login(email: string, password: string): Promise<LoginResponse> {
  return postJson<LoginResponse>("/api/auth/login", { email, password }, { skipAuth: true });
}

export async function logout(): Promise<{ ok: boolean }> {
  return postJson<{ ok: boolean }>("/api/auth/logout", {});
}

export async function fetchMe(): Promise<{ authenticated: boolean; user: AuthUser | null }> {
  return fetchJson("/api/auth/me");
}

export async function fetchMeWithToken(token: string): Promise<{ authenticated: boolean; user: AuthUser | null }> {
  const response = await fetch(`${BACKEND_URL}/api/auth/me`, {
    cache: "no-store",
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!response.ok) {
    throw new Error(`Backend API error ${response.status}`);
  }
  return response.json();
}

export async function postRagQuery(params: {
  query: string;
  topK: number;
  useLlm: boolean;
  userId?: string;
  sessionId?: string;
  includeMemory?: boolean;
}): Promise<RagResponse> {
  const response = await fetch(`${BACKEND_URL}/api/rag/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({
      query: params.query,
      top_k: params.topK,
      use_llm: params.useLlm,
      user_id: params.userId ?? authUserId(),
      session_id: params.sessionId,
      include_memory: params.includeMemory ?? true
    })
  });
  if (!response.ok) {
    throw new Error(`RAG API error ${response.status}`);
  }
  return response.json();
}

export async function postAssistantChat(params: {
  message: string;
  userId?: string;
  role?: string;
  sessionId?: string;
  includeMemory?: boolean;
  useMockGoogle?: boolean;
}): Promise<AssistantChatResponse> {
  return postJson<AssistantChatResponse>("/api/assistant/chat", {
    user_id: params.userId ?? authUserId(),
    role: params.role,
    session_id: params.sessionId,
    message: params.message,
    include_memory: params.includeMemory ?? true,
    use_mock_google: params.useMockGoogle ?? false
  });
}

export async function submitFeedback(params: {
  userId?: string;
  sessionId?: string;
  messageId?: string;
  query: string;
  answer: string;
  intent: string;
  route: string[];
  sources: AssistantSource[];
  rating: "up" | "down";
  reason?: FeedbackReason;
  correction?: string;
  diagnostics?: Record<string, any>;
}) {
  return postJson<FeedbackRecord>("/api/feedback", {
    user_id: params.userId ?? authUserId(),
    session_id: params.sessionId,
    message_id: params.messageId,
    query: params.query,
    answer: params.answer,
    intent: params.intent,
    route: params.route,
    sources: params.sources,
    rating: params.rating,
    reason: params.reason,
    correction: params.correction || null,
    diagnostics: params.diagnostics
  });
}

export async function postVoiceChat(params: {
  audio: Blob;
  filename?: string;
  userId?: string;
  sessionId?: string;
  includeMemory?: boolean;
  useMockGoogle?: boolean;
  voiceMode?: string;
}): Promise<VoiceChatResponse> {
  const form = new FormData();
  form.append("file", params.audio, params.filename ?? "voice.webm");
  form.append("user_id", params.userId ?? authUserId());
  if (params.sessionId) form.append("session_id", params.sessionId);
  form.append("include_memory", String(params.includeMemory ?? true));
  form.append("use_mock_google", String(params.useMockGoogle ?? false));
  form.append("voice_mode", params.voiceMode ?? "push_to_talk");
  const response = await fetch(`${BACKEND_URL}/api/voice/chat`, {
    method: "POST",
    headers: authHeaders(),
    body: form
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Voice API error ${response.status}: ${detail}`);
  }
  return response.json();
}

export async function fetchFeatureSummary(): Promise<FeatureSummary> {
  return fetchJson("/api/admin/feature-summary");
}

export async function fetchQaReports(): Promise<QaReports> {
  return fetchJson("/api/admin/qa-reports");
}

export async function fetchSystemSummary(): Promise<AdminSystemSummary> {
  return fetchJson("/api/admin/system-summary");
}

export async function fetchDataLayerSummary(): Promise<DataLayerSummary> {
  return fetchJson("/api/admin/data-layer-summary");
}

export async function fetchDocuments(params: { q?: string; documentType?: string; domain?: string; limit?: number }) {
  const search = new URLSearchParams();
  if (params.q) search.set("q", params.q);
  if (params.documentType) search.set("document_type", params.documentType);
  if (params.domain) search.set("domain", params.domain);
  if (params.limit) search.set("limit", String(params.limit));
  return fetchJson<{ total: number; count: number; documents: AdminDocument[]; source_path: string }>(
    `/api/admin/documents?${search.toString()}`
  );
}

export async function fetchDocumentDetail(documentId: string) {
  return fetchJson<AdminDocumentDetail>(`/api/admin/document/${encodeURIComponent(documentId)}`);
}

export async function fetchChunks(params: {
  documentType?: string;
  sourceUrl?: string;
  domain?: string;
  keyword?: string;
  limit?: number;
}) {
  const search = new URLSearchParams();
  if (params.documentType) search.set("document_type", params.documentType);
  if (params.sourceUrl) search.set("source_url", params.sourceUrl);
  if (params.domain) search.set("domain", params.domain);
  if (params.keyword) search.set("keyword", params.keyword);
  if (params.limit) search.set("limit", String(params.limit));
  return fetchJson<{ total: number; count: number; chunks: AdminChunk[]; source_path: string }>(
    `/api/admin/chunks?${search.toString()}`
  );
}

export async function fetchFeedback(params: {
  status?: string;
  reason?: string;
  severity?: string;
  intent?: string;
  rating?: string;
  limit?: number;
} = {}) {
  const search = new URLSearchParams();
  if (params.status && params.status !== "all") search.set("status", params.status);
  if (params.reason && params.reason !== "all") search.set("reason", params.reason);
  if (params.severity && params.severity !== "all") search.set("severity", params.severity);
  if (params.intent && params.intent !== "all") search.set("intent", params.intent);
  if (params.rating && params.rating !== "all") search.set("rating", params.rating);
  search.set("limit", String(params.limit ?? 50));
  return fetchJson<{ count: number; feedback: FeedbackRecord[] }>(`/api/admin/feedback?${search.toString()}`);
}

export async function fetchFeedbackSummary() {
  return fetchJson<FeedbackSummary>("/api/admin/feedback/summary");
}

export async function updateFeedback(feedbackId: string, params: { status?: string; admin_note?: string }) {
  return patchJson<FeedbackRecord>(`/api/admin/feedback/${feedbackId}`, params);
}

export async function promoteFeedbackToEval(feedbackId: string) {
  return postJson<{ feedback_id: string; eval_path: string; promoted: boolean }>(
    `/api/admin/feedback/${feedbackId}/promote-to-eval`,
    {}
  );
}

export async function queueFeedbackReindex(feedbackId: string) {
  return postJson<{ feedback_id: string; queue_path: string; status: string; queued: boolean }>(
    `/api/admin/feedback/${feedbackId}/queue-reindex`,
    {}
  );
}

export async function queueFeedbackRecrawl(feedbackId: string) {
  return postJson<{ feedback_id: string; queue_path: string; status: string; queued: boolean }>(
    `/api/admin/feedback/${feedbackId}/queue-recrawl`,
    {}
  );
}

export async function fetchJobs(params: { status?: string; jobType?: string; source?: string; limit?: number } = {}) {
  const search = new URLSearchParams();
  if (params.status && params.status !== "all") search.set("status", params.status);
  if (params.jobType && params.jobType !== "all") search.set("job_type", params.jobType);
  if (params.source && params.source !== "all") search.set("source", params.source);
  search.set("limit", String(params.limit ?? 50));
  return fetchJson<{ count: number; jobs: JobRecord[] }>(`/api/admin/jobs?${search.toString()}`);
}

export async function runNextJob(dryRun = false) {
  return postJson<{ ran: number; jobs: JobRecord[]; message: string }>(`/api/admin/jobs/run-next?dry_run=${dryRun}`, {});
}

export async function runAllJobs(dryRun = false, maxJobs = 20) {
  return postJson<{ ran: number; jobs: JobRecord[]; message: string }>(
    `/api/admin/jobs/run-all?dry_run=${dryRun}&max_jobs=${maxJobs}`,
    {}
  );
}

export async function retryJob(jobId: string) {
  return postJson<JobRecord>(`/api/admin/jobs/${jobId}/retry`, {});
}

export async function fetchMemorySummary(params: { userId?: string; sessionId?: string } = {}) {
  const search = new URLSearchParams();
  search.set("user_id", params.userId ?? authUserId());
  if (params.sessionId) search.set("session_id", params.sessionId);
  return fetchJson<MemorySummary>(`/api/memory/summary?${search.toString()}`);
}

export async function rememberFact(params: {
  text: string;
  userId?: string;
  sessionId?: string;
  memoryType?: string;
  importance?: number;
}) {
  return postJson<{ saved_memories: MemoryRecord[]; extracted_tasks: TaskRecord[]; semantic_indexed: number }>(
    "/api/memory/remember",
    {
      text: params.text,
      user_id: params.userId ?? authUserId(),
      session_id: params.sessionId,
      memory_type: params.memoryType,
      importance: params.importance ?? 0.6
    }
  );
}

export async function deleteMemory(memoryId: string, userId = authUserId()) {
  return deleteJson(`/api/memory/${memoryId}?user_id=${encodeURIComponent(userId)}`);
}

export async function createTask(params: {
  title: string;
  userId?: string;
  dueDate?: string;
  priority?: string;
  status?: string;
}) {
  return postJson<TaskRecord>("/api/tasks", {
    title: params.title,
    user_id: params.userId ?? authUserId(),
    due_date: params.dueDate || null,
    priority: params.priority ?? "medium",
    status: params.status ?? "open"
  });
}

export async function updateTask(taskId: string, params: Partial<Pick<TaskRecord, "title" | "due_date" | "priority" | "status">>, userId = authUserId()) {
  return patchJson<TaskRecord>(`/api/tasks/${taskId}?user_id=${encodeURIComponent(userId)}`, params);
}

export async function deleteTask(taskId: string, userId = authUserId()) {
  return deleteJson(`/api/tasks/${taskId}?user_id=${encodeURIComponent(userId)}`);
}

export async function fetchGoogleStatus(): Promise<GoogleStatus> {
  return fetchJson("/api/google/status");
}

export async function fetchGoogleLoginStatus(): Promise<GoogleLoginStatus> {
  return fetchJson("/api/auth/google/status");
}

export async function fetchGoogleIntegrationStatus(): Promise<GoogleIntegrationStatus> {
  return fetchJson("/api/integrations/google/status");
}

export async function getGoogleIntegrationStartUrl(integration: "gmail" | "calendar"): Promise<string> {
  const response = await fetch(`${BACKEND_URL}/api/integrations/google/${integration}/start-url`, {
    cache: "no-store",
    headers: authHeaders()
  });
  if (response.status === 401) throw new Error("Bạn cần đăng nhập trước khi kết nối Google.");
  if (!response.ok) throw new Error(`Backend API error ${response.status}`);
  const body = (await response.json()) as { url?: string };
  if (!body.url) throw new Error("Không đọc được URL kết nối Google.");
  return body.url;
}

export async function disconnectGoogleIntegration(integration: "gmail" | "calendar") {
  return postJson<{ ok: boolean; integration: string; connected: boolean }>(`/api/integrations/google/${integration}/disconnect`, {});
}

export async function syncGmail(params: {
  userId?: string;
  range?: "7d" | "30d" | "90d" | "1y" | "all_recent";
  maxResults?: number;
  useMock?: boolean;
  scenario?: string;
  query?: string;
  includeRead?: boolean;
  includeUnread?: boolean;
  includeSpamTrash?: boolean;
}) {
  return postJson<SyncResponse>("/api/google/gmail/sync", {
    user_id: params.userId ?? authUserId(),
    range: params.range ?? "90d",
    max_results: params.maxResults ?? 100,
    use_mock: params.useMock ?? false,
    scenario: params.scenario,
    query: params.query ?? "newer_than:90d",
    include_read: params.includeRead ?? true,
    include_unread: params.includeUnread ?? true,
    include_spam_trash: params.includeSpamTrash ?? false
  });
}

export async function syncCalendar(params: {
  userId?: string;
  range?: "7d" | "30d" | "90d" | "1y";
  daysAhead?: number;
  startDate?: string;
  endDate?: string;
  calendarIds?: string[];
  includeAllCalendars?: boolean;
  includeHolidays?: boolean;
  useMock?: boolean;
  scenario?: string;
  includeCancelled?: boolean;
}) {
  return postJson<SyncResponse>("/api/google/calendar/sync", {
    user_id: params.userId ?? authUserId(),
    range: params.range ?? "7d",
    days_ahead: params.daysAhead ?? 7,
    start_date: params.startDate,
    end_date: params.endDate,
    calendar_ids: params.calendarIds ?? [],
    include_all_calendars: params.includeAllCalendars ?? false,
    include_holidays: params.includeHolidays ?? false,
    use_mock: params.useMock ?? false,
    scenario: params.scenario,
    include_cancelled: params.includeCancelled ?? false
  });
}

export async function fetchCalendarList() {
  return fetchJson<CalendarListResponse>("/api/google/calendar/calendars");
}

export async function fetchGoogleSyncStatus(type: "gmail" | "calendar", userId = authUserId()) {
  return fetchJson<Record<string, any>>(`/api/google/sync-status?type=${encodeURIComponent(type)}&user_id=${encodeURIComponent(userId)}`);
}

export async function fetchGmailSummary(userId = authUserId()) {
  return fetchJson<GmailSummary>(`/api/google/gmail/summary?user_id=${encodeURIComponent(userId)}`);
}

export async function fetchCalendarToday(userId = authUserId()) {
  return fetchJson<CalendarToday>(`/api/google/calendar/today?user_id=${encodeURIComponent(userId)}`);
}

export async function fetchDailyBriefing(userId = authUserId()) {
  return fetchJson<DailyBriefing>(`/api/assistant/daily-briefing?user_id=${encodeURIComponent(userId)}`);
}

export async function fetchLatestSmartBriefing() {
  return fetchJson<SmartBriefing>("/api/briefing/latest");
}

export async function generateSmartBriefing(timeWindow = "today", allowMock = false) {
  return postJson<SmartBriefing>(
    `/api/briefing/generate?time_window=${encodeURIComponent(timeWindow)}&allow_mock=${allowMock ? "true" : "false"}`,
    {}
  );
}

export async function fetchKnowledgeSummary() {
  return fetchJson<KnowledgeSummary>("/api/knowledge/summary");
}

export async function fetchKnowledgeGraph(params: KnowledgeGraphFilters = {}) {
  const search = new URLSearchParams();
  if (params.nodeType && params.nodeType !== "all") search.set("node_type", params.nodeType);
  if (params.edgeType && params.edgeType !== "all") search.set("edge_type", params.edgeType);
  if (params.query) search.set("query", params.query);
  search.set("limit", String(params.limit ?? 250));
  const raw = await fetchJson<any>(`/api/knowledge/graph?${search.toString()}`);
  return normalizeKnowledgeGraph(raw, params);
}

export async function createMeetingPrepDraft(params: {
  query: string;
  eventId?: string;
  projectId?: string;
  includeEmails?: boolean;
  includeTasks?: boolean;
}) {
  return postJson<ActionDraft>("/api/action-studio/meeting-prep", {
    query: params.query,
    event_id: params.eventId || null,
    project_id: params.projectId || null,
    include_emails: params.includeEmails ?? true,
    include_tasks: params.includeTasks ?? true
  });
}

export async function createReportDraft(params: { period: "today" | "7d" | "30d"; style: "student" | "admin" | "research"; projectId?: string }) {
  return postJson<ActionDraft>("/api/action-studio/report", {
    period: params.period,
    style: params.style,
    project_id: params.projectId || null
  });
}

export async function createSlideDraft(params: { topic: string; source: "latest_briefing" | "project" | "free_text"; slideCount: number }) {
  return postJson<ActionDraft>("/api/action-studio/slides", {
    topic: params.topic,
    source: params.source,
    slide_count: params.slideCount,
    format: "marp_markdown"
  });
}

export async function createEmailDraft(params: { emailId?: string; threadId?: string; instruction: string; tone: "formal" | "friendly" | "short"; language: "vi" | "en" }) {
  return postJson<ActionDraft>("/api/action-studio/email-draft", {
    email_id: params.emailId || null,
    thread_id: params.threadId || null,
    instruction: params.instruction,
    tone: params.tone,
    language: params.language
  });
}

export async function fetchRecentActionDrafts() {
  return fetchJson<{ drafts: ActionDraft[]; count: number }>("/api/action-studio/recent");
}

export async function fetchActionDraft(draftId: string) {
  return fetchJson<ActionDraft>(`/api/action-studio/${encodeURIComponent(draftId)}`);
}

function normalizeKnowledgeGraph(raw: any, params: KnowledgeGraphFilters): KnowledgeGraph {
  let nodes: KnowledgeNode[] = (raw.nodes ?? []).map((node: any) => ({
    id: String(node.id ?? node.node_id ?? ""),
    type: String(node.type ?? node.node_type ?? "Unknown"),
    label: String(node.label ?? node.id ?? node.node_id ?? "Untitled"),
    metadata: node.metadata ?? node.properties ?? {},
    source_count: Number(node.source_count ?? 0),
    node_id: node.node_id ?? node.id,
    node_type: node.node_type ?? node.type,
    properties: node.properties ?? node.metadata ?? {}
  }));
  let edges: KnowledgeEdge[] = (raw.edges ?? []).map((edge: any) => ({
    id: String(edge.id ?? edge.edge_id ?? `${edge.source_id ?? edge.source}->${edge.target_id ?? edge.target}`),
    source: String(edge.source ?? edge.source_id ?? ""),
    target: String(edge.target ?? edge.target_id ?? ""),
    type: String(edge.type ?? edge.edge_type ?? "RELATED_TO"),
    weight: Number(edge.weight ?? edge.properties?.weight ?? 1),
    metadata: edge.metadata ?? edge.properties ?? {},
    edge_id: edge.edge_id ?? edge.id,
    source_id: edge.source_id ?? edge.source,
    target_id: edge.target_id ?? edge.target,
    edge_type: edge.edge_type ?? edge.type,
    properties: edge.properties ?? edge.metadata ?? {}
  }));

  if (params.nodeType && params.nodeType !== "all") {
    nodes = nodes.filter((node) => node.type === params.nodeType);
  }
  if (params.query) {
    const query = params.query.toLowerCase();
    nodes = nodes.filter((node) => {
      return node.id.toLowerCase().includes(query) || node.label.toLowerCase().includes(query) || JSON.stringify(node.metadata).toLowerCase().includes(query);
    });
  }
  const nodeIds = new Set(nodes.map((node) => node.id));
  edges = edges.filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target));
  if (params.edgeType && params.edgeType !== "all") {
    edges = edges.filter((edge) => edge.type === params.edgeType);
    const connected = new Set(edges.flatMap((edge) => [edge.source, edge.target]));
    nodes = nodes.filter((node) => connected.has(node.id));
  }
  const limit = params.limit ?? 250;
  if (nodes.length > limit) {
    nodes = nodes.slice(0, limit);
    const kept = new Set(nodes.map((node) => node.id));
    edges = edges.filter((edge) => kept.has(edge.source) && kept.has(edge.target));
  }

  const degree = new Map<string, number>();
  edges.forEach((edge) => {
    degree.set(edge.source, (degree.get(edge.source) ?? 0) + 1);
    degree.set(edge.target, (degree.get(edge.target) ?? 0) + 1);
  });
  nodes = nodes.map((node) => ({ ...node, source_count: node.source_count || degree.get(node.id) || 0 }));

  const node_counts = countBy(nodes, (node) => node.type);
  const edge_counts = countBy(edges, (edge) => edge.type);
  return {
    user_id: String(raw.user_id ?? ""),
    nodes,
    edges,
    summary: {
      user_id: String(raw.user_id ?? ""),
      node_count: nodes.length,
      edge_count: edges.length,
      node_counts,
      edge_counts,
      top_people: raw.summary?.top_people ?? [],
      top_projects: raw.summary?.top_projects ?? [],
      recent_deadlines: raw.summary?.recent_deadlines ?? [],
      metadata: raw.summary?.metadata ?? raw.metadata ?? {},
      filters: raw.summary?.filters ?? params
    },
    metadata: raw.metadata ?? {}
  };
}

function countBy<T>(items: T[], keyFn: (item: T) => string): Record<string, number> {
  return items.reduce<Record<string, number>>((acc, item) => {
    const key = keyFn(item);
    acc[key] = (acc[key] ?? 0) + 1;
    return acc;
  }, {});
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${BACKEND_URL}${path}`, { cache: "no-store", headers: authHeaders() });
  if (!response.ok) {
    throw new Error(`Backend API error ${response.status}`);
  }
  return response.json();
}

async function postJson<T>(path: string, body: unknown, options: { skipAuth?: boolean } = {}): Promise<T> {
  const response = await fetch(`${BACKEND_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(options.skipAuth ? {} : authHeaders()) },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    throw new Error(`Backend API error ${response.status}`);
  }
  return response.json();
}

async function patchJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${BACKEND_URL}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    throw new Error(`Backend API error ${response.status}`);
  }
  return response.json();
}

async function deleteJson(path: string): Promise<{ deleted: boolean; id: string }> {
  const response = await fetch(`${BACKEND_URL}${path}`, { method: "DELETE", headers: authHeaders() });
  if (!response.ok) {
    throw new Error(`Backend API error ${response.status}`);
  }
  return response.json();
}

function authHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(AUTH_STORAGE_KEY);
    const session = raw ? (JSON.parse(raw) as AuthSession) : null;
    return session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {};
  } catch {
    return {};
  }
}

function authUserId(): string {
  if (typeof window === "undefined") return "guest";
  try {
    const raw = window.localStorage.getItem(AUTH_STORAGE_KEY);
    const session = raw ? (JSON.parse(raw) as AuthSession) : null;
    return session?.user.user_id || "guest";
  } catch {
    return "guest";
  }
}
