import { render, screen, fireEvent, cleanup, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import App from './App';

afterEach(() => {
  cleanup();
});

describe('App chat', () => {
  it('shows user and bot messages after sending', async () => {
    vi.spyOn(global, 'fetch').mockImplementation((url) => {
      if (typeof url === 'string' && url.endsWith('/chat')) {
        return Promise.resolve({ ok: true, json: async () => ({ reply: 'Hi there' }) });
      }
      return Promise.resolve({ ok: true, json: async () => ({}) });
    });

    render(<App />);

    const input = screen.getByPlaceholderText(/type your message/i);
    fireEvent.change(input, { target: { value: 'Hello' } });
    fireEvent.submit(input.closest('form'));

    expect(await screen.findByText('Hello')).toBeInTheDocument();
    expect(await screen.findByText('Hi there')).toBeInTheDocument();
    expect(global.fetch).toHaveBeenCalledWith('http://test/chat', expect.any(Object));

    global.fetch.mockRestore();
  });
});

describe('mobile menu', () => {
  let mql;

  beforeEach(() => {
    mql = window.matchMedia('(max-width: 768px)');
    mql.matches = true;
  });

  it('closes when tapping outside the menu', async () => {
    render(<App />);
    const toggle = screen.getByLabelText(/toggle menu/i);
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    fireEvent.touchStart(document.body);
    await waitFor(() => expect(toggle).toHaveAttribute('aria-expanded', 'false'));
  });

  it('closes on orientation change', async () => {
    render(<App />);
    const toggle = screen.getByLabelText(/toggle menu/i);
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    mql.matches = false;
    mql.dispatchEvent({ matches: false });
    await waitFor(() => expect(toggle).toHaveAttribute('aria-expanded', 'false'));
  });
});
