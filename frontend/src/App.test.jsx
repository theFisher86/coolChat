import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { vi } from 'vitest';
import App from './App';

describe('App', () => {
  it('renders heading and shows offline when fetch fails', async () => {
    vi.spyOn(global, 'fetch').mockRejectedValueOnce(new Error('fail'));

    render(<App />);

    expect(screen.getByRole('heading', { name: /coolchat/i })).toBeInTheDocument();
    expect(await screen.findByText(/offline/i)).toBeInTheDocument();

    global.fetch.mockRestore();
  });
});
