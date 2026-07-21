import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Bot, Braces, GitBranch, LoaderCircle, Plus, Workflow } from 'lucide-react';
import { useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { createAgent, getAgents, getAutomationRuns, getAutomationTools } from '@/lib/api';

export function AutomationsPage() {
  const queryClient = useQueryClient();
  const [agentOpen, setAgentOpen] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [instructions, setInstructions] = useState('');
  const [allowedTools, setAllowedTools] = useState<string[]>([]);
  const tools = useQuery({ queryKey: ['automation-tools'], queryFn: getAutomationTools });
  const agents = useQuery({ queryKey: ['automation-agents'], queryFn: getAgents });
  const runs = useQuery({ queryKey: ['automation-runs'], queryFn: getAutomationRuns, refetchInterval: 2_000 });
  const createMutation = useMutation({
    mutationFn: () => createAgent({ name, description, instructions, allowedTools }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['automation-agents'] });
      setAgentOpen(false);
      setName('');
      setDescription('');
      setInstructions('');
      setAllowedTools([]);
    }
  });

  function toggleTool(tool: string) {
    setAllowedTools((current) => current.includes(tool) ? current.filter((item) => item !== tool) : [...current, tool]);
  }

  return (
    <div className="space-y-8">
      <section className="grid gap-3 md:grid-cols-3" aria-label="Execution modes">
        <Card className="p-5"><Workflow className="size-5 text-primary" aria-hidden="true" /><h2 className="mt-4 font-semibold">Sequential</h2><p className="mt-2 text-[13px] leading-5 text-muted-foreground">Use dependencies when later work needs an earlier result.</p></Card>
        <Card className="p-5"><GitBranch className="size-5 text-primary" aria-hidden="true" /><h2 className="mt-4 font-semibold">Parallel</h2><p className="mt-2 text-[13px] leading-5 text-muted-foreground">Run independent research or analysis tasks at the same time.</p></Card>
        <Card className="p-5"><Braces className="size-5 text-primary" aria-hidden="true" /><h2 className="mt-4 font-semibold">Model planned</h2><p className="mt-2 text-[13px] leading-5 text-muted-foreground">Let the assistant select tools and build a bounded task graph.</p></Card>
      </section>

      <section aria-labelledby="agents-title">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div><h2 id="agents-title" className="text-lg font-semibold">Custom agents</h2><p className="mt-1 text-[13px] text-muted-foreground">Give a focused agent only the tools it needs.</p></div>
          <Button onClick={() => setAgentOpen(true)}><Plus className="size-4" aria-hidden="true" />Create agent</Button>
        </div>
        {agents.data?.length ? (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {agents.data.map((agent) => <Card key={agent.id} className="p-5"><div className="flex items-start justify-between gap-3"><div className="grid size-10 place-items-center rounded-xl bg-primary-soft text-primary"><Bot className="size-5" aria-hidden="true" /></div><Badge>{agent.enabled ? 'Active' : 'Paused'}</Badge></div><h3 className="mt-4 font-semibold">{agent.name}</h3><p className="mt-1 text-[13px] leading-5 text-muted-foreground">{agent.description || 'No description'}</p><div className="mt-4 flex flex-wrap gap-1.5">{agent.allowed_tools.map((tool) => <span key={tool} className="rounded-lg bg-surface-subtle px-2 py-1 text-xs text-muted-foreground">{tool}</span>)}</div></Card>)}
          </div>
        ) : <Card className="p-6 text-sm text-muted-foreground">No custom agents yet. The default coordinator remains available in the assistant.</Card>}
      </section>

      <section aria-labelledby="runs-title">
        <div className="mb-4"><h2 id="runs-title" className="text-lg font-semibold">Recent runs</h2><p className="mt-1 text-[13px] text-muted-foreground">Durable status, tasks, and events for debugging and evaluation.</p></div>
        <Card className="overflow-hidden">
          {runs.isLoading ? <div className="flex items-center gap-2 p-5 text-sm text-muted-foreground"><LoaderCircle className="size-4 animate-spin" aria-hidden="true" />Loading runs</div> : runs.data?.length ? runs.data.slice(0, 8).map((run) => <div key={run.id} className="flex items-center gap-4 border-b border-border px-5 py-4 last:border-0"><span className="grid size-9 place-items-center rounded-xl bg-surface-subtle"><Workflow className="size-4" aria-hidden="true" /></span><div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold">{run.prompt}</p><p className="mt-0.5 text-xs text-muted-foreground">{run.tasks.length} tasks · {run.mode}</p></div><Badge variant={run.status === 'completed' ? 'success' : run.status === 'failed' ? 'danger' : 'info'}>{run.status.replace('_', ' ')}</Badge></div>) : <p className="p-5 text-sm text-muted-foreground">No automation runs yet. Ask the workspace assistant to create the first one.</p>}
        </Card>
      </section>

      <Dialog open={agentOpen} onOpenChange={setAgentOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Create a custom agent</DialogTitle><DialogDescription>Define its responsibility and allow only the required tools.</DialogDescription></DialogHeader>
          <div className="space-y-4">
            <label className="block space-y-1.5"><span className="text-[13px] font-semibold">Name</span><Input value={name} onChange={(event) => setName(event.target.value)} placeholder="Follow-up coach" /></label>
            <label className="block space-y-1.5"><span className="text-[13px] font-semibold">Description</span><Input value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Drafts evidence-based follow-ups" /></label>
            <label className="block space-y-1.5"><span className="text-[13px] font-semibold">Instructions</span><Textarea value={instructions} onChange={(event) => setInstructions(event.target.value)} className="min-h-28" placeholder="State what this agent should do, what it must verify, and when it must stop." /></label>
            <fieldset><legend className="mb-2 text-[13px] font-semibold">Allowed tools</legend><div className="space-y-2">{tools.data?.map((tool) => <label key={tool.name} className="flex min-h-11 items-start gap-3 rounded-xl border border-border px-3.5 py-3"><input className="mt-0.5" type="checkbox" checked={allowedTools.includes(tool.name)} onChange={() => toggleTool(tool.name)} /><span><span className="block text-sm font-medium">{tool.name}</span><span className="mt-0.5 block text-xs text-muted-foreground">{tool.description}{tool.requires_confirmation ? ' Confirmation required.' : ''}</span></span></label>)}</div></fieldset>
            {createMutation.error && <p className="text-sm text-danger">{createMutation.error.message}</p>}
            <div className="flex justify-end gap-2"><Button variant="ghost" onClick={() => setAgentOpen(false)}>Cancel</Button><Button disabled={name.trim().length < 2 || instructions.trim().length < 10 || createMutation.isPending} onClick={() => createMutation.mutate()}>{createMutation.isPending ? 'Creating' : 'Create agent'}</Button></div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
