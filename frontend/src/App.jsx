import React, { useState } from 'react';
import './App.css';
import { sendChat } from './api';

function App() {
  const [messages, setMessages] = useState([]); // {role: 'user'|'assistant', content}
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);

  const onSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    const trimmed = input.trim();
    if (!trimmed) return;
    const userMsg = { role: 'user', content: trimmed };
    setMessages((m) => [...m, userMsg]);
    setInput('');
    setSending(true);
    try {
      const reply = await sendChat(trimmed);
      setMessages((m) => [...m, { role: 'assistant', content: reply }]);
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="app">
      <header className="header">
        <h1>CoolChat</h1>
      </header>

      <main className="chat">
        <div className="messages" aria-live="polite">
          {messages.map((m, idx) => (
            <div key={idx} className={`message ${m.role}`}>
              <div className="bubble">{m.content}</div>
            </div>
          ))}
          {error && (
            <div className="message error">
              <div className="bubble">{error}</div>
            </div>
          )}
        </div>

        <form className="input-row" onSubmit={onSubmit}>
          <input
            type="text"
            placeholder="Type your message"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={sending}
          />
          <button type="submit" disabled={sending || !input.trim()}>
            {sending ? 'Sending…' : 'Send'}
          </button>
        </form>
      </main>
    </div>
  );
}

export default App;
