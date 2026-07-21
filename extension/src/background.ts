import type { CaptureProposal, PendingCapture } from './types';

function pendingKey(tabId: number) {
  return `pending-${tabId}`;
}

function scriptId(origin: string) {
  let hash = 0;
  for (const character of origin) hash = (hash * 31 + character.charCodeAt(0)) >>> 0;
  return `career-capture-${hash.toString(16)}`;
}

async function setPending(tabId: number, proposal: CaptureProposal) {
  const pending: PendingCapture = { tabId, proposal };
  await chrome.storage.session.set({ [pendingKey(tabId)]: pending });
  await chrome.action.setBadgeBackgroundColor({ color: '#315BE8', tabId });
  await chrome.action.setBadgeText({ text: '1', tabId });
  return pending;
}

async function clearPending(tabId: number) {
  await chrome.storage.session.remove(pendingKey(tabId));
  await chrome.action.setBadgeText({ text: '', tabId });
}

async function registerOrigin(origin: string) {
  const id = scriptId(origin);
  const existing = await chrome.scripting.getRegisteredContentScripts({ ids: [id] });
  if (!existing.length) {
    await chrome.scripting.registerContentScripts([
      {
        id,
        matches: [`${origin}/*`],
        js: ['content.js'],
        runAt: 'document_idle',
        persistAcrossSessions: true
      }
    ]);
  }
  return id;
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  void (async () => {
    if (message?.type === 'captureDetected' && sender.tab?.id !== undefined) {
      sendResponse(await setPending(sender.tab.id, message.proposal));
      return;
    }
    if (message?.type === 'setPending') {
      sendResponse(await setPending(message.tabId, message.proposal));
      return;
    }
    if (message?.type === 'getPending') {
      const result = await chrome.storage.session.get(pendingKey(message.tabId));
      sendResponse(result[pendingKey(message.tabId)] || null);
      return;
    }
    if (message?.type === 'clearPending') {
      await clearPending(message.tabId);
      sendResponse({ ok: true });
      return;
    }
    if (message?.type === 'enableOrigin') {
      sendResponse({ id: await registerOrigin(message.origin) });
      return;
    }
    sendResponse(null);
  })().catch((error) => sendResponse({ error: error instanceof Error ? error.message : String(error) }));
  return true;
});

chrome.tabs.onRemoved.addListener((tabId) => {
  void chrome.storage.session.remove(pendingKey(tabId));
});
