import type { AIState } from "../../types/ui";
import type { DemoState } from "../../types/protocol";

interface EventLayerProps { state: AIState; onSelect: (state: DemoState) => void; }
const states: DemoState[] = ["idle", "listening", "thinking", "executing", "speaking", "alert", "offline"];

export function EventLayer({ state, onSelect }: EventLayerProps) {
  return <div className="demo-control" aria-label="Visual state preview"><span>VISUAL STATE</span>{states.map((option) => <button key={option} className={option === state ? "active" : ""} type="button" onClick={() => onSelect(option)}>{option}</button>)}</div>;
}
