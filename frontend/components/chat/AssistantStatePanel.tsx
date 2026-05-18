import { Activity, Brain, Database, Route, Timer } from "lucide-react";
import type { AuthUser } from "@/lib/api";
import type { ChatMessage, Conversation, QualityMetadata } from "@/lib/types";
import { CitationCard } from "./CitationCard";
import { IntentBadge } from "./IntentBadge";
import { QualityBadge } from "./QualityBadge";

function qualityFrom(message?: ChatMessage): QualityMetadata | undefined {
  return message?.metadata?.quality;
}

export function AssistantStatePanel({
  conversation,
  lastAssistantMessage,
  user
}: {
  conversation?: Conversation;
  lastAssistantMessage?: ChatMessage;
  user?: AuthUser | null;
}) {
  const route = lastAssistantMessage?.metadata?.route ?? [];
  const sources = (lastAssistantMessage?.sources ?? []).filter((source) => source.usage !== "retrieval_debug" && source.used_in_answer !== false);
  const debugRetrieval = (lastAssistantMessage?.metadata?.debug_retrieval ?? []) as typeof sources;
  const latency = lastAssistantMessage?.metadata?.latency_ms;
  const actions = lastAssistantMessage?.actions ?? [];

  return (
    <aside className="hidden min-h-0 border-l border-line bg-white xl:flex xl:w-80 xl:flex-col">
      <div className="border-b border-line p-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-ink">
          <Activity className="h-4 w-4 text-brand" />
          Assistant state
        </div>
        <div className="mt-1 truncate text-xs text-slate-500">{conversation?.sessionId ? `session ${conversation.sessionId.slice(0, 8)}` : "session pending"}</div>
        {user ? <div className="mt-1 truncate text-xs text-slate-500">{user.email} · {user.user_id}</div> : null}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        {lastAssistantMessage ? (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              <IntentBadge intent={lastAssistantMessage.intent} />
              <QualityBadge quality={qualityFrom(lastAssistantMessage)} />
            </div>

            <div className="grid gap-2 text-sm">
              <StateRow icon={Timer} label="Latency" value={typeof latency === "number" ? `${latency} ms` : "n/a"} />
              <StateRow icon={Brain} label="Memory" value={lastAssistantMessage.memoryUsed ? "used" : "not used"} />
              <StateRow icon={Database} label="Cited sources" value={String(sources.length)} />
              <StateRow icon={Route} label="Route" value={route.length ? route.join(" -> ") : "n/a"} />
              <StateRow icon={Database} label="Debug retrieval" value={String(debugRetrieval.length)} />
            </div>

            {actions.length ? (
              <div>
                <div className="mb-2 text-xs font-semibold uppercase tracking-normal text-slate-400">Actions</div>
                <div className="flex flex-wrap gap-2">
                  {actions.map((action) => (
                    <span key={action} className="rounded-full border border-line bg-panel px-2 py-1 text-xs text-slate-700">
                      {action}
                    </span>
                  ))}
                </div>
              </div>
            ) : null}

            {sources.length ? (
              <div>
                <div className="mb-2 text-xs font-semibold uppercase tracking-normal text-slate-400">Latest sources</div>
                <div className="space-y-2">
                  {sources.slice(0, 3).map((source, index) => (
                    <CitationCard key={`${source.chunk_id ?? source.source_url ?? index}`} source={source} index={source.citation_index ?? index + 1} isAdmin />
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        ) : (
          <p className="text-sm leading-6 text-slate-500">No assistant response yet.</p>
        )}
      </div>
    </aside>
  );
}

function StateRow({ icon: Icon, label, value }: { icon: typeof Timer; label: string; value: string }) {
  return (
    <div className="rounded-lg border border-line bg-panel p-3">
      <dt className="flex items-center gap-2 text-xs font-semibold uppercase tracking-normal text-slate-400">
        <Icon className="h-3.5 w-3.5" />
        {label}
      </dt>
      <dd className="mt-1 break-words text-sm font-medium leading-5 text-ink">{value}</dd>
    </div>
  );
}
