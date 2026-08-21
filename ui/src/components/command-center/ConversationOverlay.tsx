import type { ResponseOverlay } from "../../types/ui";

interface ConversationOverlayProps { response?: ResponseOverlay; }

export function ConversationOverlay({ response }: ConversationOverlayProps) {
  if (!response) return null;
  return <section className={`conversation-overlay ${response.status}`} aria-live="polite"><p className="eyebrow">{response.source.replace(/[-_]/g, " ")}</p><p className="response-message">{response.message}</p>{response.status === "permission" && <p className="response-notice">A backend transport must provide a task-correlated decision action before this can be approved or rejected.</p>}</section>;
}
