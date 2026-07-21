import { extractProposal, looksLikeApplicationConfirmation } from './extract';

declare global {
  interface Window {
    __careerWorkspaceCaptureLoaded?: boolean;
  }
}

function currentProposal() {
  return extractProposal(document, new URL(window.location.href));
}

function notifyIfConfirmed() {
  const url = new URL(window.location.href);
  if (!looksLikeApplicationConfirmation(document, url)) return;
  const proposal = currentProposal();
  if (proposal.blocked) return;
  void chrome.runtime.sendMessage({ type: 'captureDetected', proposal }).catch(() => undefined);
}

if (!window.__careerWorkspaceCaptureLoaded) {
  window.__careerWorkspaceCaptureLoaded = true;
  let timer: number | undefined;
  const scheduleCheck = () => {
    if (timer) window.clearTimeout(timer);
    timer = window.setTimeout(notifyIfConfirmed, 650);
  };

  document.addEventListener('submit', scheduleCheck, true);
  const observer = new MutationObserver(scheduleCheck);
  observer.observe(document.documentElement, { childList: true, subtree: true });
  window.setTimeout(notifyIfConfirmed, 450);

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type === 'manualCapture') {
      sendResponse({ proposal: currentProposal() });
    }
  });
}
