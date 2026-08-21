import type { SystemMetric } from "../../types/ui";

interface SystemMonitorProps { metrics: SystemMetric[]; }

export function SystemMonitor({ metrics }: SystemMonitorProps) {
  return <aside className="system-monitor instrumentation"><p className="eyebrow">SYSTEM INTELLIGENCE</p>{metrics.map((metric) => <div className="metric" key={metric.label}><div><span>{metric.label}</span><strong>{metric.value}</strong><small>{metric.detail}</small></div><div className="metric-line"><span style={{ width: `${(metric.level ?? 0) * 100}%` }} /></div></div>)}</aside>;
}
