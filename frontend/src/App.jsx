import React, { useEffect, useState } from 'react';
import './App.css';
import { sendChat, getConfig, updateConfig, getModels, listCharacters, createCharacter, deleteCharacter } from './api';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const [showConfig, setShowConfig] = useState(false);
  const [activeProvider, setActiveProvider] = useState('echo');
  const [providers, setProviders] = useState({}); // provider -> masked config
  const [configDraft, setConfigDraft] = useState({ api_key: '', api_base: '', model: '', temperature: 0.7 });
  const [modelList, setModelList] = useState([]);
  const [loadingModels, setLoadingModels] = useState(false);
  const [characters, setCharacters] = useState([]);
  const [newChar, setNewChar] = useState({ name: '', description: '', avatar_url: '' });
  const [showCharacters, setShowCharacters] = useState(false);
  const [showLorebooks, setShowLorebooks] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const cfg = await getConfig();
        setActiveProvider(cfg.active_provider);
        setProviders(cfg.providers || {});
        const cur = cfg.providers?.[cfg.active_provider] || {};
        setConfigDraft({ api_key: '', api_base: cur.api_base || '', model: cur.model || '', temperature: cur.temperature ?? 0.7 });
      } catch (e) {
        console.warn('Could not load config', e);
      }
    })();
  }, []);

  useEffect(() => {
    (async () => {
      try { const list = await listCharacters(); setCharacters(list); } catch {}
    })();
  }, [showCharacters]);

  const refreshModels = async (prov) => {
    const p = prov ?? activeProvider;
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
    if (showConfig) {
      refreshModels();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
        {showCharacters && (
        <section className="characters">
          <h2>Characters</h2>
          <div className="row">
            <input placeholder="Name" value={newChar.name} onChange={(e) => setNewChar({ ...newChar, name: e.target.value })} />
            <input placeholder="Avatar URL (optional)" value={newChar.avatar_url} onChange={(e) => setNewChar({ ...newChar, avatar_url: e.target.value })} />
          </div>
          <div className="row">
            <input placeholder="Description" value={newChar.description} onChange={(e) => setNewChar({ ...newChar, description: e.target.value })} />
            <button onClick={async () => {
              if (!newChar.name.trim()) return;
              try { await createCharacter({ ...newChar, avatar_url: newChar.avatar_url || null }); setNewChar({ name: '', description: '', avatar_url: '' }); const list = await listCharacters(); setCharacters(list); } catch (e) { alert(e.message); }
            }}>Create</button>
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
            <p className="muted">Choose provider and set API credentials.</p>
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
                  refreshModels();
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

            <div className="hint">
              <p className="muted">
                OpenRouter uses OpenAI-compatible endpoints. You can set API Base to https://openrouter.ai/api/v1. Gemini uses the OpenAI-compatible base at https://generativelanguage.googleapis.com/v1beta/openai.
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
 
function CharacterEditor({ character, onClose, onSave, lorebooks }) {
  const [draft, setDraft] = useState(() => ({
    name: character?.name || '',
    description: character?.description || '',
    avatar_url: character?.avatar_url || '',
    first_message: character?.first_message || '',
    alternate_greetings: character?.alternate_greetings?.join(', ') || '',
    scenario: character?.scenario || '',
    system_prompt: character?.system_prompt || '',
    personality: character?.personality || '',
    mes_example: character?.mes_example || '',
    creator_notes: character?.creator_notes || '',
    tags: character?.tags?.join(', ') || '',
    post_history_instructions: character?.post_history_instructions || '',
    lorebook_ids: character?.lorebook_ids || [],
  }));

  const think = async (field) => {
    try {
      const payload = { ...draft, alternate_greetings: draft.alternate_greetings.split(',').map(s => s.trim()).filter(Boolean), tags: draft.tags.split(',').map(s => s.trim()).filter(Boolean) };
      const res = await suggestCharacterField(field, payload);
      setDraft((d) => ({ ...d, [field]: res.value }));
    } catch (e) { alert(e.message); }
  };

  return (
    <div className="modal" onClick={onClose}>
      <div className="dialog" onClick={(e) => e.stopPropagation()}>
        <h2>{character ? 'Edit Character' : 'New Character'}</h2>
        <div className="editor-grid">
          <span className="label">Name</span>
          <div><input value={draft.name} onChange={(e) => setDraft(d => ({ ...d, name: e.target.value }))} /> <button className="think" onClick={() => think('name')}>💭</button></div>
          <span className="label">Avatar URL</span>
          <div><input value={draft.avatar_url} onChange={(e) => setDraft(d => ({ ...d, avatar_url: e.target.value }))} /></div>
          <span className="label">Description</span>
          <div><textarea rows={3} value={draft.description} onChange={(e) => setDraft(d => ({ ...d, description: e.target.value }))} /> <button className="think" onClick={() => think('description')}>💭</button></div>
          <span className="label">First Message</span>
          <div><textarea rows={3} value={draft.first_message} onChange={(e) => setDraft(d => ({ ...d, first_message: e.target.value }))} /> <button className="think" onClick={() => think('first_message')}>💭</button></div>
          <span className="label">Alternate Greetings</span>
          <div><input value={draft.alternate_greetings} onChange={(e) => setDraft(d => ({ ...d, alternate_greetings: e.target.value }))} /> <button className="think" onClick={() => think('alternate_greetings')}>💭</button></div>
          <span className="label">Scenario</span>
          <div><textarea rows={3} value={draft.scenario} onChange={(e) => setDraft(d => ({ ...d, scenario: e.target.value }))} /> <button className="think" onClick={() => think('scenario')}>💭</button></div>
          <span className="label">System Prompt</span>
          <div><textarea rows={3} value={draft.system_prompt} onChange={(e) => setDraft(d => ({ ...d, system_prompt: e.target.value }))} /> <button className="think" onClick={() => think('system_prompt')}>💭</button></div>
          <span className="label">Personality</span>
          <div><textarea rows={3} value={draft.personality} onChange={(e) => setDraft(d => ({ ...d, personality: e.target.value }))} /> <button className="think" onClick={() => think('personality')}>💭</button></div>
          <span className="label">Message Example</span>
          <div><textarea rows={3} value={draft.mes_example} onChange={(e) => setDraft(d => ({ ...d, mes_example: e.target.value }))} /> <button className="think" onClick={() => think('mes_example')}>💭</button></div>
          <span className="label">Creator Notes</span>
          <div><textarea rows={3} value={draft.creator_notes} onChange={(e) => setDraft(d => ({ ...d, creator_notes: e.target.value }))} /> <button className="think" onClick={() => think('creator_notes')}>💭</button></div>
          <span className="label">Tags (comma)</span>
          <div><input value={draft.tags} onChange={(e) => setDraft(d => ({ ...d, tags: e.target.value }))} /></div>
          <span className="label">Post-History Instructions</span>
          <div><textarea rows={3} value={draft.post_history_instructions} onChange={(e) => setDraft(d => ({ ...d, post_history_instructions: e.target.value }))} /> <button className="think" onClick={() => think('post_history_instructions')}>💭</button></div>
          <span className="label">Lorebooks</span>
          <div>
            {lorebooks.map(lb => (
              <label key={lb.id} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, marginRight: 8 }}>
                <input type="checkbox" checked={draft.lorebook_ids.includes(lb.id)} onChange={(e) => {
                  const checked = e.target.checked;
                  setDraft(d => ({ ...d, lorebook_ids: checked ? [...d.lorebook_ids, lb.id] : d.lorebook_ids.filter(id => id !== lb.id) }));
                }} /> {lb.name}
              </label>
            ))}
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
