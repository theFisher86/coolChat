import { create } from 'zustand';

export interface Theme {
  primary?: string;
  secondary?: string;
  text1?: string;
  text2?: string;
  highlight?: string;
  lowlight?: string;
  phone_style?: string;
  background_animations?: string[];
}

export interface ThemeState {
  // Current theme
  appTheme: Theme;
  availableThemes: Theme[];

  // Theme management
  currentThemeName: string | null;
  customThemes: Record<string, Theme>;

  // Actions
  setAppTheme: (theme: Theme) => void;
  updateThemeColors: (colors: Partial<Theme>) => void;
  setPhoneStyle: (style: string) => void;

  // Animations management
  addBackgroundAnimation: (animationId: string) => void;
  removeBackgroundAnimation: (animationId: string) => void;
  setBackgroundAnimations: (animations: string[]) => void;

  // Theme persistence
  saveCustomTheme: (name: string, theme: Theme) => void;
  deleteCustomTheme: (name: string) => void;
  loadCustomTheme: (name: string) => void;

  // Theme sharing
  exportTheme: () => string;
  importTheme: (themeJson: string) => void;

  // Utilities
  applyTheme: (theme: Theme) => void;
  resetTheme: () => void;
}

const DEFAULT_THEME: Theme = {
  primary: '#2563eb',
  secondary: '#374151',
  text1: '#e5e7eb',
  text2: '#cbd5e1',
  highlight: '#10b981',
  lowlight: '#111827',
  phone_style: 'classic',
  background_animations: []
};

export const useThemeStore = create<ThemeState>((set, get) => ({
  // Initial state
  appTheme: DEFAULT_THEME,
  availableThemes: [DEFAULT_THEME],
  currentThemeName: null,
  customThemes: {},

  // Set current theme
  setAppTheme: (appTheme) => {
    set({ appTheme });
    get().applyTheme(appTheme);
  },

  // Update specific colors
  updateThemeColors: (colors) => {
    set(state => ({
      appTheme: { ...state.appTheme, ...colors }
    }));
    get().applyTheme(get().appTheme);
  },

  // Set phone style
  setPhoneStyle: (phone_style) => {
    set(state => ({
      appTheme: { ...state.appTheme, phone_style }
    }));
  },

  // Animation helpers
  addBackgroundAnimation: (animationId) => {
    set(state => ({
      appTheme: {
        ...state.appTheme,
        background_animations: [
          ...(state.appTheme.background_animations || []),
          animationId
        ].filter((id, index, arr) => arr.indexOf(id) === index) // Remove duplicates
      }
    }));
  },

  removeBackgroundAnimation: (animationId) => {
    set(state => ({
      appTheme: {
        ...state.appTheme,
        background_animations: (state.appTheme.background_animations || [])
          .filter(id => id !== animationId)
      }
    }));
  },

  setBackgroundAnimations: (animations) => {
    set(state => ({
      appTheme: {
        ...state.appTheme,
        background_animations: animations
      }
    }));
  },

  // Theme persistence
  saveCustomTheme: (name, theme) => {
    set(state => ({
      customThemes: {
        ...state.customThemes,
        [name]: { ...theme }
      }
    }));

    // Save to localStorage
    try {
      const saved = localStorage.getItem('coolchat-themes') || '{}';
      const themes = JSON.parse(saved);
      themes[name] = theme;
      localStorage.setItem('coolchat-themes', JSON.stringify(themes));
    } catch (err) {
      console.warn('Failed to save theme to localStorage:', err);
    }
  },

  deleteCustomTheme: (name) => {
    set(state => {
      const customThemes = { ...state.customThemes };
      delete customThemes[name];

      // Remove from localStorage
      try {
        const saved = localStorage.getItem('coolchat-themes') || '{}';
        const themes = JSON.parse(saved);
        delete themes[name];
        localStorage.setItem('coolchat-themes', JSON.stringify(themes));
      } catch (err) {
        console.warn('Failed to delete theme from localStorage:', err);
      }

      return { customThemes };
    });
  },

  loadCustomTheme: (name) => {
    const theme = get().customThemes[name];
    if (theme) {
      get().setAppTheme(theme);
      set({ currentThemeName: name });
    } else {
      console.warn('Theme not found:', name);
    }
  },

  // Export/Import
  exportTheme: () => {
    const theme = get().appTheme;
    const name = get().currentThemeName || 'Exported Theme';
    return JSON.stringify({
      name,
      theme,
      exportedAt: new Date().toISOString(),
      version: '1.0'
    }, null, 2);
  },

  importTheme: (themeJson) => {
    try {
      const { name, theme } = JSON.parse(themeJson);
      if (theme && typeof theme === 'object') {
        get().saveCustomTheme(name, theme);
      }
    } catch (err) {
      console.error('Failed to import theme:', err);
      throw new Error('Invalid theme format');
    }
  },

  // Apply theme to CSS variables
  applyTheme: (theme) => {
    const root = document.documentElement.style;

    if (theme.primary) root.setProperty('--primary', theme.primary);
    if (theme.secondary) root.setProperty('--panel', theme.secondary);
    if (theme.text1) root.setProperty('--text', theme.text1);
    if (theme.text2) root.setProperty('--muted', theme.text2);
    if (theme.highlight) root.setProperty('--assistant', theme.highlight);
    if (theme.lowlight) root.setProperty('--bg', theme.lowlight);

    // Apply background animations
    const animations = theme.background_animations || [];
    const event = new CustomEvent('coolchat:themeUpdate', {
      detail: {
        ...theme,
        background_animations: animations
      }
    });
    window.dispatchEvent(event);
  },

  // Reset to default theme
  resetTheme: () => {
    get().setAppTheme(DEFAULT_THEME);
    set({ currentThemeName: null });
  }
}));