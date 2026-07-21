import { BadgeCheck, FileStack, LockKeyhole, Waypoints } from 'lucide-react';

import { ResumeUpload } from '@/components/ResumeUpload';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';

const UPCOMING = [
  { icon: BadgeCheck, title: 'Verified evidence', text: 'Connect every claim to a resume, project, achievement, or work sample.' },
  { icon: Waypoints, title: 'Role-family positioning', text: 'Maintain a small set of focused profiles for the work you want to pursue.' },
  { icon: FileStack, title: 'Submitted snapshots', text: 'Keep the exact resume and application material seen by each employer.' }
];

export function CareerProfilePage() {
  return (
    <div className="space-y-8">
      <section>
        <div className="mb-4 flex items-center gap-2">
          <h2 className="text-lg font-semibold">Source documents</h2>
          <Badge variant="info">Assistant ready</Badge>
        </div>
        <ResumeUpload />
        <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
          <LockKeyhole className="size-4 text-success" aria-hidden="true" />
          Resume text is kept in memory for this assistant session and is not written to operational logs.
        </div>
      </section>

      <section aria-labelledby="evidence-title">
        <p className="text-[13px] font-semibold text-primary">Next product layer</p>
        <h2 id="evidence-title" className="mt-1 text-2xl font-semibold tracking-[-0.025em]">One profile, many truthful views</h2>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
          The evidence profile will become the stable source behind role-specific resumes. The first capture release keeps this structure visible without pretending it is complete.
        </p>
        <div className="mt-5 grid gap-3 md:grid-cols-3">
          {UPCOMING.map(({ icon: Icon, title, text }) => (
            <Card key={title} className="p-5">
              <div className="grid size-10 place-items-center rounded-xl bg-primary-soft text-primary"><Icon className="size-5" aria-hidden="true" /></div>
              <h3 className="mt-4 font-semibold">{title}</h3>
              <p className="mt-1.5 text-[13px] leading-5 text-muted-foreground">{text}</p>
            </Card>
          ))}
        </div>
      </section>
    </div>
  );
}
