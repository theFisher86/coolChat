import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import {
  listLorebooks,
  getLorebook,
  createLorebook,
  updateLorebook,
  deleteLorebook,
  createLoreEntry,
  updateLoreEntry,
  deleteLoreEntry,
  searchLorebooks,
  bulkCreateLoreEntries,
  linkCharacterToLorebook,
  unlinkCharacterFromLorebook,
  getCharacterLorebooks,
  injectLoreContext,
  importLorebook
} from '../api.js';

export interface Lorebook {
  id: number;
  name: string;
  description: string;
  entry_count: number;
  created_at: string;
  updated_at: string;
}

export interface LoreEntry {
  id: number;
  title: string;
  content: string;
  keywords: string[];
  secondary_keywords: string[];
  logic: 'AND ANY' | 'AND ALL' | 'NOT ANY' | 'NOT ALL';
  trigger: number;
  order: number;
  created_at: string;
  updated_at: string;
}

export interface SearchResult {
  id: number;
  title: string;
  content: string;
  lorebook_name: string;
  lorebook_id: number;
  keywords: string[];
  secondary_keywords: string[];
  logic: string;
  trigger: number;
  order: number;
  score: number;
}

export interface BulkOperation {
  type: 'update' | 'delete' | 'tag';
  data?: any;
}

interface LorebookStoreState {
  // Lorebooks
  lorebooks: Lorebook[];
  selectedLorebook: Lorebook | null;
  lorebookLoading: boolean;

  // Lore entries
  loreEntries: LoreEntry[];
  selectedEntries: Set<number>;
  entryLoading: boolean;

  // Pagination
  currentPage: number;
  pageSize: number;
  totalEntries: number;
  hasMoreEntries: boolean;

  // Search
  searchQuery: string;
  searchResults: SearchResult[];
  searchFilters: {
    keywords: string[];
    secondary_keywords: string[];
    logic?: string;
  };
  isSearching: boolean;

  // UI State
  showEditor: boolean;
  editingEntry: LoreEntry | null;
  showBulkOps: boolean;
  showImport: boolean;

  // Character Linking
  linkedCharacters: any[];
  availableCharacters: any[];

  // Cache
  cache: Map<string, any>;

  // Actions
  // Lorebook CRUD
  fetchLorebooks: () => Promise<void>;
  selectLorebook: (lorebook: Lorebook | null) => void;
  createLorebookAction: (data: { name: string; description?: string; entries?: any[] }) => Promise<Lorebook>;
  updateLorebookAction: (id: number, data: any) => Promise<void>;
  deleteLorebookAction: (id: number) => Promise<void>;

  // Entry CRUD
  refreshLoreEntries: () => Promise<void>;
  loadLoreEntriesPaginated: (page?: number, pageSize?: number) => Promise<void>;
  createLoreEntryAction: (data: any) => Promise<LoreEntry>;
  updateLoreEntryAction: (id: number, data: any) => Promise<void>;
  deleteLoreEntryAction: (id: number, updateLocal?: boolean) => Promise<void>;

  // Search
  searchLoreAction: (query: string, filters?: any) => Promise<void>;
  clearSearch: () => void;

  // Bulk Operations
  toggleEntrySelection: (id: number) => void;
  selectAllEntries: () => void;
  clearSelection: () => void;
  bulkUpdateEntries: (operation: BulkOperation) => Promise<void>;
  bulkDeleteEntries: () => Promise<void>;

  // Character Linking
  loadLinkedCharacters: (characterId: number) => Promise<void>;
  linkCharacterAction: (characterId: number) => Promise<void>;
  unlinkCharacterAction: (characterId: number) => Promise<void>;

  // Import/Export
  importLorebookAction: (file: File) => Promise<void>;

  // Context Injection
  injectContextForChat: (chatHistory: string[], options?: any) => Promise<any>;

  // UI State
  setShowEditor: (show: boolean, entry?: LoreEntry | null) => void;
  setShowBulkOps: (show: boolean) => void;
  setShowImport: (show: boolean) => void;

  // Cache
  getCached: (key: string) => any;
  setCached: (key: string, value: any) => void;

  // Utilities
  reset: () => void;
}

export const useLorebookStore = create<LorebookStoreState>()(
  devtools(
    (set, get) => ({
      // Initial state
      lorebooks: [],
      selectedLorebook: null,
      lorebookLoading: false,

      loreEntries: [],
      selectedEntries: new Set(),
      entryLoading: false,

      currentPage: 0,
      pageSize: 50,
      totalEntries: 0,
      hasMoreEntries: false,

      searchQuery: '',
      searchResults: [],
      searchFilters: {
        keywords: [],
        secondary_keywords: [],
      },
      isSearching: false,

      showEditor: false,
      editingEntry: null,
      showBulkOps: false,
      showImport: false,

      linkedCharacters: [],
      availableCharacters: [],

      cache: new Map(),

      // Lorebook CRUD
      fetchLorebooks: async () => {
        console.log('[DEBUG] fetchLorebooks called');
        try {
          set({ lorebookLoading: true });
          const response = await listLorebooks();
          const lorebooks = (response && response.lorebooks) ? response.lorebooks : [];
          console.log('[DEBUG] Fetch completed, found', lorebooks.length, 'lorebooks');
          set({ lorebooks, lorebookLoading: false });

          // Auto-select first lorebook if available and none selected
          if (lorebooks.length > 0 && !get().selectedLorebook) {
            get().selectLorebook(lorebooks[0]);
          }
        } catch (error) {
          console.error('Failed to fetch lorebooks:', error);
          set({ lorebookLoading: false });
        }
      },

      selectLorebook: (lorebook) => {
        set({ selectedLorebook: lorebook });
        if (lorebook) {
          get().refreshLoreEntries();
        } else {
          set({ loreEntries: [], totalEntries: 0, currentPage: 0, hasMoreEntries: false });
        }
      },

      createLorebookAction: async (data) => {
        try {
          const newLorebook = await createLorebook({
            name: data.name,
            description: data.description || '',
            entries: data.entries || []
          } as any);
          get().fetchLorebooks(); // Refresh the list
          return newLorebook;
        } catch (error) {
          console.error('Failed to create lorebook:', error);
          throw error;
        }
      },

      updateLorebookAction: async (id, data) => {
        try {
          await updateLorebook(id, data);
          const updatedLorebooks = get().lorebooks.map(lb =>
            lb.id === id ? { ...lb, ...data } : lb
          );
          set({ lorebooks: updatedLorebooks });

          // Update selected lorebook if it's the one being updated
          const selected = get().selectedLorebook;
          if (selected && selected.id === id) {
            set({ selectedLorebook: { ...selected, ...data } });
          }
        } catch (error) {
          console.error('Failed to update lorebook:', error);
          throw error;
        }
      },

      deleteLorebookAction: async (id) => {
        try {
          await deleteLorebook(id);
          const filteredLorebooks = get().lorebooks.filter(lb => lb.id !== id);
          set({ lorebooks: filteredLorebooks });

          // Clear selection if deleted lorebook was selected
          const selected = get().selectedLorebook;
          if (selected && selected.id === id) {
            set({ selectedLorebook: null, loreEntries: [] });
          }
        } catch (error) {
          console.error('Failed to delete lorebook:', error);
          throw error;
        }
      },

      // Entry CRUD
      refreshLoreEntries: async () => {
        const selectedLorebook = get().selectedLorebook;
        if (!selectedLorebook) return;

        try {
          set({ entryLoading: true });
          const data = await getLorebook(selectedLorebook.id);
          const entries = data.entries || [];
          set({
            loreEntries: entries,
            totalEntries: entries.length,
            currentPage: 0,
            hasMoreEntries: false, // For now, we load all entries when selecting a lorebook
            entryLoading: false
          });
        } catch (error) {
          console.error('Failed to refresh lore entries:', error);
          set({ entryLoading: false });
        }
      },

      loadLoreEntriesPaginated: async (page = 0, pageSize = 50) => {
        const selectedLorebook = get().selectedLorebook;
        if (!selectedLorebook) return;

        try {
          set({ entryLoading: true });
          // Note: Current API doesn't support server-side pagination for entries
          // This would need backend changes to implement true pagination
          const data = await getLorebook(selectedLorebook.id);
          const entries = data.entries || [];
          const start = page * pageSize;
          const end = start + pageSize;

          set({
            loreEntries: entries.slice(start, end),
            currentPage: page,
            pageSize,
            totalEntries: entries.length,
            hasMoreEntries: end < entries.length,
            entryLoading: false
          });
        } catch (error) {
          console.error('Failed to load lore entries:', error);
          set({ entryLoading: false });
        }
      },

      createLoreEntryAction: async (data) => {
        try {
          const selectedLorebook = get().selectedLorebook;
          if (!selectedLorebook) {
            throw new Error('No lorebook selected');
          }

          const fullData = { ...data, lorebook_id: selectedLorebook.id };
          const newEntry = await createLoreEntry(fullData);

          // Add to local state
          const currentEntries = get().loreEntries;
          set({
            loreEntries: [...currentEntries, newEntry],
            totalEntries: get().totalEntries + 1
          });

          return newEntry;
        } catch (error) {
          console.error('Failed to create lore entry:', error);
          throw error;
        }
      },

      updateLoreEntryAction: async (id, data) => {
        try {
          await updateLoreEntry(id, data);

          // Update local state
          const currentEntries = get().loreEntries;
          const updatedEntries = currentEntries.map(entry =>
            entry.id === id ? { ...entry, ...data } : entry
          );
          set({ loreEntries: updatedEntries });
        } catch (error) {
          console.error('Failed to update lore entry:', error);
          throw error;
        }
      },

      deleteLoreEntryAction: async (id, updateLocal = true) => {
        try {
          await deleteLoreEntry(id);

          if (updateLocal) {
            const currentEntries = get().loreEntries;
            const filteredEntries = currentEntries.filter(entry => entry.id !== id);
            set({
              loreEntries: filteredEntries,
              totalEntries: get().totalEntries - 1,
              selectedEntries: new Set([...get().selectedEntries].filter(entryId => entryId !== id))
            });
          }
        } catch (error) {
          console.error('Failed to delete lore entry:', error);
          throw error;
        }
      },

      // Search
      searchLoreAction: async (query, filters = {}) => {
        try {
          set({ isSearching: true, searchQuery: query });

          // Determine search endpoint based on filters
          const response = await searchLorebooks(query, 100);

          set({
            searchResults: response.results || [],
            isSearching: false
          });
        } catch (error) {
          console.error('Search failed:', error);
          set({ isSearching: false });
        }
      },

      clearSearch: () => {
        set({
          searchQuery: '',
          searchResults: [],
          searchFilters: { keywords: [], secondary_keywords: [] }
        });
      },

      // Bulk Operations
      toggleEntrySelection: (id) => {
        const selected = new Set(get().selectedEntries);
        if (selected.has(id)) {
          selected.delete(id);
        } else {
          selected.add(id);
        }
        set({ selectedEntries: selected });
      },

      selectAllEntries: () => {
        const allIds = get().loreEntries.map(entry => entry.id);
        const selected = new Set([...allIds].filter(id => !get().selectedEntries.has(id)))

        if (selected.size > 0) {
          // Select all
          const allSet = new Set([...get().selectedEntries, ...allIds]);
          set({ selectedEntries: allSet });
        } else {
          // Deselect all
          set({ selectedEntries: new Set() });
        }
      },

      clearSelection: () => {
        set({ selectedEntries: new Set() });
      },

      bulkUpdateEntries: async (operation) => {
        const selectedIds = Array.from(get().selectedEntries);

        try {
          for (const id of selectedIds) {
            if (operation.type === 'update') {
              await get().updateLoreEntryAction(id, operation.data);
            }
          }

          get().clearSelection();
        } catch (error) {
          console.error('Bulk update failed:', error);
          throw error;
        }
      },

      bulkDeleteEntries: async () => {
        const selectedIds = Array.from(get().selectedEntries);

        try {
          for (const id of selectedIds) {
            await get().deleteLoreEntryAction(id, false); // Don't update local state yet
          }

          // Bulk update local state
          const currentEntries = get().loreEntries;
          const filteredEntries = currentEntries.filter(entry => !selectedIds.includes(entry.id));
          set({
            loreEntries: filteredEntries,
            selectedEntries: new Set(),
            totalEntries: get().totalEntries - selectedIds.length
          });
        } catch (error) {
          console.error('Bulk delete failed:', error);
          throw error;
        }
      },

      // Character Linking
      loadLinkedCharacters: async (characterId) => {
        try {
          const response = await getCharacterLorebooks(characterId);
          set({ linkedCharacters: response.lorebooks || [] });
        } catch (error) {
          console.error('Failed to load linked characters:', error);
          throw error;
        }
      },

      linkCharacterAction: async (characterId) => {
        const selectedLorebook = get().selectedLorebook;
        if (!selectedLorebook) return;

        try {
          await linkCharacterToLorebook(characterId, selectedLorebook.id);
          get().loadLinkedCharacters(characterId);
        } catch (error) {
          console.error('Failed to link character:', error);
          throw error;
        }
      },

      unlinkCharacterAction: async (characterId) => {
        const selectedLorebook = get().selectedLorebook;
        if (!selectedLorebook) return;

        try {
          await unlinkCharacterFromLorebook(characterId, selectedLorebook.id);
          get().loadLinkedCharacters(characterId);
        } catch (error) {
          console.error('Failed to unlink character:', error);
          throw error;
        }
      },

      // Import/Export
      importLorebookAction: async (file) => {
        try {
          await importLorebook(file);
          get().fetchLorebooks(); // Refresh the list
        } catch (error) {
          console.error('Import failed:', error);
          throw error;
        }
      },

      // Context Injection
      injectContextForChat: async (chatHistory, options = {}) => {
        const selectedLorebook = get().selectedLorebook;
        if (!selectedLorebook) {
          throw new Error('No lorebook selected');
        }

        const recentText = chatHistory.slice(-3).join(' ');

        const requestData = {
          session_id: options.sessionId || 'default',
          max_tokens: options.maxTokens || 1000,
          lorebook_ids: selectedLorebook ? [selectedLorebook.id] : [],
          recent_text: recentText
        };

        try {
          const response = await injectLoreContext(requestData);
          return response;
        } catch (error) {
          console.error('Context injection failed:', error);
          throw error;
        }
      },

      // UI State
      setShowEditor: (show, entry = null) => {
        set({ showEditor: show, editingEntry: entry });
      },

      setShowBulkOps: (show) => {
        set({ showBulkOps: show });
      },

      setShowImport: (show) => {
        set({ showImport: show });
      },

      // Cache
      getCached: (key) => {
        return get().cache.get(key);
      },

      setCached: (key, value) => {
        const cache = new Map(get().cache);
        cache.set(key, value);
        set({ cache });
      },

      // Utilities
      reset: () => {
        set({
          selectedLorebook: null,
          loreEntries: [],
          selectedEntries: new Set(),
          currentPage: 0,
          searchQuery: '',
          searchResults: [],
          showEditor: false,
          editingEntry: null,
          showBulkOps: false,
          showImport: false,
          linkedCharacters: [],
          availableCharacters: []
        });
      }
    }),
    { name: 'lorebook-store' }
  )
);