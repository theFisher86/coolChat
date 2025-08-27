import React, { useEffect, useState } from 'react';

function App() {
  const [health, setHealth] = useState('unknown');

  useEffect(() => {
    fetch('/health')
      .then(() => setHealth('online'))
      .catch(() => setHealth('offline'));
  }, []);

  return (
    <div>
      <h1>CoolChat</h1>
      <p>Welcome to CoolChat, a Python/React re-imagination of SillyTavern.</p>
      <span>{health}</span>
    </div>
  );
}

export default App;
