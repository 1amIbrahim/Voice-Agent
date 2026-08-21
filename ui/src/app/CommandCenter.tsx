import { useEffect, useReducer, useState } from "react";
import { AgentMonitor } from "../components/command-center/AgentMonitor";
import { CommandInput } from "../components/command-center/CommandInput";
import { ConversationOverlay } from "../components/command-center/ConversationOverlay";
import { EventLayer } from "../components/command-center/EventLayer";
import { SystemMonitor } from "../components/command-center/SystemMonitor";
import { TopStatusBar } from "../components/command-center/TopStatusBar";
import { JarvisCore } from "../components/jarvis-core/JarvisCore";
import { initialState, reduceGatewayEvent, withDemoState } from "../store/commandCenter";
import { mockTransport } from "../transport/mockTransport";
import { useAudioReactivity } from "../hooks/useAudioReactivity";
import type { DemoState } from "../types/protocol";

export function CommandCenter() {
  const [state, dispatch] = useReducer(reduceGatewayEvent, initialState);
  const [previewState, setPreviewState] = useState<DemoState>();

  useEffect(() => mockTransport.subscribe(dispatch), []);

  const submitCommand = (instruction: string) => {
    setPreviewState(undefined);
    mockTransport.sendCommand({ instruction, sessionId: "ui-demo-session" });
  };

  const selectState = (next: DemoState) => {
    setPreviewState(next);
    mockTransport.setDemoState(next);
  };

  const display = previewState ? withDemoState(state, previewState) : state;
  const audioSignal = useAudioReactivity(display.aiState);

  return <main className={`command-center-shell state-${display.aiState}`}><JarvisCore state={display.aiState} audioSignal={audioSignal} /><div className="scan-field" /><div className="edge-rail rail-left"><span>01</span><i /><span>VOICE</span><i /><span>07</span></div><div className="edge-rail rail-right"><span>22</span><i /><span>CORE</span><i /><span>41</span></div><TopStatusBar aiState={display.aiState} turnState={display.turnState} online={display.online} /><AgentMonitor agents={display.agents} /><SystemMonitor metrics={display.metrics} /><section className="core-stage"><div className="core-caption"><span>ORCHESTRATOR</span><strong>{display.aiState}</strong></div><div className="core-readout readout-left"><span>NEURAL FIELD</span><b>98.7</b></div><div className="core-readout readout-right"><span>SYNAPTIC FLOW</span><b>ACTIVE</b></div></section><ConversationOverlay response={display.response} /><EventLayer state={display.aiState} onSelect={selectState} /><CommandInput aiState={display.aiState} turnState={display.turnState} audioLevel={display.audioLevel} onSubmit={submitCommand} /><footer className="footer-signal"><span>LOCAL-FIRST VOICE GATEWAY</span><span>EVENT-DRIVEN UI FOUNDATION</span></footer></main>;
}
