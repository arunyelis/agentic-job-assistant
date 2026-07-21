export interface CaptureProposal {
  idempotencyKey: string;
  detectedAt: string;
  sourceUrl: string;
  company: string;
  role: string;
  confidence: number;
  confirmationSignal: string;
  blocked?: boolean;
}

export interface PendingCapture {
  tabId: number;
  proposal: CaptureProposal;
}

export interface ExtensionSettings {
  apiBase: string;
  apiToken?: string;
}
