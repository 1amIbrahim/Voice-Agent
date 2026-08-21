import type { GatewayEvent } from "../types/protocol";
import type { AgentSnapshot, AIState, CommandCenterState, ResponseOverlay, TurnState } from "../types/ui";

const initialAgents: AgentSnapshot[] = [
  { id: "claude-code", name: "CLAUDE CODE", status: "idle", activity: "Available" },
  { id: "voice-gateway", name: "VOICE GATEWAY", status: "idle", activity: "Endpointed capture ready" },
  { id: "system", name: "SYSTEM OBSERVER", status: "idle", activity: "Monitoring local runtime" },
];

export const initialState: CommandCenterState = {
  aiState: "idle",
  turnState: "idle",
  agents: initialAgents,
  events: [],
  online: true,
  audioLevel: 0.16,
  metrics: [
    { label: "ASR", value: "WHISPER", detail: "small.en", level: 0.7 },
    { label: "VAD", value: "SILERO", detail: "endpointed", level: 0.52 },
    { label: "TTS", value: "PIPER", detail: "local", level: 0.38 },
    { label: "NETWORK", value: "LOCAL", detail: "standby", level: 0.2 },
  ],
};

function text(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function agentFor(event: GatewayEvent, previous: AgentSnapshot[]): AgentSnapshot[] {
  const id = text(event.content.agent, event.source);
  const current = previous.find((agent) => agent.id === id);
  const name = id.replace(/[-_]/g, " ").toUpperCase();
  const update: AgentSnapshot = {
    id,
    name,
    status: current?.status ?? "idle",
    activity: current?.activity ?? "Awaiting work",
    progress: current?.progress,
    taskId: event.task_id ?? current?.taskId,
  };

  if (event.event === "agent.started") {
    update.status = "running";
    update.activity = text(event.content.message, "Coordinating task");
    update.progress = 8;
  }
  if (event.event === "agent.progress") {
    update.status = "running";
    update.activity = text(event.content.message, "Processing request");
    update.progress = typeof event.content.progress === "number" ? event.content.progress : 52;
  }
  if (event.event === "agent.completed") {
    update.status = "completed";
    update.activity = "Completed";
    update.progress = 100;
  }
  if (event.event === "agent.failed") {
    update.status = "failed";
    update.activity = text(event.content.message, "Unable to complete task");
  }
  if (event.event === "agent.question" || event.event === "agent.permission_required") {
    update.status = "waiting";
    update.activity = text(event.content.message, "Awaiting user response");
  }

  return current ? previous.map((agent) => (agent.id === id ? update : agent)) : [...previous, update];
}

function visualState(event: GatewayEvent, prior: AIState): { aiState: AIState; turnState: TurnState; online: boolean } {
  if (event.event === "agent.started") return { aiState: "thinking", turnState: "processing", online: true };
  if (event.event === "agent.progress") return { aiState: "executing", turnState: "processing", online: true };
  if (event.event === "agent.completed") return { aiState: "speaking", turnState: "speaking", online: true };
  if (event.event === "agent.failed" || event.event === "system.error") return { aiState: "alert", turnState: "idle", online: true };
  if (event.event === "agent.question" || event.event === "agent.permission_required") return { aiState: "alert", turnState: "waiting_for_user", online: true };
  if (event.event === "system.warning") return { aiState: "alert", turnState: "idle", online: true };
  if (event.event === "system.notification") return { aiState: prior, turnState: "idle", online: true };
  return { aiState: prior, turnState: "idle", online: true };
}

function responseFor(event: GatewayEvent): ResponseOverlay | undefined {
  const message = text(event.content.message, "");
  if (!message) return undefined;
  if (event.event === "agent.progress" || event.event === "agent.started") return undefined;
  const status = event.event === "agent.failed" || event.event === "system.error"
    ? "error"
    : event.event === "system.warning"
      ? "warning"
      : event.event === "agent.question"
        ? "question"
        : event.event === "agent.permission_required"
          ? "permission"
          : "normal";
  return { id: event.id, source: event.source, message, priority: event.priority, status };
}

export function reduceGatewayEvent(state: CommandCenterState, event: GatewayEvent): CommandCenterState {
  const visual = visualState(event, state.aiState);
  return {
    ...state,
    ...visual,
    agents: event.event.startsWith("agent.") ? agentFor(event, state.agents) : state.agents,
    response: responseFor(event) ?? state.response,
    events: [event, ...state.events].slice(0, 24),
    audioLevel: event.event === "agent.completed" ? 0.72 : event.event === "agent.started" ? 0.38 : state.audioLevel,
  };
}

export function withDemoState(state: CommandCenterState, aiState: AIState): CommandCenterState {
  const turnState: TurnState = aiState === "listening" ? "listening" : aiState === "speaking" ? "speaking" : aiState === "thinking" || aiState === "executing" ? "processing" : "idle";
  return { ...state, aiState, turnState, online: aiState !== "offline", audioLevel: aiState === "speaking" ? 0.7 : aiState === "listening" ? 0.46 : 0.16 };
}
