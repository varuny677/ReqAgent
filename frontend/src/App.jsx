import { useState, useEffect, useRef } from 'react';
import { FiPlus, FiSend, FiMessageSquare, FiUser } from 'react-icons/fi';
import { BsRobot } from 'react-icons/bs';
import axios from 'axios';
import { v4 as uuidv4 } from 'uuid';
import './App.css';

const API_BASE_URL = 'http://localhost:8000';

function App() {
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const createNewChat = () => {
    const newSessionId = uuidv4();
    const newSession = {
      id: newSessionId,
      title: 'New Chat',
      preview: '',
    };
    setSessions([newSession, ...sessions]);
    setCurrentSessionId(newSessionId);
    setMessages([]);
    setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userQuery = input.trim();
    setInput('');
    setError(null);

    // Create session if none exists
    let sessionId = currentSessionId;
    if (!sessionId) {
      sessionId = uuidv4();
      setCurrentSessionId(sessionId);
      const newSession = {
        id: sessionId,
        title: userQuery.substring(0, 30) + (userQuery.length > 30 ? '...' : ''),
        preview: userQuery,
      };
      setSessions([newSession, ...sessions]);
    } else {
      // Update session title if it's the first message
      if (messages.length === 0) {
        setSessions(sessions.map(s =>
          s.id === sessionId
            ? { ...s, title: userQuery.substring(0, 30) + (userQuery.length > 30 ? '...' : ''), preview: userQuery }
            : s
        ));
      }
    }

    // Add user message
    const userMessage = {
      id: uuidv4(),
      role: 'user',
      content: userQuery,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    try {
      const response = await axios.post(`${API_BASE_URL}/api/search`, {
        query: userQuery,
        session_id: sessionId,
      });

      // Add assistant response
      const assistantMessage = {
        id: response.data.message_id,
        role: 'assistant',
        content: response.data.results,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      console.error('Error searching companies:', err);
      setError(
        err.response?.data?.detail ||
        'Failed to search companies. Please make sure the backend server and Temporal worker are running.'
      );
      // Remove the user message on error
      setMessages((prev) => prev.filter((m) => m.id !== userMessage.id));
    } finally {
      setLoading(false);
    }
  };

  const selectSession = (sessionId) => {
    setCurrentSessionId(sessionId);
    // In a real app, you'd fetch messages from the backend
    // For now, since it's session-based, we'll just clear messages
    setMessages([]);
    setError(null);
  };

  const renderCompanyResults = (results) => {
    if (!results.success) {
      return (
        <div className="error-message">
          Error: {results.error || 'Failed to fetch company information'}
        </div>
      );
    }

    const companies = results.results;

    if (!companies || companies.length === 0) {
      return <p>No companies found.</p>;
    }

    if (companies.raw_response) {
      return <div style={{ whiteSpace: 'pre-wrap' }}>{companies.raw_response}</div>;
    }

    return (
      <div>
        <p style={{ marginBottom: '12px' }}>
          Found {results.count} {results.count === 1 ? 'company' : 'companies'}:
        </p>
        {companies.map((company, index) => (
          <div key={index} className="company-card">
            <h3>{company.name || 'N/A'}</h3>
            {company.description && <p>{company.description}</p>}
            {company.industry && (
              <p>
                <strong>Industry:</strong> {company.industry}
              </p>
            )}
            {company.location && (
              <p>
                <strong>Location:</strong> {company.location}
              </p>
            )}
            {company.website && (
              <p>
                <strong>Website:</strong>{' '}
                <a href={company.website} target="_blank" rel="noopener noreferrer">
                  {company.website}
                </a>
              </p>
            )}
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="app">
      {/* Sidebar */}
      <div className="sidebar">
        <div className="sidebar-header">
          <button className="new-chat-btn" onClick={createNewChat}>
            <FiPlus /> New Chat
          </button>
        </div>
        <div className="chat-history">
          {sessions.map((session) => (
            <button
              key={session.id}
              className={`chat-history-item ${currentSessionId === session.id ? 'active' : ''}`}
              onClick={() => selectSession(session.id)}
            >
              <FiMessageSquare />
              {session.title}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <div className="main-content">
        <div className="chat-container">
          {messages.length === 0 ? (
            <div className="empty-state">
              <h1>Company Search Agent</h1>
              <p>Search for companies by name. Enter multiple company names separated by commas.</p>
            </div>
          ) : (
            <div className="messages">
              {messages.map((message) => (
                <div key={message.id} className={`message ${message.role}`}>
                  <div className="message-icon">
                    {message.role === 'user' ? <FiUser /> : <BsRobot />}
                  </div>
                  <div className="message-content">
                    {message.role === 'user' ? (
                      <p>{message.content}</p>
                    ) : (
                      renderCompanyResults(message.content.search_results)
                    )}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="message assistant">
                  <div className="message-icon">
                    <BsRobot />
                  </div>
                  <div className="message-content">
                    <div className="loading">
                      <div className="loading-dot"></div>
                      <div className="loading-dot"></div>
                      <div className="loading-dot"></div>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
          {error && <div className="error-message">{error}</div>}
        </div>

        {/* Input Container */}
        <div className="input-container">
          <div className="input-wrapper">
            <form className="input-form" onSubmit={handleSubmit}>
              <input
                type="text"
                className="input-field"
                placeholder="Search for companies... (e.g., Apple, Microsoft, Google)"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={loading}
              />
              <button
                type="submit"
                className="send-btn"
                disabled={loading || !input.trim()}
              >
                <FiSend />
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
