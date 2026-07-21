export type ApplicationStatus =
  | 'captured'
  | 'applied'
  | 'assessment'
  | 'interview'
  | 'offer'
  | 'rejected'
  | 'withdrawn';

export interface ApplicationRecord {
  id: string;
  source_url: string;
  source_type: string;
  company: string;
  role: string;
  status: ApplicationStatus;
  captured_at: string;
  extraction_confidence: number;
  selected_resume_id: string | null;
  screenshot_artifact_id: string | null;
  notes: string | null;
  needs_review: boolean;
  next_action_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TodaySummary {
  total: number;
  counts: Partial<Record<ApplicationStatus, number>>;
  needsReview: number;
  recent: ApplicationRecord[];
}

export interface SessionUser {
  id: string;
  displayName: string;
  accountMode: string;
}

export interface HealthStatus {
  status: string;
  model: string;
  apiKeyConfigured: boolean;
  browserEnabled: boolean;
  skills: string[];
}

export interface ResumeState {
  status: 'idle' | 'uploading' | 'ready' | 'error';
  fileName?: string;
  characterCount?: number;
  elapsedMs?: number;
  error?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  streaming?: boolean;
  error?: boolean;
  elapsedMs?: number;
}

export interface AgentActivity {
  type: string;
  label: string;
}

export interface ReasoningItem {
  id: string;
  text: string;
}

export interface DeletionReceipt {
  id: string;
  status: string;
  requested_at: string;
  completed_at: string | null;
  backup_expires_at: string | null;
  categories_removed: string[];
  artifacts_removed: number;
}

export interface ApplicationTimelineEvent {
  id: string;
  type: string;
  title: string;
  details: Record<string, unknown> | null;
  occurred_at: string;
}

export interface AutomationTask {
  id: string;
  task_key: string;
  name: string;
  kind: 'tool' | 'llm' | 'agent';
  tool_name: string | null;
  depends_on: string[];
  status: string;
  result: Record<string, unknown> | null;
  error: string | null;
}

export interface AutomationEvent {
  sequence: number;
  event_type: string;
  message: string;
  data: Record<string, unknown> | null;
  created_at: string;
}

export interface AutomationRun {
  id: string;
  conversation_id: string | null;
  agent_definition_id: string | null;
  prompt: string;
  mode: 'auto' | 'sequential' | 'parallel' | 'graph';
  status: string;
  context: Record<string, unknown>;
  result: string | null;
  error: string | null;
  elapsed_ms: number | null;
  created_at: string;
  tasks: AutomationTask[];
  events: AutomationEvent[];
}

export interface AutomationTool {
  name: string;
  description: string;
  input_schema: Record<string, unknown>;
  side_effect: 'none' | 'workspace' | 'external';
  requires_confirmation: boolean;
}

export interface AgentDefinition {
  id: string;
  name: string;
  description: string;
  instructions: string;
  model: string | null;
  allowed_tools: string[];
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface Conversation {
  id: string;
  title: string;
  context_started_at: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationMessage {
  id: string;
  conversation_id: string;
  run_id: string | null;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
}
