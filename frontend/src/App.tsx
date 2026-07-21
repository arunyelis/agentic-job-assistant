import { useQuery } from '@tanstack/react-query';
import { LoaderCircle, TriangleAlert } from 'lucide-react';
import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';

import { AppShell } from '@/components/AppShell';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { WorkspaceProvider } from '@/context/WorkspaceContext';
import { ensureSession } from '@/lib/api';

const TodayPage = lazy(() => import('@/pages/TodayPage').then((module) => ({ default: module.TodayPage })));
const ApplicationsPage = lazy(() => import('@/pages/ApplicationsPage').then((module) => ({ default: module.ApplicationsPage })));
const CaptureInboxPage = lazy(() => import('@/pages/CaptureInboxPage').then((module) => ({ default: module.CaptureInboxPage })));
const CareerProfilePage = lazy(() => import('@/pages/CareerProfilePage').then((module) => ({ default: module.CareerProfilePage })));
const AssistantPage = lazy(() => import('@/pages/AssistantPage').then((module) => ({ default: module.AssistantPage })));
const AutomationsPage = lazy(() => import('@/pages/AutomationsPage').then((module) => ({ default: module.AutomationsPage })));
const PrivacyPage = lazy(() => import('@/pages/PrivacyPage').then((module) => ({ default: module.PrivacyPage })));

function PageFallback() {
  return <div className="h-64 animate-pulse rounded-2xl bg-surface-subtle motion-reduce:animate-none" aria-label="Loading page" />;
}

export default function App() {
  const session = useQuery({
    queryKey: ['session'],
    queryFn: ensureSession,
    retry: false,
    staleTime: Number.POSITIVE_INFINITY
  });

  if (session.isLoading) {
    return (
      <div className="grid min-h-svh place-items-center bg-background p-6" role="status">
        <div className="text-center">
          <LoaderCircle className="mx-auto size-7 animate-spin text-primary motion-reduce:animate-none" aria-hidden="true" />
          <p className="mt-3 text-sm font-medium">Preparing your workspace</p>
        </div>
      </div>
    );
  }

  if (session.error || !session.data) {
    return (
      <div className="grid min-h-svh place-items-center bg-background p-6">
        <Card className="w-full max-w-md p-6 text-center">
          <div className="mx-auto grid size-12 place-items-center rounded-2xl bg-danger-soft text-danger"><TriangleAlert className="size-6" aria-hidden="true" /></div>
          <h1 className="mt-4 text-xl font-semibold">The workspace could not start</h1>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">{session.error?.message || 'The local account session is unavailable.'}</p>
          <Button className="mt-5" onClick={() => session.refetch()}>Try again</Button>
        </Card>
      </div>
    );
  }

  return (
    <WorkspaceProvider>
      <Suspense fallback={<PageFallback />}>
        <Routes>
          <Route element={<AppShell user={session.data} />}>
            <Route index element={<TodayPage />} />
            <Route path="applications" element={<ApplicationsPage />} />
            <Route path="capture-inbox" element={<CaptureInboxPage />} />
            <Route path="career-profile" element={<CareerProfilePage />} />
            <Route path="assistant" element={<AssistantPage />} />
            <Route path="automations" element={<AutomationsPage />} />
            <Route path="privacy" element={<PrivacyPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </Suspense>
    </WorkspaceProvider>
  );
}
