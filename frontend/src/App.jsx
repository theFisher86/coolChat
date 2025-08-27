import React, { useState } from 'react';
import './App.css';

function App() {
  const [messages, setMessages] = useState([]);
  const [currentInput, setCurrentInput] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!currentInput.trim()) return;
    setMessages([...messages, currentInput]);
    setCurrentInput('');
  };

  return (
    <div className="chat-container">
      <h1>CoolChat</h1>
      <ul>
        {messages.map((msg, idx) => (
          <li key={idx}>{msg}</li>
        ))}
      </ul>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          value={currentInput}
          onChange={(e) => setCurrentInput(e.target.value)}
          placeholder="Type a message..."
        />
        <button type="submit">Send</button>
      </form>
    </div>
  );
}

export default App;
