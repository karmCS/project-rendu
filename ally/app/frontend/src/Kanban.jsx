// Kanban board view — the default landing page.
import { useMemo, useState } from 'react';
import { Icon } from './icons.jsx';
import { COLUMNS, TYPE_BADGES, formatDateTime, formatDuration } from './data.jsx';
import { cardStyles } from './cardStyles.js';

const kanbanStyles = {
  wrap: {
    padding: '44px 48px 56px',
    maxWidth: '100%',
  },
  header: {
    display: 'flex',
    alignItems: 'flex-end',
    justifyContent: 'space-between',
    marginBottom: 36,
  },
  title: {
    fontFamily: "'Lora', Georgia, serif",
    fontSize: 32,
    fontWeight: 500,
    letterSpacing: '-0.02em',
    color: 'var(--dark)',
    margin: 0,
    lineHeight: 1.1,
  },
  subtitle: {
    fontSize: 14,
    color: 'var(--muted)',
    marginTop: 8,
    fontWeight: 400,
    fontStyle: 'italic',
    fontFamily: "'Lora', Georgia, serif",
  },
  refresh: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 8,
    fontSize: 12.5,
    color: 'var(--muted)',
    fontWeight: 450,
    padding: '7px 12px',
    borderRadius: 999,
    background: 'transparent',
    transition: 'all 160ms var(--ease)',
    cursor: 'pointer',
  },
  board: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, minmax(0, 1fr))',
    gap: 22,
    minHeight: 'calc(100vh - 220px)',
  },
  column: {
    display: 'flex',
    flexDirection: 'column',
    minWidth: 0,
  },
  columnHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '14px 18px',
    borderRadius: 'var(--radius)',
    marginBottom: 16,
    fontFamily: "'Lora', Georgia, serif",
    fontSize: 15,
    fontWeight: 500,
    letterSpacing: '-0.005em',
    transition: 'all 220ms var(--ease)',
  },
  columnList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
    minHeight: 100,
  },
  emptyState: {
    padding: '32px 16px',
    textAlign: 'center',
    fontSize: 12.5,
    color: 'var(--muted-2)',
    border: '1px dashed #E8E8E8',
    borderRadius: 'var(--radius)',
    background: 'transparent',
    fontWeight: 400,
  },
  count: {
    fontSize: 11,
    fontWeight: 600,
    padding: '2px 8px',
    borderRadius: 999,
    background: 'rgba(255, 255, 255, 0.6)',
  },
};

function ColumnHeader({ col, count }) {
  const styles = {
    unsynced: {
      background: 'var(--page-bg-soft)',
      color: 'var(--muted)',
      border: '1px solid var(--border)',
    },
    processing: {
      background: '#F3D98F',
      color: '#5C461A',
      border: '1px solid #E8CC75',
    },
    ready: {
      background: '#7298C7',
      color: 'var(--white)',
      border: '1px solid #6C90BD',
    },
    done: {
      background: 'var(--page-bg-soft)',
      color: 'var(--muted)',
      border: '1px solid var(--border)',
    },
  }[col.key];

  const countStyle = col.key === 'ready'
    ? { background: 'rgba(255,255,255,0.22)', color: 'var(--white)', fontFamily: 'var(--sans)' }
    : col.key === 'processing'
      ? { background: 'rgba(255,255,255,0.55)', color: '#5C461A', fontFamily: 'var(--sans)' }
      : { background: 'var(--white)', color: 'var(--muted)', fontFamily: 'var(--sans)' };

  return (
    <div style={{ ...kanbanStyles.columnHeader, ...styles }}>
      <span style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        {col.title}
        {col.key === 'processing' && <span className="spinner" style={{ width: 11, height: 11, borderWidth: 1.5, borderColor: 'rgba(92, 70, 26, 0.25)', borderTopColor: '#5C461A' }} />}
      </span>
      <span style={{ ...kanbanStyles.count, ...countStyle, fontSize: 11.5 }}>{count}</span>
    </div>
  );
}

function NoteCard({ note, onClick, status, index }) {
  const [hover, setHover] = useState(false);

  const statusStyle = (() => {
    if (status === 'ready') {
      return {
        background: '#FFFDF5',
        borderColor: '#EDE3CC',
        boxShadow: hover
          ? '0 8px 24px rgba(60, 50, 30, 0.08), 0 2px 4px rgba(60, 50, 30, 0.04)'
          : '0 3px 10px rgba(60, 50, 30, 0.05), 0 1px 2px rgba(60, 50, 30, 0.04)',
      };
    }
    if (status === 'processing') {
      return {
        opacity: 0.97,
        boxShadow: hover ? '0 4px 14px rgba(60, 50, 30, 0.06)' : '0 1px 3px rgba(60, 50, 30, 0.04)',
        animation: `cardIn 380ms var(--ease) ${index * 40}ms both, cardPulse 2.4s ease-in-out ${index * 40 + 380}ms infinite`,
      };
    }
    if (status === 'done') {
      return {
        background: 'transparent',
        borderColor: 'var(--border)',
        opacity: 0.6,
        boxShadow: 'none',
      };
    }
    return {
      boxShadow: hover ? '0 4px 14px rgba(60, 50, 30, 0.06)' : '0 1px 3px rgba(60, 50, 30, 0.04)',
    };
  })();

  const tplBadge = (() => {
    const t = note.template;
    if (TYPE_BADGES[t]) return TYPE_BADGES[t];
    if (t?.startsWith('Epic')) return TYPE_BADGES.Epic;
    if (t?.includes('SOAP')) return TYPE_BADGES.SOAP;
    if (t?.includes('DAP')) return TYPE_BADGES.DAP;
    return TYPE_BADGES.Custom;
  })();

  const baseAnimation = `cardIn 380ms var(--ease) ${index * 40}ms both`;
  return (
    <div
      style={{
        ...cardStyles.base,
        animation: baseAnimation,
        ...statusStyle,
        transform: hover ? 'translateY(-2px)' : 'translateY(0)',
      }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      onClick={onClick}
    >
      <div style={cardStyles.meta}>
        <span
          style={{
            color: 'var(--dark)',
            fontWeight: 500,
            fontSize: 14,
            fontFamily: "'Lora', Georgia, serif",
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            minWidth: 0,
            flex: 1,
            marginRight: 10,
          }}
          title={note.label}
        >
          {note.label}
        </span>
        <span style={cardStyles.duration}>
          <Icon name="clock" size={11} />
          {formatDuration(note.duration)}
        </span>
      </div>
      <div style={{ fontSize: 11.5, color: 'var(--muted)', marginTop: -6 }}>
        {formatDateTime(note.recordedAt)}
      </div>

      <div style={cardStyles.preview}>
        {status === 'processing' ? (
          <ProcessingShimmer text={note.preview} />
        ) : note.preview}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 2 }}>
        <span style={{ ...cardStyles.badge, background: tplBadge.bg, color: tplBadge.fg }}>
          {note.template}
        </span>
        {status === 'ready' && (
          <span style={{ fontSize: 11, fontWeight: 500, color: '#7298C7', display: 'flex', alignItems: 'center', gap: 5, fontFamily: 'var(--sans)' }}>
            <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#7298C7' }} />
            Review
          </span>
        )}
      </div>
    </div>
  );
}

function ProcessingShimmer({ text }) {
  return (
    <span style={{ position: 'relative', display: 'inline-block' }}>
      <span style={{
        background: 'linear-gradient(90deg, var(--dark-soft) 0%, var(--dark-soft) 40%, #B89A4F 50%, var(--dark-soft) 60%)',
        backgroundSize: '200% 100%',
        WebkitBackgroundClip: 'text',
        backgroundClip: 'text',
        color: 'transparent',
        animation: 'shimmer 2.4s linear infinite',
      }}>
        {text}
      </span>
    </span>
  );
}

export default function Kanban({ notes, onOpenNote, onRefresh }) {
  const grouped = useMemo(() => {
    const out = { unsynced: [], processing: [], ready: [], done: [] };
    notes.forEach(n => { if (out[n.status]) out[n.status].push(n); });
    return out;
  }, [notes]);

  const [refreshing, setRefreshing] = useState(false);
  const [hover, setHover] = useState(false);

  const handleRefresh = async () => {
    if (refreshing || !onRefresh) return;
    setRefreshing(true);
    try {
      await onRefresh();
    } finally {
      // Keep the spin visible long enough to feel intentional even on instant responses.
      setTimeout(() => setRefreshing(false), 400);
    }
  };

  return (
    <div className="view" style={kanbanStyles.wrap}>
      <div style={kanbanStyles.header}>
        <div>
          <h1 style={kanbanStyles.title}>Notes</h1>
          <div style={kanbanStyles.subtitle}>
            {grouped.ready.length > 0
              ? `${grouped.ready.length} note${grouped.ready.length > 1 ? 's' : ''} waiting for review`
              : 'You’re all caught up.'}
          </div>
        </div>
        <button
          type="button"
          onClick={handleRefresh}
          disabled={refreshing}
          onMouseEnter={() => setHover(true)}
          onMouseLeave={() => setHover(false)}
          title="Refresh now"
          style={{
            ...kanbanStyles.refresh,
            background: hover && !refreshing ? 'var(--page-bg-soft)' : 'transparent',
            color: hover && !refreshing ? 'var(--dark)' : 'var(--muted)',
            cursor: refreshing ? 'default' : 'pointer',
          }}
        >
          <Icon
            name="refresh"
            size={13}
            style={refreshing ? { animation: 'spin 0.9s linear infinite' } : undefined}
          />
          {refreshing ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>

      <div style={kanbanStyles.board}>
        {COLUMNS.map(col => (
          <div key={col.key} style={kanbanStyles.column}>
            <ColumnHeader col={col} count={grouped[col.key].length} />
            <div style={kanbanStyles.columnList}>
              {grouped[col.key].length === 0 ? (
                <div style={kanbanStyles.emptyState}>No notes here</div>
              ) : (
                grouped[col.key].map((note, i) => (
                  <NoteCard
                    key={note.id}
                    note={note}
                    status={col.key}
                    index={i}
                    onClick={() => onOpenNote(note)}
                  />
                ))
              )}
            </div>
          </div>
        ))}
      </div>

      <style>{`
        @keyframes cardIn {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes cardPulse {
          0%, 100% { box-shadow: 0 1px 3px rgba(60, 50, 30, 0.04); }
          50% { box-shadow: 0 0 0 3px rgba(243, 217, 143, 0.32), 0 2px 8px rgba(60, 50, 30, 0.06); }
        }
        @keyframes shimmer {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
      `}</style>
    </div>
  );
}
