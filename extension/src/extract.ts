import type { CaptureProposal } from './types';

const CONFIRMATION_PHRASES = [
  'application submitted',
  'application has been submitted',
  'thanks for applying',
  'thank you for applying',
  'we received your application',
  'your application has been received',
  'application complete'
];

function clean(value: unknown) {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

function findJobPosting(value: unknown): Record<string, unknown> | null {
  if (!value) return null;
  if (Array.isArray(value)) {
    for (const item of value) {
      const match = findJobPosting(item);
      if (match) return match;
    }
    return null;
  }
  if (typeof value !== 'object') return null;
  const record = value as Record<string, unknown>;
  if (record['@type'] === 'JobPosting') return record;
  return findJobPosting(record['@graph']);
}

function structuredJob(document: Document) {
  for (const script of document.querySelectorAll<HTMLScriptElement>('script[type="application/ld+json"]')) {
    try {
      const posting = findJobPosting(JSON.parse(script.textContent || ''));
      if (posting) return posting;
    } catch {
      continue;
    }
  }
  return null;
}

function readableHost(url: URL) {
  const parts = url.hostname.replace(/^www\./, '').split('.');
  const candidate = parts.find((part) => !['jobs', 'careers', 'apply', 'boards'].includes(part)) || parts[0];
  return candidate
    .split(/[-_]/)
    .map((part) => part ? part[0].toUpperCase() + part.slice(1) : '')
    .join(' ');
}

function roleFromTitle(value: string) {
  const cleanTitle = clean(value);
  if (!cleanTitle) return '';
  return cleanTitle.split(/\s+[|·]\s+|\s+-\s+|\s+at\s+/i)[0].trim();
}

export function confirmationSignal(document: Document) {
  const body = clean(document.body?.innerText || document.body?.textContent).toLowerCase();
  return CONFIRMATION_PHRASES.find((phrase) => body.includes(phrase)) || '';
}

export function isLinkedInPage(url: URL) {
  return url.hostname === 'linkedin.com' || url.hostname.endsWith('.linkedin.com');
}

export function extractProposal(document: Document, url: URL): CaptureProposal {
  const posting = structuredJob(document);
  const organization = posting?.hiringOrganization;
  const structuredCompany = typeof organization === 'object' && organization
    ? clean((organization as Record<string, unknown>).name)
    : '';
  const metaCompany = clean(document.querySelector<HTMLMetaElement>('meta[property="og:site_name"]')?.content);
  const heading = clean(document.querySelector('h1')?.textContent);
  const metaTitle = clean(document.querySelector<HTMLMetaElement>('meta[property="og:title"]')?.content);
  const role = clean(posting?.title) || roleFromTitle(heading) || roleFromTitle(metaTitle) || roleFromTitle(document.title);
  const company = structuredCompany || metaCompany || readableHost(url);
  const structured = Boolean(posting && structuredCompany && role);
  const confidence = structured ? 0.96 : heading && metaCompany ? 0.78 : 0.58;

  return {
    idempotencyKey: crypto.randomUUID(),
    detectedAt: new Date().toISOString(),
    sourceUrl: url.href,
    company: company || 'Unknown company',
    role: role || 'Unknown role',
    confidence,
    confirmationSignal: confirmationSignal(document),
    blocked: isLinkedInPage(url)
  };
}

export function looksLikeApplicationConfirmation(document: Document, url: URL) {
  return !isLinkedInPage(url) && Boolean(confirmationSignal(document));
}
