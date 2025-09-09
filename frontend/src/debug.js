/**
 * Debug utility module for CoolChat frontend.
 *
 * Loads and manages debug configurations from debug.json file.
 */
import { API_BASE } from './api.js';

class DebugLogger {
  constructor() {
    this.config = null;
    this.lastConfigCheck = 0;
    this.configCacheTime = 5000; // 5 seconds
    this.loadConfig();
  }

  // For frontend: Fetch debug config from root directory
  async loadConfig() {
    const now = Date.now();

    // Use cached config if recent enough
    if (this.config && now - this.lastConfigCheck < this.configCacheTime) {
      return await this.config;
    }

    try {
      const response = await fetch(`${API_BASE}/debug.json`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      this.config = await response.json();
      this.lastConfigCheck = now;
    } catch (error) {
      // Warning to avoid spam
      if (!this.config) {
        console.warn('Failed to load debug.json - using defaults');
      }
      // Default config if file can't be loaded
      this.config = {
        "frontend": {
          "tool_parsing": true,
          "llm_responses": true,
          "api_calls": false,
          "store_actions": false,
          "component_render": false,
          "performance": false
        },
        "enabled": true
      };
    }

    return this.config;
  }

  async isEnabled(category) {
    const config = await this.loadConfig();
    if (!config || !config.enabled) {
      return false;
    }

    const frontendConfig = config.frontend || {};
    return frontendConfig[category] === true;
  }

  async log(category, message, ...args) {
    if (await this.isEnabled(category)) {
      console.log(`[DEBUG ${category.toUpperCase()}] ${message}`, ...args);
    }
  }

  async debugToolParsing(message, ...args) {
    await this.log('tool_parsing', message, ...args);
  }

  async debugLLMResponses(message, ...args) {
    await this.log('llm_responses', message, ...args);
  }

  async debugAPICalls(message, ...args) {
    await this.log('api_calls', message, ...args);
  }

  async debugStoreActions(message, ...args) {
    await this.log('store_actions', message, ...args);
  }

  async debugComponentRender(message, ...args) {
    await this.log('component_render', message, ...args);
  }

  async debugPerformance(message, ...args) {
    await this.log('performance', message, ...args);
  }
}

// Global instance
let _debug_logger = null;

export function getDebugLogger() {
  if (!_debug_logger) {
    _debug_logger = new DebugLogger();
  }
  return _debug_logger;
}

export function debugLog(category, message, ...args) {
  const logger = getDebugLogger();
  return logger.log(category, message, ...args);
}

// Convenience functions
export const debugToolParsing = (message, ...args) => {
  const logger = getDebugLogger();
  return logger.debugToolParsing(message, ...args);
};

export const debugLLMResponses = (message, ...args) => {
  const logger = getDebugLogger();
  return logger.debugLLMResponses(message, ...args);
};

export const debugAPICalls = (message, ...args) => {
  const logger = getDebugLogger();
  return logger.debugAPICalls(message, ...args);
};

export const debugStoreActions = (message, ...args) => {
  const logger = getDebugLogger();
  return logger.debugStoreActions(message, ...args);
};

export const debugComponentRender = (message, ...args) => {
  const logger = getDebugLogger();
  return logger.debugComponentRender(message, ...args);
};

export const debugPerformance = (message, ...args) => {
  const logger = getDebugLogger();
  return logger.debugPerformance(message, ...args);
};