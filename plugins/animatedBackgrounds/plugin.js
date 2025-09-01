// Animated Backgrounds plugin for CoolChat
//
// This plugin demonstrates the minimal client-side plugin API exposed by
// the frontend host. It showcases two integration points:
// 1) registerStyles(css): injects CSS into the page at runtime.
// 2) registerBackgroundAnimations(list): contributes selectable animation
//    identifiers that the Appearance tab can add/remove from the theme.
//
// Folder layout (convention):
//   plugins/animatedBackgrounds/
//     manifest.json   -> discovered by backend and listed at GET /plugins
//     plugin.js       -> browser module imported dynamically by the host
//
// Manifest fields used:
//   { id: string, name: string, version: string, client: { entry: string } }
//   The host builds the URL /plugins/<id>/<client.entry> to import this module.
//
// Host context (provided to default export):
//   - ctx.registerStyles(cssText: string): void
//   - ctx.registerBackgroundAnimations(items: { id: string, label?: string }[]): void
//
// UI wiring on the app side:
//   - The host dispatches a CustomEvent('coolchat:pluginsUpdated') whenever
//     plugins register new contributions so the UI can refresh choices.

const css = `
/* Gradient flow */
.anim-gradient_flow { background: linear-gradient(120deg, var(--bg), var(--panel), var(--assistant)); background-size: 200% 200%; animation: gradflow 20s ease infinite; opacity: 0.15; }
@keyframes gradflow { 0% { background-position: 0% 50% } 50% { background-position: 100% 50% } 100% { background-position: 0% 50% } }

/* Floating squares */
.anim-floating_squares::before { content: ""; position: absolute; width: 200%; height: 200%; background-image: radial-gradient(rgba(255,255,255,0.06) 2px, transparent 2px); background-size: 30px 30px; animation: floatsq 30s linear infinite; }
@keyframes floatsq { from { transform: translate(-10%, -10%) rotate(0deg); } to { transform: translate(0%, 0%) rotate(360deg); } }

/* Waves */
.anim-waves::before, .anim-waves::after { content: ""; position: absolute; inset: 0; background: radial-gradient(circle at bottom, rgba(255,255,255,0.06), transparent 60%); animation: wave 8s ease-in-out infinite; opacity: 0.2; }
.anim-waves::after { animation-delay: -4s; }
@keyframes wave { 0%,100% { transform: translateY(0) } 50% { transform: translateY(10px) } }

/* Neon rain */
.anim-neon_rain::before { content: ""; position: absolute; inset: 0; background: repeating-linear-gradient( to bottom, rgba(0,255,255,0.12), rgba(0,255,255,0.12) 2px, transparent 2px, transparent 6px); animation: rain 1.2s linear infinite; }
@keyframes rain { from { background-position: 0 -20px } to { background-position: 0 0 } }

/* Matrix */
.anim-matrix::before { content: ""; position: absolute; inset: 0; background: repeating-linear-gradient( to bottom, rgba(0,255,0,0.08), rgba(0,255,0,0.08) 2px, transparent 2px, transparent 10px); animation: matrix 1.4s linear infinite; }
@keyframes matrix { from { background-position: 0 -30px } to { background-position: 0 0 } }
`;

/**
 * Plugin entry point.
 * @param {object} ctx - plugin host context
 */
export default function init(ctx) {
  // 1) Contribute CSS for the animation classes used by the UI. These are
  //    strictly additive and only used when the user enables them in theme.
  try {
    ctx.registerStyles(css);
  } catch (e) {
    // Fallback to direct DOM injection
    try {
      const style = document.createElement('style');
      style.textContent = css;
      document.head.appendChild(style);
    } catch {}
  }

  // 2) Contribute the list of available background animations. The UI will
  //    offer these in a dropdown and simply render <div class="anim-<id>" />
  //    for each selected id. The CSS above defines the visual effects.
  if (ctx.registerBackgroundAnimations) {
    ctx.registerBackgroundAnimations([
      { id: 'gradient_flow', label: 'Gradient Flow' },
      { id: 'floating_squares', label: 'Floating Squares' },
      { id: 'waves', label: 'Waves' },
      { id: 'neon_rain', label: 'Neon Rain' },
      { id: 'matrix', label: 'Matrix' },
    ]);
  }
}
