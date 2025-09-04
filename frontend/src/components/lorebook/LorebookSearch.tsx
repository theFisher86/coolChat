import React, { useState, useCallback } from 'react';
import { SearchResult } from '../../stores/lorebookStore';
import './LorebookStyles.css';

interface LorebookSearchProps {
  onSearch: (query: string) => Promise<void>;
  onClear: () => void;
  isSearching: boolean;
  searchResults: SearchResult[];
}

export const LorebookSearch: React.FC<LorebookSearchProps> = ({
  onSearch,
  onClear,
  isSearching,
  searchResults
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [debounceTimeout, setDebounceTimeout] = useState<number | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [searchFilters, setSearchFilters] = useState({
    keywords: [],
    secondaryKeywords: [],
    logic: 'AND ANY',
    minTrigger: '',
    maxTrigger: '',
    limit: 50
  });

  const debouncedSearch = useCallback((query: string) => {
    if (debounceTimeout) {
      clearTimeout(debounceTimeout);
    }

    const timeout = setTimeout(async () => {
      if (query.trim()) {
        await onSearch(query);
      } else {
        onClear();
      }
    }, 300);

    setDebounceTimeout(timeout);
  }, [onSearch, onClear, debounceTimeout]);

  const handleQueryChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchQuery(value);
    debouncedSearch(value);
  };

  const handleAdvancedSearch = async () => {
    if (searchQuery || searchFilters.keywords.length > 0) {
      await onSearch(searchQuery);
    }
  };

  const clearSearch = () => {
    setSearchQuery('');
    setSearchFilters({
      keywords: [],
      secondaryKeywords: [],
      logic: 'AND ANY',
      minTrigger: '',
      maxTrigger: '',
      limit: 50
    });
    onClear();
  };

  const addKeyword = (type: 'keywords' | 'secondaryKeywords', keyword: string) => {
    if (!keyword.trim()) return;

    setSearchFilters(prev => ({
      ...prev,
      [type]: [...prev[type], keyword.trim()].filter((v, i, arr) => arr.indexOf(v) === i)
    }));
  };

  const removeKeyword = (type: 'keywords' | 'secondaryKeywords', keyword: string) => {
    setSearchFilters(prev => ({
      ...prev,
      [type]: prev[type].filter(k => k !== keyword)
    }));
  };

  return (
    <div className="lorebook-search">
      {/* Basic Search */}
      <div className="search-input-container">
        <div className="search-input-wrapper">
          <input
            type="text"
            placeholder="Search lore entries..."
            value={searchQuery}
            onChange={handleQueryChange}
            className="search-input"
          />
          {searchQuery && (
            <button
              onClick={clearSearch}
              className="clear-search-btn"
              title="Clear search"
            >
              ✕
            </button>
          )}
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className={`advanced-search-btn ${showAdvanced ? 'active' : ''}`}
            title="Advanced search"
          >
            ⚙️
          </button>
        </div>

        {/* Quick Stats */}
        {searchResults.length > 0 && searchQuery && (
          <div className="search-stats">
            Found {searchResults.length} entries matching "{searchQuery}"
          </div>
        )}
      </div>

      {/* Advanced Search Panel */}
      {showAdvanced && (
        <div className="advanced-search-panel">
          <div className="advanced-search-content">
            {/* Keyword Filters */}
            <div className="filter-group">
              <h4>Primary Keywords</h4>
              <div className="keyword-input-group">
                {searchFilters.keywords.map((keyword, index) => (
                  <span key={index} className="keyword-tag">
                    {keyword}
                    <button
                      onClick={() => removeKeyword('keywords', keyword)}
                      className="remove-keyword"
                    >
                      ×
                    </button>
                  </span>
                ))}
                <input
                  type="text"
                  placeholder="Add keyword..."
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      addKeyword('keywords', (e.target as HTMLInputElement).value);
                      (e.target as HTMLInputElement).value = '';
                    }
                  }}
                  className="keyword-input"
                />
              </div>
            </div>

            {/* Secondary Keywords */}
            <div className="filter-group">
              <h4>Secondary Keywords</h4>
              <div className="keyword-input-group">
                {searchFilters.secondaryKeywords.map((keyword, index) => (
                  <span key={index} className="keyword-tag">
                    {keyword}
                    <button
                      onClick={() => removeKeyword('secondaryKeywords', keyword)}
                      className="remove-keyword"
                    >
                      ×
                    </button>
                  </span>
                ))}
                <input
                  type="text"
                  placeholder="Add secondary keyword..."
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      addKeyword('secondaryKeywords', (e.target as HTMLInputElement).value);
                      (e.target as HTMLInputElement).value = '';
                    }
                  }}
                  className="keyword-input"
                />
              </div>
            </div>

            {/* Logic and Trigger Filters */}
            <div className="filter-row">
              <div className="filter-group">
                <h4>Logic</h4>
                <select
                  value={searchFilters.logic}
                  onChange={(e) => setSearchFilters(prev => ({
                    ...prev,
                    logic: e.target.value
                  }))}
                  className="logic-select"
                >
                  <option value="AND ANY">AND ANY</option>
                  <option value="AND ALL">AND ALL</option>
                  <option value="NOT ANY">NOT ANY</option>
                  <option value="NOT ALL">NOT ALL</option>
                </select>
              </div>

              <div className="filter-group">
                <h4>Trigger Range</h4>
                <div className="trigger-range">
                  <input
                    type="number"
                    placeholder="Min%"
                    value={searchFilters.minTrigger}
                    onChange={(e) => setSearchFilters(prev => ({
                      ...prev,
                      minTrigger: e.target.value
                    }))}
                    min="0"
                    max="100"
                  />
                  <span>to</span>
                  <input
                    type="number"
                    placeholder="Max%"
                    value={searchFilters.maxTrigger}
                    onChange={(e) => setSearchFilters(prev => ({
                      ...prev,
                      maxTrigger: e.target.value
                    }))}
                    min="0"
                    max="100"
                  />
                </div>
              </div>

              <div className="filter-group">
                <h4>Limit Results</h4>
                <input
                  type="number"
                  value={searchFilters.limit}
                  onChange={(e) => setSearchFilters(prev => ({
                    ...prev,
                    limit: parseInt(e.target.value, 10) || 50
                  }))}
                  min="1"
                  max="1000"
                  className="limit-input"
                />
              </div>
            </div>

            {/* Search Actions */}
            <div className="advanced-search-actions">
              <button
                onClick={handleAdvancedSearch}
                disabled={isSearching}
                className="primary"
              >
                {isSearching ? 'Searching...' : 'Search'}
              </button>
              <button
                onClick={clearSearch}
                className="secondary"
              >
                Clear All
              </button>
              <button
                onClick={() => setShowAdvanced(false)}
                className="secondary"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Search Results Summary */}
      {searchQuery && (
        <div className="search-results-summary">
          {isSearching ? (
            <div className="searching-indicator">
              <div className="spinner" />
              Searching...
            </div>
          ) : searchResults.length > 0 ? (
            <SearchResultsPreview results={searchResults.slice(0, 3)} />
          ) : searchQuery && (
            <div className="no-results">
              No entries found matching "{searchQuery}"
            </div>
          )}
        </div>
      )}
    </div>
  );
};

interface SearchResultsPreviewProps {
  results: SearchResult[];
}

const SearchResultsPreview: React.FC<SearchResultsPreviewProps> = ({ results }) => {
  return (
    <div className="search-results-preview">
      {results.map((result, index) => (
        <div key={index} className="search-result-item">
          <div className="result-header">
            <h4>{result.title || 'Untitled Entry'}</h4>
            <span className="result-score">Score: {Math.round(result.score)}</span>
          </div>
          <div className="result-content">
            {result.content.substring(0, 100)}...
          </div>
          <div className="result-meta">
            {result.lorebook_name} • Keywords: {result.keywords?.join(', ') || 'none'}
          </div>
        </div>
      ))}
      {results.length >= 3 && (
        <div className="view-all-results">
          + {results.length} more results...
        </div>
      )}
    </div>
  );
};