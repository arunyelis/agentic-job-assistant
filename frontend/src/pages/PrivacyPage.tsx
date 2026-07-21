import { useMutation } from '@tanstack/react-query';
import { CheckCircle2, Database, Download, KeyRound, LockKeyhole, Mail, MonitorSmartphone, ShieldCheck, Trash2 } from 'lucide-react';
import { useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { deleteAccount, downloadAccountExport } from '@/lib/api';
import { formatDate } from '@/lib/utils';
import type { DeletionReceipt } from '@/types';

function Setting({ icon: Icon, title, description, action }: { icon: typeof ShieldCheck; title: string; description: string; action: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-3 border-b border-border py-4 last:border-b-0 sm:flex-row sm:items-center">
      <div className="flex min-w-0 flex-1 items-start gap-3">
        <div className="grid size-10 shrink-0 place-items-center rounded-xl bg-surface-subtle text-muted-foreground"><Icon className="size-5" aria-hidden="true" /></div>
        <div>
          <h3 className="text-sm font-semibold">{title}</h3>
          <p className="mt-1 max-w-2xl text-[13px] leading-5 text-muted-foreground">{description}</p>
        </div>
      </div>
      <div className="shrink-0 sm:pl-4">{action}</div>
    </div>
  );
}

export function PrivacyPage() {
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [confirmation, setConfirmation] = useState('');
  const [receipt, setReceipt] = useState<DeletionReceipt | null>(null);
  const [exportError, setExportError] = useState('');
  const deletion = useMutation({
    mutationFn: deleteAccount,
    onSuccess: (data) => {
      setReceipt(data);
      setDeleteOpen(false);
    }
  });

  async function exportData() {
    setExportError('');
    try {
      await downloadAccountExport();
    } catch (error) {
      setExportError(error instanceof Error ? error.message : 'The export could not be created.');
    }
  }

  if (receipt) {
    return (
      <Card className="mx-auto max-w-2xl p-6 sm:p-8" role="status">
        <div className="grid size-14 place-items-center rounded-2xl bg-success-soft text-success"><CheckCircle2 className="size-7" aria-hidden="true" /></div>
        <h2 className="mt-5 text-2xl font-semibold">Account data removed</h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">The local account was cleared and the deletion receipt remains available without personal content.</p>
        <dl className="mt-6 grid gap-4 rounded-xl bg-surface-subtle p-4 text-[13px] sm:grid-cols-2">
          <div><dt className="font-semibold">Receipt</dt><dd className="mt-1 break-all text-muted-foreground">{receipt.id}</dd></div>
          <div><dt className="font-semibold">Status</dt><dd className="mt-1 text-muted-foreground">{receipt.status}</dd></div>
          <div><dt className="font-semibold">Completed</dt><dd className="mt-1 text-muted-foreground">{receipt.completed_at ? formatDate(receipt.completed_at) : 'Pending'}</dd></div>
          <div><dt className="font-semibold">Backup expiry target</dt><dd className="mt-1 text-muted-foreground">{receipt.backup_expires_at ? formatDate(receipt.backup_expires_at) : 'Not available'}</dd></div>
          <div><dt className="font-semibold">Artifacts removed</dt><dd className="mt-1 text-muted-foreground">{receipt.artifacts_removed}</dd></div>
          <div><dt className="font-semibold">Categories removed</dt><dd className="mt-1 text-muted-foreground">{receipt.categories_removed.length}</dd></div>
        </dl>
        <p className="mt-5 text-xs leading-5 text-muted-foreground">Reload the application to create a new empty local development account.</p>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card className="p-5 sm:p-6">
        <div className="flex items-start gap-4">
          <div className="grid size-12 shrink-0 place-items-center rounded-2xl bg-success-soft text-success"><ShieldCheck className="size-6" aria-hidden="true" /></div>
          <div>
            <div className="flex flex-wrap items-center gap-2"><h2 className="text-lg font-semibold">Your data controls</h2><Badge variant="success">Active</Badge></div>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">Career Workspace records confirmed applications only. Screenshots are disabled by default, Gmail is not connected, and operational logs exclude resume, chat, email, and screenshot content.</p>
          </div>
        </div>
      </Card>

      <section aria-labelledby="storage-title">
        <h2 id="storage-title" className="mb-3 text-lg font-semibold">Storage and integrations</h2>
        <Card className="px-5">
          <Setting icon={Database} title="Cloud-account shaped storage" description="Application records are stored in the configured database. Local development uses an encrypted local artifact directory and can switch to PostgreSQL without changing the ownership model." action={<Badge variant="info">Configured</Badge>} />
          <Setting icon={MonitorSmartphone} title="Browser capture" description="The extension requests access only after you enable the current site. A detection stays in the extension until you confirm it." action={<Badge variant="neutral">User controlled</Badge>} />
          <Setting icon={Mail} title="Gmail" description="Email access is intentionally unavailable in this release. It requires separate consent, restricted-scope verification, and a security assessment." action={<Badge variant="neutral">Not connected</Badge>} />
          <Setting icon={KeyRound} title="AI provider" description="Resume and prompt content is sent to the model configured by the local operator only after the user starts an assistant request." action={<Badge variant="warning">External processor</Badge>} />
          <Setting icon={LockKeyhole} title="Screenshots" description="Screenshot capture is disabled unless the user selects it in the extension confirmation screen." action={<Badge variant="success">Off by default</Badge>} />
        </Card>
      </section>

      <section aria-labelledby="account-data-title">
        <h2 id="account-data-title" className="mb-3 text-lg font-semibold">Account data</h2>
        <Card className="divide-y divide-border">
          <div className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center">
            <div className="min-w-0 flex-1"><h3 className="text-sm font-semibold">Export your data</h3><p className="mt-1 text-[13px] leading-5 text-muted-foreground">Download applications, artifact metadata, and consent records as readable JSON.</p>{exportError && <p className="mt-2 text-[13px] text-danger" role="alert">{exportError}</p>}</div>
            <Button variant="outline" onClick={exportData}><Download className="size-4" aria-hidden="true" /> Download export</Button>
          </div>
          <div className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center">
            <div className="min-w-0 flex-1"><h3 className="text-sm font-semibold">Delete account data</h3><p className="mt-1 text-[13px] leading-5 text-muted-foreground">Remove applications, artifacts, evidence, consent, audit records, and derived data. A minimal receipt remains.</p></div>
            <Button variant="danger" onClick={() => setDeleteOpen(true)}><Trash2 className="size-4" aria-hidden="true" /> Delete data</Button>
          </div>
        </Card>
      </section>

      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete account data?</DialogTitle>
            <DialogDescription>This action removes the current account’s stored data and cannot be undone. Type DELETE to confirm.</DialogDescription>
          </DialogHeader>
          <label className="block space-y-1.5"><span className="text-[13px] font-semibold">Confirmation</span><Input value={confirmation} onChange={(event) => setConfirmation(event.target.value)} autoComplete="off" /></label>
          {deletion.error && <p className="mt-3 rounded-xl bg-danger-soft p-3 text-[13px] text-danger" role="alert">{deletion.error.message}</p>}
          <div className="mt-6 flex justify-end gap-2.5"><Button variant="ghost" onClick={() => setDeleteOpen(false)}>Cancel</Button><Button variant="danger" disabled={confirmation !== 'DELETE' || deletion.isPending} onClick={() => deletion.mutate()}>{deletion.isPending ? 'Deleting…' : 'Delete account data'}</Button></div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
