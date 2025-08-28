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

export default { checkHealth };
