import { useQuery } from '@tanstack/react-query';
import { ArrowRight, Bot, BriefcaseBusiness, Inbox, Sparkles, Target } from 'lucide-react';
import { Link } from 'react-router-dom';

import { ApplicationCard } from '@/components/ApplicationCard';
import { useCaptureDialog } from '@/components/AppShell';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { EmptyState } from '@/components/ui/empty-state';
import { getToday } from '@/lib/api';

function Stat({ label, value, note, icon: Icon }: { label: string; value: number; note: string; icon: typeof Target }) {
  return (
    <Card className="p-4 sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[13px] font-medium text-muted-foreground">{label}</p>
          <p className="mt-2 text-3xl font-semibold tracking-[-0.04em]">{value}</p>
          <p className="mt-1 text-xs text-muted-foreground">{note}</p>
        </div>
        <div className="grid size-10 place-items-center rounded-xl bg-primary-soft text-primary">
          <Icon className="size-5" aria-hidden="true" />
        </div>
      </div>
    </Card>
  );
}

export function TodayPage() {
  const openCapture = useCaptureDialog();
  const query = useQuery({ queryKey: ['today'], queryFn: getToday });

  if (query.isLoading) {
    return <div className="h-72 animate-pulse rounded-2xl bg-surface-subtle motion-reduce:animate-none" aria-label="Loading workspace" />;
  }
  if (query.error) {
    return (
      <EmptyState
        icon={Target}
        title="Today could not be loaded"
        description={query.error.message}
        action={<Button onClick={() => query.refetch()}>Try again</Button>}
      />
    );
  }

  const summary = query.data!;
  const active = (summary.counts.applied || 0) + (summary.counts.assessment || 0) + (summary.counts.interview || 0);

  return (
    <div className="space-y-8">
      <section aria-labelledby="overview-title">
        <div className="mb-4 flex items-end justify-between gap-4">
          <div>
            <p className="text-[13px] font-semibold text-primary">Workspace overview</p>
            <h2 id="overview-title" className="mt-1 text-2xl font-semibold tracking-[-0.025em]">Keep the search moving</h2>
          </div>
          <Button variant="ghost" asChild>
            <Link to="/applications">View timeline <ArrowRight className="size-4" aria-hidden="true" /></Link>
          </Button>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Stat label="Applications" value={summary.total} note="Confirmed records" icon={BriefcaseBusiness} />
          <Stat label="Active" value={active} note="Applied or progressing" icon={Target} />
          <Stat label="Interviews" value={summary.counts.interview || 0} note="Current interview stage" icon={Sparkles} />
          <Stat label="Needs review" value={summary.needsReview} note="Low-confidence captures" icon={Inbox} />
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.45fr)_minmax(320px,.55fr)]">
        <section aria-labelledby="recent-title">
          <div className="mb-4 flex items-center justify-between">
            <h2 id="recent-title" className="text-lg font-semibold">Recent applications</h2>
            {summary.recent.length > 0 && <span className="text-xs text-muted-foreground">Latest five</span>}
          </div>
          {summary.recent.length ? (
            <div className="space-y-3">
              {summary.recent.map((application) => <ApplicationCard key={application.id} application={application} />)}
            </div>
          ) : (
            <EmptyState
              icon={BriefcaseBusiness}
              title="Your timeline starts with one application"
              description="Add an application manually now. The extension will use the same confirmation flow when it detects a submission."
              action={<Button onClick={openCapture}>Add first application</Button>}
            />
          )}
        </section>

        <aside className="space-y-4" aria-label="Workspace guidance">
          <Card className="overflow-hidden">
            <div className="bg-primary-soft p-5">
              <div className="grid size-11 place-items-center rounded-2xl bg-primary text-white">
                <Sparkles className="size-5" aria-hidden="true" />
              </div>
              <h2 className="mt-5 text-lg font-semibold text-foreground">Capture without maintaining a CRM</h2>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                The browser extension prepares a record after a likely submission. You confirm the company and role before it reaches your account.
              </p>
            </div>
            <div className="p-5">
              <ol className="space-y-3 text-[13px] text-muted-foreground">
                <li className="flex gap-3"><span className="font-semibold text-primary">1.</span> Enable capture for the current career site.</li>
                <li className="flex gap-3"><span className="font-semibold text-primary">2.</span> Complete the application normally.</li>
                <li className="flex gap-3"><span className="font-semibold text-primary">3.</span> Review and confirm the detected record.</li>
              </ol>
            </div>
          </Card>
          <Card className="p-5">
            <div className="flex items-start gap-3">
              <div className="grid size-10 shrink-0 place-items-center rounded-xl bg-success-soft text-success">
                <Bot className="size-5" aria-hidden="true" />
              </div>
              <div>
                <h2 className="font-semibold">Need help with a role?</h2>
                <p className="mt-1 text-[13px] leading-5 text-muted-foreground">Use your resume and a public job URL for an evidence-based review.</p>
                <Button className="mt-3 px-0" variant="ghost" size="sm" asChild>
                  <Link to="/assistant">Open assistant <ArrowRight className="size-4" aria-hidden="true" /></Link>
                </Button>
              </div>
            </div>
          </Card>
        </aside>
      </div>
    </div>
  );
}
