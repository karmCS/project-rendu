// Top-level App: nav + view switching + state, wired to the FastAPI backend.
import { useCallback, useEffect, useState } from 'react';
import { Icon } from './icons.jsx';
import { RENDU_API } from './data.jsx';
import Kanban from './Kanban.jsx';
import Templates from './Templates.jsx';
import Settings from './Settings.jsx';
import NoteDetail from './NoteDetail.jsx';

const POLL_INTERVAL_MS = 10000;
const HEALTH_INTERVAL_MS = 15000;

export default function App() {
  const [view, setView] = useState('notes');
  const [notes, setNotes] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [openNote, setOpenNote] = useState(null);
  const [toast, setToast] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const [serverUp, setServerUp] = useState(true);

  const showToast = (text, icon = 'check') => {
    setToast({ text, icon, key: Date.now() });
    setTimeout(() => setToast(null), 2400);
  };

  const refreshNotes = useCallback(async () => {
    try {
      const list = await RENDU_API.listNotes();
      setNotes(list);
      setServerUp(true);
    } catch (err) {
      setServerUp(false);
    }
  }, []);

  const refreshTemplates = useCallback(async () => {
    try {
      const list = await RENDU_API.listTemplates();
      setTemplates(list);
      setServerUp(true);
    } catch (err) {
      setServerUp(false);
    }
  }, []);

  // Initial load + 10s notes poll + 15s health ping.
  useEffect(() => {
    (async () => {
      await Promise.all([refreshNotes(), refreshTemplates()]);
      setLoaded(true);
    })();
  }, [refreshNotes, refreshTemplates]);

  useEffect(() => {
    const id = setInterval(refreshNotes, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [refreshNotes]);

  useEffect(() => {
    const id = setInterval(async () => {
      const ok = await RENDU_API.health();
      setServerUp(ok);
    }, HEALTH_INTERVAL_MS);
    return () => clearInterval(id);
  }, []);

  const openNoteFull = async (note) => {
    if (note.status === 'unsynced' || note.status === 'processing') {
      showToast('Note not ready yet', 'clock');
      return;
    }
    try {
      const full = await RENDU_API.getNote(note.id);
      setOpenNote(full);
    } catch (err) {
      showToast('Could not load note', 'clock');
    }
  };

  const markDone = async (id) => {
    try {
      await RENDU_API.setNoteStatus(id, 'done');
      setOpenNote(null);
      showToast('Moved to Done');
      refreshNotes();
    } catch {
      showToast('Could not save status', 'clock');
    }
  };

  const reprocessNote = async (id, templateId) => {
    const updated = await RENDU_API.reprocessNote(id, templateId);
    setOpenNote(updated);
    refreshNotes();
    return updated;
  };

  const saveTemplate = async (tpl) => {
    try {
      const saved = await RENDU_API.updateTemplate(tpl.id, tpl);
      setTemplates(curr => {
        const next = curr.map(t => t.id === saved.id ? saved : t);
        return saved.isDefault ? next.map(t => t.id === saved.id ? t : { ...t, isDefault: false }) : next;
      });
      showToast('Template saved');
    } catch {
      showToast('Save failed', 'clock');
    }
  };

  const deleteTemplate = async (id) => {
    try {
      await RENDU_API.deleteTemplate(id);
      setTemplates(curr => curr.filter(t => t.id !== id));
      showToast('Template deleted', 'trash');
    } catch (err) {
      const msg = err.status === 400 ? 'Cannot delete the last template' : 'Delete failed';
      showToast(msg, 'clock');
    }
  };

  const createTemplate = async () => {
    try {
      const created = await RENDU_API.createTemplate({
        name: 'Untitled Template',
        type: 'Custom',
        isDefault: false,
        structure: '',
      });
      setTemplates(curr => [created, ...curr]);
      showToast('New template created');
      return created;
    } catch {
      showToast('Could not create template', 'clock');
    }
  };

  return (
    <div className="app">
      <nav className="topnav">
        <div className="brand">
          Rendu
        </div>
        <div className="nav-links">
          <button
            className={`nav-link ${view === 'notes' ? 'active' : ''}`}
            onClick={() => setView('notes')}
          >
            Notes
          </button>
          <button
            className={`nav-link ${view === 'templates' ? 'active' : ''}`}
            onClick={() => setView('templates')}
          >
            Templates
          </button>
          <button
            className={`nav-link ${view === 'settings' ? 'active' : ''}`}
            onClick={() => setView('settings')}
          >
            Settings
          </button>
        </div>
        <div className="nav-spacer" />
        <div className="nav-status">
          <span
            className="status-dot"
            style={{ background: serverUp ? '#8FBFA0' : '#C25D5D' }}
          />
          {serverUp ? 'Ally connected' : 'Reconnecting…'}
        </div>
      </nav>

      {!loaded && (
        <div style={{ padding: '64px 48px', display: 'flex', alignItems: 'center', gap: 10, color: 'var(--muted)' }}>
          <span className="spinner" />
          Loading…
        </div>
      )}

      {loaded && view === 'notes' && (
        <Kanban notes={notes} onOpenNote={openNoteFull} onRefresh={refreshNotes} />
      )}
      {loaded && view === 'templates' && (
        <Templates
          templates={templates}
          onSave={saveTemplate}
          onDelete={deleteTemplate}
          onCreate={createTemplate}
        />
      )}
      {loaded && view === 'settings' && (
        <Settings showToast={showToast} />
      )}

      {openNote && (
        <NoteDetail
          note={openNote}
          templates={templates}
          onClose={() => setOpenNote(null)}
          onMarkDone={markDone}
          onReprocess={reprocessNote}
          onCopy={() => showToast('Copied to clipboard')}
        />
      )}

      <div className={`toast ${toast ? 'show' : ''}`} key={toast?.key}>
        {toast && <Icon name={toast.icon} size={14} />}
        {toast?.text}
      </div>
    </div>
  );
}
