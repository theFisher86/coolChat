#!/usr/bin/env node

/**
 * Simple test script to verify the testing methodology works
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

console.log('🚀 Testing Methodology - Simple Test');
console.log('=====================================');

// Test file system access
try {
  const files = fs.readdirSync(path.join(__dirname, 'src'));
  console.log(`✅ Found ${files.length} items in src directory`);
} catch (error) {
  console.log(`❌ File system error: ${error.message}`);
}

// Test component file detection
try {
  const componentPath = findComponentFile('CircuitEditor2');
  if (componentPath) {
    console.log(`✅ Found CircuitEditor2 at: ${componentPath}`);
    const content = fs.readFileSync(componentPath, 'utf8');
    const hasReactFlow = content.includes('ReactFlow');
    const hasExport = content.includes('export');
    console.log(`✅ Component contains ReactFlow: ${hasReactFlow}`);
    console.log(`✅ Component has export: ${hasExport}`);
  } else {
    console.log(`❌ CircuitEditor2 component not found`);
  }
} catch (error) {
  console.log(`❌ Component detection error: ${error.message}`);
}

function findComponentFile(componentName) {
  const srcDir = path.join(__dirname, 'src');

  function findInDir(dir) {
    const files = fs.readdirSync(dir);

    for (const file of files) {
      const filePath = path.join(dir, file);
      const stat = fs.statSync(filePath);

      if (stat.isDirectory()) {
        const result = findInDir(filePath);
        if (result) return result;
      } else if (path.basename(file, path.extname(file)) === componentName) {
        return filePath;
      }
    }

    return null;
  }

  return findInDir(srcDir);
}

console.log('\n📊 Simple test completed!');
console.log('If you see ✅ marks above, the testing methodology is working.');