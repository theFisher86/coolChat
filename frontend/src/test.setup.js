import { expect, vi } from 'vitest';

// Expose expect before loading jest-dom
global.expect = expect;
await import('@testing-library/jest-dom');

// Provide a predictable API base for tests
import.meta.env.VITE_API_BASE = 'http://test';

// Minimal matchMedia stub for tests
const listeners = new Set();
const mql = {
  matches: true,
  media: '(max-width: 768px)',
  addEventListener: (_event, cb) => listeners.add(cb),
  removeEventListener: (_event, cb) => listeners.delete(cb),
  dispatchEvent: (event) => {
    listeners.forEach((cb) => cb(event));
    return true;
  },
};

global.matchMedia = vi.fn().mockReturnValue(mql);

