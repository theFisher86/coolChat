// Simple plugin host for CoolChat frontend
import { API_BASE } from './api.js';

const state = {
  backgroundAnimations: [], // [{ id, label }]
  extensions: [], // [{ id, name, client: { entry } }]
  enabledExtensions: {}, // { [id]: bool }
  pluginDisposers: {}, // { [id]: fn }
  registeredStyles: {}, // { [id]: [styleElement, ...] }
};

function notifyUpdate() {
  // This function would typically trigger a re-render in the main app
  // For now, we'll just log a message.
  console.log('Plugin state updated');
  if (Array.isArray(state._listeners)) {
    for (const cb of state._listeners.slice()) {
      try { cb(); } catch (e) { console.warn('pluginHost listener error', e); }
    }
  }
}

function ensureGlobal() {
  if (!window.coolChat) {
    window.coolChat = {};
  }
}

function registerStylesForPlugin(pluginId, cssText) {
  const style = document.createElement('style');
  style.textContent = cssText;
  document.head.appendChild(style);
  state.registeredStyles[pluginId] = state.registeredStyles[pluginId] || [];
  state.registeredStyles[pluginId].push(style);
}

function registerBackgroundAnimationsForPlugin(pluginId, items) {
  const withMeta = (items || []).map(i => ({ ...i, __pluginId: pluginId }));
  state.backgroundAnimations = [...state.backgroundAnimations, ...withMeta];
  notifyUpdate();
}

export function getBackgroundAnimations() {
  // Return a copy without internal __pluginId
  return state.backgroundAnimations.map(({ __pluginId, ...rest }) => rest);
}

export function getExtensions() {
  return state.extensions.map(ext => ({
    ...ext,
    enabled: !!state.enabledExtensions[ext.id],
  }));
}

export function setEnabledExtensions(enabledMap) {
  state.enabledExtensions = enabledMap;
  notifyUpdate();
}

export function setExtensionsList(plugins) {
  state.extensions = Array.isArray(plugins) ? plugins : [];
  notifyUpdate();
}

export async function loadPlugins(manifestData) {
  ensureGlobal();
  // Expose selected API for simple plugins (deprecated globals)
  window.coolChat.registerStyles = (css) => { console.warn('window.coolChat.registerStyles is deprecated; use the init API argument instead'); registerStylesForPlugin('__global__', css); };
  window.coolChat.registerBackgroundAnimations = (items) => { console.warn('window.coolChat.registerBackgroundAnimations is deprecated; use the init API argument instead'); registerBackgroundAnimationsForPlugin('__global__', items); };
  window.coolChat.getExtensions = getExtensions;
  window.coolChat.setEnabledExtensions = setEnabledExtensions;

  try {
    let plugins = [];
    let enabled = {};
    if (manifestData && typeof manifestData === 'object') {
      plugins = Array.isArray(manifestData.plugins) ? manifestData.plugins : [];
      enabled = manifestData.enabled || {};
    } else {
      const res = await fetch(`${API_BASE}/plugins`);
      if (!res.ok) {
        console.warn('Failed to fetch /plugins');
        return;
      }
      const data = await res.json();
      plugins = Array.isArray(data.plugins) ? data.plugins : [];
      enabled = data.enabled || {};
    }

    // Unload any previously-loaded plugins that are no longer enabled
    const enabledSet = new Set(Object.keys(enabled).filter(k => enabled[k]));
    for (const pid of Object.keys(state.pluginDisposers || {})) {
      if (!enabledSet.has(pid)) {
        try { await unloadPlugin(pid); } catch (e) { console.warn('Unload failed', pid, e); }
      }
    }

    state.extensions = plugins;
    // Only update enabled map if provided; otherwise keep current map
    state.enabledExtensions = { ...state.enabledExtensions, ...(enabled || {}) };

    for (const p of plugins) {
      if (!state.enabledExtensions[p.id]) {
        console.log(`Skipping disabled plugin: ${p.id}`);
        continue;
      }
      try {
        const entry = p?.client?.entry || 'plugin.js';
        const url = `${API_BASE}/plugins/static/${p.id}/${entry}`;
        // Vite needs @vite-ignore for fully dynamic imports
        console.log('Loading plugin:', p.id, 'from', url);
        const mod = await import(/* @vite-ignore */ url);
        const init = mod?.default || mod?.init;
        if (typeof init === 'function') {
          // Provide plugin-scoped registration APIs so we can teardown later
          const maybeDispose = await init({
            registerStyles: (css) => registerStylesForPlugin(p.id, css),
            registerBackgroundAnimations: (items) => registerBackgroundAnimationsForPlugin(p.id, items),
          });
          if (typeof maybeDispose === 'function') {
            state.pluginDisposers[p.id] = maybeDispose;
          }
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

export async function unloadPlugin(pluginId) {
  try {
    // call disposer if present
    const fn = state.pluginDisposers && state.pluginDisposers[pluginId];
    if (typeof fn === 'function') {
      try { await fn(); } catch (e) { console.warn('Plugin disposer threw', pluginId, e); }
      delete state.pluginDisposers[pluginId];
    }
    // remove styles
    const styles = state.registeredStyles[pluginId] || [];
    for (const s of styles) {
      try { s.remove(); } catch (e) {}
    }
    delete state.registeredStyles[pluginId];
    // remove background animations registered by this plugin
    state.backgroundAnimations = state.backgroundAnimations.filter(a => a.__pluginId !== pluginId);
    notifyUpdate();
  } catch (e) {
    console.warn('Failed to unload plugin', pluginId, e);
  }
}

export async function unloadAll() {
  for (const pid of Object.keys(state.pluginDisposers || {})) {
    try { await unloadPlugin(pid); } catch (e) { console.warn('UnloadAll failed for', pid, e); }
  }
}

export function onUpdate(cb) {
  state._listeners = state._listeners || [];
  state._listeners.push(cb);
}

export function offUpdate(cb) {
  state._listeners = state._listeners || [];
  const idx = state._listeners.indexOf(cb);
  if (idx >= 0) state._listeners.splice(idx, 1);
}
