export async function checkHealth() {
  try {
    const res = await fetch('/health');
    return res.ok;
  } catch (err) {
    console.error('Health check failed', err);
    return false;
  }
}

export async function sendChat(message) {
  const res = await fetch('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: 'default' }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Chat request failed: ${res.status} ${text}`);
  }
  const data = await res.json();
  return data.reply;
}

// Characters API
export async function listCharacters() {
  const res = await fetch('/characters');
  if (!res.ok) throw new Error(`List characters failed: ${res.status}`);
  return res.json();
}

export async function createCharacter({ name, description = '', avatar_url = null }) {
  const res = await fetch('/characters', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description, avatar_url }),
  });
  if (!res.ok) throw new Error(`Create character failed: ${res.status}`);
  return res.json();
}

export async function deleteCharacter(id) {
  const res = await fetch(`/characters/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`Delete character failed: ${res.status}`);
}

export async function getConfig() {
  const res = await fetch('/config');
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Get config failed: ${res.status} ${text}`);
  }
  return res.json();
}

export async function getConfigRaw() {
  const res = await fetch('/config/raw');
  if (!res.ok) throw new Error(`Get raw config failed: ${res.status}`);
  return res.json();
}

// partial can include { active_provider, providers: { [provider]: { api_base, api_key, model, temperature } } }
export async function updateConfig(partial) {
  const res = await fetch('/config', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(partial),
  });
  if (!res.ok) {
    const text = await res.text();
    try {
      const data = JSON.parse(text);
      const detail = typeof data?.detail === 'string' ? data.detail : JSON.stringify(data?.detail ?? data);
      throw new Error(`Update config failed: ${res.status} ${detail}`);
    } catch {
      throw new Error(`Update config failed: ${res.status} ${text}`);
    }
  }
  return res.json();
}

export async function getModels(provider) {
  const qs = provider ? `?provider=${encodeURIComponent(provider)}` : '';
  const res = await fetch(`/models${qs}`);
  if (!res.ok) {
    const text = await res.text();
    try {
      const data = JSON.parse(text);
      const detail = typeof data?.detail === 'string' ? data.detail : JSON.stringify(data?.detail ?? data);
      throw new Error(`Get models failed: ${res.status} ${detail}`);
    } catch {
      throw new Error(`Get models failed: ${res.status} ${text}`);
    }
  }
  return res.json(); // { models: string[] }
}

// Lorebooks API
export async function listLorebooks() {
  const res = await fetch('/lorebooks');
  if (!res.ok) throw new Error(`List lorebooks failed: ${res.status}`);
  return res.json();
}

export async function createLorebook({ name, description = '', entries = [] }) {
  const res = await fetch('/lorebooks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description, entries }),
  });
  if (!res.ok) throw new Error(`Create lorebook failed: ${res.status}`);
  return res.json();
}

export async function importLorebook(file) {
  const fd = new FormData();
  fd.append('file', file);
  const res = await fetch('/lorebooks/import', { method: 'POST', body: fd });
  if (!res.ok) throw new Error(`Import lorebook failed: ${res.status}`);
  return res.json();
}

export async function updateCharacter(id, data) {
  const res = await fetch(`/characters/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Update character failed: ${res.status}`);
  return res.json();
}

export async function suggestCharacterField(field, characterDraft) {
  const res = await fetch('/characters/suggest_field', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ field, character: characterDraft }),
  });
  if (!res.ok) throw new Error(`Suggest field failed: ${res.status}`);
  return res.json(); // { value }
}

export async function getImageModels(provider) {
  const res = await fetch(`/image/models?provider=${encodeURIComponent(provider)}`);
  if (!res.ok) throw new Error(`Get image models failed: ${res.status}`);
  return res.json();
}

export async function generateImageFromChat() {
  const res = await fetch('/images/generate_from_chat', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_id: 'default' }),
  });
  if (!res.ok) throw new Error(`Generate image failed: ${res.status}`);
  return res.json();
}

export async function updateLoreEntry(id, data) {
  const res = await fetch(`/lore/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
  if (!res.ok) throw new Error(`Update lore failed: ${res.status}`);
  return res.json();
}

export async function updateLorebook(id, data) {
  const res = await fetch(`/lorebooks/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
  if (!res.ok) throw new Error(`Update lorebook failed: ${res.status}`);
  return res.json();
}

export default { checkHealth, sendChat, getConfig, updateConfig, getModels, listCharacters, createCharacter, deleteCharacter };
