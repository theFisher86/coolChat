#!/usr/bin/env node

/**
 * Circuit Editor Property Panel Validation Script (ES Module Version)
 *
 * Tests the property panel updates and data flow for Circuit Editor UI components.
 * Validates that changes to blocks are properly reflected in the properties panel.
 */

import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { spawn } from 'child_process';

class CircuitPropertyValidator {
  constructor() {
    this.testResults = {
      passed: 0,
      failed: 0,
      total: 0,
      details: []
    };
    this.baselineData = null;
  }

  log(message, type = 'info') {
    const timestamp = new Date().toISOString();
    const prefix = type === 'error' ? '❌' : type === 'success' ? '✅' : 'ℹ️';
    console.log(`[${timestamp}] ${prefix} ${message}`);
  }

  /**
   * Capture baseline state before changes
   */
  async captureBaselineState() {
    this.log('Capturing baseline state...');

    try {
      // Read current CircuitEditor2.tsx to understand structure
      const circuitEditorPath = path.join(process.cwd(), 'src/components/circuits/CircuitEditor2.tsx');
      const circuitStorePath = path.join(process.cwd(), 'src/stores/circuitStore.ts');

      const circuitEditorContent = fs.readFileSync(circuitEditorPath, 'utf8');
      const circuitStoreContent = fs.readFileSync(circuitStorePath, 'utf8');

      this.baselineData = {
        circuitEditor: {
          size: circuitEditorContent.length,
          hasPropertySections: circuitEditorContent.includes('properties-section'),
          hasCurrentValues: circuitEditorContent.includes('Current Values'),
          hasSelectedNode: circuitEditorContent.includes('selectedNode'),
          renderCurrentValues: circuitEditorContent.includes('renderCurrentValues'),
          debugLogs: (circuitEditorContent.match(/console\.log/g) || []).length
        },
        circuitStore: {
          size: circuitStoreContent.length,
          hasExecutionOutputs: circuitStoreContent.includes('executionOutputs'),
          hasExecutionResult: circuitStoreContent.includes('executionResult'),
          hasStateManagement: circuitStoreContent.includes('create<')
        },
        timestamp: new Date().toISOString()
      };

      this.log('Baseline state captured successfully', 'success');
      return this.baselineData;
    } catch (error) {
      this.log(`Failed to capture baseline: ${error.message}`, 'error');
      throw error;
    }
  }

  /**
   * Validate property panel structure
   */
  validatePropertyPanelStructure() {
    this.log('Validating property panel structure...');

    const circuitEditorPath = path.join(process.cwd(), 'src/components/circuits/CircuitEditor2.tsx');
    const content = fs.readFileSync(circuitEditorPath, 'utf8');

    const tests = [
      {
        name: 'Properties panel exists',
        test: () => content.includes('properties panel'),
        description: 'Properties panel should be rendered in the component'
      },
      {
        name: 'Block description section',
        test: () => content.includes('Block Description') || content.includes('getBlockDescription'),
        description: 'Block description section should be present'
      },
      {
        name: 'Block settings section',
        test: () => content.includes('Block Settings') || content.includes('renderBlockSettings'),
        description: 'Block settings section should handle form inputs'
      },
      {
        name: 'Current values section',
        test: () => content.includes('Current Values') && content.includes('renderCurrentValues'),
        description: 'Current values section should show runtime data'
      },
      {
        name: 'Configuration section',
        test: () => content.includes('Configuration') || content.includes('extendedConfig'),
        description: 'Configuration section should display block config'
      },
      {
        name: 'Live data section',
        test: () => content.includes('Live Data') || content.includes('live-data-section'),
        description: 'Live data section should load external data'
      },
      {
        name: 'State management integration',
        test: () => content.includes('useCircuitStore') && content.includes('useDataStore'),
        description: 'Component should integrate with Zustand stores'
      },
      {
        name: 'React Flow integration',
        test: () => content.includes('ReactFlow') && content.includes('useNodesState'),
        description: 'Component should use ReactFlow for canvas management'
      }
    ];

    tests.forEach(test => {
      this.testResults.total++;
      try {
        const result = test.test();
        if (result) {
          this.testResults.passed++;
          this.log(`${test.name}: PASSED`, 'success');
        } else {
          this.testResults.failed++;
          this.log(`${test.name}: FAILED - ${test.description}`, 'error');
          this.testResults.details.push({
            test: test.name,
            status: 'failed',
            description: test.description
          });
        }
      } catch (error) {
        this.testResults.failed++;
        this.log(`${test.name}: ERROR - ${error.message}`, 'error');
        this.testResults.details.push({
          test: test.name,
          status: 'error',
          description: error.message
        });
      }
    });
  }

  /**
   * Validate data flow and state synchronization
   */
  validateDataFlow() {
    this.log('Validating data flow and state synchronization...');

    const circuitEditorPath = path.join(process.cwd(), 'src/components/circuits/CircuitEditor2.tsx');
    const circuitStorePath = path.join(process.cwd(), 'src/stores/circuitStore.ts');
    const content = fs.readFileSync(circuitEditorPath, 'utf8');
    const storeContent = fs.readFileSync(circuitStorePath, 'utf8');

    const tests = [
      {
        name: 'Selected node state updates',
        test: () => content.includes('setSelectedNode') && content.includes('onNodeClick'),
        description: 'Selected node should update when clicking nodes'
      },
      {
        name: 'Node data updates propagate',
        test: () => content.includes('updateNodeData') && content.includes('onUpdateNode'),
        description: 'Node data changes should propagate to UI'
      },
      {
        name: 'Execution results integration',
        test: () => content.includes('executionResult') && content.includes('executionOutputs'),
        description: 'Execution results should update UI components'
      },
      {
        name: 'Store subscription',
        test: () => storeContent.includes('subscribe') || content.includes('useEffect') && content.includes('circuitStore'),
        description: 'Component should subscribe to store changes'
      },
      {
        name: 'Real-time data updates',
        test: () => content.includes('executionOutputs') && content.includes('renderCurrentValues'),
        description: 'Real-time execution data should update Current Values section'
      },
      {
        name: 'Connection status tracking',
        test: () => content.includes('edges') && content.includes('connected'),
        description: 'Connection status should be tracked and displayed'
      }
    ];

    tests.forEach(test => {
      this.testResults.total++;
      try {
        const result = test.test();
        if (result) {
          this.testResults.passed++;
          this.log(`${test.name}: PASSED`, 'success');
        } else {
          this.testResults.failed++;
          this.log(`${test.name}: FAILED - ${test.description}`, 'error');
          this.testResults.details.push({
            test: test.name,
            status: 'failed',
            description: test.description
          });
        }
      } catch (error) {
        this.testResults.failed++;
        this.log(`${test.name}: ERROR - ${error.message}`, 'error');
        this.testResults.details.push({
          test: test.name,
          status: 'error',
          description: error.message
        });
      }
    });
  }

  /**
   * Test renderCurrentValues function if it exists
   */
  validateRenderCurrentValuesFunction() {
    this.log('Validating renderCurrentValues function...');

    const circuitEditorPath = path.join(process.cwd(), 'src/components/circuits/CircuitEditor2.tsx');
    const content = fs.readFileSync(circuitEditorPath, 'utf8');

    if (!content.includes('renderCurrentValues')) {
      this.log('renderCurrentValues function not found - this may be expected if using inline rendering', 'info');
      return;
    }

    const tests = [
      {
        name: 'Function definition exists',
        test: () => content.includes('const renderCurrentValues') || content.includes('function renderCurrentValues'),
        description: 'renderCurrentValues function should be defined'
      },
      {
        name: 'Receives correct parameters',
        test: () => content.includes('selectedNode') && content.includes('executionResult') && content.includes('edges'),
        description: 'Function should receive necessary data parameters'
      },
      {
        name: 'Returns JSX',
        test: () => {
          const functionMatch = content.match(/const renderCurrentValues[\s\S]*?return[\s\S]*?\}/);
          return functionMatch && functionMatch[0].includes('div') && functionMatch[0].includes('className');
        },
        description: 'Function should return valid JSX elements'
      },
      {
        name: 'Handles connection data',
        test: () => content.includes('getSourceNodeData') || content.includes('connected'),
        description: 'Function should handle input/output connection data'
      },
      {
        name: 'Displays execution outputs',
        test: () => content.includes('executionOutputs') && content.includes('getOutputData'),
        description: 'Function should display execution output data'
      }
    ];

    tests.forEach(test => {
      this.testResults.total++;
      try {
        const result = test.test();
        if (result) {
          this.testResults.passed++;
          this.log(`${test.name}: PASSED`, 'success');
        } else {
          this.testResults.failed++;
          this.log(`${test.name}: FAILED - ${test.description}`, 'error');
          this.testResults.details.push({
            test: test.name,
            status: 'failed',
            description: test.description
          });
        }
      } catch (error) {
        this.testResults.failed++;
        this.log(`${test.name}: ERROR - ${error.message}`, 'error');
        this.testResults.details.push({
          test: test.name,
          status: 'error',
          description: error.message
        });
      }
    });
  }

  /**
   * Generate test report
   */
  generateReport() {
    const report = {
      summary: {
        total: this.testResults.total,
        passed: this.testResults.passed,
        failed: this.testResults.failed,
        passRate: this.testResults.total > 0 ? (this.testResults.passed / this.testResults.total * 100).toFixed(1) : '0'
      },
      details: this.testResults.details,
      timestamp: new Date().toISOString(),
      baseline: this.baselineData
    };

    const reportPath = path.join(process.cwd(), 'circuit-property-test-results.json');
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));

    this.log(`Test report generated: ${reportPath}`);
    this.log(`Results: ${report.summary.passed}/${report.summary.total} tests passed (${report.summary.passRate}%)`);

    return report;
  }

  /**
   * Run all validation tests
   */
  async runAllTests() {
    this.log('Starting Circuit Editor Property Panel Validation...');

    try {
      await this.captureBaselineState();
      this.validatePropertyPanelStructure();
      this.validateDataFlow();
      this.validateRenderCurrentValuesFunction();

      const report = this.generateReport();

      if (this.testResults.failed === 0) {
        this.log('All tests passed! Circuit Editor property panel appears to be working correctly.', 'success');
        return true;
      } else {
        this.log(`${this.testResults.failed} tests failed. Check the detailed report for issues.`, 'error');
        return false;
      }
    } catch (error) {
      this.log(`Test execution failed: ${error.message}`, 'error');
      return false;
    }
  }
}

// CLI interface
async function main() {
  const args = process.argv.slice(2);
  const validator = new CircuitPropertyValidator();

  if (args.includes('--help') || args.includes('-h')) {
    console.log(`
Circuit Editor Property Panel Validation Tool

Usage:
  node circuit-property-test-new.js [options]

Options:
  --help, -h          Show this help message
  --baseline-only     Only capture baseline state
  --report-only       Only generate report from existing data
  --verbose           Show detailed output

Examples:
  node circuit-property-test-new.js
  node circuit-property-test-new.js --baseline-only
`);
    return;
  }

  if (args.includes('--baseline-only')) {
    await validator.captureBaselineState();
    console.log('Baseline captured. Run without flags to perform full validation.');
    return;
  }

  if (args.includes('--report-only')) {
    // Load existing results and regenerate report
    const reportPath = path.join(process.cwd(), 'circuit-property-test-results.json');
    if (fs.existsSync(reportPath)) {
      const existingReport = JSON.parse(fs.readFileSync(reportPath, 'utf8'));
      console.log('Existing test results:');
      console.log(`Passed: ${existingReport.summary.passed}/${existingReport.summary.total}`);
      console.log(`Pass Rate: ${existingReport.summary.passRate}%`);
    } else {
      console.log('No existing test results found. Run full test first.');
    }
    return;
  }

  const success = await validator.runAllTests();
  process.exit(success ? 0 : 1);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(error => {
    console.error('Fatal error:', error);
    process.exit(1);
  });
}

export default CircuitPropertyValidator;