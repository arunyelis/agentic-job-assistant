import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  }).format(new Date(value));
}

export function formatRelativeDate(value: string) {
  const date = new Date(value);
  const today = new Date();
  const difference = Math.round((date.getTime() - today.getTime()) / 86_400_000);
  if (difference === 0) return 'Today';
  if (difference === -1) return 'Yesterday';
  if (difference > -7 && difference < 0) return `${Math.abs(difference)} days ago`;
  return formatDate(value);
}
