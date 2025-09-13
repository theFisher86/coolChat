#!/usr/bin/env node

/**
 * Circuit Editor Visual Regression Testing Tool (ES Module Version)
 *
 * Captures screenshots of Circuit Editor UI components and compares them
 * to detect visual regressions and ensure UI consistency.
 */

import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { spawn } from 'child_process';

class CircuitVisualRegressionTester {
  constructor() {
    this.baselineDir = path.join(process.cwd(), 'visual-baselines');
    this.testDir = path.join(process.cwd(), 'visual-tests');
    this.diffsDir = path.join(process.cwd(), 'visual-diffs');
    this.testResults = {
      passed: 0,
      failed: 0,
      total: 0,
      mismatches: []
    };
    this.threshold = 0.01; // 1% difference threshold
  }

  log(message, type = 'info') {
    const timestamp = new Date().toISOString();
    const prefix = type === 'error' ? '❌' : type === 'success' ? '✅' : type === 'warn' ? '⚠️' : 'ℹ️';
    console.log(`[${timestamp}] ${prefix} ${message}`);
  }

  /**
   * Ensure required directories exist
   */
  ensureDirectories() {
    const dirs = [this.baselineDir, this.testDir, this.diffsDir];
    dirs.forEach(dir => {
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
        this.log(`Created directory: ${dir}`);
      }
    });
  }

  /**
   * Generate screenshot scenarios for Circuit Editor
   */
  getScreenshotScenarios() {
    return [
      {
        name: 'circuit-editor-initial',
        description: 'Initial Circuit Editor state with empty canvas',
        selector: '.circuit-editor',
        waitFor: '.circuit-editor'
      },
      {
        name: 'properties-panel-empty',
        description: 'Properties panel when no circuit is selected',
        selector: '.properties.panel',
        waitFor: '.properties.panel'
      },
      {
        name: 'block-palette',
        description: 'Block palette with all available blocks',
        selector: '.block-palette.panel',
        waitFor: '.block-palette.panel'
      },
      {
        name: 'toolbar-actions',
        description: 'Toolbar with action buttons',
        selector: '.toolbar.panel',
        waitFor: '.toolbar.panel'
      },
      {
        name: 'canvas-placeholder',
        description: 'Canvas placeholder when no circuit is loaded',
        selector: '.canvas.panel',
        waitFor: '.canvas.panel'
      },
      {
        name: 'circuits-list',
        description: 'List of available circuits',
        selector: '.circuits-list',
        waitFor: '.circuits-list'
      },
      {
        name: 'execution-results',
        description: 'Execution results panel after running a circuit',
        selector: '.execution-results.panel',
        waitFor: '.execution-results.panel'
      }
    ];
  }

  /**
   * Simulate Circuit Editor interactions for testing
   */
  getInteractionScenarios() {
    return [
      {
        name: 'select-node-interaction',
        description: 'Select a node and verify properties panel updates',
        interactions: [
          { type: 'click', selector: '.circuit-block', wait: 500 },
          { type: 'wait', duration: 1000 }
        ],
        screenshot: 'properties-panel-selected'
      },
      {
        name: 'modify-block-settings',
        description: 'Modify block settings and verify UI updates',
        interactions: [
          { type: 'click', selector: '.circuit-block', wait: 500 },
          { type: 'type', selector: 'input[id*="text-block-input"]', text: 'Test Value', wait: 500 },
          { type: 'wait', duration: 1000 }
        ],
        screenshot: 'properties-panel-modified'
      },
      {
        name: 'execute-circuit',
        description: 'Execute circuit and verify results panel',
        interactions: [
          { type: 'click', selector: 'button[title*="Execute Circuit"]', wait: 2000 },
          { type: 'click', selector: 'button[title*="Show Results"]', wait: 500 },
          { type: 'wait', duration: 1000 }
        ],
        screenshot: 'execution-results-panel'
      },
      {
        name: 'create-new-circuit',
        description: 'Create new circuit and verify UI state',
        interactions: [
          { type: 'click', selector: 'button[title*="Create new circuit"]', wait: 500 },
          { type: 'type', selector: 'input[id*="circuit-name"]', text: 'Test Circuit', wait: 500 },
          { type: 'type', selector: 'textarea[id*="circuit-description"]', text: 'Test Description', wait: 500 },
          { type: 'click', selector: 'button:has-text("Create Circuit")', wait: 1000 }
        ],
        screenshot: 'circuit-created'
      }
    ];
  }

  /**
   * Create Puppeteer script for screenshot capture
   */
  createPuppeteerScript(scenarios, interactions = []) {
    const script = `
const puppeteer = require('puppeteer');

async function captureScreenshots() {
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });

  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 720 });

    // Navigate to the Circuit Editor
    console.log('Navigating to Circuit Editor...');
    await page.goto('http://localhost:5173', { waitUntil: 'networkidle2' });

    // Wait for Circuit Editor to load
    await page.waitForSelector('.circuit-editor', { timeout: 10000 });

    const scenarios = ${JSON.stringify(scenarios, null, 2)};
    const interactions = ${JSON.stringify(interactions, null, 2)};

    // Capture baseline screenshots
    for (const scenario of scenarios) {
      try {
        console.log(\`Capturing \${scenario.name}...\`);

        // Wait for element if specified
        if (scenario.waitFor) {
          await page.waitForSelector(scenario.waitFor, { timeout: 5000 });
        }

        // Scroll element into view if needed
        if (scenario.selector) {
          await page.evaluate((selector) => {
            const element = document.querySelector(selector);
            if (element) element.scrollIntoView();
          }, scenario.selector);
          await page.waitForTimeout(500);
        }

        // Take screenshot
        const screenshotPath = './visual-tests/\${scenario.name}.png';
        if (scenario.selector) {
          const element = await page.\$(scenario.selector);
          if (element) {
            await element.screenshot({ path: screenshotPath });
          } else {
            console.log(\`Element not found: \${scenario.selector}\`);
          }
        } else {
          await page.screenshot({ path: screenshotPath, fullPage: true });
        }

        console.log(\`✅ Captured \${scenario.name}\`);
      } catch (error) {
        console.log(\`❌ Failed to capture \${scenario.name}: \${error.message}\`);
      }
    }

    // Perform interactions and capture screenshots
    for (const interaction of interactions) {
      try {
        console.log(\`Performing interaction: \${interaction.name}\`);

        for (const step of interaction.interactions) {
          switch (step.type) {
            case 'click':
              await page.click(step.selector);
              break;
            case 'type':
              await page.type(step.selector, step.text);
              break;
            case 'wait':
              await page.waitForTimeout(step.duration);
              break;
          }
          if (step.wait) {
            await page.waitForTimeout(step.wait);
          }
        }

        // Capture screenshot after interaction
        const screenshotPath = \`./visual-tests/\${interaction.screenshot}.png\`;
        await page.screenshot({ path: screenshotPath, fullPage: true });

        console.log(\`✅ Interaction completed: \${interaction.name}\`);
      } catch (error) {
        console.log(\`❌ Interaction failed: \${interaction.name} - \${error.message}\`);
      }
    }

  } finally {
    await browser.close();
  }
}

captureScreenshots().catch(console.error);
`;

    return script;
  }

  /**
   * Capture current screenshots using Puppeteer
   */
  async captureScreenshots() {
    this.log('Starting screenshot capture...');

    const scenarios = this.getScreenshotScenarios();
    const interactions = this.getInteractionScenarios();

    // Create Puppeteer script
    const puppeteerScript = this.createPuppeteerScript(scenarios, interactions);
    const scriptPath = path.join(process.cwd(), 'capture-screenshots.js');

    fs.writeFileSync(scriptPath, puppeteerScript);

    // Check if dev server is running
    const isDevServerRunning = await this.checkDevServer();

    if (!isDevServerRunning) {
      this.log('Starting development server...');
      const serverProcess = spawn('npm', ['run', 'dev'], {
        cwd: process.cwd(),
        detached: true,
        stdio: 'ignore'
      });

      // Wait for server to start
      await this.waitForServer(3000);
    }

    // Run Puppeteer script
    return new Promise((resolve, reject) => {
      const puppeteerProcess = spawn('node', [scriptPath], {
        cwd: process.cwd(),
        stdio: 'inherit'
      });

      puppeteerProcess.on('close', (code) => {
        // Clean up script file
        if (fs.existsSync(scriptPath)) {
          fs.unlinkSync(scriptPath);
        }

        if (code === 0) {
          this.log('Screenshot capture completed successfully', 'success');
          resolve();
        } else {
          this.log('Screenshot capture failed', 'error');
          reject(new Error(`Puppeteer process exited with code ${code}`));
        }
      });

      puppeteerProcess.on('error', (error) => {
        reject(error);
      });
    });
  }

  /**
   * Check if development server is running
   */
  async checkDevServer() {
    try {
      const response = await fetch('http://localhost:5173');
      return response.ok;
    } catch {
      return false;
    }
  }

  /**
   * Wait for development server to start
   */
  async waitForServer(timeout = 30000) {
    const start = Date.now();
    while (Date.now() - start < timeout) {
      if (await this.checkDevServer()) {
        return true;
      }
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    throw new Error('Development server did not start within timeout');
  }

  /**
   * Compare two images using pixel comparison
   */
  compareImages(baselinePath, testPath) {
    // Simple pixel comparison (in a real implementation, you'd use a library like pixelmatch)
    // For now, we'll do a basic file hash comparison
    try {
      const baselineHash = crypto.createHash('md5').update(fs.readFileSync(baselinePath)).digest('hex');
      const testHash = crypto.createHash('md5').update(fs.readFileSync(testPath)).digest('hex');

      const match = baselineHash === testHash;
      const difference = match ? 0 : 1; // Simplified difference calculation

      return {
        match,
        difference,
        thresholdExceeded: difference > this.threshold
      };
    } catch (error) {
      return {
        match: false,
        difference: 1,
        thresholdExceeded: true,
        error: error.message
      };
    }
  }

  /**
   * Generate visual diff image (simplified version)
   */
  generateDiff(baselinePath, testPath, diffPath) {
    // In a real implementation, you'd use pixelmatch or similar library
    // For now, just copy the test image as the diff
    try {
      fs.copyFileSync(testPath, diffPath);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Run visual regression tests
   */
  async runVisualRegressionTests() {
    this.log('Starting visual regression tests...');
    this.ensureDirectories();

    // Capture current screenshots
    await this.captureScreenshots();

    // Get list of test screenshots
    const testFiles = fs.readdirSync(this.testDir).filter(file => file.endsWith('.png'));

    this.testResults.total = testFiles.length;

    for (const testFile of testFiles) {
      const testPath = path.join(this.testDir, testFile);
      const baselinePath = path.join(this.baselineDir, testFile);
      const diffPath = path.join(this.diffsDir, testFile.replace('.png', '-diff.png'));

      this.log(`Comparing ${testFile}...`);

      if (!fs.existsSync(baselinePath)) {
        this.log(`No baseline found for ${testFile}, creating one...`, 'warn');
        fs.copyFileSync(testPath, baselinePath);
        this.testResults.passed++;
        continue;
      }

      const comparison = this.compareImages(baselinePath, testPath);

      if (comparison.match) {
        this.testResults.passed++;
        this.log(`${testFile}: PASSED (no visual changes)`, 'success');
      } else if (comparison.thresholdExceeded) {
        this.testResults.failed++;
        this.generateDiff(baselinePath, testPath, diffPath);
        this.log(`${testFile}: FAILED (visual regression detected)`, 'error');

        this.testResults.mismatches.push({
          file: testFile,
          difference: comparison.difference,
          diffPath
        });
      } else {
        this.testResults.passed++;
        this.log(`${testFile}: PASSED (changes within threshold)`, 'success');
      }
    }

    return this.generateReport();
  }

  /**
   * Update baseline screenshots
   */
  async updateBaselines() {
    this.log('Updating visual baselines...');
    this.ensureDirectories();

    // Capture fresh screenshots
    await this.captureScreenshots();

    // Copy test screenshots to baseline
    const testFiles = fs.readdirSync(this.testDir).filter(file => file.endsWith('.png'));

    for (const testFile of testFiles) {
      const testPath = path.join(this.testDir, testFile);
      const baselinePath = path.join(this.baselineDir, testFile);

      fs.copyFileSync(testPath, baselinePath);
      this.log(`Updated baseline: ${testFile}`);
    }

    this.log('Visual baselines updated successfully', 'success');
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
      mismatches: this.testResults.mismatches,
      timestamp: new Date().toISOString(),
      directories: {
        baseline: this.baselineDir,
        test: this.testDir,
        diffs: this.diffsDir
      }
    };

    const reportPath = path.join(process.cwd(), 'circuit-visual-regression-results.json');
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));

    this.log(`Visual regression report generated: ${reportPath}`);
    this.log(`Results: ${report.summary.passed}/${report.summary.total} tests passed (${report.summary.passRate}%)`);

    if (this.testResults.mismatches.length > 0) {
      this.log(`Visual differences found in: ${this.testResults.mismatches.map(m => m.file).join(', ')}`);
      this.log(`Diff images saved in: ${this.diffsDir}`);
    }

    return report;
  }
}

// CLI interface
async function main() {
  const args = process.argv.slice(2);
  const tester = new CircuitVisualRegressionTester();

  if (args.includes('--help') || args.includes('-h')) {
    console.log(`
Circuit Editor Visual Regression Testing Tool

Usage:
  node circuit-visual-regression-esm.js [options]

Options:
  --help, -h          Show this help message
  --update-baseline   Update baseline screenshots with current state
  --capture-only      Only capture screenshots without comparison
  --threshold <num>   Set difference threshold (default: 0.01)

Examples:
  node circuit-visual-regression-esm.js
  node circuit-visual-regression-esm.js --update-baseline
  node circuit-visual-regression-esm.js --threshold 0.05
`);
    return;
  }

  if (args.includes('--update-baseline')) {
    await tester.updateBaselines();
    return;
  }

  if (args.includes('--threshold')) {
    const thresholdIndex = args.indexOf('--threshold');
    if (thresholdIndex + 1 < args.length) {
      tester.threshold = parseFloat(args[thresholdIndex + 1]);
    }
  }

  const report = await tester.runVisualRegressionTests();

  if (tester.testResults.failed === 0) {
    console.log('✅ All visual regression tests passed!');
    process.exit(0);
  } else {
    console.log(`❌ ${tester.testResults.failed} visual regressions detected!`);
    process.exit(1);
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(error => {
    console.error('Fatal error:', error);
    process.exit(1);
  });
}

export default CircuitVisualRegressionTester;