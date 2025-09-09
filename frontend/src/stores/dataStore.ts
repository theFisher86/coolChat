import { create } from 'zustand';
import { listCharacters, deleteCharacter, listLorebooks, updateLoreEntry, getLorebook, API_BASE } from '../api.js';

export interface DataState {
  // Characters
  characters: any[];
  selectedCharacterId: string | null;

  // Lorebooks
  lorebooks: any[];
  selectedLorebook: any;
  loreEntries: any[];
  selectedLorebookId: string | null;

  // User persona
  userPersona: { name: string; description: string };

  // Extensions
  extensions: any[];
  extensionsEnabled: Record<string, boolean>;
  extensionsInitialized: boolean;

  // Actions
  setCharacters: (characters: any[]) => void;
  setSelectedCharacterId: (id: string | null) => void;

  setLorebooks: (lorebooks: any[]) => void;
  setSelectedLorebook: (lorebook: any) => void;
  setLoreEntries: (entries: any[]) => void;
  setSelectedLorebookId: (id: string | null) => void;

  setUserPersona: (persona: { name: string; description: string }) => void;

  setExtensions: (extensions: any[]) => void;
  setExtensionsEnabled: (enabled: Record<string, boolean>) => void;
  setExtensionsInitialized: (initialized: boolean) => void;

  // Async actions
  loadCharacters: () => Promise<void>;
  loadLorebooks: () => Promise<void>;
  loadLoreEntries: (lorebookId: number) => Promise<void>;
  deleteCharacterAction: (id: string) => Promise<void>;
  updateLoreEntry: (entryId: number, data: any) => Promise<void>;
  updateExtensionsEnabled: (enabled: Record<string, boolean>, options?: { persist?: boolean }) => Promise<void>;

  // Utilities
  findCharacterById: (id: string) => any;
  findLorebookById: (id: string) => any;
}

export const useDataStore = create<DataState>((set, get) => ({
  // Initial state
  characters: [],
  selectedCharacterId: null,

  lorebooks: [],
  selectedLorebook: null,
  loreEntries: [],
  selectedLorebookId: null,

  userPersona: { name: 'User', description: '' },

  extensions: [],
  extensionsEnabled: {},
  extensionsInitialized: false,

  // Setters
  setCharacters: (characters) => set({ characters }),
  setSelectedCharacterId: (selectedCharacterId) => set({ selectedCharacterId }),

  setLorebooks: (lorebooks) => set({ lorebooks }),
  setSelectedLorebook: (selectedLorebook) => set({ selectedLorebook }),
  setLoreEntries: (loreEntries) => set({ loreEntries }),
  setSelectedLorebookId: (selectedLorebookId) => set({ selectedLorebookId }),

  setUserPersona: (userPersona) => set({ userPersona }),

  setExtensions: (extensions) => set({ extensions }),
  setExtensionsEnabled: (extensionsEnabled) => set({ extensionsEnabled }),
  setExtensionsInitialized: (extensionsInitialized) => set({ extensionsInitialized }),

  // Async actions
  loadCharacters: async () => {
    try {
      const characters = await listCharacters();
      set({ characters: characters || [] });
    } catch (err: any) {
      console.warn('Failed to load characters:', err);
      // Keep existing data on error
    }
  },

  loadLorebooks: async () => {
    try {
      const lorebooksResponse = await listLorebooks();
      const lorebooks = lorebooksResponse?.lorebooks || [];
      set({ lorebooks });
      // Auto-select first lorebook if available
      if (lorebooks?.length > 0 && !get().selectedLorebook) {
        set({ selectedLorebook: lorebooks[0] });
      }
    } catch (err: any) {
      console.warn('Failed to load lorebooks:', err);
    }
  },

  loadLoreEntries: async (lorebookId: number) => {
    try {
      // Get full lorebook with all entries using the new API endpoint
      const lorebookData = await getLorebook(lorebookId);
      set({ loreEntries: lorebookData.entries || [] });
    } catch (err: any) {
      console.warn('Failed to load lore entries:', err);
      set({ loreEntries: [] });
    }
  },

  deleteCharacterAction: async (id: string) => {
    try {
      await deleteCharacter(id);
      const updatedCharacters = get().characters.filter(char => char.id !== id);
      set({ characters: updatedCharacters });

      // Clear selection if deleted character was selected
      if (get().selectedCharacterId === id) {
        set({ selectedCharacterId: null });
      }
    } catch (err: any) {
      console.error('Failed to delete character:', err);
      throw err;
    }
  },

  updateLoreEntry: async (entryId: number, data: any) => {
    try {
      await updateLoreEntry(entryId, data);
      // Update the local state with the new data
      const currentEntries = get().loreEntries;
      const updatedEntries = currentEntries.map(entry =>
        entry.id === entryId ? { ...entry, ...data } : entry
      );
      set({ loreEntries: updatedEntries });
    } catch (err: any) {
      console.error('Failed to update lore entry:', err);
      throw err;
    }
  },

  updateExtensionsEnabled: async (enabled, options = {}) => {
    const { persist = true } = options;

    try {
      set({ extensionsEnabled: enabled });

      if (persist) {
        // Persist to backend if available
        const response = await fetch(`${API_BASE}/plugins/enabled`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ enabled }),
        });

        if (!response.ok) {
          throw new Error('Failed to persist extensions');
        }
      }
    } catch (err: any) {
      console.error('Failed to update extensions:', err);
      throw err;
    }
  },

  // Utilities
  findCharacterById: (id: string) => {
    return get().characters.find(char => char.id === id) || null;
  },

  findLorebookById: (id: string) => {
    return get().lorebooks.find(lb => lb.id === id) || null;
  }
}));