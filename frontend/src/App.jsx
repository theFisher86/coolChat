import React, { useEffect, useState } from 'react';
import { checkHealth } from './api';
import './App.css';

function App() {
  const [apiOnline, setApiOnline] = useState(null);

  useEffect(() => {
    async function fetchHealth() {
      const ok = await checkHealth();
      setApiOnline(ok);
    }
    fetchHealth();
  }, []);

  return (
    <div>
      <h1>CoolChat</h1>
      <p>Welcome to CoolChat, a Python/React re-imagination of SillyTavern.</p>
      {apiOnline !== null && (
        <span
          className={`status-badge ${apiOnline ? 'status-online' : 'status-offline'}`}
        >
          API {apiOnline ? 'online' : 'offline'}
        </span>
      )}
    </div>
  );
}

export default App;
