import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { BriefcaseBusiness, LayoutGrid, Search, Table2 } from 'lucide-react';
import { useDeferredValue, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { ApplicationDetail } from '@/components/ApplicationDetail';
import { useCaptureDialog } from '@/components/AppShell';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';
import { Input } from '@/components/ui/input';
import { ApplicationsTable } from '@/features/applications/ApplicationsTable';
import { APPLICATION_STATUS_OPTIONS } from '@/features/applications/constants';
import { PipelineBoard } from '@/features/applications/PipelineBoard';
import { getApplications, updateApplication } from '@/lib/api';
import { cn } from '@/lib/utils';
import type { ApplicationRecord, ApplicationStatus } from '@/types';

type ViewMode = 'pipeline' | 'table';

export function ApplicationsPage() {
  const openCapture = useCaptureDialog();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState(() => searchParams.get('search') || '');
  const [status, setStatus] = useState(() => {
    const requested = searchParams.get('status') || 'all';
    return APPLICATION_STATUS_OPTIONS.includes(requested) ? requested : 'all';
  });
  const [selected, setSelected] = useState<ApplicationRecord | null>(null);
  const [view, setView] = useState<ViewMode>(() => (localStorage.getItem('career-applications-view') as ViewMode) || 'pipeline');
  const deferredSearch = useDeferredValue(search);
  useEffect(() => {
    const next = new URLSearchParams();
    if (deferredSearch) next.set('search', deferredSearch);
    if (status !== 'all') next.set('status', status);
    setSearchParams(next, { replace: true });
  }, [deferredSearch, setSearchParams, status]);
  const query = useQuery({
    queryKey: ['applications', deferredSearch, status],
    queryFn: () => getApplications({ search: deferredSearch, status })
  });
  const statusMutation = useMutation({
    mutationFn: ({ application, nextStatus }: { application: ApplicationRecord; nextStatus: ApplicationStatus }) => updateApplication(application.id, { status: nextStatus }),
    onMutate: async ({ application, nextStatus }) => {
      await queryClient.cancelQueries({ queryKey: ['applications'] });
      const snapshots = queryClient.getQueriesData<ApplicationRecord[]>({ queryKey: ['applications'] });
      snapshots.forEach(([key, records]) => {
        if (!records) return;
        queryClient.setQueryData<ApplicationRecord[]>(key, records.map((item) => item.id === application.id ? { ...item, status: nextStatus } : item));
      });
      setSelected((current) => current?.id === application.id ? { ...current, status: nextStatus } : current);
      return { snapshots };
    },
    onError: (_error, _variables, context) => {
      context?.snapshots.forEach(([key, records]) => queryClient.setQueryData(key, records));
    },
    onSettled: (_data, _error, variables) => {
      queryClient.invalidateQueries({ queryKey: ['applications'] });
      queryClient.invalidateQueries({ queryKey: ['today'] });
      queryClient.invalidateQueries({ queryKey: ['application-timeline', variables.application.id] });
    }
  });

  function changeView(next: ViewMode) {
    setView(next);
    localStorage.setItem('career-applications-view', next);
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center">
        <div className="flex flex-1 flex-col gap-3 sm:flex-row">
          <label className="relative min-w-0 flex-1">
            <span className="sr-only">Search applications</span>
            <Search className="pointer-events-none absolute left-3.5 top-1/2 size-4.5 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
            <Input className="pl-10" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search by company or role" />
          </label>
          <label>
            <span className="sr-only">Filter by status</span>
            <select className="h-11 min-w-40 rounded-[10px] border border-border bg-surface px-3.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" value={status} onChange={(event) => setStatus(event.target.value)}>
              {APPLICATION_STATUS_OPTIONS.map((option) => <option key={option} value={option}>{option === 'all' ? 'All stages' : option[0].toUpperCase() + option.slice(1)}</option>)}
            </select>
          </label>
        </div>
        <div className="inline-flex w-fit rounded-xl bg-surface-subtle p-1" aria-label="Application view">
          <button type="button" onClick={() => changeView('pipeline')} className={cn('inline-flex min-h-10 items-center gap-2 rounded-lg px-3 text-[13px] font-semibold text-muted-foreground', view === 'pipeline' && 'bg-surface text-foreground shadow-sm')} aria-pressed={view === 'pipeline'}><LayoutGrid className="size-4" aria-hidden="true" />Pipeline</button>
          <button type="button" onClick={() => changeView('table')} className={cn('inline-flex min-h-10 items-center gap-2 rounded-lg px-3 text-[13px] font-semibold text-muted-foreground', view === 'table' && 'bg-surface text-foreground shadow-sm')} aria-pressed={view === 'table'}><Table2 className="size-4" aria-hidden="true" />Table</button>
        </div>
      </div>

      <div aria-live="polite" className="flex items-center justify-between text-xs text-muted-foreground">
        <span>{query.data ? `${query.data.length} application${query.data.length === 1 ? '' : 's'}` : 'Loading applications'}</span>
        {statusMutation.isPending && <span>Saving stage change</span>}
      </div>

      {query.isLoading ? (
        <div className="h-[420px] animate-pulse rounded-3xl bg-surface-subtle motion-reduce:animate-none" aria-label="Loading applications" />
      ) : query.error ? (
        <EmptyState icon={BriefcaseBusiness} title="Applications could not be loaded" description={query.error.message} action={<Button onClick={() => query.refetch()}>Try again</Button>} />
      ) : query.data?.length ? (
        view === 'pipeline' ? (
          <PipelineBoard applications={query.data} onSelect={setSelected} onStatusChange={(application, nextStatus) => statusMutation.mutate({ application, nextStatus })} />
        ) : <ApplicationsTable applications={query.data} onSelect={setSelected} />
      ) : (
        <EmptyState
          icon={BriefcaseBusiness}
          title={search || status !== 'all' ? 'No applications match these filters' : 'No applications yet'}
          description={search || status !== 'all' ? 'Change the search or stage filter to see more records.' : 'Capture a submitted application or add one manually to start your pipeline.'}
          action={!search && status === 'all' ? <Button onClick={openCapture}>Add application</Button> : undefined}
        />
      )}

      <ApplicationDetail application={selected} onOpenChange={(open) => !open && setSelected(null)} />
    </div>
  );
}
