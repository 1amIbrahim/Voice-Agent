import type { VoiceEvent, VoiceState } from "../types/protocol";

const states = new Set<VoiceState>(["idle", "listening", "processing", "speaking"]);

export function parseVoiceEvent(data: string): VoiceEvent | undefined {
  try {
    const value: unknown = JSON.parse(data);
    if (!value || typeof value !== "object") return undefined;
    const payload = value as Record<string, unknown>;
    if (payload.type === "voice.state" && typeof payload.state === "string" && states.has(payload.state as VoiceState)) {
      return { type: "voice.state", state: payload.state as VoiceState };
    }
    if (payload.type === "voice.level" && typeof payload.level === "number" && Number.isFinite(payload.level)) {
      return { type: "voice.level", level: Math.max(0, Math.min(1, payload.level)) };
    }
  } catch {
    return undefined;
  }
  return undefined;
}

export type VoiceConnectionState = "connecting" | "connected" | "disconnected";

export function subscribeToVoiceEvents(
  listener: (event: VoiceEvent) => void,
  onConnectionChange?: (state: VoiceConnectionState) => void,
): () => void {
  const url = import.meta.env.VITE_VOICE_EVENTS_URL ?? "http://127.0.0.1:8765/events";
  const source = new EventSource(url);
  onConnectionChange?.("connecting");
  source.onopen = () => onConnectionChange?.("connected");
  source.onerror = () => onConnectionChange?.("disconnected");
  source.onmessage = (message) => {
    const event = parseVoiceEvent(message.data);
    if (event) listener(event);
  };
  return () => source.close();
}
