import type { DemoState, GatewayEvent, GatewayTransport, OutboundCommand } from "../types/protocol";

let counter = 0;
const listeners = new Set<(event: GatewayEvent) => void>();
const sessionId = "ui-demo-session";

function emit(event: Omit<GatewayEvent, "id" | "timestamp" | "schema_version" | "session_id">): void {
  counter += 1;
  const fullEvent: GatewayEvent = {
    ...event,
    schema_version: "1.0",
    id: `ui_evt_${counter}`,
    timestamp: new Date().toISOString(),
    session_id: sessionId,
  };
  listeners.forEach((listener) => listener(fullEvent));
}

function systemState(state: DemoState): void {
  if (state === "alert") {
    emit({ event: "system.warning", source: "ui-demo", priority: "high", content: { message: "Attention required. Review the active system event." } });
    return;
  }
  if (state === "offline") {
    emit({ event: "system.error", source: "ui-demo", priority: "high", content: { message: "Gateway transport is offline. No command was sent." } });
    return;
  }
  emit({ event: "system.notification", source: "ui-demo", priority: "low", content: { message: `Visual state switched to ${state}.` } });
}

export const mockTransport: GatewayTransport = {
  subscribe(listener) {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },
  sendCommand(command: OutboundCommand) {
    const taskId = `demo_task_${counter + 1}`;
    emit({ event: "agent.started", source: "claude-code", task_id: taskId, correlation_id: `ui_command_${counter + 1}`, priority: "normal", content: { agent: "claude-code", message: "Command accepted by UI demo" } });
    window.setTimeout(() => emit({ event: "agent.progress", source: "claude-code", task_id: taskId, priority: "low", content: { agent: "claude-code", message: "Mock transport is simulating lifecycle presentation", progress: 56 } }), 850);
    window.setTimeout(() => emit({ event: "agent.completed", source: "claude-code", task_id: taskId, priority: "normal", content: { agent: "claude-code", message: `Demo complete. The UI received: “${command.instruction}”` } }), 1700);
  },
  setDemoState(state) {
    systemState(state);
  },
};
