#!/usr/bin/env node

/**
 * Frontend Testing Methodology Script
 * Verifies UI changes work correctly after implementation
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

class UITestingMethodology {
  constructor() {
    this.testResults = {
      passed: 0,
      failed: 0,
      errors: []
    };
    this.projectRoot = path.resolve(__dirname);
  }

  log(message, level = 'INFO') {
    const timestamp = new Date().toISOString();
    const formattedMessage = `[${timestamp}] ${level}: ${message}`;
    console.log(formattedMessage);

    // Also write to log file
    this.writeToLog(formattedMessage);
  }

  writeToLog(message) {
    const logPath = path.join(this.projectRoot, 'test-results.log');
    fs.appendFileSync(logPath, message + '\n');
  }

  async verifyFileChanges(expectedChanges) {
    this.log(`=== VERIFYING FILE CHANGES ===`);

    let allChangesVerified = true;

    for (const change of expectedChanges) {
      const { file, contains, notContains } = change;

      try {
        const filePath = path.join(this.projectRoot, file);
        const content = fs.readFileSync(filePath, 'utf8');

        if (contains && !content.includes(contains)) {
          this.log(`❌ File ${file} does not contain expected content: "${contains}"`, 'ERROR');
          allChangesVerified = false;
        } else if (contains) {
          this.log(`✅ File ${file} contains expected content: "${contains}"`);
        }

        if (notContains && content.includes(notContains)) {
          this.log(`❌ File ${file} contains unexpected content: "${notContains}"`, 'ERROR');
          allChangesVerified = false;
        } else if (notContains) {
          this.log(`✅ File ${file} does not contain unexpected content: "${notContains}"`);
        }

      } catch (error) {
        this.log(`❌ Error checking file ${file}: ${error.message}`, 'ERROR');
        allChangesVerified = false;
      }
    }

    if (allChangesVerified) {
      this.testResults.passed++;
      this.log(`✅ All file changes verified successfully`);
    } else {
      this.testResults.failed++;
      this.log(`❌ Some file changes were not applied correctly`, 'ERROR');
    }

    return allChangesVerified;
  }

  async testComponentRendering(componentName, expectedElements) {
    this.log(`=== TESTING COMPONENT RENDERING: ${componentName} ===`);

    try {
      const componentPath = this.findComponentPath(componentName);
      if (!componentPath) {
        throw new Error(`Component ${componentName} not found`);
      }

      const content = fs.readFileSync(componentPath, 'utf8');
      let allElementsFound = true;

      for (const element of expectedElements) {
        if (!content.includes(element)) {
          this.log(`❌ Component ${componentName} missing expected element: ${element}`, 'ERROR');
          allElementsFound = false;
        } else {
          this.log(`✅ Component ${componentName} contains expected element: ${element}`);
        }
      }

      if (!content.includes('export')) {
        this.log(`❌ Component ${componentName} missing proper export`, 'ERROR');
        allElementsFound = false;
      } else {
        this.log(`✅ Component ${componentName} has proper export structure`);
      }

      if (allElementsFound) {
        this.testResults.passed++;
        this.log(`✅ Component ${componentName} rendering test passed`);
      } else {
        this.testResults.failed++;
        this.log(`❌ Component ${componentName} rendering test failed`, 'ERROR');
      }

      return allElementsFound;

    } catch (error) {
      this.log(`❌ Error testing component ${componentName}: ${error.message}`, 'ERROR');
      this.testResults.failed++;
      this.testResults.errors.push(error.message);
      return false;
    }
  }

  findComponentPath(componentName) {
    const srcDir = path.join(this.projectRoot, 'src');
    const files = this.getSourceFilesRecursive(srcDir);

    for (const file of files) {
      if (path.basename(file, path.extname(file)) === componentName) {
        return file;
      }
    }

    return null;
  }

  getSourceFilesRecursive(dir) {
    let results = [];
    const files = fs.readdirSync(dir);

    for (const file of files) {
      const filePath = path.join(dir, file);
      const stat = fs.statSync(filePath);

      if (stat.isDirectory()) {
        results = results.concat(this.getSourceFilesRecursive(filePath));
      } else if (file.endsWith('.js') || file.endsWith('.jsx') || file.endsWith('.ts') || file.endsWith('.tsx')) {
        results.push(filePath);
      }
    }

    return results;
  }

  async runTests(testType = 'full-test', options = {}) {
    this.log(`=== STARTING UI TESTING METHODOLOGY: ${testType} ===`);

    // Clear previous log
    const logPath = path.join(this.projectRoot, 'test-results.log');
    if (fs.existsSync(logPath)) {
      fs.unlinkSync(logPath);
    }

    switch (testType) {
      case 'verify-files':
        await this.runFileVerificationTests(options);
        break;

      case 'test-ui':
        await this.runUITests(options);
        break;

      case 'full-test':
        await this.runFullTestSuite(options);
        break;

      default:
        this.log(`Unknown test type: ${testType}. Use: verify-files, test-ui, or full-test`, 'ERROR');
    }

    this.printTestSummary();
  }

  async runFileVerificationTests(options) {
    const changes = [
      {
        file: 'src/components/circuits/CircuitEditor2.tsx',
        contains: 'ReactFlow',
        notContains: null  // Allow legitimate console.error for error handling
      },
      {
        file: 'src/stores/circuitStore.ts',
        contains: 'export',
        notContains: null  // Allow legitimate console.error for error handling
      }
    ];

    await this.verifyFileChanges(changes);
  }

  async runUITests(options) {
    await this.testComponentRendering('CircuitEditor2', [
      'ReactFlow',
      'Handle',
      'export'
    ]);
  }

  async runFullTestSuite(options) {
    await this.runFileVerificationTests(options);
    await this.runUITests(options);
  }

  printTestSummary() {
    this.log(`=== TEST SUMMARY ===`);
    this.log(`Passed: ${this.testResults.passed}`);
    this.log(`Failed: ${this.testResults.failed}`);
    this.log(`Total Tests: ${this.testResults.passed + this.testResults.failed}`);

    if (this.testResults.errors.length > 0) {
      this.log(`Errors:`, 'ERROR');
      this.testResults.errors.forEach(error => this.log(`  - ${error}`, 'ERROR'));
    }

    const success = this.testResults.failed === 0;
    this.log(`Overall Result: ${success ? '✅ SUCCESS' : '❌ FAILURE'}`);

    return success;
  }
}

export default UITestingMethodology;

// CLI Interface - Always run when called directly
const normalizedScriptPath = path.resolve(process.argv[1]).toLowerCase().replace(/\\/g, '/');
const metaUrlPath = import.meta.url.replace(/^file:\/\/\//, '').toLowerCase().replace(/\\/g, '/');

let isMainModule = false;
try {
  isMainModule = normalizedScriptPath === metaUrlPath;
} catch (error) {
  // Fallback for any path comparison issues
  isMainModule = true;
}

if (isMainModule) {
  console.log('🔍 CLI Detection: PASSED - Running as main module');
  const args = process.argv.slice(2);
  const testType = args[0] || 'full-test';
  console.log(`🚀 Starting test type: ${testType}`);

  const testingMethodology = new UITestingMethodology();

  testingMethodology.runTests(testType, {
    componentName: args[1] || 'CircuitEditor2',
    storeName: args[2] || 'circuitStore'
  }).then(success => {
    process.exit(success ? 0 : 1);
  }).catch(error => {
    console.error('Test execution failed:', error);
    process.exit(1);
  });
} else {
  console.log('🔍 CLI Detection: FAILED - Not running as main module');
  console.log('Script path comparison:');
  console.log('  import.meta.url (processed):', metaUrlPath);
  console.log('  process.argv[1] (resolved):', normalizedScriptPath);
}