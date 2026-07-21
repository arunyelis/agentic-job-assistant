import {
  closestCenter,
  DndContext,
  KeyboardSensor,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent
} from '@dnd-kit/core';
import { CSS } from '@dnd-kit/utilities';
import { GripVertical, Mail } from 'lucide-react';

import { PIPELINE_STAGES } from '@/features/applications/constants';
import { cn } from '@/lib/utils';
import type { ApplicationRecord, ApplicationStatus } from '@/types';

function PipelineCard({ application, onSelect }: { application: ApplicationRecord; onSelect: () => void }) {
  const draggable = useDraggable({
    id: application.id,
    data: { application }
  });
  const style = {
    transform: CSS.Translate.toString(draggable.transform),
    zIndex: draggable.isDragging ? 30 : undefined
  };

  return (
    <article
      ref={draggable.setNodeRef}
      style={style}
      className={cn(
        'rounded-2xl border border-border bg-surface p-3.5 shadow-sm transition-shadow motion-reduce:transition-none',
        draggable.isDragging && 'opacity-70 shadow-overlay'
      )}
    >
      <div className="flex items-start gap-2">
        <button
          type="button"
          className="min-w-0 flex-1 text-left"
          onClick={onSelect}
          aria-label={`Open ${application.role} at ${application.company}`}
        >
          <h3 className="truncate text-sm font-semibold">{application.role}</h3>
          <p className="mt-1 truncate text-xs text-muted-foreground">{application.company}</p>
        </button>
        <button
          type="button"
          className="grid size-9 shrink-0 cursor-grab place-items-center rounded-lg text-muted-foreground hover:bg-surface-subtle active:cursor-grabbing"
          aria-label={`Move ${application.role}`}
          {...draggable.listeners}
          {...draggable.attributes}
        >
          <GripVertical className="size-4" aria-hidden="true" />
        </button>
      </div>
      <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
        <span>{new Date(application.captured_at).toLocaleDateString()}</span>
        <span className="inline-flex items-center gap-1"><Mail className="size-3.5" aria-hidden="true" />No email</span>
      </div>
    </article>
  );
}

function StageColumn({
  stage,
  applications,
  onSelect
}: {
  stage: (typeof PIPELINE_STAGES)[number];
  applications: ApplicationRecord[];
  onSelect: (application: ApplicationRecord) => void;
}) {
  const droppable = useDroppable({ id: stage.id });
  return (
    <section
      ref={droppable.setNodeRef}
      className={cn(
        'min-h-[420px] w-[292px] shrink-0 rounded-3xl border border-transparent p-2 transition-colors motion-reduce:transition-none',
        droppable.isOver && 'border-primary/45 bg-primary-soft/35'
      )}
      aria-label={`${stage.label} stage`}
    >
      <div className="mb-2 flex items-center justify-between px-2 py-1.5">
        <div className="flex items-center gap-2">
          <span className={cn('size-2.5 rounded-full', stage.tone)} aria-hidden="true" />
          <h2 className="text-[13px] font-semibold">{stage.label}</h2>
        </div>
        <span className="rounded-full bg-surface-subtle px-2 py-0.5 text-xs font-semibold text-muted-foreground">{applications.length}</span>
      </div>
      <div className="space-y-2.5">
        {applications.map((application) => (
          <PipelineCard key={application.id} application={application} onSelect={() => onSelect(application)} />
        ))}
        {applications.length === 0 && (
          <div className="grid min-h-24 place-items-center rounded-2xl border border-dashed border-border px-4 text-center text-xs text-muted-foreground">
            Drop an application here
          </div>
        )}
      </div>
    </section>
  );
}

export function PipelineBoard({
  applications,
  onStatusChange,
  onSelect
}: {
  applications: ApplicationRecord[];
  onStatusChange: (application: ApplicationRecord, status: ApplicationStatus) => void;
  onSelect: (application: ApplicationRecord) => void;
}) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor)
  );

  function handleDragEnd(event: DragEndEvent) {
    const application = event.active.data.current?.application as ApplicationRecord | undefined;
    const status = event.over?.id as ApplicationStatus | undefined;
    if (application && status && application.status !== status) {
      onStatusChange(application, status);
    }
  }

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <div className="-mx-4 overflow-x-auto px-4 pb-4 sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8">
        <div className="flex min-w-max gap-2">
          {PIPELINE_STAGES.map((stage) => (
            <StageColumn
              key={stage.id}
              stage={stage}
              applications={applications.filter((item) => item.status === stage.id)}
              onSelect={onSelect}
            />
          ))}
        </div>
      </div>
    </DndContext>
  );
}
