export function init({ registerBackgroundAnimations }) {
  const items = [
    { id: 'bubbles', label: 'Bubbles' },
    { id: 'lines', label: 'Lines' },
    { id: 'topography', label: 'Topography' },
    { id: 'sparkles', label: 'Sparkles' },
  ];
  registerBackgroundAnimations(items);
  // Return a disposer to allow unregistering when disabled
  return function dispose() {
    try {
      // Plugins should not reach into host internals; host will remove registered animations by plugin id.
      // If the plugin had added styles, it could remove them here (if it kept references).
    } catch (e) {
      console.warn('dispose failed', e);
    }
  };
}
