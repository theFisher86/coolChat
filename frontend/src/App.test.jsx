import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import App from './App';

describe('App chat', () => {
  it('shows user and bot messages after sending', async () => {
    vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ reply: 'Hi there' }),
    });

    render(<App />);

    const input = screen.getByPlaceholderText(/type your message/i);
    fireEvent.change(input, { target: { value: 'Hello' } });
    fireEvent.submit(input.closest('form'));

    expect(await screen.findByText('Hello')).toBeInTheDocument();
    expect(await screen.findByText('Hi there')).toBeInTheDocument();

    global.fetch.mockRestore();
  });
});
