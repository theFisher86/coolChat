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

        // Detailed logging for validation checks
        this.log(`Validating file: ${file}`);
        if (contains) {
          this.log(`  Checking for required content: "${contains}"`);
        }
        if (notContains) {
          this.log(`  Checking for forbidden content: "${notContains}"`);
        }

        // Show file content preview for debugging
        const contentPreview = content.length > 300 ? content.substring(0, 300) + '...' : content;
        this.log(`  File content preview: ${contentPreview}`);

        if (contains && !content.includes(contains)) {
          this.log(`❌ File ${file} does not contain expected content: "${contains}"`, 'ERROR');
          this.log(`  Searched ${content.length} characters, pattern not found`);
          allChangesVerified = false;
        } else if (contains) {
          const occurrences = (content.match(new RegExp(contains.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')) || []).length;
          this.log(`✅ File ${file} contains expected content: "${contains}" (${occurrences} occurrences)`);
        }

        if (notContains && content.includes(notContains)) {
          const index = content.indexOf(notContains);
          const contextStart = Math.max(0, index - 50);
          const contextEnd = Math.min(content.length, index + notContains.length + 50);
          const context = content.substring(contextStart, contextEnd);
          this.log(`❌ File ${file} contains unexpected content: "${notContains}"`, 'ERROR');
          this.log(`  Found at position ${index}, context: "...${context}..."`);
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

  async verifyFileChangesWithContext(expectedChanges) {
    this.log(`=== VERIFYING FILE CHANGES WITH CONTEXT ===`);

    let allChangesVerified = true;

    for (const change of expectedChanges) {
      const { file, contains, containsDescription, notContains, notContainsDescription, context } = change;

      try {
        const filePath = path.join(this.projectRoot, file);
        const content = fs.readFileSync(filePath, 'utf8');

        // Context-aware logging
        this.log(`Validating ${file} (${context || 'general validation'})`);

        if (contains) {
          this.log(`  Required: ${containsDescription || contains}`);
        }
        if (notContains) {
          this.log(`  Forbidden: ${notContainsDescription || notContains}`);
        }

        const contentPreview = content.length > 200 ? content.substring(0, 200) + '...' : content;
        this.log(`  File preview: ${contentPreview}`);

        if (contains && !content.includes(contains)) {
          this.log(`❌ MISSING: ${containsDescription || contains}`, 'ERROR');
          this.log(`  ACTION: Add the required code pattern to ${file}`);
          allChangesVerified = false;
        } else if (contains) {
          const occurrences = (content.match(new RegExp(contains.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')) || []).length;
          this.log(`✅ FOUND: ${containsDescription || contains} (${occurrences} occurrence${occurrences !== 1 ? 's' : ''})`);
        }

        if (notContains && content.includes(notContains)) {
          const index = content.indexOf(notContains);
          const start = Math.max(0, index - 30);
          const end = Math.min(content.length, index + notContains.length + 30);
          const snippet = content.substring(start, end);
          this.log(`❌ VIOLATION: ${notContainsDescription || notContains}`, 'ERROR');
          this.log(`  LOCATION: Found at character ${index}, context: "...${snippet}..."`);
          this.log(`  ACTION: Remove or replace the problematic code in ${file}`);
          allChangesVerified = false;
        } else if (notContains) {
          this.log(`✅ CLEAN: ${notContainsDescription || notContains}`);
        }

      } catch (error) {
        this.log(`❌ Error validating ${file}: ${error.message}`, 'ERROR');
        this.log(`  ACTION: Check if file exists and is readable`);
        allChangesVerified = false;
      }
    }

    if (allChangesVerified) {
      this.testResults.passed++;
      this.log(`✅ All contextual validations passed`);
    } else {
      this.testResults.failed++;
      this.log(`❌ Validation failures detected - review actions above`, 'ERROR');
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

      // Detailed logging for component validation
      this.log(`Validating component file: ${componentPath}`);
      this.log(`  File size: ${content.length} characters`);
      const contentPreview = content.length > 300 ? content.substring(0, 300) + '...' : content;
      this.log(`  Content preview: ${contentPreview}`);

      let allElementsFound = true;

      for (const element of expectedElements) {
        this.log(`  Checking for element: "${element}"`);
        if (!content.includes(element)) {
          this.log(`❌ Component ${componentName} missing expected element: ${element}`, 'ERROR');
          this.log(`  Searched ${content.length} characters, element not found`);
          // Show a bit of context around common locations
          const lines = content.split('\n');
          const renderLine = lines.findIndex(line => line.includes('render') || line.includes('return'));
          if (renderLine !== -1) {
            const contextLines = lines.slice(Math.max(0, renderLine - 2), renderLine + 3);
            this.log(`  Context around render/return: ${contextLines.join('\n    ')}`);
          }
          allElementsFound = false;
        } else {
          const occurrences = (content.match(new RegExp(element.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')) || []).length;
          this.log(`✅ Component ${componentName} contains expected element: ${element} (${occurrences} occurrences)`);
        }
      }

      this.log(`  Checking for export statement`);
      if (!content.includes('export')) {
        this.log(`❌ Component ${componentName} missing proper export`, 'ERROR');
        this.log(`  No 'export' keyword found in ${content.length} characters`);
        allElementsFound = false;
      } else {
        const exportMatches = content.match(/export\s+(default\s+)?/g) || [];
        this.log(`✅ Component ${componentName} has proper export structure (${exportMatches.length} exports found)`);
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

    // Apply customizations if provided
    if (options.customize) {
      this.customizeTestPatterns(options.customize);
    }

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

      case 'test-imports':
        await this.testImportValidation(options.componentName || 'CircuitEditor2');
        break;

      case 'test-quality':
        await this.testCodeQuality(options.componentName || 'CircuitEditor2');
        break;

      case 'full-test':
        await this.runFullTestSuite(options);
        break;

      default:
        this.log(`Unknown test type: ${testType}. Use: verify-files, test-ui, test-imports, test-quality, or full-test`, 'ERROR');
    }

    this.printTestSummary();
  }

  async runFileVerificationTests(options) {
    // Context-aware validation patterns for real development scenarios
    const changes = [
      {
        file: 'src/components/circuits/CircuitEditor2.tsx',
        contains: 'import ReactFlow from \'reactflow\'',
        containsDescription: 'proper ReactFlow import statement',
        notContains: 'console.error',
        notContainsDescription: 'unwanted console.error calls (use proper error handling instead)',
        context: 'React component using ReactFlow library'
      },
      {
        file: 'src/stores/circuitStore.ts',
        contains: 'export const useCircuitStore',
        containsDescription: 'named export of useCircuitStore hook',
        notContains: 'console.error',
        notContainsDescription: 'unwanted console.error calls (use proper logging instead)',
        context: 'Zustand store implementation'
      },
      {
        file: 'src/stores/circuitStore.ts',
        contains: 'export interface Circuit',
        containsDescription: 'Circuit interface definition for type safety',
        notContains: null,
        context: 'TypeScript interface definitions'
      }
    ];

    await this.verifyFileChangesWithContext(changes);
  }

  async runUITests(options) {
    // Test component with context-aware patterns
    await this.testComponentWithContext('CircuitEditor2', {
      requiredImports: [
        { pattern: 'import ReactFlow from \'reactflow\'', description: 'ReactFlow main component import' },
        { pattern: 'import { Handle } from \'reactflow\'', description: 'Handle component for node connections' }
      ],
      requiredExports: [
        { pattern: 'export default CircuitEditor2', description: 'default export of CircuitEditor2 component' }
      ],
      requiredHooks: [
        { pattern: 'useCircuitStore', description: 'circuit store hook usage' },
        { pattern: 'useState', description: 'React state management' }
      ],
      forbiddenPatterns: [
        { pattern: 'console.error', description: 'direct console.error calls (use proper error boundaries)' }
      ]
    });

    // Additional common development scenario tests
    await this.testErrorHandling('CircuitEditor2');
    await this.testStateManagement('CircuitEditor2');
  }

  async runFullTestSuite(options) {
    await this.runFileVerificationTests(options);
    await this.runUITests(options);
  }

  async testComponentWithContext(componentName, patterns) {
    this.log(`=== TESTING COMPONENT: ${componentName} (Context-Aware) ===`);

    try {
      const componentPath = this.findComponentPath(componentName);
      if (!componentPath) {
        throw new Error(`Component ${componentName} not found`);
      }

      const content = fs.readFileSync(componentPath, 'utf8');
      let allChecksPassed = true;

      this.log(`Validating component file: ${componentPath}`);
      this.log(`  File size: ${content.length} characters`);

      // Test required imports
      if (patterns.requiredImports) {
        for (const importReq of patterns.requiredImports) {
          this.log(`  Checking import: ${importReq.description}`);
          if (!content.includes(importReq.pattern)) {
            this.log(`❌ MISSING IMPORT: ${importReq.description}`, 'ERROR');
            this.log(`  ACTION: Add import statement: ${importReq.pattern}`);
            allChecksPassed = false;
          } else {
            this.log(`✅ FOUND: ${importReq.description}`);
          }
        }
      }

      // Test required exports
      if (patterns.requiredExports) {
        for (const exportReq of patterns.requiredExports) {
          this.log(`  Checking export: ${exportReq.description}`);
          if (!content.includes(exportReq.pattern)) {
            this.log(`❌ MISSING EXPORT: ${exportReq.description}`, 'ERROR');
            this.log(`  ACTION: Add export statement: ${exportReq.pattern}`);
            allChecksPassed = false;
          } else {
            this.log(`✅ FOUND: ${exportReq.description}`);
          }
        }
      }

      // Test required hooks
      if (patterns.requiredHooks) {
        for (const hookReq of patterns.requiredHooks) {
          this.log(`  Checking hook usage: ${hookReq.description}`);
          if (!content.includes(hookReq.pattern)) {
            this.log(`❌ MISSING HOOK: ${hookReq.description}`, 'ERROR');
            this.log(`  ACTION: Ensure ${hookReq.pattern} is used in the component`);
            allChecksPassed = false;
          } else {
            this.log(`✅ FOUND: ${hookReq.description}`);
          }
        }
      }

      // Test forbidden patterns
      if (patterns.forbiddenPatterns) {
        for (const forbidden of patterns.forbiddenPatterns) {
          this.log(`  Checking forbidden: ${forbidden.description}`);
          if (content.includes(forbidden.pattern)) {
            const index = content.indexOf(forbidden.pattern);
            const start = Math.max(0, index - 40);
            const end = Math.min(content.length, index + forbidden.pattern.length + 40);
            const snippet = content.substring(start, end);
            this.log(`❌ VIOLATION: ${forbidden.description}`, 'ERROR');
            this.log(`  LOCATION: Found at character ${index}, context: "...${snippet}..."`);
            this.log(`  ACTION: Replace direct ${forbidden.pattern} with proper error handling`);
            allChecksPassed = false;
          } else {
            this.log(`✅ CLEAN: ${forbidden.description}`);
          }
        }
      }

      if (allChecksPassed) {
        this.testResults.passed++;
        this.log(`✅ Component ${componentName} passed all context-aware checks`);
      } else {
        this.testResults.failed++;
        this.log(`❌ Component ${componentName} failed context-aware validation`, 'ERROR');
      }

      return allChecksPassed;

    } catch (error) {
      this.log(`❌ Error testing component ${componentName}: ${error.message}`, 'ERROR');
      this.testResults.failed++;
      this.testResults.errors.push(error.message);
      return false;
    }
  }

  async testErrorHandling(componentName) {
    this.log(`=== TESTING ERROR HANDLING: ${componentName} ===`);

    try {
      const componentPath = this.findComponentPath(componentName);
      if (!componentPath) {
        throw new Error(`Component ${componentName} not found`);
      }

      const content = fs.readFileSync(componentPath, 'utf8');

      // Check for try-catch blocks
      const hasTryCatch = content.includes('try {') && content.includes('catch');
      if (!hasTryCatch) {
        this.log(`⚠️ WARNING: No try-catch error handling found in ${componentName}`);
        this.log(`  SUGGESTION: Add try-catch blocks around async operations`);
      } else {
        this.log(`✅ FOUND: Try-catch error handling present`);
      }

      // Check for error state management
      const hasErrorState = content.includes('useState') && (content.includes('error') || content.includes('Error'));
      if (!hasErrorState) {
        this.log(`⚠️ WARNING: No error state management found in ${componentName}`);
        this.log(`  SUGGESTION: Add error state: const [error, setError] = useState(null);`);
      } else {
        this.log(`✅ FOUND: Error state management present`);
      }

      // This is informational, not a failure
      this.testResults.passed++;
      this.log(`✅ Error handling assessment completed for ${componentName}`);

      return true;

    } catch (error) {
      this.log(`❌ Error testing error handling in ${componentName}: ${error.message}`, 'ERROR');
      this.testResults.failed++;
      this.testResults.errors.push(error.message);
      return false;
    }
  }

  async testStateManagement(componentName) {
    this.log(`=== TESTING STATE MANAGEMENT: ${componentName} ===`);

    try {
      const componentPath = this.findComponentPath(componentName);
      if (!componentPath) {
        throw new Error(`Component ${componentName} not found`);
      }

      const content = fs.readFileSync(componentPath, 'utf8');

      // Check for useState usage
      const useStateCount = (content.match(/useState/g) || []).length;
      if (useStateCount === 0) {
        this.log(`⚠️ WARNING: No useState found in ${componentName} - component may be stateless`);
      } else {
        this.log(`✅ FOUND: ${useStateCount} useState hook${useStateCount !== 1 ? 's' : ''}`);
      }

      // Check for custom hooks usage
      const customHooks = content.match(/use[A-Z]\w+/g) || [];
      const uniqueCustomHooks = [...new Set(customHooks)];
      if (uniqueCustomHooks.length > 0) {
        this.log(`✅ FOUND: Custom hooks usage: ${uniqueCustomHooks.join(', ')}`);
      }

      // Check for prop drilling indicators
      const propDrilling = content.match(/props\.\w+\.\w+/g) || [];
      if (propDrilling.length > 2) {
        this.log(`⚠️ WARNING: Potential prop drilling detected (${propDrilling.length} nested prop accesses)`);
        this.log(`  SUGGESTION: Consider using Context API or state management library`);
      }

      // This is informational, not a failure
      this.testResults.passed++;
      this.log(`✅ State management assessment completed for ${componentName}`);

      return true;

    } catch (error) {
      this.log(`❌ Error testing state management in ${componentName}: ${error.message}`, 'ERROR');
      this.testResults.failed++;
      this.testResults.errors.push(error.message);
      return false;
    }
  }

  async testImportValidation(componentName) {
    this.log(`=== TESTING IMPORT VALIDATION: ${componentName} ===`);

    try {
      const componentPath = this.findComponentPath(componentName);
      if (!componentPath) {
        throw new Error(`Component ${componentName} not found`);
      }

      const content = fs.readFileSync(componentPath, 'utf8');

      // Check for proper React imports
      const hasReactImport = content.includes('import React') || content.includes('from \'react\'');
      if (!hasReactImport) {
        this.log(`⚠️ WARNING: No React import found in ${componentName}`);
        this.log(`  SUGGESTION: Add React import: import React from 'react';`);
      } else {
        this.log(`✅ FOUND: React import present`);
      }

      // Check for default vs named imports consistency
      const defaultImports = content.match(/import\s+\w+\s+from/g) || [];
      const namedImports = content.match(/import\s*\{\s*[^}]+\}\s*from/g) || [];

      this.log(`📊 IMPORT ANALYSIS: ${defaultImports.length} default imports, ${namedImports.length} named imports`);

      // Check for unused imports (basic heuristic)
      const importLines = content.split('\n').filter(line => line.trim().startsWith('import'));
      if (importLines.length > 10) {
        this.log(`⚠️ WARNING: High number of imports (${importLines.length}) - consider code splitting`);
      }

      // This is informational, not a failure
      this.testResults.passed++;
      this.log(`✅ Import validation completed for ${componentName}`);

      return true;

    } catch (error) {
      this.log(`❌ Error testing import validation in ${componentName}: ${error.message}`, 'ERROR');
      this.testResults.failed++;
      this.testResults.errors.push(error.message);
      return false;
    }
  }

  async testCodeQuality(componentName) {
    this.log(`=== TESTING CODE QUALITY: ${componentName} ===`);

    try {
      const componentPath = this.findComponentPath(componentName);
      if (!componentPath) {
        throw new Error(`Component ${componentName} not found`);
      }

      const content = fs.readFileSync(componentPath, 'utf8');
      const lines = content.split('\n');

      // Check line length
      const longLines = lines.filter(line => line.length > 120);
      if (longLines.length > 0) {
        this.log(`⚠️ WARNING: ${longLines.length} lines exceed 120 characters`);
        this.log(`  SUGGESTION: Break long lines for better readability`);
      } else {
        this.log(`✅ GOOD: All lines within recommended length`);
      }

      // Check for console statements in production code
      const consoleStatements = content.match(/console\.\w+/g) || [];
      if (consoleStatements.length > 0) {
        this.log(`⚠️ WARNING: ${consoleStatements.length} console statements found`);
        this.log(`  SUGGESTION: Remove console statements before production`);
      } else {
        this.log(`✅ GOOD: No console statements in production code`);
      }

      // Check function length (basic heuristic)
      const functions = content.match(/function\s+\w+|const\s+\w+\s*=\s*\([^)]*\)\s*=>/g) || [];
      if (functions.length > 0) {
        this.log(`📊 FUNCTION ANALYSIS: ${functions.length} functions detected`);
        if (lines.length / functions.length > 50) {
          this.log(`⚠️ WARNING: Average function length seems high - consider refactoring`);
        }
      }

      // Check for TODO/FIXME comments
      const todoComments = content.match(/\/\/\s*(TODO|FIXME|XXX)/gi) || [];
      if (todoComments.length > 0) {
        this.log(`📝 NOTES: ${todoComments.length} TODO/FIXME comments found`);
        this.log(`  Consider addressing these technical debts`);
      }

      // This is informational, not a failure
      this.testResults.passed++;
      this.log(`✅ Code quality assessment completed for ${componentName}`);

      return true;

    } catch (error) {
      this.log(`❌ Error testing code quality in ${componentName}: ${error.message}`, 'ERROR');
      this.testResults.failed++;
      this.testResults.errors.push(error.message);
      return false;
    }
  }

  // Customization method to allow overriding default patterns
  customizeTestPatterns(options) {
    if (options.fileValidations) {
      this.defaultFileValidations = { ...this.defaultFileValidations, ...options.fileValidations };
    }
    if (options.componentPatterns) {
      this.defaultComponentPatterns = { ...this.defaultComponentPatterns, ...options.componentPatterns };
    }
    this.log(`Test patterns customized with provided options`);
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
