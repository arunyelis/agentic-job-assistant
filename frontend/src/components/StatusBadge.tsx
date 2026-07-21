import { Badge, type BadgeProps } from '@/components/ui/badge';
import type { ApplicationStatus } from '@/types';

const LABELS: Record<ApplicationStatus, string> = {
  captured: 'Captured',
  applied: 'Applied',
  assessment: 'Assessment',
  interview: 'Interview',
  offer: 'Offer',
  rejected: 'Rejected',
  withdrawn: 'Withdrawn'
};

const VARIANTS: Record<ApplicationStatus, BadgeProps['variant']> = {
  captured: 'neutral',
  applied: 'info',
  assessment: 'warning',
  interview: 'warning',
  offer: 'success',
  rejected: 'danger',
  withdrawn: 'neutral'
};

export function StatusBadge({ status }: { status: ApplicationStatus }) {
  return <Badge variant={VARIANTS[status]}>{LABELS[status]}</Badge>;
}
