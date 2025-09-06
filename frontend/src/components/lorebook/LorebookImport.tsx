import React, { useState, DragEvent, ChangeEvent } from 'react';

interface LorebookImportProps {
  onImport: (file: File) => Promise<void>;
  onCancel: () => void;
}

export const LorebookImport: React.FC<LorebookImportProps> = ({
  onImport,
  onCancel
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<any>(null);

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    setError(null);

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const handleFileSelect = async (file: File) => {
    // Check file extension
    if (!file.name.toLowerCase().endsWith('.json')) {
      setError('Only JSON files are supported');
      return;
    }

    // Check file size (limit to 10MB)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      setError('File size must be less than 10MB');
      return;
    }

    setSelectedFile(file);
    setError(null);

    // Preview file content
    try {
      const text = await file.text();
      const data = JSON.parse(text);

      // Generate preview
      const previewData = generatePreview(data);
      setPreview(previewData);
    } catch (err) {
      setError('Invalid JSON format');
      setPreview(null);
    }
  };

  const generatePreview = (data: any) => {
    try {
      let entries: any[] = [];

      if (data && typeof data === 'object') {
        // Handle different JSON formats
        if (data.entries) {
          entries = Array.isArray(data.entries) ? data.entries : Object.values(data.entries || {});
        } else if (Array.isArray(data)) {
          entries = data as any[];
        }

        // Generate stats
        const stats: any = {
          name: data.name || selectedFile?.name?.replace('.json', ''),
          description: data.description || '',
          totalEntries: entries.length,
          keywords: [],
          logicTypes: {},
          averageTrigger: 0,
          previewEntries: entries.slice(0, 3),
          format: detectFormat(data)
        };

        // Calculate statistics
        let totalTrigger = 0;
        const keywordsSet = new Set();
        const logicSet = new Set();

        entries.forEach((entry: any) => {
          if (entry.keywords && Array.isArray(entry.keywords)) {
            entry.keywords.forEach((kw: string) => keywordsSet.add(kw));
          }
          if (entry.logic) {
            stats.logicTypes[entry.logic] = (stats.logicTypes[entry.logic] || 0) + 1;
          }
          if (typeof entry.trigger === 'number') {
            totalTrigger += entry.trigger;
          }
        });

        stats.keywords = Array.from(keywordsSet) as string[];
        stats.averageTrigger = entries.length > 0 ? Math.round(totalTrigger / entries.length) : 0;

        return stats;
      }
    } catch (err) {
      console.error('Preview generation error:', err);
    }

    return null;
  };

  const detectFormat = (data: any): string => {
    if (data.entries && data.name) {
      return 'SillyTavern';
    }
    if (Array.isArray(data)) {
      return 'Compact Array';
    }
    if (data.lastUpdate) {
      return 'AidanAI';
    }
    return 'Unknown';
  };

  const handleImport = async () => {
    if (!selectedFile) return;

    setImporting(true);
    setError(null);

    try {
      await onImport(selectedFile);
      // Success handled by parent
    } catch (err: any) {
      setError(err.message || 'Import failed');
    } finally {
      setImporting(false);
    }
  };

  const clearSelection = () => {
    setSelectedFile(null);
    setPreview(null);
    setError(null);
  };

  return (
    <div className="lorebook-import-panel">
      <div className="panel-header">
        <h3>Import Lorebook</h3>
        <button
          onClick={onCancel}
          className="close-btn"
          title="Close import panel"
        >
          ×
        </button>
      </div>

      <div className="import-content">
        {!selectedFile ? (
          <div
            className={`file-dropzone ${isDragging ? 'dragging' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <div className="dropzone-content">
              <div className="upload-icon">📁</div>
              <p>Drop JSON file here</p>
              <p>or</p>
              <label className="file-input-label">
                Browse Files
                <input
                  type="file"
                  accept="application/json,.json"
                  onChange={handleFileChange}
                  hidden
                />
              </label>
              <small className="file-info">
                Supports SillyTavern, AidanAI, and compact JSON formats (max 10MB)
              </small>
            </div>
          </div>
        ) : (
          <div className="file-preview">
            {/* File Info */}
            <div className="file-header">
              <div className="file-info">
                <h4>📄 {selectedFile.name}</h4>
                <span className="file-size">
                  {(selectedFile.size / 1024).toFixed(1)} KB
                </span>
              </div>
              <div className="file-actions">
                <button onClick={clearSelection} className="secondary">
                  Choose Different File
                </button>
              </div>
            </div>

            {/* Error Display */}
            {error && (
              <div className="error-message">
                <span className="error-icon">⚠️</span>
                {error}
              </div>
            )}

            {/* Preview */}
            {preview && (
              <div className="import-preview">
                <h4>Import Preview</h4>

                <div className="preview-grid">
                  <div className="preview-section">
                    <label>Lorebook Name:</label>
                    <span>{preview.name || 'Untitled'}</span>
                  </div>

                  <div className="preview-section">
                    <label>Format:</label>
                    <span>{preview.format}</span>
                  </div>

                  <div className="preview-section">
                    <label>Entries:</label>
                    <span>{preview.totalEntries}</span>
                  </div>

                  <div className="preview-section">
                    <label>Keywords:</label>
                    <span>{preview.keywords.length} unique</span>
                  </div>

                  {Object.keys(preview.logicTypes).length > 0 && (
                    <div className="preview-section">
                      <label>Logic Types:</label>
                      <span>
                        {Object.entries(preview.logicTypes).map(([logic, count]) =>
                          `${logic}: ${count}`
                        ).join(', ')}
                      </span>
                    </div>
                  )}

                  {preview.averageTrigger > 0 && (
                    <div className="preview-section">
                      <label>Avg. Trigger:</label>
                      <span>{preview.averageTrigger}%</span>
                    </div>
                  )}
                </div>

                {/* Sample Entries */}
                {preview.previewEntries && preview.previewEntries.length > 0 && (
                  <div className="sample-entries">
                    <h5>Sample Entries:</h5>
                    <div className="entry-preview">
                      {preview.previewEntries.slice(0, 3).map((entry: any, index: number) => (
                        <div key={index} className="entry-summary">
                          <div className="entry-title">
                            {entry.title || entry.comment || 'Untitled'}
                          </div>
                          <div className="entry-content">
                            {entry.content?.substring(0, 100)}...
                          </div>
                          {entry.keywords && entry.keywords.length > 0 && (
                            <div className="entry-keywords">
                              Keywords: {entry.keywords.slice(0, 3).join(', ')}
                              {entry.keywords.length > 3 && ` +${entry.keywords.length - 3} more`}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Import Actions */}
            <div className="import-actions">
              <button
                onClick={handleImport}
                disabled={importing || !!error}
                className="primary import-btn"
              >
                {importing ? 'Importing...' : 'Import Lorebook'}
              </button>
              <button
                onClick={onCancel}
                className="secondary"
                disabled={importing}
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Help Text */}
        <div className="import-help">
          <h5>Supported Formats:</h5>
          <ul>
            <li><strong>SillyTavern:</strong> Standard lorebook JSON with name, description, and entries</li>
            <li><strong>AidanAI:</strong> Lore export with specific field mappings</li>
            <li><strong>Compact Array:</strong> Simple array of entry objects</li>
          </ul>
          <p>All formats are automatically converted to the internal structure.</p>
        </div>
      </div>
    </div>
  );
};