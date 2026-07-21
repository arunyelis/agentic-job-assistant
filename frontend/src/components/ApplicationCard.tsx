import { ExternalLink, FileCheck2, TriangleAlert } from 'lucide-react';
import type { ReactNode } from 'react';

import { StatusBadge } from '@/components/StatusBadge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { formatRelativeDate } from '@/lib/utils';
import type { ApplicationRecord } from '@/types';

interface ApplicationCardProps {
  application: ApplicationRecord;
  action?: ReactNode;
}

function initials(value: string) {
  return value
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase();
}

export function ApplicationCard({ application, action }: ApplicationCardProps) {
  return (
    <Card className="group p-4 transition-colors hover:border-primary/35 motion-reduce:transition-none">
      <div className="flex items-start gap-3.5">
        <div className="grid size-11 shrink-0 place-items-center rounded-xl bg-surface-subtle text-[13px] font-bold text-foreground">
          {initials(application.company)}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0">
              <h3 className="truncate text-[15px] font-semibold">{application.role}</h3>
              <p className="mt-0.5 truncate text-[13px] text-muted-foreground">{application.company}</p>
            </div>
            <StatusBadge status={application.status} />
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-foreground">
            <span>{formatRelativeDate(application.captured_at)}</span>
            <span className="inline-flex items-center gap-1.5">
              <FileCheck2 className="size-3.5" aria-hidden="true" />
              {application.source_type === 'extension' ? 'Browser capture' : 'Manual capture'}
            </span>
            {application.needs_review && (
              <span className="inline-flex items-center gap-1.5 font-semibold text-warning">
                <TriangleAlert className="size-3.5" aria-hidden="true" />
                Needs review
              </span>
            )}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          {action}
          <Button variant="ghost" size="icon" asChild aria-label={`Open ${application.role} source page`}>
            <a href={application.source_url} target="_blank" rel="noreferrer">
              <ExternalLink className="size-4.5" aria-hidden="true" />
            </a>
          </Button>
        </div>
      </div>
    </Card>
  );
}
