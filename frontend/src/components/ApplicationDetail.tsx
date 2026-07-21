import { useQuery } from '@tanstack/react-query';
import { Bot, CalendarClock, ExternalLink, Mail, Route, Sparkles } from 'lucide-react';

import { StatusBadge } from '@/components/StatusBadge';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { getApplicationTimeline } from '@/lib/api';
import { formatRelativeDate } from '@/lib/utils';
import type { ApplicationRecord } from '@/types';

interface ApplicationDetailProps {
  application: ApplicationRecord | null;
  onOpenChange: (open: boolean) => void;
}

export function ApplicationDetail({ application, onOpenChange }: ApplicationDetailProps) {
  const timeline = useQuery({
    queryKey: ['application-timeline', application?.id],
    queryFn: () => getApplicationTimeline(application!.id),
    enabled: Boolean(application)
  });

  function draftFollowUp() {
    if (!application) return;
    window.dispatchEvent(new CustomEvent('career-assistant-open', {
      detail: {
        prompt: `Draft a concise follow-up for my ${application.role} application at ${application.company}.`,
        applicationId: application.id
      }
    }));
  }

  return (
    <Dialog open={Boolean(application)} onOpenChange={onOpenChange}>
      <DialogContent placement="right" className="p-0">
        {application && (
          <div className="min-h-full">
            <DialogHeader className="border-b border-border px-6 py-6 pr-16">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <StatusBadge status={application.status} />
                {application.needs_review && <span className="text-xs font-semibold text-warning">Needs review</span>}
              </div>
              <DialogTitle className="text-2xl tracking-[-0.025em]">{application.role}</DialogTitle>
              <DialogDescription>{application.company}</DialogDescription>
            </DialogHeader>

            <div className="space-y-7 px-6 py-6">
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-2xl bg-surface-subtle p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground">Applied</p>
                  <p className="mt-2 text-sm font-semibold">{formatRelativeDate(application.captured_at)}</p>
                </div>
                <div className="rounded-2xl bg-surface-subtle p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.08em] text-muted-foreground">Email</p>
                  <p className="mt-2 text-sm font-semibold">No linked messages</p>
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                <Button onClick={draftFollowUp}>
                  <Bot className="size-4.5" aria-hidden="true" />
                  Draft follow-up
                </Button>
                <Button variant="outline" asChild>
                  <a href={application.source_url} target="_blank" rel="noreferrer">
                    <ExternalLink className="size-4.5" aria-hidden="true" />
                    Source page
                  </a>
                </Button>
              </div>

              <section aria-labelledby="timeline-title">
                <div className="mb-4 flex items-center gap-2">
                  <Route className="size-4.5 text-primary" aria-hidden="true" />
                  <h3 id="timeline-title" className="font-semibold">Progress timeline</h3>
                </div>
                {timeline.isLoading ? (
                  <div className="h-32 animate-pulse rounded-2xl bg-surface-subtle motion-reduce:animate-none" />
                ) : timeline.data?.length ? (
                  <ol className="relative space-y-5 border-l border-border pl-6">
                    {timeline.data.map((event) => (
                      <li key={event.id} className="relative">
                        <span className="absolute -left-[30px] top-1 grid size-3 rounded-full border-2 border-surface bg-primary" />
                        <p className="text-sm font-semibold">{event.title}</p>
                        <p className="mt-1 text-xs text-muted-foreground">{formatRelativeDate(event.occurred_at)}</p>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p className="rounded-2xl bg-surface-subtle p-4 text-sm text-muted-foreground">No progress events yet.</p>
                )}
              </section>

              <section className="space-y-3" aria-labelledby="workspace-details-title">
                <h3 id="workspace-details-title" className="font-semibold">Application workspace</h3>
                <div className="grid gap-2">
                  <div className="flex items-center gap-3 rounded-xl border border-border p-3.5">
                    <Mail className="size-4.5 text-muted-foreground" aria-hidden="true" />
                    <div><p className="text-sm font-medium">Communication</p><p className="text-xs text-muted-foreground">Email ingestion is not connected</p></div>
                  </div>
                  <div className="flex items-center gap-3 rounded-xl border border-border p-3.5">
                    <CalendarClock className="size-4.5 text-muted-foreground" aria-hidden="true" />
                    <div><p className="text-sm font-medium">Next action</p><p className="text-xs text-muted-foreground">{application.next_action_at ? formatRelativeDate(application.next_action_at) : 'Not scheduled'}</p></div>
                  </div>
                  <div className="flex items-center gap-3 rounded-xl border border-border p-3.5">
                    <Sparkles className="size-4.5 text-muted-foreground" aria-hidden="true" />
                    <div><p className="text-sm font-medium">Resume used</p><p className="text-xs text-muted-foreground">{application.selected_resume_id ? 'Linked resume version' : 'Not recorded'}</p></div>
                  </div>
                </div>
              </section>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
