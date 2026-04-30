// Templates Manager — list on left, editor on right.
// Wired to backend CRUD: onCreate / onSave / onDelete are async.
import { useEffect, useState } from 'react';
import { Icon } from './icons.jsx';
import { TYPE_BADGES } from './data.jsx';
import { cardStyles } from './cardStyles.js';

const tplStyles = {
  wrap: {
    display: 'grid',
    gridTemplateColumns: '340px 1fr',
    height: 'calc(100vh - 68px)',
    background: 'var(--page-bg)',
  },
  list: {
    background: 'var(--page-bg)',
    borderRight: '1px solid var(--border)',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  listHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '32px 24px 18px',
  },
  listTitle: {
    fontFamily: "'Lora', Georgia, serif",
    fontSize: 24,
    fontWeight: 500,
    color: 'var(--dark)',
    letterSpacing: '-0.02em',
    margin: 0,
  },
  newBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '8px 13px',
    fontSize: 12.5,
    fontWeight: 500,
    color: 'var(--white)',
    background: '#7298C7',
    borderRadius: 8,
    transition: 'all 160ms var(--ease)',
  },
  listItems: {
    flex: 1,
    overflow: 'auto',
    padding: '4px 12px 12px',
  },
  listItem: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '11px 12px',
    borderRadius: 8,
    cursor: 'pointer',
    transition: 'all 160ms var(--ease)',
    marginBottom: 2,
    border: '1px solid transparent',
  },
  editor: {
    padding: '40px 48px',
    overflow: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: 24,
    maxWidth: 860,
    width: '100%',
  },
  editorHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: 16,
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
    fontSize: 14,
    color: 'var(--dark)',
    outline: 'none',
    transition: 'all 160ms var(--ease)',
  },
  select: {
    width: '100%',
    padding: '10px 14px',
    border: '1px solid var(--border-strong)',
    borderRadius: 'var(--radius)',
    background: 'var(--white)',
    fontSize: 14,
    color: 'var(--dark)',
    outline: 'none',
    cursor: 'pointer',
    appearance: 'none',
    backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%238A8A8A' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E")`,
    backgroundRepeat: 'no-repeat',
    backgroundPosition: 'right 14px center',
    paddingRight: 36,
  },
  textarea: {
    width: '100%',
    minHeight: 360,
    padding: '20px 22px',
    border: '1px solid var(--border-strong)',
    borderRadius: 'var(--radius)',
    background: 'var(--white)',
    fontFamily: "'JetBrains Mono', 'SF Mono', Menlo, monospace",
    fontSize: 13,
    lineHeight: 1.75,
    color: 'var(--dark)',
    resize: 'vertical',
    outline: 'none',
    transition: 'all 160ms var(--ease)',
  },
  toggleWrap: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '12px 14px',
    background: 'var(--white)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius)',
  },
  toggle: {
    width: 36,
    height: 20,
    borderRadius: 999,
    position: 'relative',
    cursor: 'pointer',
    transition: 'background 200ms var(--ease)',
    flexShrink: 0,
  },
  toggleKnob: {
    position: 'absolute',
    top: 2,
    width: 16,
    height: 16,
    background: 'var(--white)',
    borderRadius: '50%',
    transition: 'left 200ms var(--ease)',
    boxShadow: '0 1px 3px rgba(0,0,0,0.18)',
  },
  footerBar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: 8,
    borderTop: '1px solid var(--border)',
    marginTop: 8,
  },
};

function Toggle({ on, onChange }) {
  return (
    <div
      style={{
        ...tplStyles.toggle,
        background: on ? 'var(--blue-grey)' : 'var(--border-strong)',
      }}
      onClick={() => onChange(!on)}
      role="switch"
      aria-checked={on}
    >
      <div style={{ ...tplStyles.toggleKnob, left: on ? 18 : 2 }} />
    </div>
  );
}

export default function Templates({ templates, onSave, onDelete, onCreate }) {
  const [selectedId, setSelectedId] = useState(templates[0]?.id);
  const selected = templates.find(t => t.id === selectedId) || templates[0];
  const [draft, setDraft] = useState(selected);
  const [savedFlash, setSavedFlash] = useState(false);
  const [saving, setSaving] = useState(false);

  // Keep selection valid as the templates list changes (create/delete).
  useEffect(() => {
    if (!templates.length) { setSelectedId(undefined); return; }
    if (!templates.find(t => t.id === selectedId)) {
      setSelectedId(templates[0].id);
    }
  }, [templates, selectedId]);

  useEffect(() => {
    setDraft(selected);
  }, [selected?.id]);

  const dirty = draft && selected && (
    draft.name !== selected.name ||
    draft.type !== selected.type ||
    draft.isDefault !== selected.isDefault ||
    draft.structure !== selected.structure
  );

  const save = async () => {
    setSaving(true);
    try {
      await onSave(draft);
      setSavedFlash(true);
      setTimeout(() => setSavedFlash(false), 1400);
    } finally {
      setSaving(false);
    }
  };

  const create = async () => {
    const created = await onCreate?.();
    if (created?.id) setSelectedId(created.id);
  };

  if (!draft) {
    return (
      <div className="view" style={tplStyles.wrap}>
        <div style={{ ...tplStyles.list, gridColumn: '1 / -1', alignItems: 'center', justifyContent: 'center' }}>
          <div style={tplStyles.listHeader}>
            <h1 style={tplStyles.listTitle}>Templates</h1>
            <button style={tplStyles.newBtn} onClick={create}>
              <Icon name="plus" size={13} />
              New
            </button>
          </div>
          <div style={{ color: 'var(--muted)', fontSize: 13, padding: '0 24px 24px' }}>
            No templates yet — create one to get started.
          </div>
        </div>
      </div>
    );
  }

  const badge = TYPE_BADGES[draft.type] || TYPE_BADGES.Custom;

  return (
    <div className="view" style={tplStyles.wrap}>
      {/* Left: list */}
      <div style={tplStyles.list}>
        <div style={tplStyles.listHeader}>
          <h1 style={tplStyles.listTitle}>Templates</h1>
          <button
            style={tplStyles.newBtn}
            onClick={create}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--blue-grey-600)'}
            onMouseLeave={e => e.currentTarget.style.background = '#7298C7'}
          >
            <Icon name="plus" size={13} />
            New
          </button>
        </div>
        <div style={tplStyles.listItems}>
          {templates.map((t, i) => {
            const b = TYPE_BADGES[t.type] || TYPE_BADGES.Custom;
            const active = t.id === selectedId;
            return (
              <div
                key={t.id}
                onClick={() => setSelectedId(t.id)}
                style={{
                  ...tplStyles.listItem,
                  background: active ? 'var(--blue-grey-50)' : 'transparent',
                  borderColor: active ? 'var(--blue-grey-100)' : 'transparent',
                  animation: `cardIn 280ms var(--ease) ${i * 30}ms both`,
                }}
                onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'var(--light-2)'; }}
                onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent'; }}
              >
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{
                      fontSize: 13.5,
                      fontWeight: active ? 600 : 500,
                      color: active ? 'var(--blue-grey-700)' : 'var(--dark)',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}>
                      {t.name}
                    </span>
                    {t.isDefault && (
                      <span style={{
                        fontSize: 10,
                        fontWeight: 600,
                        color: '#8B6F2A',
                        background: 'var(--butter-soft)',
                        padding: '1px 6px',
                        borderRadius: 4,
                        letterSpacing: '0.04em',
                        textTransform: 'uppercase',
                      }}>
                        Default
                      </span>
                    )}
                  </div>
                  <span style={{ ...cardStyles.badge, background: b.bg, color: b.fg, alignSelf: 'flex-start', fontSize: 10 }}>
                    {t.type}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Right: editor */}
      <div style={tplStyles.editor} key={draft.id}>
        <div style={tplStyles.editorHeader}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
              <span style={{ ...cardStyles.badge, background: badge.bg, color: badge.fg, fontSize: 11 }}>
                {draft.type}
              </span>
              {draft.isDefault && (
                <span style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                  fontSize: 11,
                  fontWeight: 600,
                  color: '#8B6F2A',
                }}>
                  <Icon name="star" size={11} fill="var(--butter-deep)" stroke={0} />
                  Default
                </span>
              )}
            </div>
            <h2 style={{ fontFamily: "'Lora', Georgia, serif", fontSize: 28, fontWeight: 500, color: 'var(--dark)', margin: 0, letterSpacing: '-0.02em' }}>
              {draft.name || 'Untitled template'}
            </h2>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 220px', gap: 14 }}>
          <div style={tplStyles.field}>
            <span style={tplStyles.label}>Name</span>
            <FocusInput
              value={draft.name}
              onChange={v => setDraft(d => ({ ...d, name: v }))}
              placeholder="Template name"
            />
          </div>
          <div style={tplStyles.field}>
            <span style={tplStyles.label}>Format Type</span>
            <select
              style={tplStyles.select}
              value={draft.type}
              onChange={e => setDraft(d => ({ ...d, type: e.target.value }))}
            >
              <option value="Epic">Epic</option>
              <option value="SOAP">SOAP</option>
              <option value="DAP">DAP</option>
              <option value="Progress Note">Progress Note</option>
              <option value="Custom">Custom</option>
            </select>
          </div>
        </div>

        <div style={tplStyles.toggleWrap}>
          <Toggle on={draft.isDefault} onChange={v => setDraft(d => ({ ...d, isDefault: v }))} />
          <div>
            <div style={{ fontSize: 13.5, fontWeight: 500, color: 'var(--dark)' }}>Set as default</div>
            <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 1 }}>
              New recordings will use this template automatically.
            </div>
          </div>
        </div>

        <div style={tplStyles.field}>
          <span style={tplStyles.label}>Template Structure</span>
          <FocusTextarea
            value={draft.structure}
            onChange={v => setDraft(d => ({ ...d, structure: v }))}
            placeholder="Paste or write your note structure here. Use section headers exactly as you want them to appear in the final note."
          />
        </div>

        <div style={tplStyles.footerBar}>
          <button
            className="btn-danger-link"
            onClick={() => { if (confirm(`Delete "${selected.name}"?`)) onDelete(selected.id); }}
            style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12.5, fontWeight: 500 }}
          >
            <Icon name="trash" size={13} />
            Delete template
          </button>
          <button
            className="btn"
            onClick={save}
            disabled={(!dirty && !savedFlash) || saving}
            style={{
              padding: '11px 22px',
              fontSize: 13.5,
              fontWeight: 500,
              opacity: (!dirty && !savedFlash) || saving ? 0.5 : 1,
              cursor: (!dirty && !savedFlash) || saving ? 'default' : 'pointer',
              background: savedFlash ? '#8FBFA0' : '#7298C7',
              color: 'white',
              borderRadius: 10,
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              transition: 'all 180ms var(--ease)',
            }}
          >
            {saving
              ? <span className="spinner" style={{ borderTopColor: '#FFF', borderColor: 'rgba(255,255,255,0.4)' }} />
              : <Icon name={savedFlash ? 'check' : 'edit'} size={14} />}
            {saving ? 'Saving' : savedFlash ? 'Saved' : 'Save changes'}
          </button>
        </div>
      </div>
    </div>
  );
}

function FocusInput({ value, onChange, placeholder }) {
  const [f, setF] = useState(false);
  return (
    <input
      style={{
        ...tplStyles.input,
        borderColor: f ? 'var(--blue-grey)' : 'var(--border-strong)',
        boxShadow: f ? '0 0 0 3px var(--blue-grey-50)' : 'none',
      }}
      value={value || ''}
      onChange={e => onChange(e.target.value)}
      onFocus={() => setF(true)}
      onBlur={() => setF(false)}
      placeholder={placeholder}
    />
  );
}

function FocusTextarea({ value, onChange, placeholder }) {
  const [f, setF] = useState(false);
  return (
    <textarea
      style={{
        ...tplStyles.textarea,
        borderColor: f ? 'var(--blue-grey)' : 'var(--border-strong)',
        boxShadow: f ? '0 0 0 3px var(--blue-grey-50)' : 'none',
      }}
      value={value || ''}
      onChange={e => onChange(e.target.value)}
      onFocus={() => setF(true)}
      onBlur={() => setF(false)}
      placeholder={placeholder}
    />
  );
}
