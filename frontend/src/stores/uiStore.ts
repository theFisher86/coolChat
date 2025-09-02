import { create } from 'zustand';

export interface UIState {
  // Panel/Modal visibility states
  showConfig: boolean;
  showCharacters: boolean;
  showChats: boolean;
  showTools: boolean;
  showLorebooks: boolean;
  phoneOpen: boolean;

  // UI configuration
  settingsTab: string;
  phoneUrl: string;
  phoneStyle: string;

  // Tool suggestions
  suggestOpen: boolean;
  suggests: any[];
  showSOHint: boolean;
  suppressSOHint: boolean;

  // Lorebook editor
  expandedEntries: Record<string, boolean>;

  // Character editor
  editorOpen: boolean;
  editingChar: any;

  // Theme state
  appTheme: {
    background_animations: string[];
    [key: string]: any;
  };

  // Actions
  setShowConfig: (show: boolean) => void;
  setShowCharacters: (show: boolean) => void;
  setShowChats: (show: boolean) => void;
  setShowTools: (show: boolean) => void;
  setShowLorebooks: (show: boolean) => void;
  setPhoneOpen: (show: boolean) => void;

  setSettingsTab: (tab: string) => void;
  setPhoneUrl: (url: string) => void;
  setPhoneStyle: (style: string) => void;

  setSuggestOpen: (show: boolean) => void;
  setSuggests: (suggests: any[]) => void;
  setShowSOHint: (show: boolean) => void;
  setSuppressSOHint: (suppress: boolean) => void;

  setExpandedEntries: (entries: Record<string, boolean>) => void;
  toggleExpandedEntry: (id: string) => void;

  setEditorOpen: (show: boolean) => void;
  setEditingChar: (character: any) => void;

  // Utilities
  closeAllPanels: () => void;
  togglePanel: (panelName: keyof UIState, value?: boolean) => void;
  applyPluginAnimations: (animations: string[]) => void;
  setAppTheme: (theme: any) => void;
  updateAppTheme: (theme: any) => void;
}

export const useUIStore = create<UIState>((set, get) => ({
  // Initial state
  showConfig: false,
  showCharacters: false,
  showChats: false,
  showTools: false,
  showLorebooks: false,
  phoneOpen: false,

  settingsTab: 'connection',
  phoneUrl: 'https://example.org',
  phoneStyle: 'classic',

  suggestOpen: false,
  suggests: [],
  showSOHint: false,
  suppressSOHint: false,

  expandedEntries: {},
  editorOpen: false,
  editingChar: null,
  appTheme: {
    background_animations: []
  },

  // Setters
  setShowConfig: (show) => set({ showConfig: show }),
  setShowCharacters: (show) => set({ showCharacters: show }),
  setShowChats: (show) => set({ showChats: show }),
  setShowTools: (show) => set({ showTools: show }),
  setShowLorebooks: (show) => set({ showLorebooks: show }),
  setPhoneOpen: (show) => set({ phoneOpen: show }),

  setSettingsTab: (tab) => set({ settingsTab: tab }),
  setPhoneUrl: (url) => set({ phoneUrl: url }),
  setPhoneStyle: (style) => set({ phoneStyle: style }),

  setSuggestOpen: (show) => set({ suggestOpen: show }),
  setSuggests: (suggests) => set({ suggests }),
  setShowSOHint: (show) => set({ showSOHint: show }),
  setSuppressSOHint: (suppress) => set({ suppressSOHint: suppress }),

  setExpandedEntries: (entries) => set({ expandedEntries: entries }),
  toggleExpandedEntry: (id: string) =>
    set((state) => ({
      expandedEntries: {
        ...state.expandedEntries,
        [id]: !state.expandedEntries[id]
      }
    })),

  setEditorOpen: (show) => set({ editorOpen: show }),
  setEditingChar: (character) => set({ editingChar: character }),

  // Utility functions
  closeAllPanels: () =>
    set({
      showConfig: false,
      showCharacters: false,
      showChats: false,
      showTools: false,
      showLorebooks: false,
    }),

  togglePanel: (panelName, value) => {
    const currentValue = get()[panelName] as boolean;
    const newValue = value !== undefined ? value : !currentValue;

    // Close other panels when opening a new one
    if (newValue && panelName !== 'phoneOpen') {
      get().closeAllPanels();
    }

    set({ [panelName]: newValue } as Partial<UIState>);
  },

  applyPluginAnimations: (animations) => {
    if (!animations || !Array.isArray(animations)) return;
    set((state) => ({
      ...state,
      appTheme: {
        ...state.appTheme,
        background_animations: animations.map((anim: any) => typeof anim === 'string' ? anim : anim.id).filter(Boolean)
      }
    }));
  },

  setAppTheme: (theme) => {
    set((state) => ({
      ...state,
      appTheme: { ...state.appTheme, ...theme }
    }));
  },

  updateAppTheme: (theme) => {
    set((state) => ({
      ...state,
      appTheme: { ...state.appTheme, ...theme }
    }));
  }
}));