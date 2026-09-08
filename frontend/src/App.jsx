import React, { useState, useRef, useEffect } from 'react';
import { Radio, Send, RotateCcw, ArrowRight } from 'lucide-react';
import { askTelecomAI } from './api';

const STARTER_QUESTIONS = [
  'What are the roaming charges in the EU?',
  'Troubleshoot mobile internet & APN settings',
  'How do I check my current data balance?',
  'What are diagnostic steps for poor signal strength?',
];

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
    // Parse inline bold (**bold**) and inline code (`code`)
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
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const chatBottomRef = useRef(null);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSend = async (queryText) => {
    const text = (queryText || input).trim();
    if (!text || loading) return;

    const userMessage = { id: Date.now(), role: 'user', content: text };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const answer = await askTelecomAI(text);
      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: answer,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      const errorMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: `Sorry, an error occurred: ${err.message || 'Unable to fetch response.'} Please ensure the backend is running.`,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setMessages([]);
    setInput('');
  };

  return (
    <div className="app-container">
      {/* Minimal Header */}
      <header className="app-header">
        <div className="brand-wrapper">
          <div className="brand-icon">
            <Radio size={18} />
          </div>
          <span className="brand-title">Telco AI</span>
          <span className="brand-tag">Support</span>
        </div>

        {messages.length > 0 && (
          <button className="clear-btn" onClick={handleClear} title="Clear conversation">
            <RotateCcw size={14} />
            Clear
          </button>
        )}
      </header>

      {/* Main Chat Feed */}
      <main className="chat-main">
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
      </main>

      {/* Input Dock */}
      <footer className="input-container">
        <form
          className="input-form"
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
        >
          <input
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
          AI assistant powered by Google Gemini & ChromaDB.
        </div>
      </footer>
    </div>
  );
}
