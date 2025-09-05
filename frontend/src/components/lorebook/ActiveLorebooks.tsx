import React, { useEffect, useState } from 'react';

interface Lorebook {
  id: number;
  name: string;
  description?: string;
}

interface ActiveLorebooksProps {
  lorebooks: Lorebook[];
}

const ActiveLorebooks: React.FC<ActiveLorebooksProps> = ({ lorebooks }) => {
  const [activeIds, setActiveIds] = useState<number[]>([]);

  useEffect(() => {
    const loadActiveIds = async () => {
      try {
        const response = await fetch('/config');
        if (response.ok) {
          const cfg = await response.json();
          setActiveIds(cfg.active_lorebook_ids || []);
        }
      } catch (e) {
        console.error('Failed to load active lorebook IDs:', e);
      }
    };
    loadActiveIds();
  }, []);

  const addToActive = async (id: number) => {
    if (activeIds.includes(id)) return;
    const newList = [...activeIds, id];
    setActiveIds(newList);
    try {
      await fetch('/config/active_lorebook_ids', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: newList })
      });
    } catch (e) {
      console.error('Failed to add active lorebook:', e);
    }
  };

  const removeFromActive = async (id: number) => {
    const newList = activeIds.filter(x => x !== id);
    setActiveIds(newList);
    try {
      await fetch('/config/active_lorebook_ids', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: newList })
      });
    } catch (e) {
      console.error('Failed to remove active lorebook:', e);
    }
  };

  return (
    <div style={{ padding: '16px', background: 'var(--panel)', borderRadius: '8px', marginBottom: '16px' }}>
      <h3 style={{ margin: '0 0 12px 0', color: 'var(--text)' }}>Active Lorebooks for Chat Context</h3>
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap', marginBottom: '8px' }}>
        <select
          onChange={(e) => {
            if (e.target.value) {
              addToActive(parseInt(e.target.value));
              e.target.value = '';
            }
          }}
          value=""
          style={{
            padding: '4px 8px',
            borderRadius: '4px',
            background: 'var(--bg)',
            color: 'var(--text)',
            border: '1px solid var(--muted)'
          }}
        >
          <option value="">+ Add to Active</option>
          {lorebooks
            .filter(lb => !activeIds.includes(lb.id))
            .map(lb => (
              <option key={lb.id} value={lb.id}>{lb.name}</option>
            ))}
        </select>
      </div>
      <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
        {activeIds.map(id => {
          const lb = lorebooks.find(x => x.id === id);
          return (
            <span
              key={id}
              style={{
                padding: '4px 8px',
                borderRadius: '12px',
                background: 'var(--primary)',
                color: 'var(--text)',
                fontSize: '12px',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                cursor: 'pointer'
              }}
              title={`Active in chat: ${lb?.name || `#${id}`}`}
            >
              {lb ? lb.name : `#${id}`}
              <button
                onClick={() => removeFromActive(id)}
                style={{
                  border: 'none',
                  background: 'transparent',
                  color: 'var(--text)',
                  cursor: 'pointer',
                  fontSize: '14px',
                  lineHeight: 1,
                  padding: '0',
                  marginLeft: '4px'
                }}
              >
                ×
              </button>
            </span>
          );
        })}
      </div>
      {activeIds.length === 0 && (
        <p style={{ margin: '8px 0 0 0', color: 'var(--muted)', fontSize: '14px' }}>
          No active lorebooks. Select one above to add it to your current chat context.
        </p>
      )}
    </div>
  );
};

export { ActiveLorebooks };