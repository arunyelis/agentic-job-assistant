import { useQuery } from '@tanstack/react-query';
import { Bot, BriefcaseBusiness, ChevronDown, FilePenLine, Plus, Send, Timer, Workflow } from 'lucide-react';
import { type FormEvent, useEffect, useRef, useState } from 'react';

import MarkdownContent from '@/MarkdownContent';
import { ResumeUpload } from '@/components/ResumeUpload';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { useWorkspace } from '@/context/WorkspaceContext';
import { readSse } from '@/sse';
import type { AgentActivity, ChatMessage, HealthStatus, ReasoningItem } from '@/types';

const STARTERS = [
  { icon: BriefcaseBusiness, title: 'Review a role', text: 'Analyze this public job against my resume: ' },
  { icon: FilePenLine, title: 'Write application material', text: 'Write a concise cover letter using only evidence from my resume: ' },
  { icon: Workflow, title: 'Plan a follow-up', text: 'Draft a follow-up for an application I submitted seven days ago.' }
];

export function appendReasoning(current: ReasoningItem[], data: { itemId?: string; summaryIndex?: number; text: string }) {
  const itemId = `${data.itemId || 'summary'}:${data.summaryIndex ?? 0}`;
  const existing = current.find((item) => item.id === itemId);
  if (!existing) return [...current, { id: itemId, text: data.text }];
  const separator = existing.text.endsWith('**') && data.text.startsWith('**') ? '\n\n' : '';
  return current.map((item) => item.id === itemId ? { ...item, text: item.text + separator + data.text } : item);
}

function Message({ message }: { message: ChatMessage }) {
  return (
    <article className="grid gap-2 sm:grid-cols-[72px_minmax(0,1fr)] sm:gap-4">
      <div className="pt-1 text-xs font-semibold text-muted-foreground">{message.role === 'user' ? 'You' : 'Assistant'}</div>
      <div>
        <div className={message.role === 'assistant' ? `rounded-2xl border p-4 sm:p-5 ${message.error ? 'border-danger/35 bg-danger-soft' : 'border-border bg-surface'}` : 'py-2 text-[15px] leading-7'}>
          {message.role === 'assistant' && message.text ? <MarkdownContent>{message.text}</MarkdownContent> : message.text || <span className="text-muted-foreground">Working…</span>}
        </div>
        {message.elapsedMs !== undefined && (
          <div className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground">
            <Timer className="size-3.5" aria-hidden="true" /> Response time {(message.elapsedMs / 1000).toFixed(1)} seconds
          </div>
        )}
      </div>
    </article>
  );
}

export function AssistantPage() {
  const { chatSessionId, resume, resetChatWorkspace } = useWorkspace();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [activityOpen, setActivityOpen] = useState(false);
  const [activities, setActivities] = useState<AgentActivity[]>([]);
  const [reasoning, setReasoning] = useState<ReasoningItem[]>([]);
  const end = useRef<HTMLDivElement>(null);
  const health = useQuery<HealthStatus>({
    queryKey: ['health'],
    queryFn: async () => {
      const response = await fetch('/api/health');
      if (!response.ok) throw new Error('Assistant service is unavailable.');
      return response.json();
    }
  });

  useEffect(() => {
    end.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, activities, reasoning]);

  function updateAssistant(id: string, update: Partial<ChatMessage>) {
    setMessages((current) => current.map((item) => item.id === id ? { ...item, ...update } : item));
  }

  async function sendMessage(event?: FormEvent) {
    event?.preventDefault();
    const clean = message.trim();
    if (!clean || busy || resume.status !== 'ready') return;
    const assistantId = crypto.randomUUID();
    setMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), role: 'user', text: clean },
      { id: assistantId, role: 'assistant', text: '', streaming: true }
    ]);
    setMessage('');
    setActivities([{ type: 'status', label: 'Coordinator started' }]);
    setReasoning([]);
    setActivityOpen(true);
    setBusy(true);

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: chatSessionId, message: clean })
      });
      if (!response.ok) throw new Error('The assistant rejected the request.');
      await readSse(response, ({ event: eventName, data }) => {
        if (eventName === 'token') {
          setMessages((current) => current.map((item) => item.id === assistantId ? { ...item, text: item.text + String(data.text || '') } : item));
        }
        if (eventName === 'reasoning') {
          setReasoning((current) => appendReasoning(current, {
            text: String(data.text || ''),
            itemId: String(data.itemId || ''),
            summaryIndex: Number(data.summaryIndex || 0)
          }));
        }
        if (eventName === 'activity') setActivities((current) => [...current, data as unknown as AgentActivity]);
        if (eventName === 'done') {
          updateAssistant(assistantId, {
            text: String(data.answer || ''),
            elapsedMs: Number(data.elapsedMs || 0),
            streaming: false
          });
          setActivityOpen(false);
        }
        if (eventName === 'error') throw new Error(String(data.message || 'The assistant could not complete the request.'));
      });
    } catch (error) {
      updateAssistant(assistantId, {
        text: error instanceof Error ? error.message : 'The assistant could not complete the request.',
        error: true,
        streaming: false
      });
      setActivities((current) => [...current, { type: 'warning', label: 'Request failed' }]);
    } finally {
      setBusy(false);
    }
  }

  async function newChat() {
    if (busy) return;
    await resetChatWorkspace();
    setMessages([]);
    setActivities([]);
    setReasoning([]);
    setMessage('');
  }

  const ready = resume.status === 'ready';
  const agentReady = health.data?.status === 'ok' && health.data.apiKeyConfigured;

  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Badge variant={agentReady ? 'success' : 'warning'}>{agentReady ? 'Agent ready' : health.data?.apiKeyConfigured === false ? 'API key missing' : 'Connecting'}</Badge>
          {health.data && <span className="text-xs text-muted-foreground">{health.data.model} · {health.data.skills.length} skills</span>}
        </div>
        <Button variant="outline" onClick={newChat} disabled={busy}>
          <Plus className="size-4" aria-hidden="true" /> New chat
        </Button>
      </div>

      {!ready && <ResumeUpload />}

      {!messages.length ? (
        <section className="grid gap-4 rounded-2xl border border-border bg-surface p-5 sm:p-7">
          <div className="max-w-2xl">
            <div className="grid size-11 place-items-center rounded-2xl bg-primary-soft text-primary"><Bot className="size-5" aria-hidden="true" /></div>
            <h2 className="mt-4 text-2xl font-semibold tracking-[-0.025em]">Work through the next application</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">The assistant can load focused skills, use read-only public job research, and ask a specialist for a separate pass when it improves the answer.</p>
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            {STARTERS.map(({ icon: Icon, title, text }) => (
              <button
                key={title}
                type="button"
                className="min-h-28 rounded-xl border border-border bg-background p-4 text-left transition-colors hover:border-primary/45 hover:bg-primary-soft/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary motion-reduce:transition-none"
                onClick={() => setMessage(text)}
                disabled={!ready}
              >
                <Icon className="size-5 text-primary" aria-hidden="true" />
                <strong className="mt-3 block text-sm">{title}</strong>
                <span className="mt-1 block text-xs leading-5 text-muted-foreground">{ready ? 'Use as a starting prompt' : 'Upload a resume first'}</span>
              </button>
            ))}
          </div>
        </section>
      ) : (
        <section className="space-y-6" aria-label="Conversation">
          {messages.map((item) => <Message key={item.id} message={item} />)}
          <div ref={end} />
        </section>
      )}

      {(activities.length > 0 || busy) && (
        <Card className="overflow-hidden">
          <button
            className="flex min-h-11 w-full items-center justify-between gap-3 px-4 text-left text-[13px] font-semibold hover:bg-surface-subtle focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary"
            onClick={() => setActivityOpen((current) => !current)}
            aria-expanded={activityOpen}
          >
            <span className="flex items-center gap-2"><span className={`size-2 rounded-full ${busy ? 'animate-pulse bg-success motion-reduce:animate-none' : 'bg-muted-foreground'}`} /> Agent activity</span>
            <ChevronDown className={`size-4 transition-transform ${activityOpen ? 'rotate-180' : ''}`} aria-hidden="true" />
          </button>
          {activityOpen && (
            <div className="grid gap-5 border-t border-border p-4 md:grid-cols-2">
              <div>
                <p className="mb-2 text-xs font-semibold">Tools and specialists</p>
                <div className="flex flex-wrap gap-2">
                  {activities.map((item, index) => <Badge key={`${item.label}-${index}`} variant={item.type === 'warning' ? 'warning' : item.type === 'agent' ? 'info' : 'neutral'}>{item.label}</Badge>)}
                </div>
              </div>
              <div className="md:border-l md:border-border md:pl-5">
                <p className="text-xs font-semibold">Concise work summary</p>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">This shows model-provided summaries, not private chain-of-thought.</p>
                <div className="mt-2 space-y-2 text-[13px] text-muted-foreground">
                  {reasoning.length ? reasoning.map((item) => <MarkdownContent key={item.id}>{item.text}</MarkdownContent>) : <p>Activity will appear when provided.</p>}
                </div>
              </div>
            </div>
          )}
        </Card>
      )}

      <form className="sticky bottom-3 rounded-2xl border border-border bg-surface p-2 shadow-overlay" onSubmit={sendMessage}>
        <div className="flex items-end gap-2">
          <Textarea
            className="min-h-12 resize-none border-0 bg-transparent focus:ring-0"
            rows={1}
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                void sendMessage();
              }
            }}
            placeholder={ready ? 'Ask about a role or application' : 'Upload a resume to start'}
            disabled={!ready || busy}
            aria-label="Message"
          />
          <Button size="icon" type="submit" disabled={!ready || busy || !message.trim()} aria-label="Send message">
            <Send className="size-4.5" aria-hidden="true" />
          </Button>
        </div>
        <div className="flex items-center justify-between px-2 pb-1 pt-0.5 text-xs text-muted-foreground">
          <span>{ready ? 'Resume loaded for this chat' : 'Resume required'}</span>
          <span className="hidden sm:inline">Enter to send · Shift + Enter for a new line</span>
        </div>
      </form>
    </div>
  );
}
