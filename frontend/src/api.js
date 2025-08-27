export async function checkHealth() {
  try {
    const res = await fetch('/health');
    return res.ok;
  } catch (err) {
    console.error('Health check failed', err);
    return false;
  }
}

export default { checkHealth };
