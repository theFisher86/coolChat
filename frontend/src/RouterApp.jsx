import React from 'react';
import { Routes, Route } from 'react-router-dom';
import App from './App';
import { CircuitEditor1Page, CircuitEditor2Page } from './components/CircuitEditorPage';

export default function RouterApp() {
  return (
    <Routes>
      <Route path="/" element={<App />} />
      <Route path="/circuiteditor1" element={<CircuitEditor1Page />} />
      <Route path="/circuiteditor2" element={<CircuitEditor2Page />} />
    </Routes>
  );
}