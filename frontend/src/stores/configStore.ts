import { create } from 'zustand';
import { getConfig, updateConfig, getModels } from '../api.js';

export interface ConfigState {
  // Authentication and providers
  activeProvider: string;
  providers: Record<string, any>;
  configDraft: any;

  // Model management
  modelList: any[];
  loadingModels: boolean;

  // Debug settings
  debugFlags: { log_prompts: boolean; log_responses: boolean };

  // User persona
  userPersona: { name: string; description: string };

  // Token settings
  maxTokens: number;

  // Actions
  setActiveProvider: (provider: string) => void;
  setProviders: (providers: Record<string, any>) => void;
  setConfigDraft: (draft: any) => void;

  setModelList: (models: any[]) => void;
  setLoadingModels: (loading: boolean) => void;

  setUserPersona: (persona: { name: string; description: string }) => void;
  setDebugFlags: (flags: { log_prompts: boolean; log_responses: boolean }) => void;
  setMaxTokens: (tokens: number) => void;

  // Async actions
  loadConfig: () => Promise<void>;
  updateMaxTokens: (tokens: number) => Promise<void>;
  updateDebugFlags: (flags: { log_prompts: boolean; log_responses: boolean }) => Promise<void>;
  updateUserPersona: (persona: { name: string; description: string }) => Promise<void>;
  updateProviderConfig: (provider: string, config: any) => Promise<void>;
  loadModels: () => Promise<void>;
  loadModelsForProvider: (provider: string) => Promise<void>;

  // Structured output settings
  structuredOutput: boolean;
  setStructuredOutput: (enabled: boolean) => void;
  updateStructuredOutput: (enabled: boolean) => Promise<void>;
}

export const useConfigStore = create<ConfigState>((set, get) => ({
  // Initial state
  activeProvider: 'echo',
  providers: {},
  configDraft: {
    api_key: '',
    api_base: '',
    model: '',
    temperature: 0.7
  },

  modelList: [],
  loadingModels: false,

  debugFlags: { log_prompts: false, log_responses: false },
  userPersona: { name: '', description: '' },
  maxTokens: 2048,

  structuredOutput: false,

  // Setters
  setActiveProvider: (activeProvider) => set({ activeProvider }),
  setProviders: (providers) => set({ providers }),
  setConfigDraft: (configDraft) => set({ configDraft }),

  setModelList: (modelList) => set({ modelList }),
  setLoadingModels: (loadingModels) => set({ loadingModels }),

  setUserPersona: (userPersona) => set({ userPersona }),
  setDebugFlags: (debugFlags) => set({ debugFlags }),
  setMaxTokens: (maxTokens) => set({ maxTokens }),

  setStructuredOutput: (structuredOutput) => set({ structuredOutput }),

  // Async actions
  loadConfig: async () => {
    try {
      const config = await getConfig();

      // Update provider settings
      set({
        activeProvider: config.active_provider || 'echo',
        providers: config.providers || {},
        debugFlags: config.debug || { log_prompts: false, log_responses: false },
        userPersona: config.user_persona || { name: '', description: '' },
        maxTokens: config.max_context_tokens || 2048,
        structuredOutput: config.structured_output || false,
      });

      // Set up draft for current provider
      const current = config.providers?.[config.active_provider] || {};
      set({
        configDraft: {
          api_key: '',
          api_base: current.api_base || '',
          model: current.model || '',
          temperature: current.temperature ?? 0.7,
        }
      });

      // Load models for active provider
      await get().loadModelsForProvider(config.active_provider);
    } catch (err: any) {
      console.warn('Failed to load config:', err);
    }
  },

  updateMaxTokens: async (tokens: number) => {
    try {
      await updateConfig({ max_context_tokens: tokens });
      set({ maxTokens: tokens });
    } catch (err: any) {
      console.error('Failed to update max tokens:', err);
      throw err;
    }
  },

  updateDebugFlags: async (flags: { log_prompts: boolean; log_responses: boolean }) => {
    try {
      await updateConfig({ debug: flags });
      set({ debugFlags: flags });
    } catch (err: any) {
      console.error('Failed to update debug flags:', err);
      throw err;
    }
  },

  updateUserPersona: async (persona: { name: string; description: string }) => {
    try {
      await updateConfig({ user_persona: persona });
      set({ userPersona: persona });
    } catch (err: any) {
      console.error('Failed to update user persona:', err);
      throw err;
    }
  },

  updateStructuredOutput: async (enabled: boolean) => {
    try {
      await updateConfig({ structured_output: enabled });
      set({ structuredOutput: enabled });
    } catch (err: any) {
      console.error('Failed to update structured output:', err);
      throw err;
    }
  },

  updateProviderConfig: async (provider: string, config: any) => {
    try {
      await updateConfig({ active_provider: provider, providers: { [provider]: config } });
      set(state => ({
        providers: {
          ...state.providers,
          [provider]: config
        },
        configDraft: config
      }));
    } catch (err: any) {
      console.error('Failed to update provider config:', err);
      throw err;
    }
  },

  loadModels: async () => {
    const activeProvider = get().activeProvider;
    await get().loadModelsForProvider(activeProvider);
  },

  loadModelsForProvider: async (provider: string) => {
    try {
      set({ loadingModels: true });
      const { models } = await getModels(provider);
      set({
        modelList: models || [],
        loadingModels: false
      });
    } catch (err: any) {
      console.error('Failed to load models:', err);
      set({
        modelList: [],
        loadingModels: false
      });
    }
  }
}));