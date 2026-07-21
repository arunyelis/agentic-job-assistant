import { CheckCircle2, FileText, Upload } from 'lucide-react';
import { useRef } from 'react';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { useWorkspace } from '@/context/WorkspaceContext';

export function ResumeUpload() {
  const input = useRef<HTMLInputElement>(null);
  const { resume, uploadResume } = useWorkspace();
  const ready = resume.status === 'ready';

  return (
    <Card className="p-5">
      <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
        <div className={`grid size-12 shrink-0 place-items-center rounded-2xl ${ready ? 'bg-success-soft text-success' : 'bg-primary-soft text-primary'}`}>
          {ready ? <CheckCircle2 className="size-6" aria-hidden="true" /> : <FileText className="size-6" aria-hidden="true" />}
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="text-lg font-semibold">{ready ? 'Resume ready for the assistant' : 'Add your current resume'}</h2>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            {ready
              ? `${resume.fileName} contains ${resume.characterCount?.toLocaleString()} readable characters.`
              : 'PDF, DOCX, TXT, and Markdown files up to 5 MB are supported.'}
          </p>
          {resume.status === 'error' && <p className="mt-2 text-[13px] font-medium text-danger" role="alert">{resume.error}</p>}
        </div>
        <input
          ref={input}
          className="sr-only"
          type="file"
          accept=".pdf,.docx,.txt,.md"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) void uploadResume(file);
          }}
        />
        <Button variant={ready ? 'outline' : 'default'} onClick={() => input.current?.click()} disabled={resume.status === 'uploading'}>
          <Upload className="size-4.5" aria-hidden="true" />
          {resume.status === 'uploading' ? 'Reading…' : ready ? 'Replace resume' : 'Choose resume'}
        </Button>
      </div>
    </Card>
  );
}
