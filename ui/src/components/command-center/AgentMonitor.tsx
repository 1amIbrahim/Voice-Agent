import type { AgentSnapshot } from "../../types/ui";

interface AgentMonitorProps { agents: AgentSnapshot[]; }

export function AgentMonitor({ agents }: AgentMonitorProps) {
  return <aside className="agent-monitor instrumentation"><p className="eyebrow">ACTIVE AGENTS</p>{agents.map((agent) => <div className="agent-line" key={agent.id}><div className="agent-heading"><span className={`agent-dot ${agent.status}`} /><span>{agent.name}</span><span className="agent-status">{agent.status}</span></div><p>{agent.activity}</p>{agent.progress !== undefined && <div className="progress-track"><span style={{ width: `${agent.progress}%` }} /></div>}</div>)}</aside>;
}
