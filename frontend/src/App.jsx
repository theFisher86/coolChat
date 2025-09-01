import React, { useEffect, useState, useRef } from 'react';
import './App.css';
import {
  sendChat,
  getConfig,
  updateConfig,
  getModels,
  listCharacters,
  createCharacter,
  deleteCharacter,
  updateCharacter,
  suggestCharacterField,
  listLorebooks,
  getImageModels,
  generateImageFromChat,
  generateImageDirect,
  updateLoreEntry,
  updateLorebook,
  listChats,
  getChat,
  resetChat,
  getPrompts,
  savePrompts,
  suggestLoreFromChat,
  getMcpServers,
  saveMcpServers,
  getMcpAwesome,
} from './api';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);

  const [showConfig, setShowConfig] = useState(false);
  const [settingsTab, setSettingsTab] = useState('connection');
  const [showChats, setShowChats] = useState(false);
  const [sessionId, setSessionId] = useState('default');
  const [phoneOpen, setPhoneOpen] = useState(false);
  const [phoneUrl, setPhoneUrl] = useState('https://example.org');
  const [phoneStyle, setPhoneStyle] = useState('classic');
  const [suggestOpen, setSuggestOpen] = useState(false);
  const [suggests, setSuggests] = useState([]);
  const [showSOHint, setShowSOHint] = useState(false);
  const [suppressSOHint, setSuppressSOHint] = useState(false);
  const [appTheme, setAppTheme] = useState({ background_animations: [] });
  const [showTools, setShowTools] = useState(false);
  const messagesRef = useRef(null);

  const [activeProvider, setActiveProvider] = useState('echo');
  const [providers, setProviders] = useState({}); // provider -> masked config
  const [configDraft, setConfigDraft] = useState({ api_key: '', api_base: '', model: '', temperature: 0.7 });
  const [modelList, setModelList] = useState([]);
  const [loadingModels, setLoadingModels] = useState(false);

  const [showCharacters, setShowCharacters] = useState(false);
  const [characters, setCharacters] = useState([]);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingChar, setEditingChar] = useState(null);

  const [showLorebooks, setShowLorebooks] = useState(false);
  const [lorebooks, setLorebooks] = useState([]);
  const [selectedLorebook, setSelectedLorebook] = useState(null);
  const [loreEntries, setLoreEntries] = useState([]);
  const [expandedEntries, setExpandedEntries] = useState({});

  const [debugFlags, setDebugFlags] = useState({ log_prompts: false, log_responses: false });
  const [maxTokens, setMaxTokens] = useState(2048);
  const [userPersona, setUserPersona] = useState({ name: 'User', description: '' });

  // Load config on mount
  useEffect(() => {
    (async () => {
      try {
        const cfg = await getConfig();
        setActiveProvider(cfg.active_provider);
        setProviders(cfg.providers || {});
        const cur = cfg.providers?.[cfg.active_provider] || {};
        setConfigDraft({ api_key: '', api_base: cur.api_base || '', model: cur.model || '', temperature: cur.temperature ?? 0.7 });
        setDebugFlags(cfg.debug || { log_prompts: false, log_responses: false });
        setMaxTokens(cfg.max_context_tokens || 2048);
        setUserPersona(cfg.user_persona || { name: 'User', description: '' });
        try { setPhoneStyle((cfg.theme && cfg.theme.phone_style) || 'classic'); } catch {}
        try { setAppTheme(cfg.theme || { background_animations: [] }); } catch {}
      } catch (e) {
        console.warn('Could not load config', e);
      }
    })();
  }, []);

  // Listen for phone style changes from AppearanceTab
  useEffect(() => {
    const h = (e) => { try { if (e && e.detail) setPhoneStyle(e.detail); } catch {} };
    window.addEventListener('coolchat:phoneStyle', h);
    return () => window.removeEventListener('coolchat:phoneStyle', h);
  }, []);

  // Listen for theme updates (background animations, colors, etc.)
  useEffect(() => {
    const h = (e) => { try { if (e && e.detail) setAppTheme(e.detail); } catch {} };
    window.addEventListener('coolchat:themeUpdate', h);
    return () => window.removeEventListener('coolchat:themeUpdate', h);
  }, []);

  // Load chat history on session change
  useEffect(() => {
    (async () => { try { const { messages: msgs } = await getChat(sessionId); setMessages(msgs || []);} catch {} })();
  }, [sessionId]);

  // Characters and lorebooks
  useEffect(() => {
    (async () => { if (showCharacters) { try { const list = await listCharacters(); setCharacters(list); } catch {} } })();
  }, [showCharacters]);
  useEffect(() => {
    (async () => { if (showLorebooks) { try { const lbs = await listLorebooks(); setLorebooks(lbs); if (!selectedLorebook && lbs.length) setSelectedLorebook(lbs[0]); } catch {} } })();
  }, [showLorebooks]);

  useEffect(() => {
    (async () => {
      if (selectedLorebook) {
        // fetch entries by ids
        const ids = selectedLorebook.entry_ids || [];
        const fetched = [];
        for (const id of ids) {
          try { const r = await fetch(`/lore/${id}`); if (r.ok) fetched.push(await r.json()); } catch {}
        }
        setLoreEntries(fetched);
      } else {
        setLoreEntries([]);
      }
    })();
  }, [selectedLorebook]);

  // Models when provider changes and settings are open
  useEffect(() => {
    if (!showConfig) return;
    (async () => {
      try {
        setLoadingModels(true);
        const { models } = await getModels(activeProvider);
        setModelList(models || []);
      } catch (e) {
        setModelList([]);
      } finally {
        setLoadingModels(false);
      }
    })();
  }, [activeProvider, showConfig]);

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
      const cfgForSO = await getConfig();
      const reply = await sendChat(trimmed, sessionId);
      // Try to parse tool calls
      let handled = false;
      let captionText = '';
      try {
        let obj = null;
        try { obj = JSON.parse(reply); } catch (e) {
          // Extract JSON object from mixed text
          const m = reply.match(/\{[\s\S]*\}$/);
          if (m) { obj = JSON.parse(m[0]); captionText = reply.slice(0, m.index).trim(); }
          // Also support array after 'toolCalls:' when SO is off
          if (!obj) {
            const a = reply.match(/toolCalls\s*:\s*(\[[\s\S]*\])/);
            if (a) { try { obj = { toolCalls: JSON.parse(a[1]) }; } catch {} if (!cfgForSO.structured_output && !suppressSOHint) setShowSOHint(true); }
          }
        }
        // Structured calls preferred: toolCalls: [{type,payload}]
        if (obj && Array.isArray(obj.toolCalls)) {
          for (const tc of obj.toolCalls) {
            if (!tc || !tc.type) continue;
            if (tc.type === 'image_request' && tc.payload?.prompt) {
              const r = await generateImageDirect(tc.payload.prompt, sessionId);
              setMessages((m) => [...m, { role: 'assistant', image_url: r.image_url, content: tc.payload.prompt }]);
              handled = true;
            } else if (tc.type === 'phone_url' && tc.payload?.url) {
              let u = tc.payload.url; if (!/^https?:/i.test(u)) u = 'https://' + u; setPhoneUrl(u); setPhoneOpen(true); handled = true;
            } else if (tc.type === 'lore_suggestions' && Array.isArray(tc.payload?.items)) {
              setSuggests(tc.payload.items.map(x => ({ keyword: x.keyword, content: x.content })));
              setSuggestOpen(true); handled = true;
            }
          }
        } else {
          // Flat keys fallback
          if (obj && obj.image_request) {
            const prompt = typeof obj.image_request === 'string' ? obj.image_request : obj.image_request.prompt;
            if (prompt) { const r = await generateImageDirect(prompt, sessionId); setMessages((m) => [...m, { role: 'assistant', image_url: r.image_url, content: prompt }]); handled = true; }
          }
          if (obj && obj.phone_url) { let u = obj.phone_url; if (!/^https?:/i.test(u)) u = 'https://' + u; setPhoneUrl(u); setPhoneOpen(true); handled = true; }
          if (obj && Array.isArray(obj.lore_suggestions)) { setSuggests(obj.lore_suggestions); setSuggestOpen(true); handled = true; }
          if (!cfgForSO.structured_output && !suppressSOHint && /toolCalls\s*:|image_request|phone_url|lore_suggestions/.test(reply) && !handled) {
            setShowSOHint(true);
          }
        }
      } catch (e) { console.warn('Tool parse failed', e); }
      if (!handled) {
        setMessages((m) => [...m, { role: 'assistant', content: reply }]);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className={`app ${phoneOpen ? 'phone-open' : ''}`}>
      <div className="bg-animations">
        {(appTheme.background_animations||[]).map((id, idx) => (
          <div key={idx} className={`anim-${id}`} />
        ))}
      </div>
      <header className="header">
        <h1>CoolChat</h1>
        <div className="spacer" />
        <button className="secondary" onClick={() => { const next = !showCharacters; setShowCharacters(next); if (next) { setShowChats(false); setShowTools(false); setShowLorebooks(false); setShowConfig(false); } }}>
          {showCharacters ? 'Hide Characters' : 'Characters'}
        </button>
        <button className="secondary" onClick={() => { const next = !showChats; setShowChats(next); if (next) { setShowCharacters(false); setShowTools(false); setShowLorebooks(false); setShowConfig(false); } }}>
          {showChats ? 'Hide Chats' : 'Chats'}
        </button>
        <button className="secondary" onClick={() => { const next = !showTools; setShowTools(next); if (next) { setShowCharacters(false); setShowChats(false); setShowLorebooks(false); setShowConfig(false); } }}>
          {showTools ? 'Hide Tools' : 'Tools'}
        </button>
        <button className="secondary" onClick={() => { const next = !showLorebooks; setShowLorebooks(next); if (next) { setShowCharacters(false); setShowChats(false); setShowTools(false); setShowConfig(false); } }}>
          {showLorebooks ? 'Hide Lorebooks' : 'Lorebooks'}
        </button>
        <button className="secondary" onClick={() => setPhoneOpen(o => !o)}>
          {phoneOpen ? 'Close Phone' : 'Phone'}
        </button>
        <button className="secondary" onClick={() => { const next = !showConfig; setShowConfig(next); if (next) { setShowCharacters(false); setShowChats(false); setShowTools(false); setShowLorebooks(false); } }}>
          {showConfig ? 'Close Settings' : 'Settings'}
        </button>
      </header>

      {phoneOpen && (
        <div className={`phone-panel ${phoneStyle}`}>
          <div className="skin"></div>
          <div className="screen">
            <div className="statusbar">
              {phoneStyle === 'iphone' ? (
                <>
                  <span className="left">📶</span>
                  <span className="time">{new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</span>
                  <span className="right">🔊 📶</span>
                </>
              ) : (
                <>
                  <span>{new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</span>
                  <span>📶 📍 🔔</span>
                </>
              )}
            </div>
            <div className="bar">
              <input style={{ flex: 1 }} placeholder="https://" value={phoneUrl} onChange={(e)=> setPhoneUrl(e.target.value)} />
              <button className="secondary" onClick={()=> { let u = phoneUrl; if (!/^https?:/i.test(u)) u = 'https://' + u; setPhoneUrl(u); }}>Go</button>
              <button className="secondary" title="Open in new tab" onClick={()=> { try { let u = phoneUrl; if (!/^https?:/i.test(u)) u = 'https://' + u; window.open(u, '_blank'); } catch (e) { console.error(e);} }}>✨</button>
            </div>
            <iframe src={/^https?:/i.test(phoneUrl) ? phoneUrl : ('https://' + phoneUrl)} title="Phone" onLoad={()=>{ try { fetch('/phone/debug', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ event:'load', url: phoneUrl }) }); } catch (e) { console.error(e);} }} onError={()=>{ try { fetch('/phone/debug', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ event:'error', url: phoneUrl }) }); } catch (e) { console.error(e);} }} />
          </div>
        </div>
      )}
      <main className="chat">
        
        {showCharacters && (
          <section className="characters overlay">
            <h2>Characters</h2>
            <div className="row">
              <label className="secondary" style={{ padding: '8px 10px', borderRadius: 6, cursor: 'pointer' }}>
                Import JSON/PNG
                <input type="file" accept="application/json,.json,image/png" style={{ display: 'none' }} onChange={async (e) => {
                  const f = e.target.files?.[0]; if (!f) return;
                  try {
                    if (f.type === 'image/png') {
                      const fd = new FormData(); fd.append('file', f);
                      const res = await fetch('/characters/import', { method: 'POST', body: fd });
                      if (!res.ok) throw new Error('Import failed');
                    } else {
                      const text = await f.text(); const data = JSON.parse(text); if (!data.name) throw new Error('JSON must include name'); await createCharacter({ name: data.name, description: data.description || '', avatar_url: data.avatar_url || null });
                    }
                    const list = await listCharacters(); setCharacters(list);
                  } catch (err) { alert(err.message); }
                  e.target.value = '';
                }} />
              </label>
              <button className="secondary" onClick={async () => { try { const list = await listCharacters(); setCharacters(list); } catch (e) { alert(e.message);} }}>Refresh</button>
            </div>

            <div className="char-grid">
              <div className="char-card" onClick={() => { setEditingChar(null); setEditorOpen(true); }}>
                <img src={'https://placehold.co/400x600?text=New+Character'} alt="New Character" />
                <div className="name">+ New</div>
              </div>
              {characters.map(c => (
                <div key={c.id} className="char-card">
                  <img src={c.avatar_url || 'https://placehold.co/400x600?text=Character'} alt={c.name} />
                  <div className="name">{c.name}</div>
                  <div className="cog" onClick={(e) => { e.stopPropagation(); setEditingChar(c); setEditorOpen(true); }}><span>⚙️</span></div>
                  <div style={{ padding: '8px' }}>
                    <div className="row" style={{ justifyContent: 'space-between' }}>
                    <button onClick={async () => { try { await updateConfig({ active_character_id: c.id }); setShowCharacters(false);} catch (e) { console.error(e); alert(e.message); } }}>Use</button>
                      <button className="secondary" onClick={async () => { try { await deleteCharacter(c.id); const list = await listCharacters(); setCharacters(list);} catch (e) { alert(e.message);} }}>Delete</button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {showChats && (
          <section className="panel overlay">
            <h2>Chats</h2>
            <ChatManager sessionId={sessionId} setSessionId={setSessionId} onClose={() => setShowChats(false)} />
          </section>
        )}

        {showTools && (
          <section className="panel overlay">
            <h2>Tools</h2>
            <ToolsOverlay onClose={() => setShowTools(false)} />
          </section>
        )}

        {showConfig && (
          <section className="panel overlay">
            <h2>Configuration</h2>
            <div className="row" style={{ gap: 6, marginBottom: 8 }}>
              <button className="secondary" onClick={(e) => { e.preventDefault(); setSettingsTab('connection'); }}>Connection</button>
              <button className="secondary" onClick={(e) => { e.preventDefault(); setSettingsTab('persona'); }}>Persona</button>
              <button className="secondary" onClick={(e) => { e.preventDefault(); setSettingsTab('appearance'); }}>Appearance</button>
              <button className="secondary" onClick={(e) => { e.preventDefault(); setSettingsTab('images'); }}>Images</button>
              <button className="secondary" onClick={(e) => { e.preventDefault(); setSettingsTab('prompts'); }}>Prompts</button>
              <button className="secondary" onClick={(e) => { e.preventDefault(); setSettingsTab('advanced'); }}>Advanced</button>
            </div>
            {settingsTab === 'connection' && (
              <form
                className="config-form"
                onSubmit={async (e) => {
                  e.preventDefault();
                  try {
                    const cfg = await getConfig();
                    const current = cfg.providers?.[activeProvider] || {};
                    const changes = {};
                    for (const k of ['api_key','api_base','model','temperature']) {
                      const nv = configDraft[k];
                      const ov = current[k] ?? '';
                      if (k === 'temperature') { if (typeof nv === 'number' && nv !== ov) changes[k] = nv; }
                      else if (nv && nv !== ov) { changes[k] = nv; }
                    }
                    if (Object.keys(changes).length) {
                      const lines = Object.entries(changes).map(([k,v])=>`- ${k}: old=${current[k] ?? '(none)'} -> new=${v}`).join('\n');
                      if (!window.confirm(`Config.json already has this information, would you like to update it or discard?\n${lines}`)) {
                        setConfigDraft({ api_key: '', api_base: current.api_base || '', model: current.model || '', temperature: current.temperature ?? 0.7 });
                        return;
                      }
                    }
                    const updated = await updateConfig({ active_provider: activeProvider, providers: { [activeProvider]: changes }, max_context_tokens: maxTokens });
                    setProviders(updated.providers || {});
                  } catch (e) { console.error(e); alert(e.message); }
                }}
              >
                <label>
                  <span>Provider</span>
                  <select
                    value={activeProvider}
                    onChange={async (e) => {
                      const next = e.target.value;
                      setActiveProvider(next);
                      const cur = providers[next] || {};
                      setConfigDraft({ api_key: '', api_base: cur.api_base || '', model: cur.model || '', temperature: cur.temperature ?? 0.7 });
                      try { await updateConfig({ active_provider: next }); } catch {}
                    }}
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
                    placeholder={providers[activeProvider]?.api_key_masked ? `Saved: ${providers[activeProvider].api_key_masked}` : 'sk-...'}
                    value={configDraft.api_key}
                    onChange={(e) => setConfigDraft((d) => ({ ...d, api_key: e.target.value }))}
                  />
                </label>

                <label>
                  <span>API Base</span>
                  <input
                    type="text"
                    placeholder={
                      activeProvider === 'openrouter'
                        ? 'https://openrouter.ai/api/v1'
                        : activeProvider === 'openai'
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
                      placeholder={activeProvider === 'gemini' ? 'gemini-1.5-flash' : 'gpt-4o-mini'}
                      value={configDraft.model}
                      onChange={(e) => setConfigDraft((d) => ({ ...d, model: e.target.value }))}
                    />
                  )}
                </label>

                <div className="row">
                  <button type="button" className="secondary" onClick={async () => {
                    try {
                      await updateConfig({ providers: { [activeProvider]: configDraft } });
                      const cfg = await getConfig();
                      setProviders(cfg.providers || {});
                    } catch {}
                    try { const { models } = await getModels(activeProvider); setModelList(models || []); } catch { setModelList([]); }
                  }} disabled={loadingModels}>
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
                <label>
                  <span>Structured Output (Gemini)</span>
                  <input type="checkbox" onChange={async (e)=>{ try { await updateConfig({ structured_output: e.target.checked }); } catch (err) { alert(err.message);} }} />
                </label>

                <div className="row">
                  <button type="submit">Save</button>
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => setConfigDraft({
                      api_key: '',
                      api_base: providers[activeProvider]?.api_base || '',
                      model: providers[activeProvider]?.model || '',
                      temperature: providers[activeProvider]?.temperature ?? 0.7,
                    })}
                  >
                    Reset
                  </button>
                </div>
                <label>
                  <span>Max Context Tokens ({maxTokens})</span>
                  <input type="range" min="512" max="8192" step="128" value={maxTokens} onChange={(e)=> setMaxTokens(parseInt(e.target.value,10))} />
                </label>
              </form>
            )}
            {settingsTab === 'persona' && (
              <div className="config-form">
                <label>
                  <span>User Name</span>
                  <input value={userPersona.name} onChange={(e) => setUserPersona(u => ({ ...u, name: e.target.value }))} onBlur={async () => { try { await updateConfig({ user_persona: userPersona }); } catch (e) { console.error(e); alert(e.message);} }} />
                </label>
                <label>
                  <span>User Description</span>
                  <textarea rows={3} value={userPersona.description} onChange={(e) => setUserPersona(u => ({ ...u, description: e.target.value }))} onBlur={async () => { try { await updateConfig({ user_persona: userPersona }); } catch (e) { console.error(e); alert(e.message);} }} />
                </label>
              </div>
            )}

            {settingsTab === 'debug' && (
              <div className="config-form">
                <label>
                  <span>Log Prompts</span>
                  <input type="checkbox" checked={debugFlags.log_prompts} onChange={async (e) => { const v = e.target.checked; setDebugFlags(d => ({ ...d, log_prompts: v })); try { await updateConfig({ debug: { ...debugFlags, log_prompts: v } }); } catch {} }} />
                </label>
                <label>
                  <span>Log Responses</span>
                  <input type="checkbox" checked={debugFlags.log_responses} onChange={async (e) => { const v = e.target.checked; setDebugFlags(d => ({ ...d, log_responses: v })); try { await updateConfig({ debug: { ...debugFlags, log_responses: v } }); } catch {} }} />
                </label>
                <label>
                  <span>Max Context Tokens ({maxTokens})</span>
                  <input type="range" min="512" max="8192" step="128" value={maxTokens} onChange={async (e) => { const v = parseInt(e.target.value,10); setMaxTokens(v); try { await updateConfig({ max_context_tokens: v }); } catch {} }} />
                </label>
                <label>
                  <span>User Name</span>
                  <input value={userPersona.name} onChange={(e) => setUserPersona(u => ({ ...u, name: e.target.value }))} onBlur={async () => { try { await updateConfig({ user_persona: userPersona }); } catch {} }} />
                </label>
                <label>
                  <span>User Description</span>
                  <textarea rows={3} value={userPersona.description} onChange={(e) => setUserPersona(u => ({ ...u, description: e.target.value }))} onBlur={async () => { try { await updateConfig({ user_persona: userPersona }); } catch {} }} />
                </label>
              </div>
            )}
            {settingsTab === 'appearance' && (
              <AppearanceTab />
            )}
            {settingsTab === 'images' && (
              <ImagesTab providers={providers} />
            )}
            {settingsTab === 'prompts' && (
              <PromptsTab />
            )}\n            {settingsTab === 'advanced' && (
              <AdvancedTab />
            )}

            {settingsTab === 'connection' && (<div className="hint">)
              <p className="muted">
                OpenRouter uses OpenAI-compatible endpoints. You can set API Base to https://openrouter.ai/api/v1. Gemini uses the OpenAI-compatible base at https://generativelanguage.googleapis.com/v1beta/openai.
              </p>
            </div>)}
          </section>
        )}

        {showLorebooks && (
          <section className="characters overlay">
            <h2>Lorebooks</h2>
            <ActiveLorebooks lorebooks={lorebooks} />
            <div className="row">
              <label className="secondary" style={{ padding: '8px 10px', borderRadius: 6, cursor: 'pointer' }}>
                Import Lorebook JSON
                <input type="file" accept="application/json,.json" style={{ display: 'none' }} onChange={async (e) => {
                  const f = e.target.files?.[0]; if (!f) return;
                  try { const fd = new FormData(); fd.append('file', f); const res = await fetch('/lorebooks/import', { method: 'POST', body: fd }); if (!res.ok) throw new Error('Import failed'); const lbs = await listLorebooks(); setLorebooks(lbs); setSelectedLorebook(lbs[lbs.length-1]||null);} catch (err) { console.error(err); alert(err.message); }
                  e.target.value = '';
                }} />
              </label>
            </div>
            <div className="row" style={{ gap: 8 }}>
              <select value={selectedLorebook?.id || ''} onChange={(e) => { const id = parseInt(e.target.value,10); const lb = lorebooks.find(x => x.id===id); setSelectedLorebook(lb||null); }}>
                {lorebooks.map(lb => (<option key={lb.id} value={lb.id}>{lb.name}</option>))}
              </select>
              {selectedLorebook && (
                <>
                <input style={{ flex: 1 }} value={selectedLorebook.name} onChange={(e) => setSelectedLorebook({ ...selectedLorebook, name: e.target.value })} onBlur={async () => { try { await updateLorebook(selectedLorebook.id, { name: selectedLorebook.name }); } catch (e) { alert(e.message); } }} />
                <input style={{ flex: 2 }} value={selectedLorebook.description} onChange={(e) => setSelectedLorebook({ ...selectedLorebook, description: e.target.value })} onBlur={async () => { try { await updateLorebook(selectedLorebook.id, { description: selectedLorebook.description }); } catch (e) { alert(e.message); } }} />
                </>
              )}
            </div>
            <div className="char-list">
              {loreEntries.map(le => (
                <div key={le.id} className="char-item" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
                <div className="row" style={{ gap: 8, width: '100%', alignItems: 'center' }}>
                    <button className="secondary" onClick={() => setExpandedEntries(s => ({ ...s, [le.id]: !s[le.id] }))}>{expandedEntries[le.id] ? '▾' : '▸'}</button>
                    <input style={{ flex: 1 }} value={le.title || le.keyword || '(untitled)'} onChange={(e) => setLoreEntries(arr => arr.map(x => x.id===le.id? { ...x, title: e.target.value }: x))} onBlur={async (e) => { try { await updateLoreEntry(le.id, { title: e.target.value }); } catch (err) { console.error(err); alert(err.message); } }} />
                  </div>
                  {expandedEntries[le.id] && (
                    <div style={{ display: 'grid', gridTemplateColumns: '180px 1fr', gap: 8, marginTop: 8 }}>
                      <div className="muted">Primary Keywords</div>
                      <input value={(le.keywords||[]).join(', ')} onChange={(e) => setLoreEntries(arr => arr.map(x => x.id===le.id? { ...x, keywords: e.target.value.split(',').map(s=>s.trim()).filter(Boolean) }: x))} onBlur={async (e) => { try { await updateLoreEntry(le.id, { keywords: e.target.value.split(',').map(s=>s.trim()).filter(Boolean) }); } catch (err) { console.error(err); alert(err.message); } }} />
                      <div className="muted">Logic</div>
                      <select value={le.logic || 'AND ANY'} onChange={(e) => setLoreEntries(arr => arr.map(x => x.id===le.id? { ...x, logic: e.target.value }: x))} onBlur={async (e) => { try { await updateLoreEntry(le.id, { logic: e.target.value }); } catch (err) { alert(err.message); } }}>
                        <option>AND ANY</option>
                        <option>AND ALL</option>
                        <option>NOT ANY</option>
                        <option>NOT ALL</option>
                      </select>
                      <div className="muted">Secondary Keywords</div>
                      <input value={(le.secondary_keywords||[]).join(', ')} onChange={(e) => setLoreEntries(arr => arr.map(x => x.id===le.id? { ...x, secondary_keywords: e.target.value.split(',').map(s=>s.trim()).filter(Boolean) }: x))} onBlur={async (e) => { try { await updateLoreEntry(le.id, { secondary_keywords: e.target.value.split(',').map(s=>s.trim()).filter(Boolean) }); } catch (err) { console.error(err); alert(err.message); } }} />
                      <div className="muted">Order</div>
                      <input type="number" value={le.order||0} onChange={(e) => setLoreEntries(arr => arr.map(x => x.id===le.id? { ...x, order: parseInt(e.target.value,10) }: x))} onBlur={async (e) => { try { await updateLoreEntry(le.id, { order: parseInt(e.target.value,10) }); } catch (err) { alert(err.message); } }} />
                      <div className="muted">Trigger %</div>
                      <input type="number" value={le.trigger||100} onChange={(e) => setLoreEntries(arr => arr.map(x => x.id===le.id? { ...x, trigger: parseInt(e.target.value,10) }: x))} onBlur={async (e) => { try { await updateLoreEntry(le.id, { trigger: parseInt(e.target.value,10) }); } catch (err) { alert(err.message); } }} />
                      <div className="muted">Content</div>
                      <textarea rows={4} value={le.content} onChange={(e) => setLoreEntries(arr => arr.map(x => x.id===le.id? { ...x, content: e.target.value }: x))} onBlur={async (e) => { try { await updateLoreEntry(le.id, { content: e.target.value }); } catch (err) { alert(err.message); } }} />
                    </div>
                  )}
                </div>
              ))}
            </div>
            {selectedLorebook && (
              <div className="row">
                <button onClick={async () => {
                  try { const r = await fetch('/lore', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ keyword: 'keyword', content: 'content' })}); if (!r.ok) throw new Error('Failed'); const entry = await r.json(); const ids = [...(selectedLorebook.entry_ids||[]), entry.id]; await updateLorebook(selectedLorebook.id, { entry_ids: ids }); const lbs = await listLorebooks(); setLorebooks(lbs); const lb = lbs.find(x => x.id===selectedLorebook.id); setSelectedLorebook(lb||null); } catch (e) { console.error(e); alert(e.message); }
                }}>+ Add Entry</button>
              </div>
            )}
          </section>
        )}

        <div className="messages" aria-live="polite" ref={messagesRef}>
          {messages.map((m, idx) => (
            <div key={idx} className={`message ${m.role}`}>
              <div className="bubble">{m.image_url ? (<div><img src={m.image_url} alt="generated" style={{ maxWidth: '100%', borderRadius: 8 }} />{m.content ? (<div className="img-caption">{m.content}</div>) : null}</div>) : m.content}</div>
            </div>
          ))}
          {error && (
            <div className="message error">
              <div className="bubble">{error}</div>
            </div>
          )}
        </div>

        <div className="input-tools">
  <button className="secondary" title="Suggest lore entries from chat" onClick={async () => {
    try {
      const s = await suggestLoreFromChat(sessionId);
      if (!s.suggestions || s.suggestions.length === 0) { alert('No suggestions'); return; }
      setSuggests(s.suggestions);
      setSuggestOpen(true);
    } catch (e) { console.error(e); alert(e.message); }
  }}>📖</button>
  <button className="secondary" title="Generate image from chat" onClick={async () => {
    try { const r = await generateImageFromChat(sessionId); setMessages(m => [...m, { role: 'assistant', image_url: r.image_url }]); } catch (e) { console.error(e); alert(e.message); }
  }}>🎨</button>
          <button className="secondary" title="Send URL to phone" onClick={() => { let u = prompt('Open URL on phone:'); if (u) { if (!/^https?:/i.test(u)) u = 'https://' + u; setPhoneUrl(u); setPhoneOpen(true); } }}>📱</button>
          <button className="secondary" title="Scroll to bottom" style={{ marginLeft: 'auto' }} onClick={() => { try { if (messagesRef.current) { messagesRef.current.scrollTop = messagesRef.current.scrollHeight; } } catch (e) { console.error(e); } }}>⬇️</button>
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

        {editorOpen && (
          <CharacterEditor
            character={editingChar}
            lorebooks={lorebooks}
            onClose={() => setEditorOpen(false)}
            onSave={async (draft) => {
              try {
                if (editingChar) {
                  await updateCharacter(editingChar.id, draft);
                } else {
                  await createCharacter(draft);
                }
                const list = await listCharacters(); setCharacters(list);
                setEditorOpen(false);
              } catch (e) { alert(e.message); }
            }}
            onThink={async (field, draft) => {
              try {
                const payload = { ...draft };
                if (typeof payload.alternate_greetings === 'string') {
                  payload.alternate_greetings = payload.alternate_greetings.split(',').map(s => s.trim()).filter(Boolean);
                }
                if (typeof payload.tags === 'string') {
                  payload.tags = payload.tags.split(',').map(s => s.trim()).filter(Boolean);
                }
                const res = await suggestCharacterField(field, payload);
                return res.value;
              } catch (e) { alert(e.message); return ''; }
            }}
          />
        )}
        {suggestOpen && (
          <SuggestLoreModal suggestions={suggests} onClose={() => setSuggestOpen(false)} onApply={async (edited, targetLbId) => {
            try {
              const cfg = await getConfig();
              const activeIds = cfg.active_lorebook_ids || [];
              const lbId = targetLbId || activeIds[0];
              if (!lbId) { alert('No active lorebooks set'); return; }
              const newIds = [];
              for (const sug of edited.filter(x=>x.include)) {
                const r = await fetch('/lore', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ keyword: sug.keyword, content: sug.content })});
                if (r.ok) { const e = await r.json(); newIds.push(e.id); }
              }
              if (newIds.length) {
                const lbcur = await (await fetch(`/lorebooks/${lbId}`)).json();
                const ids = [...(lbcur.entry_ids||[]), ...newIds];
                await updateLorebook(lbId, { entry_ids: ids });
              }
              setSuggestOpen(false);
            } catch (e) { console.error(e); alert(e.message);} }} />
        )}
        {showSOHint && (
          <section className="panel overlay" onClick={()=> setShowSOHint(false)}>
            <div className="dialog" onClick={(e)=> e.stopPropagation()}>
              <h3>Enable Structured Output?</h3>
              <p className="muted">The assistant attempted to call a tool. Structured Output improves tool reliability on Gemini models.</p>
              <div className="row" style={{ gap: 8, alignItems: 'center' }}>
                <label><input type="checkbox" onChange={(e)=> setSuppressSOHint(e.target.checked)} /> Don't show again (this session)</label>
                <span style={{ flex: 1 }} />
                <button className="secondary" onClick={()=> setShowSOHint(false)}>Cancel</button>
                <button onClick={async ()=>{ try { await updateConfig({ structured_output: true }); setShowSOHint(false); } catch (e) { alert(String(e)); } }}>Enable</button>
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;

function ImagesTab() {
  const [cfg, setCfg] = useState({ active: 'pollinations', pollinations: { api_key: '', model: '' }, dezgo: { api_key: '', model: '', lora_flux_1: '', lora_flux_2: '', lora_sd1_1: '', lora_sd1_2: '', transparent: false, width: '', height: '', steps: '', upscale: false } });
  const [models, setModels] = useState([]);
  const [familyFilter, setFamilyFilter] = useState('');

  useEffect(() => { (async () => { try { const c = await getConfig(); setCfg(c.images); const m = await getImageModels(c.images.active); setModels(m.models || []); const fam0 = modelFamily(c.images?.dezgo?.model); setFamilyFilter(fam0);} catch (e) { console.error(e);} })(); }, []);

  const loadModels = async (prov) => { try { const m = await getImageModels(prov); setModels(m.models || []);} catch (e) { console.error(e); setModels([]);} };

  const saveCfg = async (next) => { try { await updateConfig({ images: next }); } catch (e) { console.error(e); alert(e.message);} };

  // Helpers for Dezgo model family
  const modelFamily = (m) => {
    const s = (m || '').toLowerCase();
    if (s.includes('flux')) return 'flux';
    if (s.includes('lightning')) return 'sdxl_lightning';
    if (s.includes('sdxl')) return 'sdxl';
    return 'sd1';
  };

  const fam = modelFamily(cfg.dezgo?.model);
  const famView = familyFilter || fam;
  const familyOptions = [
    { id: 'flux', label: 'Flux' },
    { id: 'sdxl', label: 'SDXL' },
    { id: 'sdxl_lightning', label: 'SDXL Lightning' },
    { id: 'sd1', label: 'SD1' },
  ];
  const filteredModels = (models||[]).filter(m => modelFamily(m) === famView);

  return (
    <div className="config-form">
      <label>
        <span>Active Provider</span>
        <select value={cfg.active} onChange={async (e) => { const v = e.target.value; const next = { ...cfg, active: v }; setCfg(next); await saveCfg(next); await loadModels(v); }}>
          <option value="pollinations">Pollinations</option>
          <option value="dezgo">Dezgo</option>
        </select>
      </label>
      {cfg.active === 'pollinations' && (
        <>
          <label>
            <span>Model</span>
            <select value={cfg.pollinations.model || ''} onChange={async (e) => { const v = e.target.value; const next = { ...cfg, pollinations: { ...cfg.pollinations, model: v } }; setCfg(next); await saveCfg(next); }}>
              <option value="">(default)</option>
              {models.map(m => (<option key={m} value={m}>{m}</option>))}
            </select>
          </label>
          <label>
            <span>API Key</span>
            <input placeholder={cfg.pollinations.api_key_masked ? `Saved: ${cfg.pollinations.api_key_masked}` : ''} value={cfg.pollinations.api_key || ''} onChange={(e) => setCfg(c => ({ ...c, pollinations: { ...c.pollinations, api_key: e.target.value } }))} />
          </label>
        </>
      )}
      {cfg.active === 'dezgo' && (
        <>
          <label>
            <span>API Key</span>
            <input placeholder={cfg.dezgo.api_key_masked ? `Saved: ${cfg.dezgo.api_key_masked}` : ''} value={cfg.dezgo.api_key || ''} onChange={(e) => setCfg(c => ({ ...c, dezgo: { ...c.dezgo, api_key: e.target.value } }))} />
          </label>
          <label>
            <span>Family</span>
            <select value={famView} onChange={(e)=> setFamilyFilter(e.target.value)}>
              {familyOptions.map(o => (<option key={o.id} value={o.id}>{o.label}</option>))}
            </select>
          </label>
          <label>
            <span>Model</span>
            <select value={cfg.dezgo.model || ''} onChange={(e) => {
              const v = e.target.value; const fam = modelFamily(v);
              const next = { ...cfg, dezgo: { ...cfg.dezgo, model: v, steps: fam==='flux' ? 4 : (fam==='sdxl_lightning' ? '' : (cfg.dezgo.steps || 30)) } };
              setCfg(next); saveCfg(next);
            }}>
              <option value="">(default)</option>
              {filteredModels.map(m => (<option key={m} value={m}>{m}</option>))}
            </select>
          </label>
          <div className="muted">Family: {famView.toUpperCase()}</div>
          <div className="muted">
            {famView==='sd1' ? 'Transparent background disabled; Upscale available.' : (famView==='sdxl_lightning' ? 'Steps disabled (Lightning is fixed).' : 'Transparent background available; consider steps ~30.')}
          </div>
          {famView==='flux' && (
            <>
              <label>
                <span>Flux LORA #1 (SHA256)</span>
                <input value={cfg.dezgo.lora_flux_1 || ''} onChange={(e) => setCfg(c => ({ ...c, dezgo: { ...c.dezgo, lora_flux_1: e.target.value } }))} />
              </label>
              <label>
                <span>Flux LORA #2 (SHA256)</span>
                <input value={cfg.dezgo.lora_flux_2 || ''} onChange={(e) => setCfg(c => ({ ...c, dezgo: { ...c.dezgo, lora_flux_2: e.target.value } }))} />
              </label>
              <label>
                <span>LoRA 1 Strength</span>
                <input type="range" min="0" max="1" step="0.05" disabled={!cfg.dezgo.lora_flux_1} value={cfg.dezgo.lora1_strength ?? 0.7} onChange={(e) => setCfg(c => ({ ...c, dezgo: { ...c.dezgo, lora1_strength: parseFloat(e.target.value) } }))} />
              </label>
              <label>
                <span>LoRA 2 Strength</span>
                <input type="range" min="0" max="1" step="0.05" disabled={!cfg.dezgo.lora_flux_2} value={cfg.dezgo.lora2_strength ?? 0.7} onChange={(e) => setCfg(c => ({ ...c, dezgo: { ...c.dezgo, lora2_strength: parseFloat(e.target.value) } }))} />
              </label>
            </>
          )}
          {famView==='sd1' && (
            <>
              <label>
                <span>SD1 LORA #1 (SHA256)</span>
                <input value={cfg.dezgo.lora_sd1_1 || ''} onChange={(e) => setCfg(c => ({ ...c, dezgo: { ...c.dezgo, lora_sd1_1: e.target.value } }))} />
              </label>
              <label>
                <span>SD1 LORA #2 (SHA256)</span>
                <input value={cfg.dezgo.lora_sd1_2 || ''} onChange={(e) => setCfg(c => ({ ...c, dezgo: { ...c.dezgo, lora_sd1_2: e.target.value } }))} />
              </label>
              <label>
                <span>LoRA 1 Strength</span>
                <input type="range" min="0" max="1" step="0.05" disabled={!cfg.dezgo.lora_sd1_1} value={cfg.dezgo.lora1_strength ?? 0.7} onChange={(e) => setCfg(c => ({ ...c, dezgo: { ...c.dezgo, lora1_strength: parseFloat(e.target.value) } }))} />
              </label>
              <label>
                <span>LoRA 2 Strength</span>
                <input type="range" min="0" max="1" step="0.05" disabled={!cfg.dezgo.lora_sd1_2} value={cfg.dezgo.lora2_strength ?? 0.7} onChange={(e) => setCfg(c => ({ ...c, dezgo: { ...c.dezgo, lora2_strength: parseFloat(e.target.value) } }))} />
              </label>
            </>
          )}
          <label>
            <span>Width</span>
            <input type="number" value={cfg.dezgo.width || ''} onChange={(e) => setCfg(c => ({ ...c, dezgo: { ...c.dezgo, width: e.target.value } }))} />
          </label>
          <label>
            <span>Height</span>
            <input type="number" value={cfg.dezgo.height || ''} onChange={(e) => setCfg(c => ({ ...c, dezgo: { ...c.dezgo, height: e.target.value } }))} />
          </label>
          {famView!=='sdxl_lightning' && (
            <label>
              <span>Steps</span>
              <input type="number" value={cfg.dezgo.steps || ''} onChange={(e) => setCfg(c => ({ ...c, dezgo: { ...c.dezgo, steps: e.target.value } }))} />
            </label>
          )}
          <label>
            <span>Transparent Background</span>
            <input type="checkbox" disabled={famView === 'sd1'} checked={!!cfg.dezgo.transparent} onChange={(e) => setCfg(c => ({ ...c, dezgo: { ...c.dezgo, transparent: e.target.checked } }))} />
          </label>
          <label>
            <span>Upscale</span>
            <input type="checkbox" disabled={famView !== 'sd1'} checked={!!cfg.dezgo.upscale} onChange={(e) => setCfg(c => ({ ...c, dezgo: { ...c.dezgo, upscale: e.target.checked } }))} />
          </label>
        </>
      )}
      <div className="row" style={{ gridColumn: '1 / -1' }}>
        <button onClick={async () => { try { const current = (await getConfig()).images; const changes = JSON.stringify(cfg) !== JSON.stringify(current); if (changes) { if (!window.confirm('Images config.json will be updated. Proceed?')) return; } await saveCfg(cfg); alert('Saved'); } catch (e) { console.error(e); alert(e.message); } }}>Save Image Settings</button>
      </div>
    </div>
  );
}

function PromptsTab() {
  const [all, setAll] = useState([]);
  const [active, setActive] = useState([]);
  const [newText, setNewText] = useState('');
  const [system, setSystem] = useState({ lore_suggest: '', image_summary: '', main: '', tool_call: '' });
  const [vars, setVars] = useState({});
  const [newVarName, setNewVarName] = useState('');
  const [newVarValue, setNewVarValue] = useState('');
  const [showPH, setShowPH] = useState(false);
  useEffect(() => { (async () => { try { const d = await getPrompts(); setAll(d.all || []); setActive(d.active || []); setSystem(d.system || { lore_suggest: '', image_summary: '' }); setVars(d.variables || {});} catch (e) { console.error(e);} })(); }, []);
  const save = async (na = all, aa = active, sys = system, vs = vars) => { try { await savePrompts({ all: na, active: aa, system: sys, variables: vs }); setAll(na); setActive(aa); setSystem(sys); setVars(vs);} catch (e) { console.error(e); alert(e.message);} };
  const toggleActive = (txt) => { const aa = active.includes(txt) ? active.filter(x=>x!==txt) : [...active, txt]; save(all, aa); };
  const add = () => { const t = newText.trim(); if (!t) return; const na = [...all, t]; setNewText(''); save(na, active); };
  const remove = (txt) => { const na = all.filter(x=>x!==txt); const aa = active.filter(x=>x!==txt); save(na, aa); };
  return (
    <>
    <div className="config-form" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
      <div style={{ gridColumn: '1 / -1' }}>
        <h3>System Prompts</h3>
        <div className="muted">These prompts guide built-in tools. <a href="#" onClick={(e)=>{ e.preventDefault(); setShowPH(true); }}>Use placeholders</a>.</div>
      </div>
      <label>
        <span>Main System Prompt</span>
        <textarea rows={4} value={system.main || ''} onChange={(e)=> setSystem(s => ({ ...s, main: e.target.value }))} onBlur={()=> save(all, active, { ...system }, vars)} placeholder="{{tool_call_prompt}}, {{user_persona}}, {{character_description}}, {{tool_list}}, {{conversation}}" />
      </label>
      <label>
        <span>Tool Call Prompt</span>
        <textarea rows={4} value={system.tool_call || ''} onChange={(e)=> setSystem(s => ({ ...s, tool_call: e.target.value }))} onBlur={()=> save(all, active, { ...system }, vars)} placeholder="Describe structured output JSON with toolCalls array." />
      </label>
      <label>
        <span>Lorebook suggestion prompt</span>
        <textarea rows={4} value={system.lore_suggest} onChange={(e)=> setSystem(s => ({ ...s, lore_suggest: e.target.value }))} onBlur={()=> save(all, active, { ...system }, vars)} placeholder="Use {{conversation}} and {{existing_keywords}}" />
      </label>
      <label>
        <span>Image generation prompt</span>
        <textarea rows={4} value={system.image_summary} onChange={(e)=> setSystem(s => ({ ...s, image_summary: e.target.value }))} onBlur={()=> save(all, active, { ...system }, vars)} placeholder="Use {{conversation}}" />
      </label>
      <div style={{ gridColumn: '1 / -1', marginTop: 8 }}>
        <h3>Variables</h3>
        <div className="muted">Define reusable snippets that replace tags like <code>{'{'}{'{'}company{'}'}{'}'}</code> anywhere the LLM sees them.</div>
      </div>
      <div className="row" style={{ gap: 8 }}>
        <input placeholder="name (e.g., site)" value={newVarName} onChange={(e)=> setNewVarName(e.target.value)} />
        <input placeholder="value" value={newVarValue} onChange={(e)=> setNewVarValue(e.target.value)} />
        <button className="secondary" onClick={()=>{ const n = newVarName.trim(); if (!n) return; const vs = { ...vars, [n]: newVarValue }; setNewVarName(''); setNewVarValue(''); save(all, active, system, vs); }}>Add</button>
      </div>
      <div className="row" style={{ display: 'block', marginTop: 8 }}>
        {Object.entries(vars).map(([k,v]) => (
          <div key={k} className="row" style={{ gap: 8, alignItems: 'center', marginBottom: 6 }}>
            <code style={{ width: 160 }}>{`{{${k}}}`}</code>
            <input style={{ flex: 1 }} value={v} onChange={(e)=> { const vs = { ...vars, [k]: e.target.value }; setVars(vs); }} onBlur={()=> save(all, active, system, vars)} />
            <button className="secondary" onClick={()=>{ const vs = { ...vars }; delete vs[k]; save(all, active, system, vs); }}>Delete</button>
          </div>
        ))}
      </div>
      <div style={{ gridColumn: '1 / -1', marginTop: 8 }}>
        <h3>General Prompts</h3>
        <div className="muted">Short, reusable prompts that can be toggled on to influence replies globally.</div>
      </div>
      <label>
        <span>New Prompt</span>
        <div className="row" style={{ gap: 8 }}>
          <input value={newText} onChange={(e)=> setNewText(e.target.value)} placeholder="Short prompt text to include in system context" />
          <button className="secondary" onClick={add}>Add</button>
        </div>
      </label>
      <div className="row" style={{ display: 'block' }}>
        {(all||[]).map((p, i) => (
          <div key={i} className="row" style={{ gap: 8, alignItems: 'center', marginBottom: 6 }}>
            <input type="checkbox" checked={active.includes(p)} onChange={()=> toggleActive(p)} />
            <span style={{ flex: 1 }}>{p}</span>
            <button className="secondary" onClick={()=> remove(p)}>Delete</button>
          </div>
        ))}
      </div>
    </div>
    {showPH && (
      <section className="panel overlay" onClick={()=> setShowPH(false)}>
        <div className="dialog" onClick={(e)=> e.stopPropagation()}>
          <h3>Available placeholders</h3>
          <ul className="muted">
            <li><code>{'{{conversation}}'}</code>: recent conversation window</li>
            <li><code>{'{{existing_keywords}}'}</code>: active lore keywords</li>
            <li><code>{'{{tool_call_prompt}}'}</code>: tool call guidance</li>
            <li><code>{'{{user_persona}}'}</code>: user persona summary</li>
            <li><code>{'{{character_description}}'}</code>: character description/personality</li>
            <li><code>{'{{tool_list}}'}</code>: enabled tools list</li>
            {Object.keys(vars).map(k => (<li key={k}><code>{`{{${k}}}`}</code>: variable</li>))}
          </ul>
          <div className="row" style={{ justifyContent: 'flex-end' }}>
            <button className="secondary" onClick={()=> setShowPH(false)}>Close</button>
          </div>
        </div>
      </section>
    )}
    </>
  );
}

function ToolsTab() {
  const [servers, setServers] = useState([]);
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  const [catalog, setCatalog] = useState([]);
  const [selIdx, setSelIdx] = useState('');
  useEffect(() => { (async () => { try { const d = await getMcpServers(); setServers(d.servers || []); const c = await getMcpAwesome(); setCatalog(c.items || []);} catch (e) { console.error(e);} })(); }, []);
  const save = async (list) => { try { await saveMcpServers({ servers: list }); setServers(list);} catch (e) { console.error(e); alert('Save failed'); } };
  return (
    <div className="config-form">
      <p className="muted">Register MCP servers the assistant can call in future sessions.</p>
      <label>
        <span>Catalog</span>
        <div className="row" style={{ gap: 8, alignItems: 'center' }}>
          <select value={selIdx} onChange={(e)=> setSelIdx(e.target.value)}>
            <option value="">(select server)</option>
            {catalog.map((it, i) => (<option key={i} value={i}>{it.name}</option>))}
          </select>
          {selIdx!=='' && (
            <>
              <button className="secondary" onClick={()=>{ const it=catalog[parseInt(selIdx,10)]; if (!it) return; const list=[...servers,{ name: it.name, url: it.url }]; save(list); }}>Add Server</button>
              <a className="secondary" href={catalog[parseInt(selIdx,10)]?.url} target="_blank" rel="noreferrer">Open</a>
            </>
          )}
        </div>
        {selIdx!=='' && (
          <div className="muted" style={{ marginTop: 6 }}>{catalog[parseInt(selIdx,10)]?.description}</div>
        )}
      </label>
      <div className="row" style={{ gap: 8 }}>
        <input placeholder="Name" value={name} onChange={(e)=> setName(e.target.value)} />
        <input placeholder="URL or command" value={url} onChange={(e)=> setUrl(e.target.value)} />
        <button onClick={()=>{ const n = name.trim(); const u = url.trim(); if (!n || !u) return; const list = [...servers, { name: n, url: u }]; save(list); setName(''); setUrl(''); }}>Add</button>
      </div>
      <div style={{ marginTop: 8 }}>
        {servers.map((s, i) => (
          <div key={i} className="row" style={{ gap: 8, alignItems: 'center', marginBottom: 6 }}>
            <span style={{ width: 180 }}>{s.name}</span>
            <span style={{ flex: 1 }} className="muted">{s.url}</span>
            <button className="secondary" onClick={()=>{ const list = servers.filter((_,idx)=> idx!==i); save(list); }}>Remove</button>
          </div>
        ))}
      </div>
    </div>
  );
}

function ToolsOverlay({ onClose }) {
  const [enabled, setEnabled] = useState({ phone: false, image_gen: false, lore_suggest: false });
  const [structured, setStructured] = useState(false);
  const [notified, setNotified] = useState(false);
  const [servers, setServers] = useState([]);
  const [catalog, setCatalog] = useState([]);
  const [selIdx, setSelIdx] = useState('');
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  useEffect(() => { (async () => { try { const cfg = await getConfig(); setStructured(!!cfg.structured_output); const cid = cfg.active_character_id; const t = await (await fetch(`/tools/settings${cid?`?character_id=${cid}`:''}`)).json(); setEnabled(t.enabled || {}); } catch (e) { console.error(e);} })(); }, []);
  const save = async (en) => { try { const cfg = await getConfig(); const cid = cfg.active_character_id; await fetch(`/tools/settings${cid?`?character_id=${cid}`:''}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ enabled: en }) }); setEnabled(en); if (!notified && (en.phone||en.image_gen||en.lore_suggest) && !structured) { alert('Enabling tools benefits from Structured Output. You can toggle it in Connection settings.'); setNotified(true);} } catch (e) { console.error(e); alert('Save failed'); } };
  useEffect(() => { (async () => { try { const d = await getMcpServers(); setServers(d.servers || []); const c = await getMcpAwesome(); setCatalog(c.items || []);} catch (e) { console.error(e);} })(); }, []);
  const saveServers = async (list) => { try { await saveMcpServers({ servers: list }); setServers(list);} catch (e) { console.error(e); alert('Save failed'); } };
  return (
    <div className="config-form">
      <div className="row" style={{ gap: 8 }}>
        <label><input type="checkbox" checked={!!enabled.phone} onChange={(e)=> save({ ...enabled, phone: e.target.checked })} /> Phone Panel <em>(phone_url)</em></label>
        <label><input type="checkbox" checked={!!enabled.image_gen} onChange={(e)=> save({ ...enabled, image_gen: e.target.checked })} /> Image Generation <em>(image_request)</em></label>
        <label><input type="checkbox" checked={!!enabled.lore_suggest} onChange={(e)=> save({ ...enabled, lore_suggest: e.target.checked })} /> Lore Suggest <em>(lore_suggestions)</em></label>
      </div>
      <p className="muted">When tools are enabled, the assistant receives concise instructions about each tool. For Gemini models, enable "Structured Output" in Connection to get reliable tool-usage responses.</p>
      <hr />
      <h3>MCP Servers</h3>
      <label>
        <span>Catalog</span>
        <div className="row" style={{ gap: 8, alignItems: 'center' }}>
          <select value={selIdx} onChange={(e)=> setSelIdx(e.target.value)}>
            <option value="">(select server)</option>
            {catalog.map((it, i) => (<option key={i} value={i}>{it.name}</option>))}
          </select>
          {selIdx!=='' && (
            <>
              <button className="secondary" onClick={()=>{ const it=catalog[parseInt(selIdx,10)]; if (!it) return; const list=[...servers,{ name: it.name, url: it.url }]; saveServers(list); }}>Add Server</button>
              <a className="secondary" href={catalog[parseInt(selIdx,10)]?.url} target="_blank" rel="noreferrer">Open</a>
            </>
          )}
        </div>
        {selIdx!=='' && (
          <div className="muted" style={{ marginTop: 6 }}>{catalog[parseInt(selIdx,10)]?.description}</div>
        )}
      </label>
      <div className="row" style={{ gap: 8 }}>
        <input placeholder="Name" value={name} onChange={(e)=> setName(e.target.value)} />
        <input placeholder="URL or command" value={url} onChange={(e)=> setUrl(e.target.value)} />
        <button onClick={()=>{ const n = name.trim(); const u = url.trim(); if (!n || !u) return; const list = [...servers, { name: n, url: u }]; saveServers(list); setName(''); setUrl(''); }}>Add</button>
      </div>
      <div style={{ marginTop: 8 }}>
        {servers.map((s, i) => (
          <div key={i} className="row" style={{ gap: 8, alignItems: 'center', marginBottom: 6 }}>
            <span style={{ width: 180 }}>{s.name}</span>
            <span style={{ flex: 1 }} className="muted">{s.url}</span>
            <button className="secondary" onClick={()=>{ const list = servers.filter((_,idx)=> idx!==i); saveServers(list); }}>Remove</button>
          </div>
        ))}
      </div>
      <div className="row" style={{ justifyContent: 'flex-end' }}>
        <button className="secondary" onClick={onClose}>Close</button>
      </div>
    </div>
  );
}

function ActiveLorebooks({ lorebooks }) {
  const [activeIds, setActiveIds] = useState([]);
  const [selId, setSelId] = useState('');
  useEffect(() => { (async () => { try { const cfg = await getConfig(); setActiveIds(cfg.active_lorebook_ids || []);} catch (e) { console.error(e);} })(); }, []);
  const add = async () => { try { const id = parseInt(selId,10); if (!id) return; if (!activeIds.includes(id)) { const list = [...activeIds, id]; setActiveIds(list); await updateConfig({ active_lorebook_ids: list }); } } catch (e) { console.error(e); alert(e.message);} };
  const remove = async (id) => { try { const list = activeIds.filter(x => x!==id); setActiveIds(list); await updateConfig({ active_lorebook_ids: list }); } catch (e) { console.error(e); alert(e.message);} };
  return (
    <div className="row" style={{ gap: 8, alignItems: 'center' }}>
      <span className="muted">Active Lorebooks</span>
      <select value={selId} onChange={(e)=> setSelId(e.target.value)}>
        <option value="">(select)</option>
        {lorebooks.map(lb => (<option key={lb.id} value={lb.id}>{lb.name}</option>))}
      </select>
      <button className="secondary" onClick={add}>➕</button>
      <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
        {activeIds.map(id => { const lb = lorebooks.find(x => x.id===id); return (
          <span key={id} className="secondary" style={{ padding: '4px 8px', borderRadius: 6 }}>{lb ? lb.name : `#${id}`} <button className="secondary" onClick={() => remove(id)}>➖</button></span>
        ); })}
      </div>
    </div>
  );
}

function AdvancedTab() {
  const [raw, setRaw] = useState('');
  useEffect(() => { (async () => { try { const r = await fetch('/config/raw'); if (r.ok) setRaw(JSON.stringify(await r.json(), null, 2)); } catch (e) { console.error(e);} })(); }, []);
  return (
    <div>
      <p className="muted">Full settings.json (copy/share):</p>
      <textarea rows={16} style={{ width: '100%' }} value={raw} onChange={(e)=>setRaw(e.target.value)} />
      <div className="row" style={{ marginTop: 8 }}>
        <button className="secondary" onClick={() => {
          const blob = new Blob([raw], { type: 'application/json' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a'); a.href = url; a.download = 'settings.json'; a.click(); URL.revokeObjectURL(url);
        }}>Export settings.json</button>
        <label className="secondary" style={{ padding: '8px 10px', borderRadius: 6, cursor: 'pointer' }}>
          Import settings.json
          <input type="file" accept="application/json,.json" style={{ display: 'none' }} onChange={async (e) => {
            const f = e.target.files?.[0]; if (!f) return;
            try { const text = await f.text(); const data = JSON.parse(text); const r = await fetch('/config/raw', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); if (!r.ok) throw new Error('Import failed'); alert('Imported. Reloading...'); location.reload(); } catch (err) { console.error(err); alert(err.message); } finally { e.target.value=''; }
          }} />
        </label>
        <button onClick={async ()=>{ try { const data = JSON.parse(raw); const r = await fetch('/config/raw', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); if (!r.ok) throw new Error('Save failed'); alert('Saved. Reloading...'); location.reload(); } catch (e) { console.error(e); alert(e.message);} }}>Save settings.json</button>
      </div>
      <hr />
      <p className="muted">Advanced settings</p>
    </div>
  );
}

function ThemesManager() {
  const [names, setNames] = useState([]);
  const [sel, setSel] = useState('');
  const [theme, setTheme] = useState(null);
  const load = async () => { try { const r = await fetch('/themes'); if (r.ok) { const d = await r.json(); setNames(d.names || []); } } catch (e) { console.error(e);} };
  useEffect(() => { load(); }, []);
  return (
    <div className="row" style={{ gap: 8 }}>
      <select value={sel} onChange={(e)=> setSel(e.target.value)}>
        <option value="">(select)</option>
        {names.map(n => (<option key={n} value={n}>{n}</option>))}
      </select>
      <button className="secondary" onClick={async ()=>{ if (!sel) return; try { const r = await fetch(`/themes/${sel}`); if (!r.ok) throw new Error('Load failed'); const t = await r.json(); await fetch('/config', { method: 'PUT', headers: { 'Content-Type':'application/json' }, body: JSON.stringify({ theme: t }) }); try { const root = document.documentElement; root.style.setProperty('--primary', t.primary); root.style.setProperty('--panel', t.secondary); root.style.setProperty('--text', t.text1); root.style.setProperty('--muted', t.text2); root.style.setProperty('--assistant', t.highlight); root.style.setProperty('--bg', t.lowlight);} catch (e) { console.error(e);} alert('Theme loaded'); } catch (e) { console.error(e); alert(e.message);} }}>Load Theme</button>
      <button onClick={async ()=>{ const name = prompt('Save theme as:'); if (!name) return; try { const cfg = await getConfig(); const t = cfg.theme || {}; const r = await fetch('/themes', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ name, theme: t })}); if (!r.ok) throw new Error('Save theme failed'); alert('Theme saved'); load(); } catch (e) { console.error(e); alert(e.message);} }}>Save Current Theme</button>
    </div>
  );
}

function AppearanceTab() {
  const [theme, setTheme] = useState({ primary: '#2563eb', secondary: '#374151', text1: '#e5e7eb', text2: '#cbd5e1', highlight: '#10b981', lowlight: '#111827', phone_style: 'classic' });
  useEffect(() => { (async () => { try { const r = await getConfig(); if (r.theme) setTheme(r.theme);} catch (e) { console.error(e);} })(); }, []);
  useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty('--primary', theme.primary);
    root.style.setProperty('--panel', theme.secondary);
    root.style.setProperty('--text', theme.text1);
    root.style.setProperty('--muted', theme.text2);
    root.style.setProperty('--assistant', theme.highlight);
    root.style.setProperty('--bg', theme.lowlight);
  }, [theme]);

  const save = async (next) => { setTheme(next); try { await updateConfig({ theme: next }); try { window.dispatchEvent(new CustomEvent('coolchat:themeUpdate', { detail: next })); } catch {} } catch (e) { console.error(e); alert(e.message);} };

  const suggest = async () => {
    try {
      const r = await fetch('/theme/suggest', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ primary: theme.primary }) });
      if (!r.ok) throw new Error('Suggest failed');
      const { colors } = await r.json();
      if (colors.length >= 5) {
        const next = { ...theme, secondary: colors[0], text1: colors[1], text2: colors[2], highlight: colors[3], lowlight: colors[4] };
        await save(next);
      }
    } catch (e) { console.error(e); alert(e.message);} 
  };

  const Color = ({ label, keyName, withThink }) => (
    <label>
      <span>{label}</span>
      <div className="row color-row" style={{ gap: 8, alignItems: 'center' }}>
        <input className="color-swatch" type="color" value={theme[keyName]} onChange={async (e) => { await save({ ...theme, [keyName]: e.target.value }); }} />
        <input value={theme[keyName]} onChange={async (e) => { await save({ ...theme, [keyName]: e.target.value }); }} />
        {withThink && (<button className="think" title="Have the AI suggest a color theme based on your chosen primary color. This will overwrite your current theme configuration." onClick={suggest}>💭</button>)}
      </div>
    </label>
  );

  return (
    <div className="config-form">
      <Color label="Primary" keyName="primary" withThink />
      <Color label="Secondary" keyName="secondary" />
      <Color label="Text 1" keyName="text1" />
      <Color label="Text 2" keyName="text2" />
      <Color label="Highlight" keyName="highlight" />
      <Color label="Lowlight" keyName="lowlight" />
      <label>
        <span>Phone Style</span>
        <select value={theme.phone_style || 'classic'} onChange={async (e)=> { const next = { ...theme, phone_style: e.target.value }; await save(next); try { window.dispatchEvent(new CustomEvent('coolchat:phoneStyle', { detail: next.phone_style })); } catch {} }}>
          <option value="classic">Classic</option>
          <option value="modern">Modern</option>
          <option value="iphone">iPhone</option>
          <option value="cyberpunk">Cyberpunk</option>
        </select>
      </label>
      <label>
        <span>Background Animations</span>
        <div className="row" style={{ gap: 8, alignItems: 'center' }}>
          <select id="anim-select">
            <option value="gradient_flow">Gradient Flow</option>
            <option value="floating_squares">Floating Squares</option>
            <option value="waves">Waves</option>
            <option value="neon_rain">Neon Rain</option>
            <option value="matrix">Matrix</option>
          </select>
          <button className="secondary" onClick={() => {
            try {
              const sel = document.getElementById('anim-select');
              const id = sel.value;
              if (!id) return;
              const list = Array.isArray(theme.background_animations) ? [...theme.background_animations] : [];
              if (!list.includes(id)) { save({ ...theme, background_animations: [...list, id] }); }
            } catch (e) { console.error(e); }
          }}>+</button>
        </div>
        <div className="row" style={{ gap: 6, flexWrap: 'wrap', marginTop: 6 }}>
          {(theme.background_animations||[]).map((id, i) => (
            <span key={i} className="secondary" style={{ padding: '4px 8px', borderRadius: 6 }}>{id} <button className="secondary" onClick={() => { const list = (theme.background_animations||[]).filter(x => x!==id); save({ ...theme, background_animations: list }); }}>-</button></span>
          ))}
        </div>
      </label>
      <hr />
      <p className="muted">Saved themes</p>
      <ThemesManager />
    </div>
  );
}

function SuggestLoreModal({ suggestions, onClose, onApply }) {
  const [rows, setRows] = useState(() => (suggestions || []).map(s => ({ include: true, keyword: s.keyword || '', content: s.content || '' })));
  const [lbOptions, setLbOptions] = useState([]);
  const [selLb, setSelLb] = useState('');
  useEffect(() => { (async () => { try { const cfg = await getConfig(); const actives = cfg.active_lorebook_ids || []; if (actives.length) { const lbs = await listLorebooks(); const opts = lbs.filter(x => actives.includes(x.id)).map(x => ({ id: x.id, name: x.name })); setLbOptions(opts); setSelLb(String(opts[0]?.id || '')); } } catch (e) { console.error(e);} })(); }, []);
  return (
    <section className="panel overlay">
      <h2>Lore Suggestions</h2>
      {lbOptions.length > 1 && (
        <div className="row" style={{ gap: 8, alignItems: 'center' }}>
          <span className="muted">Target Lorebook</span>
          <select value={selLb} onChange={(e)=> setSelLb(e.target.value)}>
            {lbOptions.map(o => (<option key={o.id} value={o.id}>{o.name}</option>))}
          </select>
        </div>
      )}
      <div className="char-list" style={{ maxHeight: 360, overflow: 'auto' }}>
        {rows.map((r, i) => (
          <div key={i} className="char-item" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
            <div className="row" style={{ gap: 8, alignItems: 'center' }}>
              <input type="checkbox" checked={r.include} onChange={(e)=> setRows(arr => arr.map((x,idx)=> idx===i? { ...x, include: e.target.checked }: x))} />
              <input placeholder="Keyword" value={r.keyword} onChange={(e)=> setRows(arr => arr.map((x,idx)=> idx===i? { ...x, keyword: e.target.value }: x))} />
            </div>
            <textarea rows={3} placeholder="Content" value={r.content} onChange={(e)=> setRows(arr => arr.map((x,idx)=> idx===i? { ...x, content: e.target.value }: x))} />
          </div>
        ))}
      </div>
      <div className="row" style={{ justifyContent: 'flex-end', gap: 8, marginTop: 8 }}>
        <button className="secondary" onClick={onClose}>Cancel</button>
        <button onClick={()=> onApply(rows, selLb ? parseInt(selLb,10) : null)}>Add Selected</button>
      </div>
    </section>
  );
}

function ChatManager({ sessionId, setSessionId, onClose }) {
  const [sessions, setSessions] = useState([]);
  const [newName, setNewName] = useState('');
  const load = async () => { try { const d = await listChats(); setSessions(d.sessions || []);} catch (e) { console.error(e);} };
  useEffect(() => { load(); }, []);
  return (
    <div className="config-form">
      <div className="row" style={{ gap: 8, alignItems: 'center' }}>
        <select value={sessionId} onChange={async (e)=> { const id = e.target.value; setSessionId(id); }}>
          {[...sessions].map(id => (<option key={id} value={id}>{id}</option>))}
        </select>
        <button className="secondary" onClick={load}>Refresh</button>
        <button className="secondary" onClick={async ()=>{ try { await resetChat(sessionId); await load(); setSessionId('default'); } catch (e) { alert(e.message);} }}>Reset</button>
        <button className="secondary" onClick={onClose}>Close</button>
      </div>
      <div className="row" style={{ gap: 8, marginTop: 8 }}>
        <input placeholder="New session id (e.g., 2025-01-01T12:00)" value={newName} onChange={(e)=> setNewName(e.target.value)} />
        <button onClick={async ()=>{ const id = (newName||'').trim() || String(Date.now()); if (!sessions.includes(id)) setSessions(s => [...s, id]); setSessionId(id); setNewName(''); }}>New</button>
      </div>
    </div>
  );
}

function CharacterEditor({ character, onClose, onSave, onThink, lorebooks }) {
  const [draft, setDraft] = useState(() => ({
    name: character?.name || '',
    description: character?.description || '',
    avatar_url: character?.avatar_url || '',
    first_message: character?.first_message || '',
    alternate_greetings: (character?.alternate_greetings || []).join(', '),
    scenario: character?.scenario || '',
    system_prompt: character?.system_prompt || '',
    personality: character?.personality || '',
    mes_example: character?.mes_example || '',
    creator_notes: character?.creator_notes || '',
    tags: (character?.tags || []).join(', '),
    post_history_instructions: character?.post_history_instructions || '',
    lorebook_ids: character?.lorebook_ids || [],
    image_prompt_prefix: character?.image_prompt_prefix || '',
    image_prompt_suffix: character?.image_prompt_suffix || '',
  }));
  const [thinkingField, setThinkingField] = useState(null);
  const [painting, setPainting] = useState(false);
  const [uploading, setUploading] = useState(false);

  const think = async (field) => {
    try {
      setThinkingField(field);
      const val = await onThink(field, draft);
      setDraft((d) => ({ ...d, [field]: val }));
    } finally {
      setThinkingField(null);
    }
  };

  return (
    <div className="modal" onClick={onClose}>
      <div className="dialog" onClick={(e) => e.stopPropagation()}>
        <h2>{character ? 'Edit Character' : 'New Character'}</h2>
        <div className="editor-grid">
          <span className="label">Name</span>
          <div><input value={draft.name} onChange={(e) => setDraft(d => ({ ...d, name: e.target.value }))} /> <button className="think" onClick={() => think('name')}>💭</button></div>
          <span className="label">Avatar</span>
          <div>
            {draft.avatar_url && (
              <img src={draft.avatar_url} alt="Avatar preview" style={{ width: 80, height: 80, objectFit: 'cover', borderRadius: 8, marginRight: 8, border: '1px solid #1f2937' }} />
            )}
            <input type="file" accept="image/*" onChange={async (e) => {
              const f = e.target.files?.[0]; if (!f) return;
              try {
                setUploading(true);
                const fd = new FormData(); fd.append('file', f);
                const res = await fetch('/characters/upload_avatar', { method: 'POST', body: fd });
                if (!res.ok) throw new Error('Upload failed');
                const data = await res.json();
                setDraft(d => ({ ...d, avatar_url: data.avatar_url }));
              } catch (err) { alert(err.message); } finally { setUploading(false); e.target.value = ''; }
            }} />
            <button className={`paint ${painting ? 'thinking' : ''}`} onClick={async () => {
              try {
                setPainting(true);
                const res = await fetch('/characters/generate_avatar', {
                  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ character: draft }),
                });
                if (!res.ok) throw new Error('Generate failed');
                const data = await res.json();
                setDraft(d => ({ ...d, avatar_url: data.avatar_url }));
              } catch (err) { alert(err.message); } finally { setPainting(false); }
            }}>🖌️</button>
          </div>
          <span className="label">Description</span>
          <div><textarea rows={3} value={draft.description} onChange={(e) => setDraft(d => ({ ...d, description: e.target.value }))} /> <button className={`think ${thinkingField==='description'?'thinking':''}`} onClick={() => think('description')}>💭</button></div>
          <span className="label">First Message</span>
          <div><textarea rows={3} value={draft.first_message} onChange={(e) => setDraft(d => ({ ...d, first_message: e.target.value }))} /> <button className={`think ${thinkingField==='first_message'?'thinking':''}`} onClick={() => think('first_message')}>💭</button></div>
          <span className="label">Alternate Greetings (comma)</span>
          <div><input value={draft.alternate_greetings} onChange={(e) => setDraft(d => ({ ...d, alternate_greetings: e.target.value }))} /> <button className={`think ${thinkingField==='alternate_greetings'?'thinking':''}`} onClick={() => think('alternate_greetings')}>💭</button></div>
          <span className="label">Scenario</span>
          <div><textarea rows={3} value={draft.scenario} onChange={(e) => setDraft(d => ({ ...d, scenario: e.target.value }))} /> <button className={`think ${thinkingField==='scenario'?'thinking':''}`} onClick={() => think('scenario')}>💭</button></div>
          <span className="label">System Prompt</span>
          <div><textarea rows={3} value={draft.system_prompt} onChange={(e) => setDraft(d => ({ ...d, system_prompt: e.target.value }))} /> <button className={`think ${thinkingField==='system_prompt'?'thinking':''}`} onClick={() => think('system_prompt')}>💭</button></div>
          <span className="label">Personality</span>
          <div><textarea rows={3} value={draft.personality} onChange={(e) => setDraft(d => ({ ...d, personality: e.target.value }))} /> <button className={`think ${thinkingField==='personality'?'thinking':''}`} onClick={() => think('personality')}>💭</button></div>
          <span className="label">Message Example</span>
          <div><textarea rows={3} value={draft.mes_example} onChange={(e) => setDraft(d => ({ ...d, mes_example: e.target.value }))} /> <button className={`think ${thinkingField==='mes_example'?'thinking':''}`} onClick={() => think('mes_example')}>💭</button></div>
          <span className="label">Creator Notes</span>
          <div><textarea rows={3} value={draft.creator_notes} onChange={(e) => setDraft(d => ({ ...d, creator_notes: e.target.value }))} /> <button className={`think ${thinkingField==='creator_notes'?'thinking':''}`} onClick={() => think('creator_notes')}>💭</button></div>
          <span className="label">Prepend to image prompts</span>
          <div><input value={draft.image_prompt_prefix} onChange={(e) => setDraft(d => ({ ...d, image_prompt_prefix: e.target.value }))} /> <button className={`think ${thinkingField==='image_prompt_prefix'?'thinking':''}`} onClick={() => think('image_prompt_prefix')}>💭</button></div>
          <span className="label">Append to image prompts</span>
          <div><input value={draft.image_prompt_suffix} onChange={(e) => setDraft(d => ({ ...d, image_prompt_suffix: e.target.value }))} /> <button className={`think ${thinkingField==='image_prompt_suffix'?'thinking':''}`} onClick={() => think('image_prompt_suffix')}>💭</button></div>
          <span className="label">Tags (comma)</span>
          <div><input value={draft.tags} onChange={(e) => setDraft(d => ({ ...d, tags: e.target.value }))} /></div>
          <span className="label">Post-History Instructions</span>
          <div><textarea rows={3} value={draft.post_history_instructions} onChange={(e) => setDraft(d => ({ ...d, post_history_instructions: e.target.value }))} /> <button className={`think ${thinkingField==='post_history_instructions'?'thinking':''}`} onClick={() => think('post_history_instructions')}>💭</button></div>
          <span className="label">Lorebook</span>
          <div>
            <select value={draft.lorebook_ids[0] || ''} onChange={(e) => {
              const id = e.target.value ? [parseInt(e.target.value,10)] : [];
              setDraft(d => ({ ...d, lorebook_ids: id }));
            }}>
              <option value="">-- None --</option>
              {lorebooks.map(lb => (<option key={lb.id} value={lb.id}>{lb.name}</option>))}
            </select>
          </div>
        </div>
        <div className="row" style={{ justifyContent: 'flex-end', marginTop: 12 }}>
          <button className="secondary" onClick={onClose}>Cancel</button>
          <button onClick={() => {
            const payload = {
              ...draft,
              alternate_greetings: draft.alternate_greetings.split(',').map(s => s.trim()).filter(Boolean),
              tags: draft.tags.split(',').map(s => s.trim()).filter(Boolean),
            };
            onSave(payload);
          }}>Save</button>
        </div>
      </div>
    </div>
  );
}


