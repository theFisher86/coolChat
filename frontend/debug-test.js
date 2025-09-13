#!/usr/bin/env node

import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);

console.log('=== DEBUG TEST SCRIPT ===');
console.log('Node.js version:', process.version);
console.log('Current working directory:', process.cwd());
console.log('Script file:', __filename);
console.log('Arguments:', process.argv);
console.log('import.meta.url:', import.meta.url);
console.log('process.argv[1]:', process.argv[1]);

// Original detection (fails on Windows)
console.log('Original CLI Detection:', import.meta.url === `file://${process.argv[1]}`);

// Better CLI detection for Windows
const normalizedScriptPath = process.argv[1].replace(/\\/g, '/');
const isMainModule = import.meta.url === `file:///${normalizedScriptPath}`;

console.log('Normalized script path:', normalizedScriptPath);
console.log('Fixed CLI Detection:', isMainModule);

if (isMainModule) {
  console.log('✅ CLI detection passed - script is running as main module');
  console.log('🚀 Now executing test logic...');

  // Test the actual testing methodology
  console.log('\n=== TESTING ACTUAL FUNCTIONALITY ===');
  console.log('This would run the test suite...');

} else {
  console.log('❌ CLI detection failed - script is NOT running as main module');
}

console.log('=== END DEBUG ===');