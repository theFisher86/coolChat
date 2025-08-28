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
    body: JSON.stringify({ message }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Chat request failed: ${res.status} ${text}`);
  }
  const data = await res.json();
  return data.reply;
}

export async function getConfig() {
  const res = await fetch('/config');
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Get config failed: ${res.status} ${text}`);
  }
  return res.json();
}

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

export default { checkHealth, sendChat, getConfig, updateConfig, getModels };
