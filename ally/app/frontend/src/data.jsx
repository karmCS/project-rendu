// API client + helpers.
//
// API base resolution order:
//   1. window.RENDU_API_BASE (runtime override — set before main.jsx loads)
//   2. import.meta.env.VITE_API_BASE (build-time, e.g. dev points to :8000)
//   3. '' (same-origin — what the production build uses, since FastAPI serves both)

const API_BASE =
  (typeof window !== 'undefined' && window.RENDU_API_BASE) ||
  import.meta.env.VITE_API_BASE ||
  '';

export const FORMAT_TYPE_TO_LABEL = {
  epic: 'Epic',
  soap: 'SOAP',
  dap: 'DAP',
  progress: 'Progress Note',
  custom: 'Custom',
};

export const LABEL_TO_FORMAT_TYPE = {
  Epic: 'epic',
  SOAP: 'soap',
  DAP: 'dap',
  'Progress Note': 'progress',
  Custom: 'custom',
};

export const COLUMNS = [
  { key: 'unsynced',   title: 'Unsynced',         subtitle: 'On the Pi, awaiting sync' },
  { key: 'processing', title: 'Processing',       subtitle: 'AI is formatting the note' },
  { key: 'ready',      title: 'Ready to Review',  subtitle: 'Waiting for your eyes' },
  { key: 'done',       title: 'Done',             subtitle: 'Pasted into Epic' },
];

export const TYPE_BADGES = {
  Epic: { bg: '#FBF1D2', fg: '#8B6F2A' },
  SOAP: { bg: '#FBF1D2', fg: '#8B6F2A' },
  DAP:  { bg: '#FBF1D2', fg: '#8B6F2A' },
  'Progress Note': { bg: '#F4F4F4', fg: '#5A5A5A' },
  Custom: { bg: '#F4F4F4', fg: '#5A5A5A' },
};

function adaptNote(api) {
  return {
    id: api.id,
    status: api.status,
    recordedAt: api.recorded_at,
    duration: api.duration_seconds || 0,
    template: api.template_name || 'Custom',
    templateId: api.template_id,
    preview: api.processed_note_preview || '',
    transcript: api.raw_transcript || '',
    processed: api.processed_note || '',
    filename: api.filename,
    label: api.label || api.filename,
    createdAt: api.created_at,
    processedAt: api.processed_at,
  };
}

function adaptTemplate(api) {
  return {
    id: api.id,
    name: api.name,
    type: FORMAT_TYPE_TO_LABEL[api.format_type] || 'Custom',
    isDefault: !!api.is_default,
    structure: api.template_text || '',
  };
}

function templateToApi(t) {
  return {
    name: t.name || 'Untitled Template',
    format_type: LABEL_TO_FORMAT_TYPE[t.type] || 'custom',
    template_text: t.structure || '',
    is_default: !!t.isDefault,
  };
}

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: options.body && !(options.body instanceof FormData)
      ? { 'Content-Type': 'application/json', ...(options.headers || {}) }
      : (options.headers || {}),
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    const err = new Error(`HTTP ${res.status} ${path}: ${text}`);
    err.status = res.status;
    throw err;
  }
  if (res.status === 204) return null;
  const ct = res.headers.get('content-type') || '';
  return ct.includes('application/json') ? res.json() : res.text();
}

export const RENDU_API = {
  // Notes
  async listNotes() {
    const data = await request('/notes');
    return data.map(adaptNote);
  },
  async getNote(id) {
    return adaptNote(await request(`/notes/${id}`));
  },
  async setNoteStatus(id, status) {
    return adaptNote(await request(`/notes/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    }));
  },
  async deleteNote(id) {
    return request(`/notes/${id}`, { method: 'DELETE' });
  },
  async reprocessNote(id, templateId) {
    return adaptNote(await request(`/notes/${id}/reprocess`, {
      method: 'POST',
      body: JSON.stringify({ template_id: templateId }),
    }));
  },
  audioUrl(id) {
    return `${API_BASE}/notes/${id}/audio`;
  },

  // Templates
  async listTemplates() {
    const data = await request('/templates');
    return data.map(adaptTemplate);
  },
  async createTemplate(t) {
    return adaptTemplate(await request('/templates', {
      method: 'POST',
      body: JSON.stringify(templateToApi(t)),
    }));
  },
  async updateTemplate(id, t) {
    return adaptTemplate(await request(`/templates/${id}`, {
      method: 'PUT',
      body: JSON.stringify(templateToApi(t)),
    }));
  },
  async deleteTemplate(id) {
    return request(`/templates/${id}`, { method: 'DELETE' });
  },

  // Settings
  async getSettings() {
    return request('/settings');
  },
  async updateSettings(payload) {
    return request('/settings', {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  },
  async purgeDone() {
    return request('/settings/purge-done', { method: 'POST' });
  },
  async pingOllama() {
    try {
      const r = await request('/settings/ollama-ping');
      return !!(r && r.reachable);
    } catch {
      return false;
    }
  },

  // Health
  async health() {
    try {
      const r = await request('/health');
      return !!(r && r.ok);
    } catch {
      return false;
    }
  },
};

export function formatDateTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  const date = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  const time = d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
  return `${date} · ${time}`;
}

export function formatDuration(seconds) {
  const total = Math.max(0, Math.floor(seconds || 0));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}m ${String(s).padStart(2, '0')}s`;
}

export function formatLastSynced(iso) {
  if (!iso) return 'No notes synced yet';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return 'No notes synced yet';
  const date = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  const time = d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
  return `${date} · ${time}`;
}

export function formatTimestamp(seconds) {
  const total = Math.max(0, Math.floor(seconds || 0));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}
