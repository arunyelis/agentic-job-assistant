import { createContext, type ReactNode, useContext, useMemo, useState } from 'react';

import type { ResumeState } from '@/types';

interface WorkspaceContextValue {
  chatSessionId: string;
  resume: ResumeState;
  uploadResume: (file: File) => Promise<void>;
  resetChatWorkspace: () => Promise<void>;
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [chatSessionId, setChatSessionId] = useState(() => crypto.randomUUID());
  const [resume, setResume] = useState<ResumeState>({ status: 'idle' });

  async function uploadResume(file: File) {
    setResume({ status: 'uploading', fileName: file.name });
    const formData = new FormData();
    formData.append('session_id', chatSessionId);
    formData.append('resume', file);

    try {
      const response = await fetch('/api/resume', { method: 'POST', body: formData });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Resume upload failed.');
      setResume({ status: 'ready', ...data });
    } catch (error) {
      setResume({
        status: 'error',
        fileName: file.name,
        error: error instanceof Error ? error.message : 'Resume upload failed.'
      });
    }
  }

  async function resetChatWorkspace() {
    await fetch('/api/reset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: chatSessionId })
    }).catch(() => undefined);
    setChatSessionId(crypto.randomUUID());
    setResume({ status: 'idle' });
  }

  const value = useMemo(
    () => ({ chatSessionId, resume, uploadResume, resetChatWorkspace }),
    [chatSessionId, resume]
  );

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace() {
  const context = useContext(WorkspaceContext);
  if (!context) throw new Error('useWorkspace must be used inside WorkspaceProvider.');
  return context;
}
