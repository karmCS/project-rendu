// Note Detail view — opens when a kanban card is clicked.
// Wired to a real <audio> element + real /reprocess + real /status.
import { useEffect, useMemo, useRef, useState } from 'react';
import { Icon } from './icons.jsx';
import { RENDU_API, TYPE_BADGES, formatDateTime, formatDuration, formatTimestamp } from './data.jsx';
import { cardStyles } from './cardStyles.js';

const detailStyles = {
  overlay: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(45, 45, 45, 0.32)',
    backdropFilter: 'blur(4px)',
    WebkitBackdropFilter: 'blur(4px)',
    zIndex: 60,
    animation: 'overlayIn 240ms var(--ease)',
  },
  panel: {
    position: 'fixed',
    top: 0,
    right: 0,
    bottom: 0,
    width: 'min(1100px, 92vw)',
    background: 'var(--page-bg)',
    boxShadow: '-8px 0 32px rgba(45,45,45,0.14)',
    zIndex: 61,
    display: 'flex',
    flexDirection: 'column',
    animation: 'panelIn 320ms var(--ease)',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '20px 36px',
    background: 'var(--page-bg)',
    borderBottom: '1px solid var(--border)',
    flexShrink: 0,
  },
  back: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    color: 'var(--muted)',
    fontSize: 13,
    fontWeight: 500,
  },
  body: {
    flex: 1,
    display: 'grid',
    gridTemplateColumns: '1fr 1.15fr',
    gap: 0,
    overflow: 'hidden',
  },
  leftCol: {
    padding: '36px 40px',
    overflow: 'auto',
    borderRight: '1px solid var(--border)',
    background: 'var(--page-bg)',
    display: 'flex',
    flexDirection: 'column',
    gap: 28,
  },
  rightCol: {
    padding: '36px 40px',
    overflow: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: 20,
    background: 'var(--white)',
  },
  sectionLabel: {
    fontFamily: "'Lora', Georgia, serif",
    fontSize: 17,
    fontWeight: 500,
    letterSpacing: '-0.01em',
    color: 'var(--dark)',
    marginBottom: 12,
  },
  player: {
    background: 'var(--white)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius)',
    padding: 16,
    boxShadow: 'var(--shadow-sm)',
  },
  playerRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 14,
  },
  playBtn: {
    width: 40,
    height: 40,
    borderRadius: '50%',
    background: 'var(--blue-grey)',
    color: 'var(--white)',
    display: 'grid',
    placeItems: 'center',
    transition: 'all 200ms var(--ease)',
    boxShadow: '0 2px 6px rgba(74, 110, 158, 0.25)',
    flexShrink: 0,
  },
  scrubber: {
    flex: 1,
    height: 4,
    background: 'var(--blue-grey-100)',
    borderRadius: 999,
    cursor: 'pointer',
    position: 'relative',
    overflow: 'hidden',
  },
  scrubberFill: {
    position: 'absolute',
    inset: 0,
    background: 'linear-gradient(90deg, var(--blue-grey) 0%, var(--blue-grey-600) 100%)',
    borderRadius: 999,
    transformOrigin: 'left center',
    transition: 'transform 80ms linear',
  },
  timestamp: {
    fontSize: 12,
    fontVariantNumeric: 'tabular-nums',
    color: 'var(--muted)',
    minWidth: 78,
    textAlign: 'right',
  },
  waveform: {
    display: 'flex',
    alignItems: 'center',
    gap: 2,
    height: 32,
    marginTop: 14,
    cursor: 'pointer',
  },
  waveBar: {
    flex: 1,
    background: 'var(--blue-grey-100)',
    borderRadius: 1,
    transition: 'background 200ms var(--ease)',
  },
  transcriptToggle: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    width: '100%',
    padding: '12px 14px',
    background: 'var(--white)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius)',
    fontSize: 13,
    fontWeight: 500,
    color: 'var(--dark)',
    transition: 'all 180ms var(--ease)',
  },
  transcriptBody: {
    background: 'var(--white)',
    border: '1px solid var(--border)',
    borderTop: 'none',
    borderRadius: '0 0 var(--radius) var(--radius)',
    padding: '18px 22px',
    fontSize: 14,
    lineHeight: 1.75,
    color: 'var(--dark-soft)',
    fontFamily: "'Lora', Georgia, serif",
    maxHeight: 360,
    overflow: 'auto',
    marginTop: -1,
    whiteSpace: 'pre-wrap',
  },
  templateSelect: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
    padding: '10px 14px',
    background: 'var(--white)',
    border: '1px solid var(--border-strong)',
    borderRadius: 'var(--radius)',
    fontSize: 13,
    cursor: 'pointer',
    transition: 'border-color 160ms',
  },
  noteTextarea: {
    flex: 1,
    minHeight: 380,
    width: '100%',
    padding: '22px 24px',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius)',
    background: 'var(--page-bg)',
    fontFamily: "'Lora', Georgia, serif",
    fontSize: 14.5,
    lineHeight: 1.75,
    color: 'var(--dark)',
    resize: 'vertical',
    outline: 'none',
    transition: 'border-color 160ms, background 160ms',
    whiteSpace: 'pre-wrap',
  },
  actions: {
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
    paddingTop: 8,
  },
};

function AudioPlayer({ src, fallbackDuration }) {
  const audioRef = useRef(null);
  const [playing, setPlaying] = useState(false);
  const [current, setCurrent] = useState(0);
  const [duration, setDuration] = useState(fallbackDuration || 0);
  const [errored, setErrored] = useState(false);

  useEffect(() => {
    const el = audioRef.current;
    if (!el) return;
    const onTime = () => setCurrent(el.currentTime || 0);
    const onMeta = () => {
      if (Number.isFinite(el.duration) && el.duration > 0) setDuration(el.duration);
    };
    const onEnd = () => { setPlaying(false); setCurrent(0); };
    const onErr = () => setErrored(true);
    el.addEventListener('timeupdate', onTime);
    el.addEventListener('loadedmetadata', onMeta);
    el.addEventListener('ended', onEnd);
    el.addEventListener('error', onErr);
    return () => {
      el.removeEventListener('timeupdate', onTime);
      el.removeEventListener('loadedmetadata', onMeta);
      el.removeEventListener('ended', onEnd);
      el.removeEventListener('error', onErr);
    };
  }, [src]);

  const toggle = () => {
    const el = audioRef.current;
    if (!el || errored) return;
    if (playing) { el.pause(); setPlaying(false); }
    else { el.play().then(() => setPlaying(true)).catch(() => setErrored(true)); }
  };

  const seekTo = (frac) => {
    const el = audioRef.current;
    if (!el || !duration) return;
    el.currentTime = Math.max(0, Math.min(duration, frac * duration));
    setCurrent(el.currentTime);
  };

  const pct = duration ? Math.min(1, current / duration) : 0;
  const bars = useMemo(
    () => Array.from({ length: 60 }, (_, i) => 0.2 + 0.8 * Math.abs(Math.sin(i * 0.7) * Math.cos(i * 0.3))),
    []
  );

  return (
    <div style={detailStyles.player}>
      <audio ref={audioRef} src={src} preload="metadata" style={{ display: 'none' }} />
      <div style={detailStyles.playerRow}>
        <button
          style={detailStyles.playBtn}
          onClick={toggle}
          onMouseEnter={e => e.currentTarget.style.transform = 'scale(1.06)'}
          onMouseLeave={e => e.currentTarget.style.transform = 'scale(1)'}
          aria-label={playing ? 'Pause' : 'Play'}
          disabled={errored}
        >
          <Icon name={playing ? 'pause' : 'play'} size={16} />
        </button>
        <div
          style={detailStyles.scrubber}
          onClick={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            seekTo((e.clientX - rect.left) / rect.width);
          }}
        >
          <div style={{ ...detailStyles.scrubberFill, transform: `scaleX(${pct})` }} />
        </div>
        <div style={detailStyles.timestamp}>
          {formatTimestamp(current)} / {formatTimestamp(duration)}
        </div>
      </div>
      <div
        style={detailStyles.waveform}
        onClick={(e) => {
          const rect = e.currentTarget.getBoundingClientRect();
          seekTo((e.clientX - rect.left) / rect.width);
        }}
      >
        {bars.map((h, i) => {
          const active = i / bars.length <= pct;
          return (
            <div
              key={i}
              style={{
                ...detailStyles.waveBar,
                height: `${h * 100}%`,
                background: active ? 'var(--blue-grey)' : 'var(--blue-grey-100)',
                opacity: playing && active && i / bars.length > pct - 0.04 ? 0.6 : 1,
              }}
            />
          );
        })}
      </div>
      {errored && (
        <div style={{ marginTop: 10, fontSize: 12, color: '#C25D5D' }}>
          Audio unavailable.
        </div>
      )}
    </div>
  );
}

export default function NoteDetail({ note, templates, onClose, onMarkDone, onReprocess, onCopy }) {
  const [transcriptOpen, setTranscriptOpen] = useState(false);
  const [tplOpen, setTplOpen] = useState(false);
  const [activeTemplateId, setActiveTemplateId] = useState(note.templateId);
  const [activeTemplateName, setActiveTemplateName] = useState(note.template);
  const [noteText, setNoteText] = useState(note.processed || '');
  const [reprocessing, setReprocessing] = useState(false);
  const [copied, setCopied] = useState(false);
  const [textareaFocused, setTextareaFocused] = useState(false);
  const [reprocessErr, setReprocessErr] = useState(null);

  // Sync local state when note prop changes (e.g. after a successful reprocess).
  useEffect(() => {
    setActiveTemplateId(note.templateId);
    setActiveTemplateName(note.template);
    setNoteText(note.processed || '');
  }, [note.id, note.processed, note.templateId, note.template]);

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const handleCopy = () => {
    navigator.clipboard?.writeText(noteText).catch(() => {});
    setCopied(true);
    onCopy?.();
    setTimeout(() => setCopied(false), 1800);
  };

  const handleTemplateChange = async (tpl) => {
    setTplOpen(false);
    if (tpl.id === activeTemplateId) return;
    setActiveTemplateId(tpl.id);
    setActiveTemplateName(tpl.name);
    setReprocessing(true);
    setReprocessErr(null);
    try {
      await onReprocess(note.id, tpl.id);
    } catch (err) {
      setReprocessErr('Reprocess failed — Ollama may be down. Try again.');
    } finally {
      setReprocessing(false);
    }
  };

  const tplBadge = (() => {
    if (activeTemplateName?.startsWith('Epic')) return TYPE_BADGES.Epic;
    if (activeTemplateName === 'SOAP Note') return TYPE_BADGES.SOAP;
    if (activeTemplateName === 'DAP Note') return TYPE_BADGES.DAP;
    return TYPE_BADGES.Custom;
  })();

  const audioSrc = RENDU_API.audioUrl(note.id);

  return (
    <>
      <div style={detailStyles.overlay} onClick={onClose} />
      <div style={detailStyles.panel}>
        <div style={detailStyles.header}>
          <button
            style={detailStyles.back}
            onClick={onClose}
            onMouseEnter={e => e.currentTarget.style.color = 'var(--dark)'}
            onMouseLeave={e => e.currentTarget.style.color = 'var(--muted)'}
          >
            <Icon name="chevronLeft" size={14} />
            Back to board
          </button>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14, minWidth: 0 }}>
            <span
              style={{
                fontFamily: "'Lora', Georgia, serif",
                fontSize: 17,
                fontWeight: 500,
                letterSpacing: '-0.01em',
                color: 'var(--dark)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                maxWidth: 360,
              }}
              title={note.label}
            >
              {note.label}
            </span>
            <span style={{ width: 1, height: 14, background: 'var(--border-strong)' }} />
            <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--dark)' }}>
              {formatDateTime(note.recordedAt)}
            </span>
            <span style={{ width: 1, height: 14, background: 'var(--border-strong)' }} />
            <span style={{ fontSize: 12, color: 'var(--muted)' }}>
              {formatDuration(note.duration)}
            </span>
            <span style={{ ...cardStyles.badge, background: tplBadge.bg, color: tplBadge.fg }}>
              {activeTemplateName}
            </span>
          </div>
        </div>

        <div style={detailStyles.body}>
          {/* LEFT: Audio + Transcript */}
          <div style={detailStyles.leftCol}>
            <div>
              <div style={detailStyles.sectionLabel}>Recording</div>
              <AudioPlayer src={audioSrc} fallbackDuration={note.duration} />
            </div>

            <div>
              <button
                style={{
                  ...detailStyles.transcriptToggle,
                  borderRadius: transcriptOpen ? 'var(--radius) var(--radius) 0 0' : 'var(--radius)',
                }}
                onClick={() => setTranscriptOpen(o => !o)}
              >
                <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Icon name="mic" size={14} stroke={1.6} style={{ color: 'var(--muted)' }} />
                  Raw Transcript
                  <span style={{ fontSize: 11, color: 'var(--muted)', fontWeight: 400, marginLeft: 6 }}>Whisper.cpp</span>
                </span>
                <span style={{ transform: transcriptOpen ? 'rotate(180deg)' : 'none', transition: 'transform 220ms var(--ease)', display: 'flex' }}>
                  <Icon name="chevronDown" size={14} />
                </span>
              </button>
              {transcriptOpen && (
                <div style={{ ...detailStyles.transcriptBody, animation: 'slideDown 240ms var(--ease)' }}>
                  {note.transcript || 'Transcript unavailable for this note.'}
                </div>
              )}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11.5, color: 'var(--muted)', marginTop: 'auto', paddingTop: 8 }}>
              <Icon name="clock" size={11} />
              Synced from Pi · {formatDateTime(note.createdAt)}
            </div>
          </div>

          {/* RIGHT: Processed note */}
          <div style={detailStyles.rightCol}>
            <div>
              <div style={detailStyles.sectionLabel}>Template</div>
              <div style={{ position: 'relative' }}>
                <button
                  style={{
                    ...detailStyles.templateSelect,
                    width: '100%',
                    borderColor: tplOpen ? 'var(--blue-grey)' : 'var(--border-strong)',
                  }}
                  onClick={() => setTplOpen(o => !o)}
                >
                  <span style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ ...cardStyles.badge, background: tplBadge.bg, color: tplBadge.fg, fontSize: 10 }}>
                      {activeTemplateName?.startsWith('Epic') ? 'Epic' : activeTemplateName?.replace(' Note', '')}
                    </span>
                    <span style={{ fontWeight: 500 }}>{activeTemplateName}</span>
                    {reprocessing && (
                      <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--muted)', fontSize: 11.5 }}>
                        <span className="spinner" />
                        Reprocessing
                      </span>
                    )}
                  </span>
                  <span style={{ transform: tplOpen ? 'rotate(180deg)' : 'none', transition: 'transform 200ms', display: 'flex', color: 'var(--muted)' }}>
                    <Icon name="chevronDown" size={14} />
                  </span>
                </button>
                {tplOpen && (
                  <div style={{
                    position: 'absolute',
                    top: 'calc(100% + 4px)',
                    left: 0,
                    right: 0,
                    background: 'var(--white)',
                    border: '1px solid var(--border-strong)',
                    borderRadius: 'var(--radius)',
                    boxShadow: 'var(--shadow-lg)',
                    zIndex: 5,
                    overflow: 'hidden',
                    animation: 'slideDown 200ms var(--ease)',
                  }}>
                    {templates.map(t => {
                      const b = TYPE_BADGES[t.type] || TYPE_BADGES.Custom;
                      const active = t.id === activeTemplateId;
                      return (
                        <button
                          key={t.id}
                          onClick={() => handleTemplateChange(t)}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            width: '100%',
                            padding: '10px 14px',
                            fontSize: 13,
                            background: active ? 'var(--blue-grey-50)' : 'transparent',
                            color: active ? 'var(--blue-grey-700)' : 'var(--dark)',
                            fontWeight: active ? 500 : 400,
                            transition: 'background 140ms',
                          }}
                          onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'var(--light-2)'; }}
                          onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent'; }}
                        >
                          <span style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                            <span style={{ ...cardStyles.badge, background: b.bg, color: b.fg, fontSize: 10 }}>{t.type}</span>
                            {t.name}
                          </span>
                          {active && <Icon name="check" size={14} style={{ color: 'var(--blue-grey)' }} />}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
              {reprocessErr && (
                <div style={{ fontSize: 12, color: '#C25D5D', marginTop: 8 }}>{reprocessErr}</div>
              )}
            </div>

            <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
              <div style={detailStyles.sectionLabel}>Processed Note</div>
              <textarea
                value={noteText}
                onChange={e => setNoteText(e.target.value)}
                onFocus={() => setTextareaFocused(true)}
                onBlur={() => setTextareaFocused(false)}
                style={{
                  ...detailStyles.noteTextarea,
                  borderColor: textareaFocused ? 'var(--blue-grey)' : 'var(--border)',
                  background: textareaFocused ? 'var(--white)' : 'var(--light-2)',
                  boxShadow: textareaFocused ? '0 0 0 3px var(--blue-grey-50)' : 'none',
                  opacity: reprocessing ? 0.5 : 1,
                  pointerEvents: reprocessing ? 'none' : 'auto',
                }}
                placeholder="Processed note will appear here…"
              />
            </div>

            <div style={detailStyles.actions}>
              <button
                className="btn"
                style={{
                  width: '100%',
                  padding: '13px 16px',
                  fontSize: 14,
                  fontWeight: 500,
                  background: copied ? '#8FBFA0' : '#7298C7',
                  color: '#FFFFFF',
                  borderRadius: 10,
                  border: 'none',
                  transition: 'all 180ms var(--ease)',
                }}
                onMouseEnter={e => { if (!copied) e.currentTarget.style.background = '#5C82B3'; }}
                onMouseLeave={e => { if (!copied) e.currentTarget.style.background = '#7298C7'; }}
                onClick={handleCopy}
              >
                <Icon name={copied ? 'check' : 'copy'} size={15} />
                {copied ? 'Copied!' : 'Copy to Clipboard'}
              </button>
              <button
                style={{
                  width: '100%',
                  padding: '11px 16px',
                  fontSize: 13.5,
                  fontWeight: 500,
                  background: 'transparent',
                  color: '#7298C7',
                  border: '1.5px solid #7298C7',
                  borderRadius: 10,
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                  cursor: 'pointer',
                  transition: 'all 180ms var(--ease)',
                }}
                onMouseEnter={e => e.currentTarget.style.background = 'var(--blue-grey-50)'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                onClick={() => onMarkDone(note.id)}
              >
                <Icon name="check" size={14} />
                Mark as Done
              </button>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes overlayIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes panelIn {
          from { transform: translateX(40px); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideDown {
          from { opacity: 0; transform: translateY(-6px); max-height: 0; }
          to { opacity: 1; transform: translateY(0); max-height: 600px; }
        }
      `}</style>
    </>
  );
}
