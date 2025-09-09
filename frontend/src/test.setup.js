import { expect } from 'vitest';

// Expose expect before loading jest-dom
global.expect = expect;
await import('@testing-library/jest-dom');

// Provide a predictable API base for tests
import.meta.env.VITE_API_BASE = 'http://test';

