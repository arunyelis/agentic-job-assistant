import { useEffect, useRef, useState } from 'react';
import MarkdownContent from './MarkdownContent.jsx';
import { readSse } from './sse.js';

const STARTERS = [
  {
    number: '01',
    title: 'Check my fit for a role',
    note: 'Paste a public job URL',
    prompt: 'Analyze this role against my resume: '
  },
  {
    number: '02',
    title: 'Write a cover letter',
    note: 'Truthful and role-specific',
    prompt: 'Write a concise cover letter for this job using only facts from my resume: '
  },
  {
    number: '03',
    title: 'Draft a follow-up',
    note: 'Short email and timing',
    prompt: 'Draft a follow-up for an application I submitted seven days ago.'
  }
];

function newSessionId() {
  return crypto.randomUUID();
}

export function appendReasoning(current, data) {
  const itemId = `${data.itemId || 'summary'}:${data.summaryIndex ?? 0}`;
  const existing = current.find((item) => item.id === itemId);
  if (!existing) return [...current, { id: itemId, text: data.text }];

  const separator = existing.text.endsWith('**') && data.text.startsWith('**') ? '\n\n' : '';
  return current.map((item) => (
    item.id === itemId ? { ...item, text: item.text + separator + data.text } : item
  ));
}

function Sidebar({ collapsed, mobileOpen, onToggle, resume, onResume }) {
  const fileInput = useRef(null);
  let statusText = 'PDF, DOCX, TXT, or MD · max 5 MB';
  if (resume.status === 'uploading') statusText = 'Reading resume…';
  if (resume.status === 'ready') {
    statusText = `${resume.fileName} · ${resume.characterCount.toLocaleString()} characters`;
  }
  if (resume.status === 'error') statusText = resume.error;

  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''} ${mobileOpen ? 'mobile-open' : ''}`}>
      <div className="brand-row">
        <div className="brand">
          <span className="brand-mark">JA</span>
          <span className="brand-name">Job Assistant</span>
        </div>
        <button className="icon-button collapse-button" onClick={onToggle} aria-label="Toggle sidebar">
          <span>{collapsed ? '›' : '‹'}</span>
        </button>
      </div>

      <div className="sidebar-content">
        <p className="eyebrow">Candidate context</p>
        <h2>Upload your resume</h2>
        <p className="sidebar-copy">Your resume is sent to the model for this chat, kept in server memory, and not written to logs.</p>

        <input
          ref={fileInput}
          className="file-input"
          type="file"
          accept=".pdf,.docx,.txt,.md"
          onChange={(event) => onResume(event.target.files?.[0])}
        />
        <button
          className={`upload-card ${resume.status}`}
          onClick={() => fileInput.current?.click()}
          disabled={resume.status === 'uploading'}
        >
          <span className="upload-icon">↑</span>
          <span>
            <strong>{resume.status === 'ready' ? 'Resume ready' : 'Choose a resume'}</strong>
            <small>{statusText}</small>
          </span>
        </button>

        <div className="boundary">
          <span className="boundary-icon">✓</span>
          <div>
            <strong>Read-only browser</strong>
            <p>Can inspect public job pages. It cannot log in, fill forms, submit applications, or send email.</p>
          </div>
        </div>
      </div>
    </aside>
  );
}

function Message({ message }) {
  return (
    <article className={`message ${message.role} ${message.error ? 'error' : ''}`}>
      <div className="message-label">{message.role === 'user' ? 'You' : 'Agent'}</div>
      <div>
        <div className="message-body">
          {message.text && message.role === 'assistant' ? (
            <MarkdownContent>{message.text}</MarkdownContent>
          ) : message.text || (message.streaming ? <span className="typing">Working</span> : '')}
        </div>
        {message.elapsedMs !== undefined && (
          <div className="response-time">Response time {(message.elapsedMs / 1000).toFixed(1)}s</div>
        )}
      </div>
    </article>
  );
}

export default function App() {
  const [sessionId, setSessionId] = useState(newSessionId);
  const [resume, setResume] = useState({ status: 'idle' });
  const [messages, setMessages] = useState([]);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [health, setHealth] = useState(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileSidebar, setMobileSidebar] = useState(false);
  const [activityOpen, setActivityOpen] = useState(false);
  const [activities, setActivities] = useState([]);
  const [reasoning, setReasoning] = useState([]);
  const conversationRef = useRef(null);

  useEffect(() => {
    fetch('/api/health')
      .then((response) => response.json())
      .then(setHealth)
      .catch(() => setHealth({ status: 'error' }));
  }, []);

  useEffect(() => {
    conversationRef.current?.scrollTo({
      top: conversationRef.current.scrollHeight,
      behavior: 'smooth'
    });
  }, [messages, activities, reasoning]);

  async function uploadResume(file) {
    if (!file) return;
    setResume({ status: 'uploading', fileName: file.name });
    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('resume', file);

    try {
      const response = await fetch('/api/resume', { method: 'POST', body: formData });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Resume upload failed.');
      setResume({ status: 'ready', ...data });
      setMobileSidebar(false);
    } catch (error) {
      setResume({ status: 'error', error: error.message });
    }
  }

  function updateAssistant(id, update) {
    setMessages((current) => current.map((item) => item.id === id ? { ...item, ...update } : item));
  }

  function addToken(id, text) {
    setMessages((current) => current.map((item) => (
      item.id === id ? { ...item, text: item.text + text } : item
    )));
  }

  function addReasoning(data) {
    setReasoning((current) => appendReasoning(current, data));
  }

  async function sendMessage(event) {
    event?.preventDefault();
    const cleanMessage = message.trim();
    if (!cleanMessage || busy || resume.status !== 'ready') return;

    const assistantId = crypto.randomUUID();
    setMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), role: 'user', text: cleanMessage },
      { id: assistantId, role: 'assistant', text: '', streaming: true }
    ]);
    setMessage('');
    setActivities([{ type: 'status', label: 'Coordinator started' }]);
    setReasoning([]);
    setActivityOpen(true);
    setBusy(true);

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: cleanMessage })
      });
      if (!response.ok) throw new Error('The server rejected the request.');

      await readSse(response, ({ event: eventName, data }) => {
        if (eventName === 'token') addToken(assistantId, data.text);
        if (eventName === 'reasoning') addReasoning(data);
        if (eventName === 'activity') setActivities((current) => [...current, data]);
        if (eventName === 'done') {
          updateAssistant(assistantId, {
            text: data.answer,
            elapsedMs: data.elapsedMs,
            streaming: false
          });
          setActivityOpen(false);
        }
        if (eventName === 'error') throw new Error(data.message);
      });
    } catch (error) {
      updateAssistant(assistantId, {
        text: error.message,
        error: true,
        streaming: false
      });
      setActivities((current) => [...current, { type: 'warning', label: 'Request failed' }]);
    } finally {
      setBusy(false);
    }
  }

  async function startNewChat() {
    if (busy) return;
    await fetch('/api/reset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId })
    }).catch(() => {});
    setSessionId(newSessionId());
    setResume({ status: 'idle' });
    setMessages([]);
    setActivities([]);
    setReasoning([]);
    setMessage('');
  }

  const ready = resume.status === 'ready';
  const agentReady = health?.status === 'ok' && health?.apiKeyConfigured;

  return (
    <div className={`app-shell ${sidebarCollapsed ? 'sidebar-is-collapsed' : ''}`}>
      <Sidebar
        collapsed={sidebarCollapsed}
        mobileOpen={mobileSidebar}
        onToggle={() => {
          setSidebarCollapsed((current) => !current);
          setMobileSidebar(false);
        }}
        resume={resume}
        onResume={uploadResume}
      />
      {mobileSidebar && <button className="backdrop" onClick={() => setMobileSidebar(false)} aria-label="Close sidebar" />}

      <main className="workspace">
        <header className="topbar">
          <div className="topbar-title">
            <button className="mobile-menu" onClick={() => setMobileSidebar(true)} aria-label="Open sidebar">☰</button>
            <div>
              <p className="eyebrow">Local agent workspace</p>
              <h1>Job application assistant</h1>
              <div className="model-line">
                {health?.model || 'Checking model'}
                {health?.skills && ` · ${health.skills.length} skills`}
                {health?.browserEnabled !== undefined && ` · Playwright ${health.browserEnabled ? 'on' : 'off'}`}
              </div>
            </div>
          </div>
          <div className="topbar-actions">
            <div className={`health ${agentReady ? 'ready' : health?.status === 'error' || health?.apiKeyConfigured === false ? 'error' : ''}`}>
              <span />
              {agentReady ? 'Agent ready' : health?.apiKeyConfigured === false ? 'API key missing' : health?.status === 'error' ? 'Server offline' : 'Connecting'}
            </div>
            <button className="new-chat" onClick={startNewChat} disabled={busy}>
              <span>＋</span> New chat
            </button>
          </div>
        </header>

        <section className="main-content">
          {!messages.length && (
            <div className="starter">
              <div className="starter-copy">
                <span className="kicker">Skills · tools · specialists</span>
                <h2>One place to work through your next application.</h2>
                <p>Upload a resume, then ask about a public role, create truthful application material, or prepare a follow-up.</p>
                {!ready && <div className="resume-required">Upload a resume in the left panel to begin.</div>}
              </div>
              <div className="prompt-grid">
                {STARTERS.map((starter) => (
                  <button key={starter.number} className="prompt" onClick={() => setMessage(starter.prompt)}>
                    <span>{starter.number}</span>
                    <strong>{starter.title}</strong>
                    <small>{starter.note}</small>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="conversation" ref={conversationRef}>
            {messages.map((item) => <Message key={item.id} message={item} />)}
          </div>
        </section>

        <section className={`activity-panel ${activityOpen ? 'open' : ''}`}>
          <button className="activity-heading" onClick={() => setActivityOpen((current) => !current)}>
            <span><i className={busy ? 'pulse' : ''} /> Agent activity</span>
            <span>{activityOpen ? 'Hide' : 'Show'}</span>
          </button>
          {activityOpen && (
            <div className="activity-body">
              <div className="event-list">
                {activities.length ? activities.map((item, index) => (
                  <span className={`event ${item.type}`} key={`${item.label}-${index}`}>{item.label}</span>
                )) : <span className="quiet">Activity will appear during a run.</span>}
              </div>
              <div className="reasoning-summary">
                <strong>Concise reasoning summary</strong>
                {reasoning.length ? reasoning.map((item) => (
                  <div className="reasoning-item" key={item.id}>
                    <MarkdownContent>{item.text}</MarkdownContent>
                  </div>
                )) : (
                  <p>Shown here when the model provides one. Private chain-of-thought is not displayed.</p>
                )}
              </div>
            </div>
          )}
        </section>

        <form className="composer-wrap" onSubmit={sendMessage}>
          <div className="composer">
            <textarea
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault();
                  sendMessage();
                }
              }}
              placeholder={ready ? 'Ask about a role or application…' : 'Upload a resume to start chatting'}
              disabled={!ready || busy}
              rows="1"
              aria-label="Message"
            />
            <button type="submit" disabled={!ready || busy || !message.trim()} aria-label="Send message">↑</button>
          </div>
          <div className="composer-meta">
            <span>{ready ? 'Resume loaded for this chat' : 'Resume required'}</span>
            <span>Enter to send · Shift + Enter for a new line</span>
          </div>
        </form>
      </main>
    </div>
  );
}
