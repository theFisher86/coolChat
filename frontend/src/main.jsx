import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { loadPlugins } from './pluginHost';

// Warm up plugin system (non-blocking)
loadPlugins();

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
