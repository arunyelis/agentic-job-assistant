import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Bot, LoaderCircle, Mic, MicOff, Plus, Send, Sparkles } from 'lucide-react';
import { lazy, Suspense, useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import {
  clearConversation,
  createAutomationRun,
  createConversation,
  getAutomationRun,
  getConversationMessages,
  getConversations
} from '@/lib/api';
import { cn } from '@/lib/utils';
import type { Conversation } from '@/types';

const MarkdownContent = lazy(() => import('@/MarkdownContent'));

interface AssistantOpenDetail {
  prompt?: string;
  applicationId?: string;
}

interface SpeechResultEvent {
  results: ArrayLike<{ 0: { transcript: string } }>;
}

interface SpeechRecognitionLike {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: SpeechResultEvent) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
  start: () => void;
  stop: () => void;
}

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

function speechRecognitionConstructor() {
  const browserWindow = window as typeof window & {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  };
  return browserWindow.SpeechRecognition || browserWindow.webkitSpeechRecognition;
}

export function AssistantDock() {
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState('');
  const [activeConversationId, setActiveConversationId] = useState<string | null>(() => localStorage.getItem('career-active-conversation'));
  const [applicationId, setApplicationId] = useState<string | null>(null);
  const [runState, setRunState] = useState<'idle' | 'working' | 'error'>('idle');
  const [activity, setActivity] = useState<string[]>([]);
  const [error, setError] = useState('');
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const conversations = useQuery({ queryKey: ['conversations'], queryFn: getConversations });
  const messages = useQuery({
    queryKey: ['conversation-messages', activeConversationId],
    queryFn: () => getConversationMessages(activeConversationId!),
    enabled: Boolean(activeConversationId)
  });

  useEffect(() => {
    const available = conversations.data || [];
    if (activeConversationId && available.some((item) => item.id === activeConversationId)) return;
    if (available[0]) setActiveConversationId(available[0].id);
  }, [activeConversationId, conversations.data]);

  useEffect(() => {
    if (activeConversationId) localStorage.setItem('career-active-conversation', activeConversationId);
  }, [activeConversationId]);

  useEffect(() => {
    function handleOpen(event: Event) {
      const detail = (event as CustomEvent<AssistantOpenDetail>).detail || {};
      setDraft(detail.prompt || '');
      setApplicationId(detail.applicationId || null);
      setOpen(true);
    }
    window.addEventListener('career-assistant-open', handleOpen);
    return () => window.removeEventListener('career-assistant-open', handleOpen);
  }, []);

  async function newConversation(title = 'New conversation'): Promise<Conversation> {
    const conversation = await createConversation(title);
    setActiveConversationId(conversation.id);
    queryClient.invalidateQueries({ queryKey: ['conversations'] });
    return conversation;
  }

  async function waitForRun(runId: string) {
    return new Promise<Awaited<ReturnType<typeof getAutomationRun>>>((resolve, reject) => {
      const source = new EventSource(`/api/v1/automation/runs/${runId}/events`);
      let settled = false;
      const terminalEvents = new Set([
        'run_completed',
        'run_failed',
        'run_cancelled',
        'approval_required'
      ]);
      const timeout = window.setTimeout(() => {
        source.close();
        reject(new Error('The automation is still running. It remains available in run history.'));
      }, 120_000);

      async function finish() {
        if (settled) return;
        settled = true;
        window.clearTimeout(timeout);
        source.close();
        try {
          resolve(await getAutomationRun(runId));
        } catch (runError) {
          reject(runError);
        }
      }

      source.addEventListener('run', (event) => {
        try {
          const update = JSON.parse((event as MessageEvent<string>).data) as {
            type?: string;
            message?: string;
          };
          if (update.message) {
            const message = update.message;
            setActivity((current) => [...current.slice(-2), message]);
          }
          if (update.type && terminalEvents.has(update.type)) void finish();
        } catch {
          setActivity((current) => [...current.slice(-2), 'Received an unreadable activity update']);
        }
      });

      source.onerror = () => {
        void getAutomationRun(runId).then((run) => {
          if (['completed', 'failed', 'cancelled', 'waiting_approval'].includes(run.status)) {
            void finish();
          }
        }).catch(() => undefined);
      };
    });
  }

  function applyWorkspaceAction(run: Awaited<ReturnType<typeof getAutomationRun>>) {
    for (const task of run.tasks) {
      const action = task.result?.ui_action;
      if (!action || typeof action !== 'object' || Array.isArray(action)) continue;
      const values = action as Record<string, unknown>;
      if (values.type !== 'filter_applications') continue;
      const query = new URLSearchParams();
      if (typeof values.search === 'string' && values.search) query.set('search', values.search);
      if (typeof values.status === 'string' && values.status !== 'all') query.set('status', values.status);
      navigate(`/applications${query.size ? `?${query.toString()}` : ''}`);
      return;
    }
  }

  async function submit() {
    const prompt = draft.trim();
    if (!prompt || runState === 'working') return;
    setError('');
    if (prompt === '/new') {
      await newConversation();
      setDraft('');
      return;
    }
    if (prompt === '/clear') {
      if (!activeConversationId) await newConversation();
      else await clearConversation(activeConversationId);
      setDraft('');
      queryClient.invalidateQueries({ queryKey: ['conversation-messages', activeConversationId] });
      return;
    }

    setRunState('working');
    setActivity([]);
    try {
      const conversation = activeConversationId
        ? { id: activeConversationId }
        : await newConversation(prompt.slice(0, 70));
      setDraft('');
      const run = await createAutomationRun({
        prompt,
        conversationId: conversation.id,
        context: {
          page: location.pathname,
          application_id: applicationId,
          interaction: 'global_assistant'
        }
      });
      queryClient.invalidateQueries({ queryKey: ['conversation-messages', conversation.id] });
      const finished = await waitForRun(run.id);
      if (finished.status === 'failed') throw new Error(finished.error || 'The automation failed.');
      if (finished.status === 'waiting_approval') setError('This workflow needs your approval before changing workspace data.');
      if (finished.status === 'completed') applyWorkspaceAction(finished);
      queryClient.invalidateQueries({ queryKey: ['conversation-messages', conversation.id] });
      queryClient.invalidateQueries({ queryKey: ['automation-runs'] });
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : 'The assistant could not complete the request.');
      setRunState('error');
      return;
    }
    setRunState('idle');
  }

  function toggleVoice() {
    if (listening) {
      recognitionRef.current?.stop();
      return;
    }
    const Recognition = speechRecognitionConstructor();
    if (!Recognition) {
      setError('Voice dictation is not supported in this browser.');
      return;
    }
    const recognition = new Recognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';
    recognition.onresult = (event) => {
      const transcript = event.results[0]?.[0]?.transcript || '';
      setDraft((current) => `${current}${current ? ' ' : ''}${transcript}`);
    };
    recognition.onend = () => setListening(false);
    recognition.onerror = () => {
      setListening(false);
      setError('Voice dictation stopped before a transcript was available.');
    };
    recognitionRef.current = recognition;
    setListening(true);
    recognition.start();
  }

  return (
    <>
      <Button
        className="fixed bottom-5 right-5 z-40 size-14 rounded-2xl px-0 shadow-overlay sm:bottom-7 sm:right-7"
        onClick={() => { setApplicationId(null); setOpen(true); }}
        aria-label="Open assistant"
      >
        <Sparkles className="size-5" aria-hidden="true" />
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent placement="right" className="flex overflow-hidden p-0 sm:w-[min(92vw,580px)]">
          <div className="flex min-h-0 flex-1 flex-col">
            <DialogHeader className="mb-0 border-b border-border px-5 py-5 pr-16">
              <div className="flex items-center gap-2"><Bot className="size-5 text-primary" aria-hidden="true" /><DialogTitle>Workspace assistant</DialogTitle></div>
              <DialogDescription>Ask from anywhere. The current page and selected application stay in context.</DialogDescription>
            </DialogHeader>

            <div className="flex items-center gap-2 border-b border-border px-4 py-3">
              <label className="min-w-0 flex-1">
                <span className="sr-only">Conversation</span>
                <select className="h-10 w-full rounded-lg border border-border bg-surface px-3 text-[13px]" value={activeConversationId || ''} onChange={(event) => setActiveConversationId(event.target.value)}>
                  <option value="" disabled>Choose a conversation</option>
                  {(conversations.data || []).map((conversation) => <option key={conversation.id} value={conversation.id}>{conversation.title}</option>)}
                </select>
              </label>
              <Button variant="outline" size="sm" onClick={() => newConversation()}><Plus className="size-4" aria-hidden="true" />New chat</Button>
            </div>

            <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-5" aria-live="polite">
              {!messages.data?.length && (
                <div className="rounded-3xl bg-primary-soft p-5">
                  <p className="font-semibold">Start with the outcome</p>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">Try “Show applications waiting more than ten days” or “Draft a follow-up for the selected role.”</p>
                  <p className="mt-3 text-xs text-muted-foreground">Commands: /new and /clear</p>
                </div>
              )}
              {messages.data?.map((message) => (
                <div key={message.id} className={cn('max-w-[90%] rounded-2xl px-4 py-3 text-sm', message.role === 'user' ? 'ml-auto bg-primary text-white' : message.role === 'system' ? 'mx-auto bg-surface-subtle text-xs text-muted-foreground' : 'bg-surface-subtle text-foreground')}>
                  {message.role === 'assistant' ? (
                    <Suspense fallback={<p>{message.content}</p>}>
                      <MarkdownContent>{message.content}</MarkdownContent>
                    </Suspense>
                  ) : message.content}
                </div>
              ))}
              {runState === 'working' && (
                <div className="rounded-2xl bg-surface-subtle px-4 py-3 text-sm text-muted-foreground">
                  <div className="flex items-center gap-2"><LoaderCircle className="size-4 animate-spin motion-reduce:animate-none" aria-hidden="true" />Planning and running the workflow</div>
                  {activity.length > 0 && <ul className="mt-2 space-y-1 text-xs">{activity.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul>}
                </div>
              )}
              {error && <p className="rounded-xl bg-danger-soft p-3 text-sm text-danger">{error}</p>}
            </div>

            <div className="border-t border-border bg-surface px-4 py-4">
              <div className="rounded-2xl border border-border bg-background p-2 focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/15">
                <Textarea value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); submit(); } }} className="min-h-20 resize-none border-0 bg-transparent focus-visible:ring-0" placeholder="Ask about your pipeline, a role, or the next action" />
                <div className="flex items-center justify-between gap-2">
                  <Button variant="ghost" size="icon" onClick={toggleVoice} aria-label={listening ? 'Stop voice input' : 'Start voice input'}>{listening ? <MicOff className="size-4.5" aria-hidden="true" /> : <Mic className="size-4.5" aria-hidden="true" />}</Button>
                  <Button size="icon" onClick={submit} disabled={!draft.trim() || runState === 'working'} aria-label="Send message"><Send className="size-4.5" aria-hidden="true" /></Button>
                </div>
              </div>
              <p className="mt-2 text-center text-xs text-muted-foreground">The assistant drafts external communication. Sending always requires review.</p>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
