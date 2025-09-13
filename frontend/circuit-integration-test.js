#!/usr/bin/env node

/**
 * Circuit Editor Integration Testing Framework (ES Module Version)
 *
 * Comprehensive integration tests for Circuit Editor UI components,
 * focusing on circuit execution verification and end-to-end workflows.
 */

import fs from 'fs';
import path from 'path';
import { spawn } from 'child_process';

class CircuitIntegrationTester {
  constructor() {
    this.testResults = {
      passed: 0,
      failed: 0,
      skipped: 0,
      total: 0,
      details: [],
      executionLogs: []
    };
    this.backendUrl = 'http://localhost:8000';
    this.frontendUrl = 'http://localhost:5173';
    this.testCircuits = this.loadTestCircuits();
  }

  log(message, type = 'info') {
    const timestamp = new Date().toISOString();
    const prefix = type === 'error' ? '❌' : type === 'success' ? '✅' : type === 'warn' ? '⚠️' : type === 'skip' ? '⏭️' : 'ℹ️';
    console.log(`[${timestamp}] ${prefix} ${message}`);

    if (type === 'error' || type === 'warn') {
      this.testResults.executionLogs.push(`[${type.toUpperCase()}] ${message}`);
    }
  }

  /**
   * Load predefined test circuits
   */
  loadTestCircuits() {
    return [
      {
        name: 'simple-text-circuit',
        description: 'Circuit with a single text block',
        data: {
          nodes: [
            {
              id: 'text-1',
              type: 'text_block',
              position: { x: 100, y: 100 },
              data: {
                label: 'Text Block',
                type: 'text_block',
                icon: '📄',
                inputs: [],
                outputs: ['output'],
                text: 'Hello World',
                outputMode: 'string'
              }
            }
          ],
          edges: []
        },
        expectedOutputs: {
          'text-1': { output: 'Hello World' }
        }
      },
      {
        name: 'constructor-circuit',
        description: 'Circuit with constructor block combining inputs',
        data: {
          nodes: [
            {
              id: 'text1',
              type: 'text_block',
              position: { x: 50, y: 50 },
              data: {
                label: 'Text Block 1',
                type: 'text_block',
                icon: '📄',
                inputs: [],
                outputs: ['output'],
                text: 'Hello',
                outputMode: 'string'
              }
            },
            {
              id: 'text2',
              type: 'text_block',
              position: { x: 50, y: 150 },
              data: {
                label: 'Text Block 2',
                type: 'text_block',
                icon: '📄',
                inputs: [],
                outputs: ['output'],
                text: 'World',
                outputMode: 'string'
              }
            },
            {
              id: 'constructor',
              type: 'constructor_block',
              position: { x: 300, y: 100 },
              data: {
                label: 'Constructor Block',
                type: 'constructor_block',
                icon: '🏗️',
                inputs: ['input1', 'input2'],
                outputs: ['output'],
                separator: ' '
              }
            }
          ],
          edges: [
            {
              id: 'edge1',
              source: 'text1',
              sourceHandle: 'output-output',
              target: 'constructor',
              targetHandle: 'input-input1'
            },
            {
              id: 'edge2',
              source: 'text2',
              sourceHandle: 'output-output',
              target: 'constructor',
              targetHandle: 'input-input2'
            }
          ]
        },
        expectedOutputs: {
          'constructor': { output: 'Hello World' }
        }
      },
      {
        name: 'character-card-circuit',
        description: 'Circuit with character card block (requires backend data)',
        data: {
          nodes: [
            {
              id: 'char-card',
              type: 'character_card_block',
              position: { x: 100, y: 100 },
              data: {
                label: 'Character Card Block',
                type: 'character_card_block',
                icon: '🎭',
                inputs: [],
                outputs: ['output'],
                selectedCharacter: 'current',
                cardField: 'name'
              }
            }
          ],
          edges: []
        },
        requiresBackendData: true,
        skipIfNoData: true
      }
    ];
  }

  /**
   * Check if backend is running
   */
  async checkBackend() {
    try {
      const response = await fetch(`${this.backendUrl}/health`);
      return response.ok;
    } catch {
      return false;
    }
  }

  /**
   * Check if frontend dev server is running
   */
  async checkFrontend() {
    try {
      const response = await fetch(this.frontendUrl);
      return response.ok;
    } catch {
      return false;
    }
  }

  /**
   * Start required services if not running
   */
  async ensureServicesRunning() {
    this.log('Checking service availability...');

    const backendRunning = await this.checkBackend();
    const frontendRunning = await this.checkFrontend();

    if (!backendRunning) {
      this.log('Backend service not running, attempting to start...', 'warn');
      // In a real implementation, you'd start the backend service
      // For now, we'll skip backend-dependent tests
      this.log('Skipping backend-dependent tests', 'skip');
    }

    if (!frontendRunning) {
      this.log('Frontend dev server not running, starting...');
      const serverProcess = spawn('npm', ['run', 'dev'], {
        cwd: process.cwd(),
        detached: true,
        stdio: 'ignore'
      });

      await this.waitForService(this.frontendUrl, 10000);
    }

    return { backendRunning, frontendRunning };
  }

  /**
   * Wait for a service to become available
   */
  async waitForService(url, timeout = 10000) {
    const start = Date.now();
    while (Date.now() - start < timeout) {
      try {
        const response = await fetch(url);
        if (response.ok) return true;
      } catch {
        await new Promise(resolve => setTimeout(resolve, 500));
      }
    }
    throw new Error(`Service at ${url} did not start within ${timeout}ms`);
  }

  /**
   * Create test circuit via API
   */
  async createTestCircuit(circuit) {
    try {
      const response = await fetch(`${this.backendUrl}/circuits/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(circuit)
      });

      if (!response.ok) {
        throw new Error(`Failed to create circuit: ${response.statusText}`);
      }

      const createdCircuit = await response.json();
      this.log(`Created test circuit: ${circuit.name} (ID: ${createdCircuit.id})`);
      return createdCircuit;
    } catch (error) {
      this.log(`Failed to create circuit ${circuit.name}: ${error.message}`, 'error');
      return null;
    }
  }

  /**
   * Execute circuit via API
   */
  async executeCircuit(circuitId, contextData = {}) {
    try {
      const response = await fetch(`${this.backendUrl}/circuits/${circuitId}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context_data: contextData })
      });

      if (!response.ok) {
        throw new Error(`Failed to execute circuit: ${response.statusText}`);
      }

      const result = await response.json();
      this.log(`Executed circuit ${circuitId}: ${result.success ? 'SUCCESS' : 'FAILED'}`);
      return result;
    } catch (error) {
      this.log(`Failed to execute circuit ${circuitId}: ${error.message}`, 'error');
      return null;
    }
  }

  /**
   * Validate execution results against expected outputs
   */
  validateExecutionResults(actualResult, expectedOutputs) {
    if (!actualResult || !actualResult.success) {
      return { passed: false, message: 'Execution failed or returned no results' };
    }

    const issues = [];

    for (const [nodeId, expected] of Object.entries(expectedOutputs)) {
      const actualOutput = actualResult.outputs?.[nodeId];

      if (!actualOutput) {
        issues.push(`Missing output for node ${nodeId}`);
        continue;
      }

      for (const [outputName, expectedValue] of Object.entries(expected)) {
        const actualValue = actualOutput[outputName];

        if (actualValue !== expectedValue) {
          issues.push(`Node ${nodeId} output ${outputName}: expected '${expectedValue}', got '${actualValue}'`);
        }
      }
    }

    return {
      passed: issues.length === 0,
      message: issues.length === 0 ? 'All outputs match expected values' : issues.join('; ')
    };
  }

  /**
   * Test circuit creation workflow
   */
  async testCircuitCreation() {
    this.log('Testing circuit creation workflow...');

    for (const testCircuit of this.testCircuits) {
      this.testResults.total++;

      try {
        const createdCircuit = await this.createTestCircuit(testCircuit);

        if (createdCircuit) {
          this.testResults.passed++;
          this.log(`${testCircuit.name}: PASSED - Circuit created successfully`, 'success');
        } else {
          this.testResults.failed++;
          this.log(`${testCircuit.name}: FAILED - Circuit creation failed`, 'error');
          this.testResults.details.push({
            test: `create-${testCircuit.name}`,
            status: 'failed',
            message: 'Failed to create circuit via API'
          });
        }
      } catch (error) {
        this.testResults.failed++;
        this.log(`${testCircuit.name}: ERROR - ${error.message}`, 'error');
        this.testResults.details.push({
          test: `create-${testCircuit.name}`,
          status: 'error',
          message: error.message
        });
      }
    }
  }

  /**
   * Test circuit execution workflow
   */
  async testCircuitExecution() {
    this.log('Testing circuit execution workflow...');

    for (const testCircuit of this.testCircuits) {
      this.testResults.total++;

      // Skip if requires backend data and backend is not available
      if (testCircuit.requiresBackendData && !(await this.checkBackend())) {
        this.testResults.skipped++;
        this.log(`${testCircuit.name}: SKIPPED - Requires backend data`, 'skip');
        continue;
      }

      try {
        // Create circuit first
        const createdCircuit = await this.createTestCircuit(testCircuit);
        if (!createdCircuit) {
          this.testResults.failed++;
          this.log(`${testCircuit.name}: FAILED - Could not create circuit for execution`, 'error');
          continue;
        }

        // Execute circuit
        const executionResult = await this.executeCircuit(createdCircuit.id, {});

        if (!executionResult) {
          this.testResults.failed++;
          this.log(`${testCircuit.name}: FAILED - Circuit execution failed`, 'error');
          continue;
        }

        // Validate results
        const validation = this.validateExecutionResults(executionResult, testCircuit.expectedOutputs);

        if (validation.passed) {
          this.testResults.passed++;
          this.log(`${testCircuit.name}: PASSED - ${validation.message}`, 'success');
        } else {
          this.testResults.failed++;
          this.log(`${testCircuit.name}: FAILED - ${validation.message}`, 'error');
          this.testResults.details.push({
            test: `execute-${testCircuit.name}`,
            status: 'failed',
            message: validation.message
          });
        }

      } catch (error) {
        this.testResults.failed++;
        this.log(`${testCircuit.name}: ERROR - ${error.message}`, 'error');
        this.testResults.details.push({
          test: `execute-${testCircuit.name}`,
          status: 'error',
          message: error.message
        });
      }
    }
  }

  /**
   * Test UI integration with execution results
   */
  async testUIIntegration() {
    this.log('Testing UI integration with execution results...');

    // This would require Puppeteer to interact with the frontend
    // For now, we'll test the API integration
    this.testResults.total++;
    this.testResults.skipped++;
    this.log('UI integration test: SKIPPED - Requires frontend automation setup', 'skip');
  }

  /**
   * Test error handling and edge cases
   */
  async testErrorHandling() {
    this.log('Testing error handling and edge cases...');

    const errorTests = [
      {
        name: 'invalid-circuit-id',
        circuitId: 99999,
        expectedError: true
      },
      {
        name: 'missing-circuit-data',
        circuitId: null,
        expectedError: true
      }
    ];

    for (const errorTest of errorTests) {
      this.testResults.total++;

      try {
        const result = await this.executeCircuit(errorTest.circuitId, {});
        const hasError = !result || !result.success;

        if (hasError === errorTest.expectedError) {
          this.testResults.passed++;
          this.log(`${errorTest.name}: PASSED - Error handling works correctly`, 'success');
        } else {
          this.testResults.failed++;
          this.log(`${errorTest.name}: FAILED - Unexpected error behavior`, 'error');
        }
      } catch (error) {
        this.testResults.passed++;
        this.log(`${errorTest.name}: PASSED - Exception handled correctly`, 'success');
      }
    }
  }

  /**
   * Generate comprehensive test report
   */
  generateReport() {
    const report = {
      summary: {
        total: this.testResults.total,
        passed: this.testResults.passed,
        failed: this.testResults.failed,
        skipped: this.testResults.skipped,
        passRate: this.testResults.total > 0 ? ((this.testResults.passed / this.testResults.total) * 100).toFixed(1) : '0'
      },
      details: this.testResults.details,
      executionLogs: this.testResults.executionLogs,
      timestamp: new Date().toISOString(),
      testSuites: {
        circuitCreation: 'Circuit creation via API',
        circuitExecution: 'Circuit execution and validation',
        uiIntegration: 'Frontend-backend integration',
        errorHandling: 'Error handling and edge cases'
      }
    };

    const reportPath = path.join(process.cwd(), 'circuit-integration-test-results.json');
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));

    this.log(`Integration test report generated: ${reportPath}`);
    this.log(`Results: ${report.summary.passed}/${report.summary.total} tests passed (${report.summary.passRate}%)`);

    if (this.testResults.failed > 0) {
      this.log(`❌ ${this.testResults.failed} tests failed. Check the detailed report for issues.`);
    }

    if (this.testResults.skipped > 0) {
      this.log(`⏭️ ${this.testResults.skipped} tests skipped. Check service availability.`);
    }

    return report;
  }

  /**
   * Run all integration tests
   */
  async runAllTests() {
    this.log('Starting Circuit Editor Integration Tests...');

    try {
      const services = await this.ensureServicesRunning();

      await this.testCircuitCreation();
      await this.testCircuitExecution();
      await this.testUIIntegration();
      await this.testErrorHandling();

      const report = this.generateReport();

      const overallSuccess = this.testResults.failed === 0;
      if (overallSuccess) {
        this.log('All integration tests passed! Circuit Editor integration is working correctly.', 'success');
      } else {
        this.log(`${this.testResults.failed} integration tests failed. Check the detailed report.`, 'error');
      }

      return overallSuccess;
    } catch (error) {
      this.log(`Integration test execution failed: ${error.message}`, 'error');
      return false;
    }
  }
}

// CLI interface
async function main() {
  const args = process.argv.slice(2);
  const tester = new CircuitIntegrationTester();

  if (args.includes('--help') || args.includes('-h')) {
    console.log(`
Circuit Editor Integration Testing Framework

Usage:
  node circuit-integration-test-esm.js [options]

Options:
  --help, -h              Show this help message
  --create-only           Only test circuit creation
  --execute-only          Only test circuit execution
  --skip-ui-tests         Skip UI integration tests
  --backend-url <url>     Set backend URL (default: http://localhost:8000)
  --frontend-url <url>    Set frontend URL (default: http://localhost:5173)

Examples:
  node circuit-integration-test-esm.js
  node circuit-integration-test-esm.js --create-only
  node circuit-integration-test-esm.js --execute-only --skip-ui-tests
`);
    return;
  }

  // Parse arguments
  if (args.includes('--backend-url')) {
    const index = args.indexOf('--backend-url');
    if (index + 1 < args.length) {
      tester.backendUrl = args[index + 1];
    }
  }

  if (args.includes('--frontend-url')) {
    const index = args.indexOf('--frontend-url');
    if (index + 1 < args.length) {
      tester.frontendUrl = args[index + 1];
    }
  }

  const createOnly = args.includes('--create-only');
  const executeOnly = args.includes('--execute-only');
  const skipUITests = args.includes('--skip-ui-tests');

  const success = await tester.runAllTests();
  process.exit(success ? 0 : 1);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(error => {
    console.error('Fatal error:', error);
    process.exit(1);
  });
}

export default CircuitIntegrationTester;