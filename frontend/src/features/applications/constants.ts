import type { ApplicationStatus } from '@/types';

export const PIPELINE_STAGES: Array<{ id: ApplicationStatus; label: string; tone: string }> = [
  { id: 'captured', label: 'Captured', tone: 'bg-surface-subtle' },
  { id: 'applied', label: 'Applied', tone: 'bg-primary-soft' },
  { id: 'assessment', label: 'Assessment', tone: 'bg-warning-soft' },
  { id: 'interview', label: 'Interview', tone: 'bg-success-soft' },
  { id: 'offer', label: 'Offer', tone: 'bg-success-soft' },
  { id: 'rejected', label: 'Closed', tone: 'bg-danger-soft' },
  { id: 'withdrawn', label: 'Withdrawn', tone: 'bg-surface-subtle' }
];

export const APPLICATION_STATUS_OPTIONS = [
  'all',
  'captured',
  'applied',
  'assessment',
  'interview',
  'offer',
  'rejected',
  'withdrawn'
];
