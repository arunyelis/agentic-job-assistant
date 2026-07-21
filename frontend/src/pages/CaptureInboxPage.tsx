import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, Inbox } from 'lucide-react';

import { ApplicationCard } from '@/components/ApplicationCard';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';
import { getApplications, updateApplication } from '@/lib/api';

export function CaptureInboxPage() {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ['capture-inbox'],
    queryFn: () => getApplications({ needsReview: true })
  });
  const review = useMutation({
    mutationFn: (applicationId: string) => updateApplication(applicationId, { needs_review: false }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['capture-inbox'] }),
        queryClient.invalidateQueries({ queryKey: ['today'] }),
        queryClient.invalidateQueries({ queryKey: ['applications'] })
      ]);
    }
  });

  if (query.isLoading) return <div className="h-64 animate-pulse rounded-2xl bg-surface-subtle motion-reduce:animate-none" />;
  if (query.error) return <EmptyState icon={Inbox} title="The capture inbox could not be loaded" description={query.error.message} action={<Button onClick={() => query.refetch()}>Try again</Button>} />;
  if (!query.data?.length) {
    return <EmptyState icon={Inbox} title="Nothing needs review" description="Low-confidence browser captures will wait here until you confirm the extracted company and role." />;
  }

  return (
    <div className="space-y-3">
      {query.data.map((application) => (
        <ApplicationCard
          key={application.id}
          application={application}
          action={
            <Button variant="outline" size="sm" onClick={() => review.mutate(application.id)} disabled={review.isPending}>
              <Check className="size-4" aria-hidden="true" /> Reviewed
            </Button>
          }
        />
      ))}
    </div>
  );
}
