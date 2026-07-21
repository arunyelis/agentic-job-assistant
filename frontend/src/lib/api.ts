import type {
  AgentDefinition,
  ApplicationRecord,
  ApplicationStatus,
  ApplicationTimelineEvent,
  AutomationRun,
  AutomationTool,
  Conversation,
  ConversationMessage,
  DeletionReceipt,
  SessionUser,
  TodaySummary
} from '@/types';

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(url, {
    credentials: 'same-origin',
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...options.headers
    }
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(body.detail || 'The request could not be completed.', response.status);
  }
  return response.json() as Promise<T>;
}

export async function ensureSession(): Promise<SessionUser> {
  const response = await request<{ user: SessionUser }>('/api/v1/auth/local-session', {
    method: 'POST'
  });
  return response.user;
}

export function getToday() {
  return request<TodaySummary>('/api/v1/today');
}

export function getApplications(filters: {
  search?: string;
  status?: string;
  needsReview?: boolean;
} = {}) {
  const query = new URLSearchParams();
  if (filters.search) query.set('search', filters.search);
  if (filters.status && filters.status !== 'all') query.set('status', filters.status);
  if (filters.needsReview !== undefined) {
    query.set('needs_review', String(filters.needsReview));
  }
  const suffix = query.size ? `?${query.toString()}` : '';
  return request<ApplicationRecord[]>(`/api/v1/applications${suffix}`);
}

export interface CaptureInput {
  sourceUrl: string;
  sourceType?: 'extension' | 'manual' | 'import';
  company: string;
  role: string;
  status?: ApplicationStatus;
  confidence?: number;
  screenshotArtifactId?: string;
  pageExcerpt?: string;
  idempotencyKey?: string;
}

export function captureApplication(input: CaptureInput) {
  return request<ApplicationRecord>('/api/v1/applications/capture', {
    method: 'POST',
    body: JSON.stringify({
      idempotency_key: input.idempotencyKey || crypto.randomUUID(),
      captured_at: new Date().toISOString(),
      source_url: input.sourceUrl,
      source_type: input.sourceType || 'manual',
      company: input.company,
      role: input.role,
      status: input.status || 'applied',
      extraction_confidence: input.confidence ?? 1,
      screenshot_artifact_id: input.screenshotArtifactId || null,
      page_excerpt: input.pageExcerpt || null
    })
  });
}

export function updateApplication(
  applicationId: string,
  input: Partial<{
    company: string;
    role: string;
    status: ApplicationStatus;
    notes: string;
    needs_review: boolean;
    next_action_at: string | null;
  }>
) {
  return request<ApplicationRecord>(`/api/v1/applications/${applicationId}`, {
    method: 'PATCH',
    body: JSON.stringify(input)
  });
}

export function getApplicationTimeline(applicationId: string) {
  return request<ApplicationTimelineEvent[]>(
    `/api/v1/applications/${applicationId}/timeline`
  );
}

export interface AutomationTaskInput {
  key: string;
  name: string;
  kind: 'tool' | 'llm' | 'agent';
  tool_name?: string;
  instructions?: string;
  input?: Record<string, unknown>;
  depends_on?: string[];
}

export function createAutomationRun(input: {
  prompt: string;
  mode?: 'auto' | 'sequential' | 'parallel' | 'graph';
  agentId?: string;
  conversationId?: string;
  context?: Record<string, unknown>;
  tasks?: AutomationTaskInput[];
}) {
  return request<AutomationRun>('/api/v1/automation/runs', {
    method: 'POST',
    body: JSON.stringify({
      prompt: input.prompt,
      mode: input.mode || 'auto',
      agent_id: input.agentId || null,
      conversation_id: input.conversationId || null,
      context: input.context || {},
      tasks: input.tasks || []
    })
  });
}

export function getAutomationRun(runId: string) {
  return request<AutomationRun>(`/api/v1/automation/runs/${runId}`);
}

export function getAutomationRuns() {
  return request<AutomationRun[]>('/api/v1/automation/runs');
}

export function getAutomationTools() {
  return request<AutomationTool[]>('/api/v1/automation/tools');
}

export function getAgents() {
  return request<AgentDefinition[]>('/api/v1/automation/agents');
}

export function createAgent(input: {
  name: string;
  description: string;
  instructions: string;
  allowedTools: string[];
}) {
  return request<AgentDefinition>('/api/v1/automation/agents', {
    method: 'POST',
    body: JSON.stringify({
      name: input.name,
      description: input.description,
      instructions: input.instructions,
      allowed_tools: input.allowedTools
    })
  });
}

export function getConversations() {
  return request<Conversation[]>('/api/v1/assistant/conversations');
}

export function createConversation(title = 'New conversation') {
  return request<Conversation>('/api/v1/assistant/conversations', {
    method: 'POST',
    body: JSON.stringify({ title })
  });
}

export function getConversationMessages(conversationId: string) {
  return request<ConversationMessage[]>(
    `/api/v1/assistant/conversations/${conversationId}/messages`
  );
}

export function clearConversation(conversationId: string) {
  return request<Conversation>(
    `/api/v1/assistant/conversations/${conversationId}/clear`,
    { method: 'POST' }
  );
}

export async function downloadAccountExport() {
  const response = await fetch('/api/v1/account/export', { credentials: 'same-origin' });
  if (!response.ok) throw new ApiError('The export could not be created.', response.status);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'career-workspace-export.json';
  anchor.click();
  URL.revokeObjectURL(url);
}

export function deleteAccount() {
  return request<DeletionReceipt>('/api/v1/account/deletion', { method: 'POST' });
}
