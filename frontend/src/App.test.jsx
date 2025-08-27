import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import App from './App';

test('renders expected text', () => {
  render(<App />);
  expect(
    screen.getByText('Welcome to CoolChat, a Python/React re-imagination of SillyTavern.')
  ).toBeInTheDocument();
});

