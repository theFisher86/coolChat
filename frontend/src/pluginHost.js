// Simple plugin host for CoolChat frontend

const state = {
  backgroundAnimations: [], // [{ id, label }]
};

function notifyUpdate() {
  try {
    window.dispatchEvent(new CustomEvent('coolchat:pluginsUpdated', { detail: {
      backgroundAnimations: getBackgroundAnimations(),
    }}));
  } catch {}
}

function ensureGlobal() {
  if (!window.coolChat) {
    window.coolChat = {};
  }
}

function registerStyles(cssText) {
  if (!cssText) return;
  try {
    const style = document.createElement('style');
    style.setAttribute('data-plugin', 'coolchat');
    style.textContent = cssText;
    document.head.appendChild(style);
  } catch {}
}

function registerBackgroundAnimations(items) {
  if (!Array.isArray(items)) return;
  for (const it of items) {
    if (!it || !it.id) continue;
    if (!state.backgroundAnimations.find(x => x.id === it.id)) {
      state.backgroundAnimations.push({ id: it.id, label: it.label || it.id });
    }
  }
  notifyUpdate();
}

export function getBackgroundAnimations() {
  return [...state.backgroundAnimations];
}

export async function loadPlugins() {
  ensureGlobal();
  // Expose selected API for simple plugins
  window.coolChat.registerStyles = registerStyles;
  window.coolChat.registerBackgroundAnimations = registerBackgroundAnimations;

  try {
    const res = await fetch('/plugins');
    if (!res.ok) return;
    const data = await res.json();
    const plugins = Array.isArray(data.plugins) ? data.plugins : [];
    for (const p of plugins) {
      try {
        const entry = p?.client?.entry || 'plugin.js';
        const url = `/plugins/${p.id}/${entry}`;
        // Vite needs @vite-ignore for fully dynamic imports
        const mod = await import(/* @vite-ignore */ url);
        const init = mod?.default || mod?.init;
        if (typeof init === 'function') {
          await init({
            registerStyles,
            registerBackgroundAnimations,
          });
        }
      } catch (e) {
        console.warn('Plugin load failed:', p?.id, e);
      }
    }
    notifyUpdate();
  } catch (e) {
    console.warn('Plugin manifest load failed', e);
  }
}
