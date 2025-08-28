import React, { useEffect, useState } from 'react';
import './App.css';
import { sendChat, getConfig, updateConfig, getModels } from './api';

function App() {
  const [messages, setMessages] = useState([]); // {role: 'user'|'assistant', content}
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const [showConfig, setShowConfig] = useState(false);
  const [config, setConfig] = useState({ provider: 'echo', api_key_masked: null, api_base: '', model: '', temperature: 0.7 });
  const [configDraft, setConfigDraft] = useState({ provider: 'echo', api_key: '', api_base: '', model: '', temperature: 0.7 });
  const [modelList, setModelList] = useState([]);
  const [loadingModels, setLoadingModels] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const cfg = await getConfig();
        setConfig(cfg);
        setConfigDraft({
          provider: cfg.provider,
          api_key: '',
          api_base: cfg.api_base,
          model: cfg.model,
          temperature: cfg.temperature,
        });
      } catch (e) {
        console.warn('Could not load config', e);
      }
    })();
  }, []);

  const refreshModels = async (prov) => {
    const p = prov ?? configDraft.provider;
    if (p === 'echo') { setModelList([]); return; }
    try {
      setLoadingModels(true);
      const { models } = await getModels(p);
      setModelList(models || []);
    } catch (e) {
      setModelList([]);
      console.warn('Model load failed', e);
    } finally {
      setLoadingModels(false);
    }
  };

  useEffect(() => {
    // Load models when provider changes and settings are shown
    if (showConfig) {
      refreshModels();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [configDraft.provider, showConfig]);

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
        <div className="spacer" />
        <button className="secondary" onClick={() => setShowConfig((s) => !s)}>
          {showConfig ? 'Close Settings' : 'Settings'}
        </button>
      </header>

      <main className="chat">
        {showConfig && (
          <section className="panel">
            <h2>Configuration</h2>
            <p className="muted">Choose provider and set API credentials.</p>
            <form
              className="config-form"
              onSubmit={async (e) => {
                e.preventDefault();
                try {
                  const updated = await updateConfig(configDraft);
                  setConfig(updated);
                } catch (e) {
                  alert(e.message);
                }
              }}
            >
              <label>
                <span>Provider</span>
                <select
                  value={configDraft.provider}
                  onChange={(e) => setConfigDraft((d) => ({ ...d, provider: e.target.value }))}
                >
                  <option value="echo">Echo (no API key)</option>
                  <option value="openai">OpenAI-compatible</option>
                  <option value="openrouter">OpenRouter</option>
                  <option value="gemini">Google Gemini</option>
                </select>
              </label>

              <label>
                <span>API Key</span>
                <input
                  type="password"
                  placeholder={config.api_key_masked ? `Saved: ${config.api_key_masked}` : 'sk-...'}
                  value={configDraft.api_key}
                  onChange={(e) => setConfigDraft((d) => ({ ...d, api_key: e.target.value }))}
                />
              </label>

              <label>
                <span>API Base</span>
                <input
                  type="text"
                  placeholder={
                    configDraft.provider === 'openrouter'
                      ? 'https://openrouter.ai/api/v1'
                      : configDraft.provider === 'openai'
                      ? 'https://api.openai.com/v1'
                      : 'https://generativelanguage.googleapis.com/v1beta/openai'
                  }
                  value={configDraft.api_base}
                  onChange={(e) => setConfigDraft((d) => ({ ...d, api_base: e.target.value }))}
                />
              </label>

              <label>
                <span>Model</span>
                {modelList.length > 0 ? (
                  <select
                    value={configDraft.model || ''}
                    onChange={(e) => setConfigDraft((d) => ({ ...d, model: e.target.value }))}
                  >
                    <option value="">{loadingModels ? 'Loading…' : 'Select a model'}</option>
                    {modelList.map((m) => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="text"
                    placeholder={configDraft.provider === 'gemini' ? 'gemini-1.5-flash' : 'gpt-4o-mini'}
                    value={configDraft.model}
                    onChange={(e) => setConfigDraft((d) => ({ ...d, model: e.target.value }))}
                  />
                )}
              </label>

              <div className="row">
                <button type="button" className="secondary" onClick={() => refreshModels()} disabled={loadingModels}>
                  {loadingModels ? 'Refreshing…' : 'Refresh models'}
                </button>
              </div>

              <label>
                <span>Temperature</span>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="2"
                  value={configDraft.temperature}
                  onChange={(e) => setConfigDraft((d) => ({ ...d, temperature: parseFloat(e.target.value) }))}
                />
              </label>

              <div className="row">
                <button type="submit">Save</button>
                <button
                  type="button"
                  className="secondary"
                  onClick={() => setConfigDraft({
                    provider: config.provider,
                    api_key: '',
                    api_base: config.api_base,
                    model: config.model,
                    temperature: config.temperature,
                  })}
                >
                  Reset
                </button>
              </div>
            </form>

            <div className="hint">
              <p className="muted">
                OpenRouter uses OpenAI-compatible endpoints. You can set API Base to https://openrouter.ai/api/v1. Gemini requires a model like gemini-1.5-flash and uses Google’s API.
              </p>
            </div>
          </section>
        )}

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
