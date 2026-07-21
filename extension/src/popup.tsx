import { CheckCircle2, ChevronLeft, ExternalLink, LoaderCircle, MonitorCheck, ScanSearch, Settings, ShieldCheck } from 'lucide-react';
import { StrictMode, type FormEvent, useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';

import './popup.css';
import type { CaptureProposal, ExtensionSettings, PendingCapture } from './types';

const DEFAULT_API = 'http://127.0.0.1:3000';

function normalizeApi(value: string) {
  return value.trim().replace(/\/$/, '');
}

async function activeTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id || !tab.url) throw new Error('The current tab is unavailable.');
  return tab as chrome.tabs.Tab & { id: number; url: string };
}

function supportedUrl(value: string) {
  return value.startsWith('https://') || value.startsWith('http://');
}

async function dataUrlToBlob(value: string) {
  return (await fetch(value)).blob();
}

async function ensureApiToken(apiBase: string, force = false) {
  if (!force) {
    const stored = await chrome.storage.session.get('apiToken');
    if (stored.apiToken) return String(stored.apiToken);
  }
  const response = await fetch(`${apiBase}/api/v1/auth/local-session`, { method: 'POST' });
  if (!response.ok) throw new Error('Career Workspace is not available at this address.');
  const body = await response.json();
  await chrome.storage.session.set({ apiToken: body.token });
  return String(body.token);
}

async function authorizedFetch(apiBase: string, path: string, options: RequestInit, retry = true): Promise<Response> {
  const token = await ensureApiToken(apiBase);
  const response = await fetch(`${apiBase}${path}`, {
    ...options,
    headers: { ...options.headers, Authorization: `Bearer ${token}` }
  });
  if (response.status === 401 && retry) {
    const refreshed = await ensureApiToken(apiBase, true);
    return fetch(`${apiBase}${path}`, {
      ...options,
      headers: { ...options.headers, Authorization: `Bearer ${refreshed}` }
    });
  }
  return response;
}

function App() {
  const [tab, setTab] = useState<(chrome.tabs.Tab & { id: number; url: string }) | null>(null);
  const [enabled, setEnabled] = useState(false);
  const [pending, setPending] = useState<PendingCapture | null>(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const [apiBase, setApiBase] = useState(DEFAULT_API);
  const [company, setCompany] = useState('');
  const [role, setRole] = useState('');
  const [includeScreenshot, setIncludeScreenshot] = useState(false);

  const origin = useMemo(() => {
    if (!tab?.url || !supportedUrl(tab.url)) return '';
    return new URL(tab.url).origin;
  }, [tab]);
  const isLinkedIn = useMemo(() => {
    if (!tab?.url || !supportedUrl(tab.url)) return false;
    const host = new URL(tab.url).hostname;
    return host === 'linkedin.com' || host.endsWith('.linkedin.com');
  }, [tab]);

  useEffect(() => {
    void (async () => {
      try {
        const current = await activeTab();
        setTab(current);
        const settings = await chrome.storage.local.get('apiBase') as ExtensionSettings;
        setApiBase(settings.apiBase || DEFAULT_API);
        if (supportedUrl(current.url)) {
          const currentOrigin = new URL(current.url).origin;
          setEnabled(await chrome.permissions.contains({ origins: [`${currentOrigin}/*`] }));
        }
        const item = await chrome.runtime.sendMessage({ type: 'getPending', tabId: current.id });
        if (item && !item.error) setPending(item as PendingCapture);
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : 'The extension could not read this tab.');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  useEffect(() => {
    setCompany(pending?.proposal.company || '');
    setRole(pending?.proposal.role || '');
  }, [pending]);

  async function enableSite() {
    if (!tab || !origin) return;
    setWorking(true);
    setError('');
    try {
      const granted = await chrome.permissions.request({ origins: [`${origin}/*`] });
      if (!granted) throw new Error('Site access was not granted.');
      const registered = await chrome.runtime.sendMessage({ type: 'enableOrigin', origin });
      if (registered?.error) throw new Error(registered.error);
      await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ['content.js'] });
      setEnabled(true);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'This site could not be enabled.');
    } finally {
      setWorking(false);
    }
  }

  async function captureCurrentPage() {
    if (!tab || isLinkedIn) return;
    setWorking(true);
    setError('');
    try {
      if (!enabled) await enableSite();
      await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ['content.js'] }).catch(() => undefined);
      const response = await chrome.tabs.sendMessage(tab.id, { type: 'manualCapture' });
      const proposal = response?.proposal as CaptureProposal | undefined;
      if (!proposal) throw new Error('The page details could not be read.');
      const item = await chrome.runtime.sendMessage({ type: 'setPending', tabId: tab.id, proposal });
      if (item?.error) throw new Error(item.error);
      setPending(item as PendingCapture);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The page could not be captured.');
    } finally {
      setWorking(false);
    }
  }

  async function confirm(event: FormEvent) {
    event.preventDefault();
    if (!tab || !pending) return;
    setWorking(true);
    setError('');
    try {
      const base = normalizeApi(apiBase);
      let screenshotArtifactId: string | null = null;
      if (includeScreenshot) {
        const screenshot = await chrome.tabs.captureVisibleTab(tab.windowId, { format: 'png' });
        const form = new FormData();
        form.append('kind', 'screenshot');
        form.append('file', await dataUrlToBlob(screenshot), 'application.png');
        const upload = await authorizedFetch(base, '/api/v1/artifacts', { method: 'POST', body: form });
        if (!upload.ok) throw new Error('The optional screenshot could not be stored.');
        screenshotArtifactId = (await upload.json()).id;
      }

      const response = await authorizedFetch(base, '/api/v1/applications/capture', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          idempotency_key: pending.proposal.idempotencyKey,
          captured_at: pending.proposal.detectedAt,
          source_url: pending.proposal.sourceUrl,
          source_type: 'extension',
          company: company.trim(),
          role: role.trim(),
          status: 'applied',
          extraction_confidence: pending.proposal.confidence,
          screenshot_artifact_id: screenshotArtifactId
        })
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || 'The application could not be saved.');
      }
      await chrome.runtime.sendMessage({ type: 'clearPending', tabId: tab.id });
      setPending(null);
      setSaved(true);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The application could not be saved.');
    } finally {
      setWorking(false);
    }
  }

  async function dismiss() {
    if (!tab) return;
    await chrome.runtime.sendMessage({ type: 'clearPending', tabId: tab.id });
    setPending(null);
  }

  async function saveSettings() {
    const normalized = normalizeApi(apiBase);
    if (!normalized.startsWith('http://') && !normalized.startsWith('https://')) {
      setError('Enter a valid Career Workspace URL.');
      return;
    }
    await chrome.storage.local.set({ apiBase: normalized });
    await chrome.storage.session.remove('apiToken');
    setApiBase(normalized);
    setShowSettings(false);
    setError('');
  }

  if (loading) {
    return <main className="grid min-h-[360px] place-items-center" role="status"><LoaderCircle className="size-6 animate-spin text-primary motion-reduce:animate-none" aria-hidden="true" /><span className="sr-only">Loading extension</span></main>;
  }

  return (
    <main className="min-h-[360px] bg-background text-foreground">
      <header className="flex min-h-16 items-center gap-3 border-b border-border px-4">
        {showSettings && <button className="icon-button" onClick={() => setShowSettings(false)} aria-label="Back"><ChevronLeft className="size-5" /></button>}
        <div className="grid size-9 place-items-center rounded-xl bg-primary font-bold text-white">C</div>
        <div className="min-w-0 flex-1"><h1 className="truncate text-sm font-semibold">Career Workspace</h1><p className="truncate text-xs text-muted">Confirm before capture</p></div>
        {!showSettings && <button className="icon-button" onClick={() => setShowSettings(true)} aria-label="Extension settings"><Settings className="size-4.5" /></button>}
      </header>

      <div className="p-4">
        {showSettings ? (
          <section>
            <h2 className="text-lg font-semibold">Connection</h2>
            <p className="mt-1 text-[13px] leading-5 text-muted">The local development extension connects only to the address below.</p>
            <label className="mt-5 block"><span className="label">Workspace URL</span><input className="input mt-1.5" value={apiBase} onChange={(event) => setApiBase(event.target.value)} /></label>
            <button className="primary-button mt-4 w-full" onClick={saveSettings}>Save settings</button>
          </section>
        ) : saved ? (
          <section className="py-8 text-center" role="status">
            <div className="mx-auto grid size-14 place-items-center rounded-2xl bg-success-soft text-success"><CheckCircle2 className="size-7" /></div>
            <h2 className="mt-4 text-lg font-semibold">Application saved</h2>
            <p className="mx-auto mt-2 max-w-[280px] text-[13px] leading-5 text-muted">The confirmed record is now in your Career Workspace timeline.</p>
            <button className="secondary-button mt-5" onClick={() => setSaved(false)}>Done</button>
          </section>
        ) : pending ? (
          <form onSubmit={confirm}>
            <div className="flex items-center justify-between gap-2"><h2 className="text-lg font-semibold">Confirm application</h2><span className={`badge ${pending.proposal.confidence >= 0.72 ? 'badge-success' : 'badge-warning'}`}>{Math.round(pending.proposal.confidence * 100)}% confidence</span></div>
            <p className="mt-1 text-[13px] leading-5 text-muted">Review what was detected. Nothing is stored until you save.</p>
            <label className="mt-4 block"><span className="label">Company</span><input className="input mt-1.5" value={company} onChange={(event) => setCompany(event.target.value)} required /></label>
            <label className="mt-3 block"><span className="label">Role</span><input className="input mt-1.5" value={role} onChange={(event) => setRole(event.target.value)} required /></label>
            <div className="mt-3 rounded-xl bg-surface-subtle p-3 text-xs leading-5 text-muted"><span className="font-semibold text-foreground">Source</span><br />{new URL(pending.proposal.sourceUrl).hostname}</div>
            <label className="mt-4 flex min-h-11 cursor-pointer items-center gap-3 rounded-xl border border-border px-3"><input className="size-4 accent-primary" type="checkbox" checked={includeScreenshot} onChange={(event) => setIncludeScreenshot(event.target.checked)} /><span><strong className="block text-[13px]">Include current screenshot</strong><small className="block text-xs text-muted">Off by default</small></span></label>
            <div className="mt-4 flex gap-2"><button type="button" className="secondary-button flex-1" onClick={dismiss}>Dismiss</button><button className="primary-button flex-1" disabled={working}>{working ? 'Saving…' : 'Save application'}</button></div>
          </form>
        ) : isLinkedIn ? (
          <section className="py-4">
            <div className="grid size-12 place-items-center rounded-2xl bg-warning-soft text-warning"><ShieldCheck className="size-6" /></div>
            <h2 className="mt-4 text-lg font-semibold">Automatic capture is off here</h2>
            <p className="mt-2 text-[13px] leading-5 text-muted">Career Workspace does not scrape LinkedIn. Add this application manually in the web workspace instead.</p>
            <button className="primary-button mt-5 w-full" onClick={() => chrome.tabs.create({ url: apiBase })}>Open Career Workspace <ExternalLink className="size-4" /></button>
          </section>
        ) : !tab || !supportedUrl(tab.url) ? (
          <section className="py-6 text-center"><ScanSearch className="mx-auto size-8 text-muted" /><h2 className="mt-3 font-semibold">This page cannot be captured</h2><p className="mt-1 text-[13px] text-muted">Open a public job or application page first.</p></section>
        ) : (
          <section>
            <div className={`flex items-center gap-2 rounded-xl px-3 py-2.5 text-[13px] ${enabled ? 'bg-success-soft text-success' : 'bg-surface-subtle text-muted'}`}><MonitorCheck className="size-4.5" /><span>{enabled ? 'Capture is enabled for this site' : 'This site is not enabled yet'}</span></div>
            <div className="py-7 text-center"><ScanSearch className="mx-auto size-9 text-primary" /><h2 className="mt-3 text-lg font-semibold">{enabled ? 'Waiting for an application' : 'Capture this career site'}</h2><p className="mx-auto mt-2 max-w-[300px] text-[13px] leading-5 text-muted">{enabled ? 'A likely submission will appear here for review. You can also capture the current page manually.' : 'Access is requested for this site only. Other browsing remains unavailable to the extension.'}</p></div>
            {!enabled && <button className="primary-button w-full" onClick={enableSite} disabled={working}>{working ? 'Enabling…' : 'Enable this site'}</button>}
            {enabled && <button className="secondary-button w-full" onClick={captureCurrentPage} disabled={working}>{working ? 'Reading page…' : 'Capture current page'}</button>}
          </section>
        )}
        {error && <p className="mt-4 rounded-xl bg-danger-soft p-3 text-[13px] leading-5 text-danger" role="alert">{error}</p>}
      </div>
    </main>
  );
}

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>);
