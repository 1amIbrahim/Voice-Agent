import { useState } from "react";
import type { FormEvent } from "react";
import type { AIState, TurnState } from "../../types/ui";

interface CommandInputProps { aiState: AIState; turnState: TurnState; audioLevel: number; onSubmit: (instruction: string) => void; }

export function CommandInput({ aiState, turnState, audioLevel, onSubmit }: CommandInputProps) {
  const [value, setValue] = useState("");
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!value.trim()) return;
    onSubmit(value.trim());
    setValue("");
  };
  const bars = Array.from({ length: 31 }, (_, index) => 0.26 + Math.abs(Math.sin(index * 1.74)) * audioLevel);
  return <form className="command-interface" onSubmit={submit}><div className="waveform" aria-hidden="true">{bars.map((height, index) => <span key={index} style={{ transform: `scaleY(${height})` }} />)}</div><div className="command-row"><button className="mic-button" type="button" title="Microphone capture is not connected yet" aria-label="Microphone capture is not connected yet"><span /></button><input value={value} onChange={(event) => setValue(event.target.value)} placeholder="What would you like me to do, sir?" aria-label="Command input" /><button type="submit" className="execute-button">EXECUTE</button></div><p className="command-state">{turnState.replaceAll("_", " ")} / {aiState} <span>DEMO TRANSPORT</span></p></form>;
}
