import {
  Bot,
  BriefcaseBusiness,
  ChevronLeft,
  FileUser,
  Inbox,
  LayoutDashboard,
  Menu,
  Moon,
  PanelLeftOpen,
  Plus,
  ShieldCheck,
  Sun,
  Workflow
} from 'lucide-react';
import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';

import { CaptureDialog } from '@/components/CaptureDialog';
import { AssistantDock } from '@/features/assistant/AssistantDock';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import type { SessionUser } from '@/types';

const NAVIGATION = [
  { href: '/', label: 'Today', icon: LayoutDashboard },
  { href: '/applications', label: 'Applications', icon: BriefcaseBusiness },
  { href: '/capture-inbox', label: 'Capture Inbox', icon: Inbox },
  { href: '/career-profile', label: 'Career Profile', icon: FileUser },
  { href: '/assistant', label: 'Assistant', icon: Bot },
  { href: '/automations', label: 'Automations', icon: Workflow },
  { href: '/privacy', label: 'Privacy', icon: ShieldCheck }
];

const PAGE_DETAILS: Record<string, { title: string; description: string }> = {
  '/': { title: 'Today', description: 'Your job search, organized around the next useful action.' },
  '/applications': { title: 'Applications', description: 'A searchable record of every confirmed application.' },
  '/capture-inbox': { title: 'Capture Inbox', description: 'Review records that need a quick correction.' },
  '/career-profile': { title: 'Career Profile', description: 'The evidence and documents that support your applications.' },
  '/assistant': { title: 'Assistant', description: 'Research roles and create truthful, evidence-based material.' },
  '/automations': { title: 'Automations', description: 'Create agents and inspect the workflows running across your workspace.' },
  '/privacy': { title: 'Privacy', description: 'Control stored data, exports, permissions, and deletion.' }
};

const CaptureContext = createContext<() => void>(() => undefined);

export function useCaptureDialog() {
  return useContext(CaptureContext);
}

function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex min-w-0 items-center gap-3">
      <div className="grid size-10 shrink-0 place-items-center rounded-xl bg-primary text-base font-bold text-white shadow-sm">
        C
      </div>
      {!compact && (
        <div className="min-w-0">
          <p className="truncate text-[15px] font-semibold">Career Workspace</p>
          <p className="truncate text-xs text-muted-foreground">Private job search</p>
        </div>
      )}
    </div>
  );
}

function Navigation({ compact = false, onNavigate }: { compact?: boolean; onNavigate?: () => void }) {
  return (
    <nav className="space-y-1" aria-label="Workspace navigation">
      {NAVIGATION.map(({ href, label, icon: Icon }) => {
        const link = (
          <NavLink
            to={href}
            end={href === '/'}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                'flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-surface-subtle hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary motion-reduce:transition-none',
                isActive && 'bg-primary-soft font-semibold text-primary-strong',
                compact && 'justify-center px-0'
              )
            }
          >
            <Icon className="size-5 shrink-0" aria-hidden="true" />
            {!compact && <span>{label}</span>}
          </NavLink>
        );
        if (!compact) return <div key={href}>{link}</div>;
        return (
          <Tooltip key={href}>
            <TooltipTrigger asChild>{link}</TooltipTrigger>
            <TooltipContent side="right">{label}</TooltipContent>
          </Tooltip>
        );
      })}
    </nav>
  );
}

function AccountSummary({ user, compact = false }: { user: SessionUser; compact?: boolean }) {
  return (
    <div className={cn('flex items-center gap-3 rounded-xl border border-border p-3', compact && 'justify-center p-2')}>
      <div className="grid size-9 shrink-0 place-items-center rounded-full bg-success-soft text-[13px] font-bold text-success">
        LW
      </div>
      {!compact && (
        <div className="min-w-0">
          <p className="truncate text-[13px] font-semibold">{user.displayName}</p>
          <p className="truncate text-xs text-muted-foreground">Development account</p>
        </div>
      )}
    </div>
  );
}

export function AppShell({ user }: { user: SessionUser }) {
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem('career-nav-collapsed') === 'true');
  const [mobileOpen, setMobileOpen] = useState(false);
  const [captureOpen, setCaptureOpen] = useState(false);
  const [dark, setDark] = useState(() => document.documentElement.classList.contains('dark'));
  const details = PAGE_DETAILS[location.pathname] || PAGE_DETAILS['/'];

  useEffect(() => {
    localStorage.setItem('career-nav-collapsed', String(collapsed));
  }, [collapsed]);

  function toggleTheme() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle('dark', next);
    localStorage.setItem('career-theme', next ? 'dark' : 'light');
  }

  const openCapture = useMemo(() => () => setCaptureOpen(true), []);

  return (
    <TooltipProvider delayDuration={250}>
      <CaptureContext.Provider value={openCapture}>
        <div className="min-h-svh bg-background text-foreground">
          <aside
            className={cn(
              'fixed inset-y-0 left-0 z-30 hidden border-r border-border bg-surface px-3 py-4 transition-[width] duration-200 lg:flex lg:flex-col motion-reduce:transition-none',
              collapsed ? 'w-[76px]' : 'w-[256px]'
            )}
          >
            <div className={cn('flex items-center', collapsed ? 'justify-center' : 'justify-between px-1')}>
              <Logo compact={collapsed} />
              {!collapsed && (
                <Button variant="ghost" size="icon" onClick={() => setCollapsed(true)} aria-label="Collapse navigation">
                  <ChevronLeft className="size-5" aria-hidden="true" />
                </Button>
              )}
            </div>
            {collapsed && (
              <Button className="mt-4" variant="ghost" size="icon" onClick={() => setCollapsed(false)} aria-label="Expand navigation">
                <PanelLeftOpen className="size-5" aria-hidden="true" />
              </Button>
            )}
            <div className="mt-8 flex-1">
              <Navigation compact={collapsed} />
            </div>
            <AccountSummary user={user} compact={collapsed} />
          </aside>

          <div className={cn('min-h-svh transition-[padding] duration-200 motion-reduce:transition-none', collapsed ? 'lg:pl-[76px]' : 'lg:pl-[256px]')}>
            <header className="sticky top-0 z-20 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/85">
              <div className="flex min-h-[76px] items-center gap-3 px-4 sm:px-6 lg:px-8">
                <Button className="lg:hidden" variant="ghost" size="icon" onClick={() => setMobileOpen(true)} aria-label="Open navigation">
                  <Menu className="size-5" aria-hidden="true" />
                </Button>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h1 className="truncate text-xl font-semibold tracking-[-0.02em] sm:text-2xl">{details.title}</h1>
                    <Badge className="hidden sm:inline-flex" variant="success">Account protected</Badge>
                  </div>
                  <p className="mt-0.5 hidden truncate text-[13px] text-muted-foreground sm:block">{details.description}</p>
                </div>
                <Button variant="ghost" size="icon" onClick={toggleTheme} aria-label={dark ? 'Use light theme' : 'Use dark theme'}>
                  {dark ? <Sun className="size-5" aria-hidden="true" /> : <Moon className="size-5" aria-hidden="true" />}
                </Button>
                <Button onClick={openCapture}>
                  <Plus className="size-4.5" aria-hidden="true" />
                  <span className="hidden sm:inline">Add application</span>
                  <span className="sm:hidden">Add</span>
                </Button>
              </div>
            </header>

            <main className="mx-auto w-full max-w-[1440px] p-4 sm:p-6 lg:p-8">
              <Outlet />
            </main>
          </div>

          <Dialog open={mobileOpen} onOpenChange={setMobileOpen}>
            <DialogContent className="left-0 top-0 h-svh w-[min(88vw,320px)] -translate-x-0 -translate-y-0 rounded-none border-y-0 border-l-0 p-4">
              <DialogTitle className="sr-only">Workspace navigation</DialogTitle>
              <Logo />
              <div className="mt-8">
                <Navigation onNavigate={() => setMobileOpen(false)} />
              </div>
              <div className="absolute bottom-4 left-4 right-4">
                <AccountSummary user={user} />
              </div>
            </DialogContent>
          </Dialog>

          <CaptureDialog open={captureOpen} onOpenChange={setCaptureOpen} />
          <AssistantDock />
        </div>
      </CaptureContext.Provider>
    </TooltipProvider>
  );
}
