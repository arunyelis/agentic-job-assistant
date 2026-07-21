import { useMutation, useQueryClient } from '@tanstack/react-query';
import { CheckCircle2, ShieldCheck } from 'lucide-react';
import { type FormEvent, useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { captureApplication } from '@/lib/api';

interface CaptureDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CaptureDialog({ open, onOpenChange }: CaptureDialogProps) {
  const queryClient = useQueryClient();
  const [company, setCompany] = useState('');
  const [role, setRole] = useState('');
  const [url, setUrl] = useState('');
  const [saved, setSaved] = useState(false);

  const mutation = useMutation({
    mutationFn: captureApplication,
    onSuccess: async () => {
      setSaved(true);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['today'] }),
        queryClient.invalidateQueries({ queryKey: ['applications'] }),
        queryClient.invalidateQueries({ queryKey: ['capture-inbox'] })
      ]);
    }
  });

  useEffect(() => {
    if (open) return;
    setCompany('');
    setRole('');
    setUrl('');
    setSaved(false);
    mutation.reset();
  }, [open]);

  function submit(event: FormEvent) {
    event.preventDefault();
    mutation.mutate({ company, role, sourceUrl: url, sourceType: 'manual' });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        {saved ? (
          <div className="py-5 text-center" role="status">
            <div className="mx-auto grid size-14 place-items-center rounded-2xl bg-success-soft text-success">
              <CheckCircle2 className="size-7" aria-hidden="true" />
            </div>
            <h2 className="mt-4 text-xl font-semibold">Application saved</h2>
            <p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-muted-foreground">
              It is now available in your application timeline.
            </p>
            <Button className="mt-6" onClick={() => onOpenChange(false)}>Done</Button>
          </div>
        ) : (
          <form onSubmit={submit}>
            <DialogHeader>
              <DialogTitle>Add an application</DialogTitle>
              <DialogDescription>
                Use this when a site is not connected to the capture extension.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <label className="block space-y-1.5">
                <span className="text-[13px] font-semibold">Company</span>
                <Input value={company} onChange={(event) => setCompany(event.target.value)} required autoFocus />
              </label>
              <label className="block space-y-1.5">
                <span className="text-[13px] font-semibold">Role</span>
                <Input value={role} onChange={(event) => setRole(event.target.value)} required />
              </label>
              <label className="block space-y-1.5">
                <span className="text-[13px] font-semibold">Application URL</span>
                <Input
                  type="url"
                  value={url}
                  onChange={(event) => setUrl(event.target.value)}
                  placeholder="https://company.example/jobs/123"
                  required
                />
              </label>
              <div className="flex gap-2.5 rounded-xl bg-primary-soft p-3 text-[13px] leading-5 text-primary-strong">
                <ShieldCheck className="mt-0.5 size-4.5 shrink-0" aria-hidden="true" />
                Screenshots are not collected by this form. In the extension they remain off until you choose to include one.
              </div>
              {mutation.error && (
                <p className="rounded-xl bg-danger-soft px-3 py-2.5 text-[13px] text-danger" role="alert">
                  {mutation.error.message}
                </p>
              )}
            </div>
            <div className="mt-6 flex justify-end gap-2.5">
              <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? 'Saving…' : 'Save application'}
              </Button>
            </div>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
