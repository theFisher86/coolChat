import React, { useEffect, useState } from 'react';
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
  updateLoreEntry,
  updateLorebook,
} from './api';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);

  const [showConfig, setShowConfig] = useState(false);
  const [settingsTab, setSettingsTab] = useState('connection');

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
      } catch (e) {
        console.warn('Could not load config', e);
      }
    })();
  }, []);

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
        <button className="secondary" onClick={() => setShowCharacters((s) => !s)}>
          {showCharacters ? 'Hide Characters' : 'Characters'}
        </button>
        <button className="secondary" onClick={() => setShowLorebooks((s) => !s)}>
          {showLorebooks ? 'Hide Lorebooks' : 'Lorebooks'}
        </button>
        <button className="secondary" onClick={() => setShowConfig((s) => !s)}>
          {showConfig ? 'Close Settings' : 'Settings'}
        </button>
      </header>

      <main className="chat">
        <div className="row" style={{ gap: 8, padding: '8px 16px', borderBottom: '1px solid #1f2937', background: '#0b1220' }}>
          <button className="secondary" title="Generate image from chat" onClick={async () => {
            try { const r = await generateImageFromChat(); setMessages(m => [...m, { role: 'assistant', image_url: r.image_url }]); } catch (e) { alert(e.message); }
          }}>🖌️</button>
        </div>
        {showCharacters && (
          <section className="characters">
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
                      <button onClick={async () => { try { await updateConfig({ active_character_id: c.id }); } catch (e) { alert(e.message); } }}>Use</button>
                      <button className="secondary" onClick={async () => { try { await deleteCharacter(c.id); const list = await listCharacters(); setCharacters(list);} catch (e) { alert(e.message);} }}>Delete</button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {showConfig && (
          <section className="panel">
            <h2>Configuration</h2>
            <div className="row" style={{ gap: 6, marginBottom: 8 }}>
              <button className="secondary" onClick={(e) => { e.preventDefault(); setSettingsTab('connection'); }}>Connection</button>
              <button className="secondary" onClick={(e) => { e.preventDefault(); setSettingsTab('debug'); }}>Debug</button>
              <button className="secondary" onClick={(e) => { e.preventDefault(); setSettingsTab('appearance'); }}>Appearance</button>
              <button className="secondary" onClick={(e) => { e.preventDefault(); setSettingsTab('images'); }}>Images</button>
              <button className="secondary" onClick={(e) => { e.preventDefault(); setSettingsTab('advanced'); }}>Advanced</button>
            </div>
            {settingsTab === 'connection' && (
              <form
                className="config-form"
                onSubmit={async (e) => {
                  e.preventDefault();
                  try {
                    const updated = await updateConfig({ active_provider: activeProvider, providers: { [activeProvider]: configDraft } });
                    setProviders(updated.providers || {});
                  } catch (e) {
                    alert(e.message);
                  }
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
              </form>
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
              <p className="muted">Theme options coming soon.</p>
            )}
            {settingsTab === 'images' && (
              <ImagesTab providers={providers} />
            )}
            {settingsTab === 'advanced' && (
              <AdvancedTab />
            )}

            <div className="hint">
              <p className="muted">
                OpenRouter uses OpenAI-compatible endpoints. You can set API Base to https://openrouter.ai/api/v1. Gemini uses the OpenAI-compatible base at https://generativelanguage.googleapis.com/v1beta/openai.
              </p>
            </div>
          </section>
        )}

        {showLorebooks && (
          <section className="characters">
            <h2>Lorebooks</h2>
            <div className="row">
              <label className="secondary" style={{ padding: '8px 10px', borderRadius: 6, cursor: 'pointer' }}>
                Import Lorebook JSON
                <input type="file" accept="application/json,.json" style={{ display: 'none' }} onChange={async (e) => {
                  const f = e.target.files?.[0]; if (!f) return;
                  try { const fd = new FormData(); fd.append('file', f); const res = await fetch('/lorebooks/import', { method: 'POST', body: fd }); if (!res.ok) throw new Error('Import failed'); const lbs = await listLorebooks(); setLorebooks(lbs); } catch (err) { alert(err.message); }
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
                <div key={le.id} className="char-item">
                  <div className="row" style={{ gap: 8, width: '100%' }}>
                    <input style={{ width: 180 }} value={le.keyword} onChange={(e) => setLoreEntries(arr => arr.map(x => x.id===le.id? { ...x, keyword: e.target.value }: x))} onBlur={async (e) => { try { await updateLoreEntry(le.id, { keyword: e.target.value }); } catch (err) { alert(err.message); } }} />
                    <input style={{ flex: 1 }} value={le.content} onChange={(e) => setLoreEntries(arr => arr.map(x => x.id===le.id? { ...x, content: e.target.value }: x))} onBlur={async (e) => { try { await updateLoreEntry(le.id, { content: e.target.value }); } catch (err) { alert(err.message); } }} />
                  </div>
                </div>
              ))}
            </div>
            {selectedLorebook && (
              <div className="row">
                <button onClick={async () => {
                  try { const r = await fetch('/lore', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ keyword: 'keyword', content: 'content' })}); if (!r.ok) throw new Error('Failed'); const entry = await r.json(); const ids = [...(selectedLorebook.entry_ids||[]), entry.id]; await updateLorebook(selectedLorebook.id, { entry_ids: ids }); const lbs = await listLorebooks(); setLorebooks(lbs); const lb = lbs.find(x => x.id===selectedLorebook.id); setSelectedLorebook(lb||null); } catch (e) { alert(e.message); }
                }}>+ Add Entry</button>
              </div>
            )}
          </section>
        )}

        <div className="messages" aria-live="polite">
          {messages.map((m, idx) => (
            <div key={idx} className={`message ${m.role}`}>
              <div className="bubble">{m.image_url ? (<img src={m.image_url} alt="generated" style={{ maxWidth: '100%', borderRadius: 8 }} />) : m.content}</div>
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
      </main>
    </div>
  );
}

export default App;

function ImagesTab() {
  const [cfg, setCfg] = useState({ active: 'pollinations', pollinations: { api_key: '', model: '' }, dezgo: { api_key: '', model: '', lora_url: '' } });
  const [models, setModels] = useState([]);

  useEffect(() => { (async () => { try { const c = await getConfig(); setCfg(c.images); const m = await getImageModels(c.images.active); setModels(m.models || []);} catch {} })(); }, []);

  const loadModels = async (prov) => { try { const m = await getImageModels(prov); setModels(m.models || []);} catch { setModels([]);} };

  const saveCfg = async (next) => { try { await updateConfig({ images: next }); } catch (e) { alert(e.message);} };

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
        </>
      )}
      {cfg.active === 'dezgo' && (
        <>
          <label>
            <span>API Key</span>
            <input value={cfg.dezgo.api_key || ''} onChange={(e) => setCfg(c => ({ ...c, dezgo: { ...c.dezgo, api_key: e.target.value } }))} onBlur={async () => { await saveCfg(cfg); }} />
          </label>
          <label>
            <span>Model</span>
            <select value={cfg.dezgo.model || ''} onChange={async (e) => { const v = e.target.value; const next = { ...cfg, dezgo: { ...cfg.dezgo, model: v } }; setCfg(next); await saveCfg(next); }}>
              <option value="">(default)</option>
              {models.map(m => (<option key={m} value={m}>{m}</option>))}
            </select>
          </label>
          <label>
            <span>LORA URL</span>
            <input value={cfg.dezgo.lora_url || ''} onChange={(e) => setCfg(c => ({ ...c, dezgo: { ...c.dezgo, lora_url: e.target.value } }))} onBlur={async () => { await saveCfg(cfg); }} />
          </label>
        </>
      )}
    </div>
  );
}

function AdvancedTab() {
  const [raw, setRaw] = useState('');
  useEffect(() => { (async () => { try { const r = await fetch('/config/raw'); if (r.ok) setRaw(JSON.stringify(await r.json(), null, 2)); } catch {} })(); }, []);
  return (
    <div>
      <p className="muted">Full settings.json (copy/share):</p>
      <textarea rows={16} style={{ width: '100%' }} readOnly value={raw} />
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
