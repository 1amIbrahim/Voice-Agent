import type { AIState, TurnState } from "../../types/ui";

interface TopStatusBarProps { aiState: AIState; turnState: TurnState; online: boolean; }

export function TopStatusBar({ aiState, turnState, online }: TopStatusBarProps) {
  const time = new Intl.DateTimeFormat([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(new Date());
  return (
    <header className="top-status">
      <div className="brand"><span className="brand-name">JARVIS</span><span className={`status-dot ${online ? "online" : "offline"}`} /> <span>{online ? "ONLINE" : "OFFLINE"}</span></div>
      <div className="center-label">COMMAND CENTER <span>/{aiState}</span></div>
      <div className="system-clock"><span>{time}</span><span>{turnState.replaceAll("_", " ")}</span></div>
    </header>
  );
}
