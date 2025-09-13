#!/usr/bin/env node

/**
 * Frontend Test Watcher
 * Automatically runs UI testing methodology when frontend files change
 */

import chokidar from 'chokidar';
import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const SRC_DIR = path.join(__dirname, 'src');
const TEST_SCRIPT = path.join(__dirname, 'test-methodology.js');

console.log('👀 Starting frontend test watcher...');
console.log(`📁 Watching directory: ${SRC_DIR}`);
console.log(`🧪 Test script: ${TEST_SCRIPT}`);
console.log('Press Ctrl+C to stop watching\n');

let isRunning = false;
let pendingRun = false;

function runTests() {
  if (isRunning) {
    pendingRun = true;
    return;
  }

  isRunning = true;
  console.log('🚀 Running UI tests...');

  const testProcess = spawn('node', [TEST_SCRIPT, 'full-test'], {
    stdio: 'inherit',
    cwd: __dirname
  });

  testProcess.on('close', (code) => {
    isRunning = false;
    console.log(`✅ Test run completed (exit code: ${code})`);

    if (pendingRun) {
      pendingRun = false;
      console.log('🔄 Pending test run detected, starting...');
      runTests();
    }
  });

  testProcess.on('error', (error) => {
    console.error('❌ Error running tests:', error);
    isRunning = false;
  });
}

// Watch for changes in source files
const watcher = chokidar.watch(SRC_DIR, {
  ignored: /(^|[\/\\])\../, // ignore dotfiles
  persistent: true,
  ignoreInitial: true
});

watcher.on('change', (filePath) => {
  console.log(`📝 File changed: ${path.relative(__dirname, filePath)}`);
  runTests();
});

watcher.on('add', (filePath) => {
  console.log(`➕ File added: ${path.relative(__dirname, filePath)}`);
  runTests();
});

watcher.on('unlink', (filePath) => {
  console.log(`🗑️  File removed: ${path.relative(__dirname, filePath)}`);
  runTests();
});

// Handle graceful shutdown
process.on('SIGINT', () => {
  console.log('\n👋 Stopping test watcher...');
  watcher.close();
  process.exit(0);
});

console.log('🎯 Ready! Tests will run automatically on file changes.');