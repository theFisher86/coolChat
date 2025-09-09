import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { vi, describe, it, expect } from 'vitest';
import App from './App';

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
