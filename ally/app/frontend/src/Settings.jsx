// Settings page — sections rendered top to bottom in a single scrollable column.
// Sections are filled in incrementally; placeholders carry the spec layout.
import { useCallback, useEffect, useState } from 'react';
import { Icon } from './icons.jsx';
import { RENDU_API, formatLastSynced } from './data.jsx';

const settingsStyles = {
  page: {
    maxWidth: 760,
    margin: '0 auto',
    padding: '40px 32px 80px',
    display: 'flex',
    flexDirection: 'column',
    gap: 28,
  },
  pageHeader: {
    fontFamily: "'Lora', Georgia, serif",
    fontSize: 28,
    fontWeight: 500,
    color: 'var(--dark)',
    letterSpacing: '-0.02em',
    margin: '0 0 4px',
  },
  pageSub: {
    fontSize: 13.5,
    color: 'var(--muted)',
    margin: 0,
  },
  card: {
    background: 'var(--white)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-lg)',
    padding: '24px 26px',
    display: 'flex',
    flexDirection: 'column',
    gap: 18,
    boxShadow: 'var(--shadow-sm)',
  },
  sectionHeader: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  sectionTitle: {
    fontFamily: "'Lora', Georgia, serif",
    fontSize: 18,
    fontWeight: 500,
    color: 'var(--dark)',
    letterSpacing: '-0.01em',
    margin: 0,
  },
  sectionHint: {
    fontSize: 12.5,
    color: 'var(--muted)',
    margin: 0,
    lineHeight: 1.55,
  },
  field: { display: 'flex', flexDirection: 'column', gap: 6 },
  label: {
    fontSize: 11,
    fontWeight: 500,
    letterSpacing: '0.05em',
    textTransform: 'uppercase',
    color: 'var(--muted)',
  },
  input: {
    width: '100%',
    padding: '10px 14px',
    border: '1px solid var(--border-strong)',
    borderRadius: 'var(--radius)',
    background: 'var(--white)',
    fontFamily: 'var(--mono)',
    fontSize: 13,
    color: 'var(--dark)',
    outline: 'none',
    transition: 'all 160ms var(--ease)',
  },
  inlineMsg: {
    fontSize: 12.5,
    margin: 0,
  },
  rowEnd: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'flex-end',
    gap: 12,
  },
  saveBtn: {
    padding: '9px 18px',
    fontSize: 13,
    fontWeight: 500,
    background: '#7298C7',
    color: 'var(--white)',
    borderRadius: 8,
    display: 'inline-flex',
    alignItems: 'center',
    gap: 8,
    transition: 'all 180ms var(--ease)',
  },
  placeholder: {
    fontSize: 12.5,
    color: 'var(--muted)',
    fontStyle: 'italic',
  },
};

function FocusInput({ value, onChange, placeholder, onEnter }) {
  const [f, setF] = useState(false);
  return (
    <input
      style={{
        ...settingsStyles.input,
        borderColor: f ? 'var(--blue-grey)' : 'var(--border-strong)',
        boxShadow: f ? '0 0 0 3px var(--blue-grey-50)' : 'none',
      }}
      value={value || ''}
      onChange={e => onChange(e.target.value)}
      onFocus={() => setF(true)}
      onBlur={() => setF(false)}
      onKeyDown={e => { if (e.key === 'Enter' && onEnter) onEnter(); }}
      placeholder={placeholder}
      spellCheck={false}
    />
  );
}

function SectionCard({ title, hint, children }) {
  return (
    <section style={settingsStyles.card}>
      <header style={settingsStyles.sectionHeader}>
        <h2 style={settingsStyles.sectionTitle}>{title}</h2>
        {hint && <p style={settingsStyles.sectionHint}>{hint}</p>}
      </header>
      {children}
    </section>
  );
}

function InferenceSection({ settings, onSave }) {
  const [endpoint, setEndpoint] = useState(settings.ollama_endpoint || '');
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null); // { kind: 'success' | 'error', text }

  useEffect(() => {
    setEndpoint(settings.ollama_endpoint || '');
  }, [settings.ollama_endpoint]);

  const dirty = endpoint !== (settings.ollama_endpoint || '');

  const handleSave = async () => {
    setMsg(null);
    setSaving(true);
    try {
      await onSave({ ollama_endpoint: endpoint.trim() });
      setMsg({ kind: 'success', text: 'Saved.' });
    } catch (err) {
      const detail = err.detail || err.message || 'Could not save settings.';
      setMsg({ kind: 'error', text: detail });
    } finally {
      setSaving(false);
    }
  };

  return (
    <SectionCard
      title="Inference"
      hint="If inference moves to a separate machine on the LAN, update this URL to point to the new host. No code changes needed."
    >
      <div style={settingsStyles.field}>
        <span style={settingsStyles.label}>Ollama Endpoint URL</span>
        <FocusInput
          value={endpoint}
          onChange={setEndpoint}
          placeholder="http://localhost:11434"
          onEnter={() => { if (dirty && !saving) handleSave(); }}
        />
      </div>

      <div style={settingsStyles.rowEnd}>
        {msg && (
          <span
            style={{
              ...settingsStyles.inlineMsg,
              color: msg.kind === 'success' ? '#5C8A6E' : '#C25D5D',
            }}
          >
            {msg.text}
          </span>
        )}
        <button
          className="btn"
          onClick={handleSave}
          disabled={!dirty || saving}
          style={{
            ...settingsStyles.saveBtn,
            opacity: !dirty || saving ? 0.5 : 1,
            cursor: !dirty || saving ? 'default' : 'pointer',
          }}
        >
          {saving
            ? <span className="spinner" style={{ borderTopColor: '#FFF', borderColor: 'rgba(255,255,255,0.4)' }} />
            : <Icon name="check" size={14} />}
          {saving ? 'Saving' : 'Save'}
        </button>
      </div>
    </SectionCard>
  );
}

function StoragePathsSection({ settings, onSave }) {
  const [audio, setAudio] = useState(settings.audio_storage_path || '');
  const [transcript, setTranscript] = useState(settings.transcript_storage_path || '');
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);

  useEffect(() => {
    setAudio(settings.audio_storage_path || '');
    setTranscript(settings.transcript_storage_path || '');
  }, [settings.audio_storage_path, settings.transcript_storage_path]);

  const dirty =
    audio !== (settings.audio_storage_path || '') ||
    transcript !== (settings.transcript_storage_path || '');

  const handleSave = async () => {
    setMsg(null);
    setSaving(true);
    try {
      await onSave({
        audio_storage_path: audio.trim(),
        transcript_storage_path: transcript.trim(),
      });
      setMsg({ kind: 'success', text: 'Saved.' });
    } catch (err) {
      const detail = err.detail || err.message || 'Could not save settings.';
      setMsg({ kind: 'error', text: detail });
    } finally {
      setSaving(false);
    }
  };

  return (
    <SectionCard
      title="Storage Paths"
      hint="Absolute or relative paths on the server. Both directories must already exist on disk."
    >
      <div style={settingsStyles.field}>
        <span style={settingsStyles.label}>Audio Storage Path</span>
        <FocusInput
          value={audio}
          onChange={setAudio}
          placeholder="storage/audio"
          onEnter={() => { if (dirty && !saving) handleSave(); }}
        />
      </div>
      <div style={settingsStyles.field}>
        <span style={settingsStyles.label}>Transcript Storage Path</span>
        <FocusInput
          value={transcript}
          onChange={setTranscript}
          placeholder="storage/transcripts"
          onEnter={() => { if (dirty && !saving) handleSave(); }}
        />
      </div>

      <div style={settingsStyles.rowEnd}>
        {msg && (
          <span
            style={{
              ...settingsStyles.inlineMsg,
              color: msg.kind === 'success' ? '#5C8A6E' : '#C25D5D',
            }}
          >
            {msg.text}
          </span>
        )}
        <button
          className="btn"
          onClick={handleSave}
          disabled={!dirty || saving}
          style={{
            ...settingsStyles.saveBtn,
            opacity: !dirty || saving ? 0.5 : 1,
            cursor: !dirty || saving ? 'default' : 'pointer',
          }}
        >
          {saving
            ? <span className="spinner" style={{ borderTopColor: '#FFF', borderColor: 'rgba(255,255,255,0.4)' }} />
            : <Icon name="check" size={14} />}
          {saving ? 'Saving' : 'Save'}
        </button>
      </div>
    </SectionCard>
  );
}

function StatCard({ label, value }) {
  return (
    <div style={{
      flex: 1,
      minWidth: 0,
      padding: '14px 16px',
      background: 'var(--page-bg-soft)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius)',
      display: 'flex',
      flexDirection: 'column',
      gap: 4,
    }}>
      <span style={{
        fontSize: 11,
        fontWeight: 500,
        letterSpacing: '0.05em',
        textTransform: 'uppercase',
        color: 'var(--muted)',
      }}>
        {label}
      </span>
      <span style={{
        fontFamily: "'Lora', Georgia, serif",
        fontSize: 22,
        fontWeight: 500,
        color: 'var(--dark)',
        letterSpacing: '-0.01em',
      }}>
        {value}
      </span>
    </div>
  );
}

function ConfirmDialog({ title, message, confirmLabel, onConfirm, onCancel, busy }) {
  return (
    <div
      onClick={onCancel}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(45,45,45,0.36)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 200,
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: 'var(--white)',
          borderRadius: 'var(--radius-lg)',
          padding: '24px 26px',
          maxWidth: 420,
          width: 'calc(100% - 32px)',
          boxShadow: 'var(--shadow-lg)',
          display: 'flex',
          flexDirection: 'column',
          gap: 14,
        }}
      >
        <h3 style={{
          fontFamily: "'Lora', Georgia, serif",
          fontSize: 18,
          fontWeight: 500,
          margin: 0,
          color: 'var(--dark)',
        }}>
          {title}
        </h3>
        <p style={{ fontSize: 13.5, color: 'var(--dark-soft)', margin: 0, lineHeight: 1.55 }}>
          {message}
        </p>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 4 }}>
          <button className="btn-ghost" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
          <button
            className="btn"
            onClick={onConfirm}
            disabled={busy}
            style={{
              padding: '9px 18px',
              fontSize: 13,
              fontWeight: 500,
              background: '#C25D5D',
              color: 'var(--white)',
              borderRadius: 8,
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              opacity: busy ? 0.6 : 1,
              cursor: busy ? 'default' : 'pointer',
            }}
          >
            {busy && <span className="spinner" style={{ borderTopColor: '#FFF', borderColor: 'rgba(255,255,255,0.4)' }} />}
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

function DiskUsageSection({ settings, onRefresh, showToast }) {
  const [confirming, setConfirming] = useState(false);
  const [purging, setPurging] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const fmt = (mb) => `${(mb || 0).toFixed(1)} MB`;

  const purge = async () => {
    setPurging(true);
    setError(null);
    try {
      const res = await RENDU_API.purgeDone();
      if (!res.purged_count) {
        setError('No done notes to purge.');
        setResult(null);
      } else {
        setResult(res);
        showToast?.(`Purged ${res.purged_count} notes`);
      }
      await onRefresh();
    } catch {
      setError('Could not purge. Check that the server is running.');
    } finally {
      setPurging(false);
      setConfirming(false);
    }
  };

  return (
    <SectionCard title="Disk Usage">
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <StatCard label="Audio files" value={fmt(settings.audio_size_mb)} />
        <StatCard label="Transcripts" value={fmt(settings.transcript_size_mb)} />
        <StatCard label="Database" value={fmt(settings.database_size_mb)} />
      </div>

      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 12,
        flexWrap: 'wrap',
      }}>
        <div style={{ fontSize: 12.5, color: 'var(--muted)', maxWidth: 360 }}>
          {result
            ? `Purged ${result.purged_count} notes · ${result.space_reclaimed_mb.toFixed(1)} MB reclaimed`
            : error
            ? <span style={{ color: '#C25D5D' }}>{error}</span>
            : 'Frees disk space by deleting audio and transcript files for done notes. Database records are kept.'}
        </div>
        <button
          className="btn"
          onClick={() => { setError(null); setResult(null); setConfirming(true); }}
          style={{
            padding: '9px 16px',
            fontSize: 13,
            fontWeight: 500,
            color: '#C25D5D',
            background: 'transparent',
            border: '1.5px solid #E3B8B8',
            borderRadius: 8,
            display: 'inline-flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <Icon name="trash" size={13} />
          Purge done notes
        </button>
      </div>

      {confirming && (
        <ConfirmDialog
          title="Purge done notes?"
          message="This will delete audio and transcript files for all done notes. This cannot be undone."
          confirmLabel={purging ? 'Purging' : 'Purge'}
          onConfirm={purge}
          onCancel={() => setConfirming(false)}
          busy={purging}
        />
      )}
    </SectionCard>
  );
}

function ReadOnlyRow({ label, value, mono, last }) {
  return (
    <div style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'baseline',
      gap: 16,
      padding: '10px 0',
      borderBottom: last ? 'none' : '1px solid var(--border)',
    }}>
      <span style={{ fontSize: 12.5, color: 'var(--muted)' }}>{label}</span>
      <span style={{
        fontSize: 13,
        color: 'var(--dark)',
        fontFamily: mono ? 'var(--mono)' : 'inherit',
        textAlign: 'right',
        wordBreak: 'break-word',
      }}>
        {value}
      </span>
    </div>
  );
}

function SyncSection({ settings }) {
  const piTarget = (typeof window !== 'undefined' && window.location)
    ? `${window.location.protocol}//${window.location.host}/sync`
    : '/sync';

  return (
    <SectionCard
      title="Sync"
      hint="The Pi's sync script should POST recordings to the URL below."
    >
      <div>
        <ReadOnlyRow
          label="Last Synced"
          value={formatLastSynced(settings.last_synced_at)}
        />
        <ReadOnlyRow label="Pi Sync Target" value={piTarget} mono last />
      </div>
    </SectionCard>
  );
}

function SystemInfoSection({ settings }) {
  return (
    <SectionCard title="System Info">
      <div>
        <ReadOnlyRow label="Total Notes" value={String(settings.total_notes ?? 0)} />
        <ReadOnlyRow label="Python Version" value={settings.python_version || '—'} mono />
        <ReadOnlyRow label="FastAPI Version" value={settings.fastapi_version || '—'} mono last />
      </div>
    </SectionCard>
  );
}

export default function Settings({ showToast }) {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const data = await RENDU_API.getSettings();
      setSettings(data);
      setError(null);
    } catch (err) {
      setError('Could not load settings. Check that the server is running.');
    }
  }, []);

  useEffect(() => {
    (async () => {
      await refresh();
      setLoading(false);
    })();
  }, [refresh]);

  const handleSave = async (patch) => {
    let updated;
    try {
      updated = await RENDU_API.updateSettings(patch);
    } catch (err) {
      // Try to parse the FastAPI {detail: "..."} body so the section can show a precise message.
      const body = err.message?.match(/\{.*\}$/)?.[0];
      let detail;
      try { detail = body && JSON.parse(body).detail; } catch { /* ignore */ }
      const e = new Error(detail || 'Could not save settings. Check that the server is running.');
      e.detail = detail;
      throw e;
    }
    setSettings(updated);
    showToast?.('Settings saved');
    return updated;
  };

  if (loading) {
    return (
      <div className="view" style={{ padding: '64px 48px', display: 'flex', alignItems: 'center', gap: 10, color: 'var(--muted)' }}>
        <span className="spinner" />
        Loading settings…
      </div>
    );
  }

  if (error || !settings) {
    return (
      <div className="view" style={settingsStyles.page}>
        <div style={{ ...settingsStyles.card, color: '#C25D5D' }}>
          {error || 'Settings unavailable.'}
        </div>
      </div>
    );
  }

  return (
    <div className="view" style={settingsStyles.page}>
      <header>
        <h1 style={settingsStyles.pageHeader}>Settings</h1>
        <p style={settingsStyles.pageSub}>
          Configure inference, storage, and sync. Changes take effect on the next operation.
        </p>
      </header>

      <InferenceSection settings={settings} onSave={handleSave} />
      <StoragePathsSection settings={settings} onSave={handleSave} />
      <DiskUsageSection settings={settings} onRefresh={refresh} showToast={showToast} />
      <SyncSection settings={settings} />
      <SystemInfoSection settings={settings} />
    </div>
  );
}
