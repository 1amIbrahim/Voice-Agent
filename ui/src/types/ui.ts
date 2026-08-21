import type { GatewayEvent, Priority } from "./protocol";

export type AIState = "idle" | "listening" | "thinking" | "executing" | "speaking" | "alert" | "offline";
export type TurnState = "idle" | "listening" | "capturing" | "processing" | "speaking" | "waiting_for_user" | "interrupted" | "cancelled";
export type AgentStatus = "idle" | "running" | "waiting" | "completed" | "failed" | "cancelled";

export interface AgentSnapshot {
  id: string;
  name: string;
  status: AgentStatus;
  activity: string;
  progress?: number;
  taskId?: string;
}

export interface ResponseOverlay {
  id: string;
  source: string;
  message: string;
  priority: Priority;
  status: "normal" | "warning" | "error" | "question" | "permission";
}

export interface SystemMetric {
  label: string;
  value: string;
  detail?: string;
  level?: number;
}

export interface CommandCenterState {
  aiState: AIState;
  turnState: TurnState;
  agents: AgentSnapshot[];
  response?: ResponseOverlay;
  events: GatewayEvent[];
  metrics: SystemMetric[];
  online: boolean;
  audioLevel: number;
}
