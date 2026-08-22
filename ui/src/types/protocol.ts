export type GatewayEventType =
  | "user.command"
  | "user.query"
  | "user.confirmation"
  | "user.rejection"
  | "user.cancellation"
  | "agent.started"
  | "agent.progress"
  | "agent.completed"
  | "agent.failed"
  | "agent.question"
  | "agent.permission_required"
  | "system.notification"
  | "system.warning"
  | "system.error";

export type Priority = "low" | "normal" | "high";

export interface GatewayEvent {
  schema_version: string;
  event: GatewayEventType;
  id: string;
  timestamp: string;
  source: string;
  session_id: string;
  correlation_id?: string;
  task_id?: string;
  priority: Priority;
  content: Record<string, unknown>;
}

export type VoiceState = "idle" | "listening" | "processing" | "speaking";

export type VoiceEvent =
  | { type: "voice.state"; state: VoiceState }
  | { type: "voice.level"; level: number };

export interface OutboundCommand {
  instruction: string;
  sessionId: string;
}

export interface GatewayTransport {
  subscribe(listener: (event: GatewayEvent) => void): () => void;
  sendCommand(command: OutboundCommand): void;
  setDemoState(state: DemoState): void;
}

export type DemoState = "idle" | "listening" | "thinking" | "executing" | "speaking" | "alert" | "offline";
