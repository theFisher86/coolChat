#!/usr/bin/env node

/**
 * Example Test Configurations for Frontend UI Testing Methodology
 * Practical examples for testing circuit editor components and functionality
 */

import UITestingMethodology from './test-methodology.js';

class CircuitEditorTestExamples {
  constructor() {
    this.testingMethodology = new UITestingMethodology();
  }

  /**
   * EXAMPLE 1: Test CircuitEditor2 Component Changes
   */
  async testCircuitEditor2Changes() {
    console.log('\n=== EXAMPLE 1: Testing CircuitEditor2 Changes ===');

    // 1. Verify file changes were applied
    const fileChanges = await this.testingMethodology.verifyFileChanges([
      {
        file: 'src/components/circuits/CircuitEditor2.tsx',
        contains: 'export const CircuitEditor2',
        notContains: 'console.log("old debug code")'
      }
    ]);

    // 2. Test component rendering
    const renderingTest = await this.testingMethodology.testComponentRendering('CircuitEditor2', [
      'ReactFlow',
      'Handle',
      'Position.Left',
      'Position.Right',
      'useCircuitStore',
      'BlockNode',
      'nodeTypes',
      'onConnect',
      'onDrop'
    ]);

    return {
      fileChanges,
      renderingTest,
      overallSuccess: fileChanges && renderingTest
    };
  }

  /**
   * EXAMPLE 2: Test Circuit Store Integration
   */
  async testCircuitStoreIntegration() {
    console.log('\n=== EXAMPLE 2: Testing Circuit Store Integration ===');

    // 1. Test store file structure
    const storeStructureTest = await this.testingMethodology.verifyFileChanges([
      {
        file: 'src/stores/circuitStore.ts',
        contains: 'create<CircuitStore>',
        contains: 'export { useCircuitStore }',
        contains: 'interface Circuit',
        contains: 'circuits: Circuit[]'
      }
    ]);

    return {
      storeStructureTest,
      overallSuccess: storeStructureTest
    };
  }

  /**
   * MAIN TEST RUNNER
   */
  async runExample(exampleNumber) {
    console.log(`🚀 Running Testing Methodology Example ${exampleNumber}`);

    try {
      let result;

      switch (exampleNumber) {
        case 1:
          result = await this.testCircuitEditor2Changes();
          break;
        case 2:
          result = await this.testCircuitStoreIntegration();
          break;
        default:
          console.log('❌ Invalid example number. Choose 1-2');
          return;
      }

      console.log(`\n📊 Example ${exampleNumber} Results:`, result);

      if (result && result.overallSuccess !== undefined) {
        console.log(result.overallSuccess ? '✅ Example passed' : '❌ Example failed');
      }

    } catch (error) {
      console.error(`❌ Example ${exampleNumber} failed:`, error.message);
    }
  }
}

// CLI Interface for Examples
if (import.meta.url === `file://${process.argv[1].replace(/\\/g, '/')}`) {
  const args = process.argv.slice(2);
  const exampleNumber = args[0] ? parseInt(args[0]) : null;

  const examples = new CircuitEditorTestExamples();

  if (exampleNumber) {
    examples.runExample(exampleNumber);
  } else {
    console.log('🧪 Frontend UI Testing Methodology - Examples');
    console.log('Usage: node test-examples.js [example-number]');
    console.log('Examples:');
    console.log('  1: Test CircuitEditor2 Changes');
    console.log('  2: Test Circuit Store Integration');
    console.log('');
  }
}

export default CircuitEditorTestExamples;