import React, { useState, useMemo } from 'react';
import {
  MessageSquare,
  HelpCircle,
  Plus,
  Trash2,
  Search,
  X,
  ChevronRight,
  Radio,
  Clock,
  Sparkles,
} from 'lucide-react';

export const FAQ_ITEMS = [
  {
    category: 'Roaming',
    question: 'What are the roaming charges in the EU?',
    desc: 'EU bundle costs, per-MB charges, and rates.',
  },
  {
    category: 'Roaming',
    question: 'How do I activate international roaming?',
    desc: 'Activation timeline, portal steps, and bundles.',
  },
  {
    category: 'Roaming',
    question: 'Why am I unable to make international calls?',
    desc: 'Account enablement, add-ons, and per-minute rates.',
  },
  {
    category: 'Connectivity',
    question: 'What are diagnostic steps for poor signal strength?',
    desc: 'Step-by-step troubleshooting, coverage, and APN reset.',
  },
  {
    category: 'Connectivity',
    question: 'How do I activate 4G/LTE on my phone?',
    desc: 'Settings path, SIM compatibility, and network mode.',
  },
  {
    category: 'Connectivity',
    question: 'How do I check if there is a network outage in my area?',
    desc: 'Postal code checks, live status page, and maintenance.',
  },
  {
    category: 'Billing',
    question: 'Why is my bill higher than usual?',
    desc: 'Roaming fees, premium SMS, add-on data packs.',
  },
  {
    category: 'Billing',
    question: 'When is my bill due?',
    desc: 'Monthly anniversary dates and grace periods.',
  },
  {
    category: 'Billing',
    question: 'How do I set up autopay?',
    desc: 'Payment methods, SMS reminders, and recurring billing.',
  },
  {
    category: 'Billing',
    question: 'How do I get an itemised bill?',
    desc: 'PDF download, call history, and past 12 months.',
  },
  {
    category: 'SIM & Device',
    question: 'How do I replace a lost or stolen SIM card?',
    desc: 'Reporting loss, blocking, replacement fee, store pickup.',
  },
  {
    category: 'SIM & Device',
    question: 'How long does SIM activation take?',
    desc: 'Activation duration, phone restart, and support quoting.',
  },
  {
    category: 'SIM & Device',
    question: 'Can I keep my number when switching to your network?',
    desc: 'Free number porting steps and SMS confirmation.',
  },
  {
    category: 'SIM & Device',
    question: 'My phone shows SIM not detected after a restart. What should I do?',
    desc: 'Reseating SIM, hardware checks, and tray troubleshooting.',
  },
  {
    category: 'Data & Voice',
    question: 'How do I check my current data balance?',
    desc: 'Dialing code *123# and MyTelecom app usage.',
  },
  {
    category: 'Data & Voice',
    question: 'Why is my mobile internet so slow?',
    desc: 'Throttling, network congestion, and airplane mode resets.',
  },
  {
    category: 'Data & Voice',
    question: 'How do I enable Wi-Fi calling?',
    desc: 'Settings toggle, weak signal backup, and compatibility.',
  },
  {
    category: 'Data & Voice',
    question: 'How do I contact customer support?',
    desc: 'Dial 611, in-app live chat hours, and email.',
  },
];

const FAQ_CATEGORIES = ['All', 'Roaming', 'Connectivity', 'Billing', 'SIM & Device', 'Data & Voice'];

function formatTime(timestamp) {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  const now = new Date();
  const diffMinutes = Math.floor((now - date) / (1000 * 60));

  if (diffMinutes < 1) return 'Just now';
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export default function Sidebar({
  isOpen,
  onClose,
  sessions = [],
  currentSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  onSelectFaq,
}) {
  const [activeTab, setActiveTab] = useState('history'); // 'history' | 'faqs'
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');

  // Filter FAQs based on category & search query
  const filteredFaqs = useMemo(() => {
    return FAQ_ITEMS.filter((item) => {
      const matchesCategory =
        selectedCategory === 'All' || item.category === selectedCategory;
      const matchesQuery =
        !searchQuery.trim() ||
        item.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.desc.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesCategory && matchesQuery;
    });
  }, [selectedCategory, searchQuery]);

  return (
    <>
      {/* Mobile backdrop overlay */}
      <div
        className={`sidebar-overlay ${isOpen ? 'active' : ''}`}
        onClick={onClose}
        aria-hidden="true"
      />

      <aside className={`app-sidebar ${isOpen ? 'open' : 'closed'}`}>
        {/* Sidebar Header */}
        <div className="sidebar-header">
          <div className="sidebar-brand">
            <div className="sidebar-brand-icon">
              <Radio size={16} />
            </div>
            <span className="sidebar-brand-text">Knowledge Hub</span>
          </div>
          <button
            className="sidebar-close-btn"
            onClick={onClose}
            aria-label="Close sidebar"
            title="Close sidebar"
          >
            <X size={18} />
          </button>
        </div>

        {/* Action: New Chat Button */}
        <div className="sidebar-action-bar">
          <button
            type="button"
            className="new-chat-btn"
            onClick={() => {
              onNewChat();
              if (window.innerWidth < 768) onClose();
            }}
          >
            <Plus size={16} />
            <span>New Chat</span>
          </button>
        </div>

        {/* Tab Switcher: History vs FAQs */}
        <div className="sidebar-tabs">
          <button
            type="button"
            className={`sidebar-tab ${activeTab === 'history' ? 'active' : ''}`}
            onClick={() => setActiveTab('history')}
          >
            <MessageSquare size={15} />
            <span>History</span>
            {sessions.length > 0 && (
              <span className="tab-count-badge">{sessions.length}</span>
            )}
          </button>
          <button
            type="button"
            className={`sidebar-tab ${activeTab === 'faqs' ? 'active' : ''}`}
            onClick={() => setActiveTab('faqs')}
          >
            <HelpCircle size={15} />
            <span>FAQs</span>
            <span className="tab-count-badge">{FAQ_ITEMS.length}</span>
          </button>
        </div>

        {/* Tab Content */}
        <div className="sidebar-content">
          {activeTab === 'history' ? (
            <div className="history-tab-pane">
              {sessions.length === 0 ? (
                <div className="sidebar-empty-state">
                  <Clock size={28} className="sidebar-empty-icon" />
                  <p className="sidebar-empty-title">No conversations yet</p>
                  <p className="sidebar-empty-text">
                    Ask a question to start your first telecom support session.
                  </p>
                </div>
              ) : (
                <div className="session-list">
                  {sessions.map((session) => {
                    const isActive = session.id === currentSessionId;
                    return (
                      <div
                        key={session.id}
                        className={`session-item ${isActive ? 'active' : ''}`}
                        onClick={() => {
                          onSelectSession(session.id);
                          if (window.innerWidth < 768) onClose();
                        }}
                        role="button"
                        tabIndex={0}
                      >
                        <div className="session-item-icon">
                          <MessageSquare size={15} />
                        </div>
                        <div className="session-item-details">
                          <span className="session-item-title">
                            {session.title || 'Support Inquiry'}
                          </span>
                          <span className="session-item-time">
                            {formatTime(session.updatedAt)}
                          </span>
                        </div>
                        <button
                          type="button"
                          className="session-delete-btn"
                          title="Delete session"
                          onClick={(e) => {
                            e.stopPropagation();
                            onDeleteSession(session.id);
                          }}
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ) : (
            <div className="faqs-tab-pane">
              {/* FAQ Search */}
              <div className="faq-search-wrapper">
                <Search size={14} className="faq-search-icon" />
                <input
                  type="text"
                  placeholder="Search FAQs (roaming, SIM, 4G)..."
                  className="faq-search-input"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
                {searchQuery && (
                  <button
                    className="faq-search-clear"
                    onClick={() => setSearchQuery('')}
                    title="Clear search"
                  >
                    <X size={12} />
                  </button>
                )}
              </div>

              {/* Category Pills */}
              <div className="faq-categories">
                {FAQ_CATEGORIES.map((cat) => (
                  <button
                    key={cat}
                    type="button"
                    className={`faq-cat-pill ${
                      selectedCategory === cat ? 'active' : ''
                    }`}
                    onClick={() => setSelectedCategory(cat)}
                  >
                    {cat}
                  </button>
                ))}
              </div>

              {/* FAQ List */}
              <div className="faq-list">
                {filteredFaqs.length === 0 ? (
                  <div className="sidebar-empty-state">
                    <p className="sidebar-empty-title">No matching FAQs</p>
                    <p className="sidebar-empty-text">
                      Try searching with another keyword or pick 'All'.
                    </p>
                  </div>
                ) : (
                  filteredFaqs.map((faq, idx) => (
                    <button
                      key={idx}
                      type="button"
                      className="faq-item"
                      onClick={() => {
                        onSelectFaq(faq.question);
                        if (window.innerWidth < 768) onClose();
                      }}
                    >
                      <div className="faq-item-header">
                        <span className="faq-badge">{faq.category}</span>
                        <ChevronRight size={13} className="faq-chevron" />
                      </div>
                      <div className="faq-item-question">{faq.question}</div>
                      <div className="faq-item-desc">{faq.desc}</div>
                    </button>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* Sidebar Footer */}
        <div className="sidebar-footer">
          <div className="sidebar-footer-badge">
            <Sparkles size={12} />
            <span>ChromaDB RAG Grounded</span>
          </div>
          <div className="sidebar-credits">
            Data courtesy of{' '}
            <a
              href="https://codebasics.io/resources/agentic-ai-crash-course"
              target="_blank"
              rel="noopener noreferrer"
            >
              Codebasics
            </a>
          </div>
        </div>
      </aside>
    </>
  );
}
