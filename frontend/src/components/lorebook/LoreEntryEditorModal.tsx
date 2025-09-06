import React, { useState, useEffect } from 'react';
import { LoreEntry, useLorebookStore } from '../../stores/lorebookStore';

interface LoreEntryEditorModalProps {
  entry: LoreEntry | null;
  isOpen: boolean;
  onClose: () => void;
  onSave: (entry: Partial<LoreEntry>) => Promise<void>;
}

export const LoreEntryEditorModal: React.FC<LoreEntryEditorModalProps> = ({
  entry,
  isOpen,
  onClose,
  onSave
}) => {
  const [editingEntry, setEditingEntry] = useState<Partial<LoreEntry>>({
    title: '',
    content: '',
    keywords: [],
    secondary_keywords: [],
    logic: 'AND ANY',
    trigger: 100,
    order: 0,
  });

  const [keywordInput, setKeywordInput] = useState('');
  const [secondaryKeywordInput, setSecondaryKeywordInput] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (entry && isOpen) {
      setEditingEntry({
        ...entry,
        keywords: entry.keywords || [],
        secondary_keywords: entry.secondary_keywords || []
      });
    } else if (isOpen) {
      // Create mode - reset form
      setEditingEntry({
        title: '',
        content: '',
        keywords: [],
        secondary_keywords: [],
        logic: 'AND ANY',
        trigger: 100,
        order: 0,
      });
      setKeywordInput('');
      setSecondaryKeywordInput('');
    }
  }, [entry, isOpen]);

  const handleSave = async () => {
    if (!editingEntry.title || !editingEntry.content) {
      alert('Title and content are required');
      return;
    }

    setSaving(true);
    try {
      await onSave({
        ...editingEntry,
        keywords: editingEntry.keywords || [],
        secondary_keywords: editingEntry.secondary_keywords || []
      });
      onClose();
    } catch (error) {
      console.error('Failed to save entry:', error);
      alert('Failed to save entry. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const addKeyword = (type: 'keywords' | 'secondary_keywords', keyword: string) => {
    if (keyword.trim()) {
      const currentKeywords = editingEntry[type] || [];
      if (!currentKeywords.includes(keyword)) {
        setEditingEntry(prev => ({
          ...prev,
          [type]: [...currentKeywords, keyword]
        }));
      }
    }
  };

  const removeKeyword = (type: 'keywords' | 'secondary_keywords', keyword: string) => {
    const currentKeywords = editingEntry[type] || [];
    setEditingEntry(prev => ({
      ...prev,
      [type]: currentKeywords.filter(k => k !== keyword)
    }));
  };

  const handleKeywordKeyPress = (
    e: React.KeyboardEvent,
    type: 'keywords' | 'secondary_keywords',
    inputValue: string,
    setter: (value: string) => void
  ) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addKeyword(type, inputValue);
      setter('');
    }
  };

  const handleChange = (field: keyof LoreEntry, value: any) => {
    setEditingEntry(prev => ({ ...prev, [field]: value }));
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '800px', maxHeight: '90vh', overflow: 'auto' }}>
        <div className="modal-header">
          <h2>{entry ? 'Edit Lore Entry' : 'Create New Lore Entry'}</h2>
          <button onClick={onClose} className="close-btn">×</button>
        </div>

        <div className="modal-body lorebook-editor">
          {/* Top Row: Title, Logic, Trigger, Order */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '10px', marginBottom: '20px', alignItems: 'end' }}>
            {/* Title */}
            <div className="form-group">
              <label>Title:</label>
              <input
                type="text"
                value={editingEntry.title || ''}
                onChange={(e) => handleChange('title', e.target.value)}
                placeholder="Entry title..."
                required
                style={{ width: '100%' }}
              />
            </div>

            {/* Logic */}
            <div className="form-group">
              <label>Logic:</label>
              <select
                value={editingEntry.logic || 'AND ANY'}
                onChange={(e) => handleChange('logic', e.target.value)}
                style={{ width: '100%' }}
              >
                <option value="AND ANY">AND ANY</option>
                <option value="AND ALL">AND ALL</option>
                <option value="NOT ANY">NOT ANY</option>
                <option value="NOT ALL">NOT ALL</option>
              </select>
            </div>

            {/* Trigger */}
            <div className="form-group">
              <label>Trigger (%):</label>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={editingEntry.trigger || 100}
                  onChange={(e) => handleChange('trigger', parseInt(e.target.value, 10))}
                  style={{ flex: '1' }}
                />
                <span style={{ fontWeight: 'bold', minWidth: '30px', textAlign: 'right', fontSize: '12px' }}>
                  {editingEntry.trigger || 100}%
                </span>
              </div>
            </div>

            {/* Order */}
            <div className="form-group">
              <label>Order:</label>
              <input
                type="number"
                step="0.1"
                value={editingEntry.order || 0}
                onChange={(e) => handleChange('order', parseFloat(e.target.value))}
                placeholder="0.0"
                style={{ width: '100%' }}
              />
            </div>
          </div>

          {/* Keywords Section */}
          <div className="keyword-grid">
            {/* Primary Keywords */}
            <div className="form-group">
              <label>Primary Keywords:</label>
              <div className="keyword-section">
                <div className="keyword-tags">
                  {(editingEntry.keywords || []).map((keyword, index) => (
                    <span key={index} className="keyword-tag" style={{ margin: '2px', fontSize: '12px' }}>
                      {keyword}
                      <button
                        onClick={() => removeKeyword('keywords', keyword)}
                        className="remove-keyword"
                        style={{ marginLeft: '4px', fontSize: '10px' }}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
                <input
                  type="text"
                  placeholder="Add keyword..."
                  value={keywordInput}
                  onChange={(e) => setKeywordInput(e.target.value)}
                  onKeyPress={(e) => handleKeywordKeyPress(e, 'keywords', keywordInput, setKeywordInput)}
                  style={{ marginTop: '8px', width: '100%' }}
                />
              </div>
            </div>

            {/* Secondary Keywords */}
            <div className="form-group">
              <label>Secondary Keywords:</label>
              <div className="keyword-section">
                <div className="keyword-tags">
                  {(editingEntry.secondary_keywords || []).map((keyword, index) => (
                    <span key={index} className="keyword-tag secondary" style={{ margin: '2px', fontSize: '12px' }}>
                      {keyword}
                      <button
                        onClick={() => removeKeyword('secondary_keywords', keyword)}
                        className="remove-keyword"
                        style={{ marginLeft: '4px', fontSize: '10px' }}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
                <input
                  type="text"
                  placeholder="Add secondary keyword..."
                  value={secondaryKeywordInput}
                  onChange={(e) => setSecondaryKeywordInput(e.target.value)}
                  onKeyPress={(e) =>
                    handleKeywordKeyPress(e, 'secondary_keywords', secondaryKeywordInput, setSecondaryKeywordInput)
                  }
                  style={{ marginTop: '8px', width: '100%' }}
                />
              </div>
            </div>
          </div>

          {/* Content Section */}
           <div className="form-group">
             <label>Content:</label>
             <textarea
               value={editingEntry.content || ''}
               onChange={(e) => handleChange('content', e.target.value)}
               placeholder="Entry content..."
               rows={18}
               required
               style={{ resize: 'vertical', minHeight: '200px', width: '100%' }}
             />
           </div>

          {/* Preview */}
          <div className="form-group">
            <label>Preview:</label>
            <div className="entry-preview">
              <div className="preview-title">{editingEntry.title || 'No title'}</div>
              <div className="preview-content">
                {editingEntry.content ? (
                  editingEntry.content.substring(0, 200) + (editingEntry.content.length > 200 ? '...' : '')
                ) : 'No content'}
              </div>
              <div className="preview-meta">
                Keywords: {(editingEntry.keywords || []).join(', ') || 'none'} •
                Logic: {editingEntry.logic || 'AND ANY'} •
                Trigger: {editingEntry.trigger || 100}%
              </div>
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button onClick={onClose} className="btn-secondary">
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="btn-primary"
            disabled={saving || !editingEntry.title?.trim() || !editingEntry.content?.trim()}
          >
            {saving ? 'Saving...' : entry ? 'Save Changes' : 'Create Entry'}
          </button>
        </div>
      </div>
    </div>
  );
};