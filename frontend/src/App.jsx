import React, { useState, useRef, useEffect } from 'react';
import {
  Radio,
  Send,
  RotateCcw,
  ArrowRight,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
} from 'lucide-react';
import { askTelecomAI } from './api';
import Sidebar from './components/Sidebar';
import ThemeToggle from './components/ThemeToggle';

const STARTER_QUESTIONS = [
  'What are the roaming charges in the EU?',
  'Troubleshoot mobile internet & APN settings',
  'How do I check my current data balance?',
  'What are diagnostic steps for poor signal strength?',
];

const SESSIONS_STORAGE_KEY = 'telecom_rag_sessions_v1';
const THEME_STORAGE_KEY = 'telecom_rag_theme_v1';

/**
 * Format markdown text (bold, lists, code) into clean React elements.
 */
function FormattedMessage({ content }) {
  const lines = content.split('\n');
  const elements = [];
  let currentList = [];
  let listType = null; // 'ul' or 'ol'

  const flushList = () => {
    if (currentList.length > 0) {
      if (listType === 'ol') {
        elements.push(<ol key={`ol-${elements.length}`}>{currentList}</ol>);
      } else {
        elements.push(<ul key={`ul-${elements.length}`}>{currentList}</ul>);
      }
      currentList = [];
      listType = null;
    }
  };

  const parseInline = (text) => {
    const parts = [];
    const regex = /(\*\*[^*]+\*\*|`[^`]+`)/g;
    let lastIndex = 0;
    let match;

    while ((match = regex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        parts.push(text.substring(lastIndex, match.index));
      }
      const token = match[0];
      if (token.startsWith('**') && token.endsWith('**')) {
        parts.push(<strong key={match.index}>{token.slice(2, -2)}</strong>);
      } else if (token.startsWith('`') && token.endsWith('`')) {
        parts.push(<code key={match.index}>{token.slice(1, -1)}</code>);
      }
      lastIndex = regex.lastIndex;
    }

    if (lastIndex < text.length) {
      parts.push(text.substring(lastIndex));
    }

    return parts.length > 0 ? parts : text;
  };

  lines.forEach((line, index) => {
    const trimmed = line.trim();

    if (!trimmed) {
      flushList();
      return;
    }

    // Numbered list: e.g. "1. Step"
    const numMatch = trimmed.match(/^(\d+)\.\s+(.*)/);
    if (numMatch) {
      if (listType !== 'ol') {
        flushList();
        listType = 'ol';
      }
      currentList.push(<li key={`li-${index}`}>{parseInline(numMatch[2])}</li>);
      return;
    }

    // Bullet list: e.g. "- item" or "* item"
    const bulletMatch = trimmed.match(/^[-*•]\s+(.*)/);
    if (bulletMatch) {
      if (listType !== 'ul') {
        flushList();
        listType = 'ul';
      }
      currentList.push(<li key={`li-${index}`}>{parseInline(bulletMatch[1])}</li>);
      return;
    }

    // Regular paragraph
    flushList();
    elements.push(<p key={`p-${index}`}>{parseInline(trimmed)}</p>);
  });

  flushList();

  return <div className="formatted-content">{elements}</div>;
}

export default function App() {
  // Theme State
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem(THEME_STORAGE_KEY);
    if (saved === 'dark' || saved === 'light') return saved;
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light';
  });

  // Sessions State
  const [sessions, setSessions] = useState(() => {
    try {
      const saved = localStorage.getItem(SESSIONS_STORAGE_KEY);
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [currentSessionId, setCurrentSessionId] = useState(() => {
    try {
      const saved = localStorage.getItem(SESSIONS_STORAGE_KEY);
      const parsed = saved ? JSON.parse(saved) : [];
      if (parsed && parsed.length > 0 && parsed[0].id) {
        return parsed[0].id;
      }
    } catch {}
    return 'session_' + Date.now();
  });

  const [messages, setMessages] = useState(() => {
    try {
      const saved = localStorage.getItem(SESSIONS_STORAGE_KEY);
      const parsed = saved ? JSON.parse(saved) : [];
      if (parsed && parsed.length > 0 && Array.isArray(parsed[0].messages)) {
        return parsed[0].messages;
      }
    } catch {}
    return [];
  });

  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  // Default to false so users land directly on the chat session
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const chatBottomRef = useRef(null);
  const inputRef = useRef(null);

  // Focus chat input on mount or session change
  useEffect(() => {
    inputRef.current?.focus();
  }, [currentSessionId]);

  // Apply theme to document element
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [theme]);

  // Persist sessions whenever sessions array updates
  useEffect(() => {
    try {
      localStorage.setItem(SESSIONS_STORAGE_KEY, JSON.stringify(sessions));
    } catch {
      // quota or localstorage disabled
    }
  }, [sessions]);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const handleNewChat = () => {
    const newId = 'session_' + Date.now();
    setCurrentSessionId(newId);
    setMessages([]);
    setInput('');
    setSidebarOpen(false);
    setTimeout(() => inputRef.current?.focus(), 50);
  };

  const handleSelectSession = (sessionId) => {
    const target = sessions.find((s) => s.id === sessionId);
    if (target) {
      setCurrentSessionId(target.id);
      setMessages(target.messages || []);
      setInput('');
      setSidebarOpen(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  };

  const handleDeleteSession = (sessionId) => {
    setSessions((prev) => prev.filter((s) => s.id !== sessionId));
    if (sessionId === currentSessionId) {
      handleNewChat();
    }
  };

  const updateSessionRecord = (sessionId, updatedMessages) => {
    if (updatedMessages.length === 0) return;

    setSessions((prev) => {
      const existingIdx = prev.findIndex((s) => s.id === sessionId);
      const title =
        updatedMessages[0]?.content?.slice(0, 42) +
        (updatedMessages[0]?.content?.length > 42 ? '...' : '');

      const updatedSession = {
        id: sessionId,
        title: title || 'Support Inquiry',
        messages: updatedMessages,
        updatedAt: Date.now(),
      };

      if (existingIdx >= 0) {
        const copy = [...prev];
        copy[existingIdx] = updatedSession;
        // Keep most recently updated at the top
        return copy.sort((a, b) => b.updatedAt - a.updatedAt);
      } else {
        return [updatedSession, ...prev];
      }
    });
  };

  const handleSend = async (queryText) => {
    const text = (queryText || input).trim();
    if (!text || loading) return;

    const userMessage = { id: Date.now(), role: 'user', content: text };
    const nextMessages = [...messages, userMessage];
    setMessages(nextMessages);
    setInput('');
    setLoading(true);

    // Save user message immediately to session
    updateSessionRecord(currentSessionId, nextMessages);

    try {
      const answer = await askTelecomAI(text);
      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: answer,
      };
      const finalMessages = [...nextMessages, assistantMessage];
      setMessages(finalMessages);
      updateSessionRecord(currentSessionId, finalMessages);
    } catch (err) {
      const errorMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: `Sorry, an error occurred: ${
          err.message || 'Unable to fetch response.'
        } Please ensure the backend is running.`,
      };
      const finalMessages = [...nextMessages, errorMessage];
      setMessages(finalMessages);
      updateSessionRecord(currentSessionId, finalMessages);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setMessages([]);
    setInput('');
    // Remove or empty current session
    setSessions((prev) => prev.filter((s) => s.id !== currentSessionId));
  };

  return (
    <div className="app-root">
      {/* Collapsible Sidebar */}
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelectSession={handleSelectSession}
        onNewChat={handleNewChat}
        onDeleteSession={handleDeleteSession}
        onSelectFaq={(faqText) => {
          setSidebarOpen(false);
          handleSend(faqText);
        }}
      />

      {/* Main Chat Container */}
      <div className="chat-container">
        {/* Top Header */}
        <header className="app-header">
          <div className="header-left">
            <button
              type="button"
              className="sidebar-toggle-btn"
              onClick={() => setSidebarOpen((prev) => !prev)}
              aria-label={sidebarOpen ? 'Hide sidebar' : 'Open sidebar'}
              title={sidebarOpen ? 'Collapse sidebar' : 'Open sidebar'}
            >
              {sidebarOpen ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}
            </button>

            <div className="brand-wrapper">
              <div className="brand-icon">
                <Radio size={18} />
              </div>
              <span className="brand-title">Telco AI</span>
              <span className="brand-tag">Support</span>
            </div>
          </div>

          <div className="header-actions">
            <ThemeToggle theme={theme} onToggle={toggleTheme} />

            {messages.length > 0 && (
              <button className="clear-btn" onClick={handleClear} title="Clear conversation">
                <RotateCcw size={14} />
                <span>Clear</span>
              </button>
            )}
          </div>
        </header>

        {/* Main Chat Feed */}
        <main className="chat-main">
          <div className="chat-inner-wrap">
            {messages.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">
                  <Radio size={24} />
                </div>
                <h1 className="empty-title">Telecom Support Assistant</h1>
                <p className="empty-subtitle">
                  Ask any question regarding international roaming, billing, SIM setup, or network troubleshooting.
                </p>

                <div className="starter-chips-grid">
                  {STARTER_QUESTIONS.map((question, idx) => (
                    <button
                      key={idx}
                      className="starter-chip"
                      onClick={() => handleSend(question)}
                    >
                      <span>{question}</span>
                      <ArrowRight size={14} className="starter-chip-arrow" />
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="messages-list">
                {messages.map((msg) => (
                  <div key={msg.id} className={`message-row ${msg.role}`}>
                    <div className="message-bubble">
                      {msg.role === 'user' ? (
                        msg.content
                      ) : (
                        <FormattedMessage content={msg.content} />
                      )}
                    </div>
                  </div>
                ))}

                {loading && (
                  <div className="message-row assistant">
                    <div className="message-bubble">
                      <div className="typing-indicator">
                        <div className="typing-dot"></div>
                        <div className="typing-dot"></div>
                        <div className="typing-dot"></div>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={chatBottomRef} />
              </div>
            )}
          </div>
        </main>

        {/* Bottom Input Dock */}
        <footer className="input-container">
          <div className="input-inner-wrap">
            <form
              className="input-form"
              onSubmit={(e) => {
                e.preventDefault();
                handleSend();
              }}
            >
              <input
                ref={inputRef}
                type="text"
                className="chat-input"
                placeholder="Ask a question about telecom services, billing, or network..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={loading}
                autoFocus
              />
              <button
                type="submit"
                className="send-btn"
                disabled={loading || !input.trim()}
                title="Send question"
              >
                <Send size={16} />
              </button>
            </form>
            <div className="input-disclaimer">
              AI assistant powered by Google Gemini & ChromaDB. Data provided by{' '}
              <a
                href="https://codebasics.io/resources/agentic-ai-crash-course"
                target="_blank"
                rel="noopener noreferrer"
              >
                Codebasics
              </a>.
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}
