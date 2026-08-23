export const SUPER_BOT_VERSION = "0.1.0" as const;

export type TaskStatus =
  | "queued"
  | "running"
  | "waiting_approval"
  | "succeeded"
  | "failed"
  | "cancelled";

export type ExecutionMode = "local" | "sandbox" | "remote";
export type RiskLevel = "read" | "write" | "sensitive" | "critical";

export interface Bot {
  id: string;
  name: string;
  role: string;
  description: string;
  model_id: string | null;
  execution_mode: ExecutionMode;
  max_steps: number;
  daily_budget_usd: number | null;
  fallback_model_ids: string[];
  archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface Task {
  id: string;
  bot_id: string;
  conversation_id: string;
  parent_task_id: string | null;
  status: TaskStatus;
  model_id: string | null;
  current_step: number;
  max_steps: number;
  budget_usd: number | null;
  spent_usd: number;
  created_at: string;
  updated_at: string;
}

export interface TaskEvent {
  id: number;
  task_id: string;
  type: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface Approval {
  id: string;
  task_id: string;
  tool_name: string;
  risk: RiskLevel;
  summary: string;
  arguments: Record<string, unknown>;
  status: "pending" | "approved" | "denied" | "expired";
  created_at: string;
}

export interface ModelCapability {
  text: boolean;
  vision: boolean;
  tool_calling: boolean;
  structured_output: boolean;
  thinking: boolean;
  streaming: boolean;
  context_window: number;
  max_output_tokens: number;
}

export interface ModelDefinition {
  id: string;
  display_name: string;
  provider_id: string | null;
  capability: ModelCapability;
  input_cost_per_million: number | null;
  output_cost_per_million: number | null;
  enabled: boolean;
}
