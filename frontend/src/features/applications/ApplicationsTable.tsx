import {
  columnVisibilityFeature,
  createColumnHelper,
  tableFeatures,
  useTable,
  type ColumnVisibilityState
} from '@tanstack/react-table';
import { Columns3, Mail } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { StatusBadge } from '@/components/StatusBadge';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { formatRelativeDate } from '@/lib/utils';
import type { ApplicationRecord } from '@/types';

const features = tableFeatures({ columnVisibilityFeature });
const columnHelper = createColumnHelper<typeof features, ApplicationRecord>();

export function ApplicationsTable({ applications, onSelect }: { applications: ApplicationRecord[]; onSelect: (application: ApplicationRecord) => void }) {
  const [columnsOpen, setColumnsOpen] = useState(false);
  const [columnVisibility, setColumnVisibility] = useState<ColumnVisibilityState>(() => {
    try {
      return JSON.parse(localStorage.getItem('career-table-columns') || '{}');
    } catch {
      return {};
    }
  });
  useEffect(() => {
    localStorage.setItem('career-table-columns', JSON.stringify(columnVisibility));
  }, [columnVisibility]);

  const columns = useMemo(() => columnHelper.columns([
    columnHelper.accessor('role', {
      header: 'Role',
      cell: ({ row }) => (
        <button type="button" className="max-w-64 text-left font-semibold text-foreground hover:text-primary" onClick={() => onSelect(row.original)}>
          <span className="block truncate">{row.original.role}</span>
          <span className="mt-0.5 block truncate text-xs font-normal text-muted-foreground">{row.original.company}</span>
        </button>
      )
    }),
    columnHelper.accessor('status', { header: 'Stage', cell: (info) => <StatusBadge status={info.getValue()} /> }),
    columnHelper.accessor('captured_at', { header: 'Applied', cell: (info) => formatRelativeDate(info.getValue()) }),
    columnHelper.display({ id: 'email', header: 'Email', cell: () => <span className="inline-flex items-center gap-1.5 text-muted-foreground"><Mail className="size-3.5" aria-hidden="true" />None</span> }),
    columnHelper.accessor('selected_resume_id', { header: 'Resume', cell: (info) => info.getValue() ? 'Linked' : 'Not recorded' }),
    columnHelper.accessor('next_action_at', { header: 'Next action', cell: (info) => info.getValue() ? formatRelativeDate(info.getValue()!) : 'Not scheduled' }),
    columnHelper.accessor('source_type', { header: 'Source', cell: (info) => info.getValue() === 'extension' ? 'Browser' : 'Manual' })
  ]), [onSelect]);

  const table = useTable({
    features,
    data: applications,
    columns,
    state: { columnVisibility },
    onColumnVisibilityChange: setColumnVisibility
  });

  return (
    <div>
      <div className="mb-3 flex justify-end">
        <Button variant="outline" size="sm" onClick={() => setColumnsOpen(true)}><Columns3 className="size-4" aria-hidden="true" />Columns</Button>
      </div>
      <div className="overflow-x-auto rounded-2xl border border-border bg-surface">
        <table className="w-full min-w-[860px] border-collapse text-sm">
          <thead className="bg-surface-subtle text-left text-xs uppercase tracking-[0.06em] text-muted-foreground">
            {table.getHeaderGroups().map((group) => (
              <tr key={group.id}>{group.headers.map((header) => <th key={header.id} className="px-4 py-3 font-semibold"><table.FlexRender header={header} /></th>)}</tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id} className="border-t border-border hover:bg-surface-subtle/55">
                {row.getVisibleCells().map((cell) => <td key={cell.id} className="whitespace-nowrap px-4 py-3.5 text-[13px] text-muted-foreground"><table.FlexRender cell={cell} /></td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Dialog open={columnsOpen} onOpenChange={setColumnsOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Visible columns</DialogTitle><DialogDescription>Keep the information you use most in the first glance.</DialogDescription></DialogHeader>
          <div className="grid gap-2 sm:grid-cols-2">
            {table.getAllLeafColumns().map((column) => (
              <label key={column.id} className="flex min-h-11 items-center gap-3 rounded-xl border border-border px-3.5 text-sm">
                <input type="checkbox" checked={column.getIsVisible()} onChange={column.getToggleVisibilityHandler()} />
                {typeof column.columnDef.header === 'string' ? column.columnDef.header : column.id}
              </label>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
