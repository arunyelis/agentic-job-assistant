import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import type { ButtonHTMLAttributes } from 'react';

import { cn } from '@/lib/utils';

export const buttonVariants = cva(
  'inline-flex min-h-11 items-center justify-center gap-2 whitespace-nowrap rounded-[10px] px-4 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50 motion-reduce:transition-none',
  {
    variants: {
      variant: {
        default: 'bg-primary text-white hover:bg-primary-strong active:bg-primary-strong',
        secondary: 'bg-surface-subtle text-foreground hover:bg-border',
        outline: 'border border-border bg-surface text-foreground hover:bg-surface-subtle',
        ghost: 'text-muted-foreground hover:bg-surface-subtle hover:text-foreground',
        danger: 'bg-danger text-white hover:bg-danger/90'
      },
      size: {
        default: 'h-11',
        sm: 'h-9 min-h-9 px-3 text-[13px]',
        lg: 'h-12 px-5',
        icon: 'size-11 px-0'
      }
    },
    defaultVariants: {
      variant: 'default',
      size: 'default'
    }
  }
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export function Button({ className, variant, size, asChild, ...props }: ButtonProps) {
  const Component = asChild ? Slot : 'button';
  return <Component className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}
