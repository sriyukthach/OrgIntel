/**
 * OrgIntel Frontend API Configuration & Client
 * Manages REST communication with backend services.
 * 
 * Target resolution hierarchy:
 * 1. Runtime override: window.ORGINTEL_API_BASE
 * 2. LocalStorage override: localStorage.getItem('ORGINTEL_API_BASE')
 * 3. Local standalone dev server (e.g. localhost:5173) -> http://localhost:8000/api
 * 4. Integrated FastAPI server (port 8000 / relative) -> /api
 * 5. Production hosted without configuration -> null (explicitly prompts user)
 */

const getApiBase = () => {
  if (typeof window !== 'undefined') {
    // 1. Runtime override
    if (window.ORGINTEL_API_BASE) {
      return window.ORGINTEL_API_BASE.replace(/\/+$/, '');
    }

    // 2. LocalStorage override
    try {
      const stored = localStorage.getItem('ORGINTEL_API_BASE');
      if (stored) return stored.replace(/\/+$/, '');
    } catch (_) {}

    const hostname = window.location.hostname || 'localhost';
    const port = window.location.port;

    // 3. Local standalone dev server (e.g. localhost:5173, 127.0.0.1:3000)
    if ((hostname === 'localhost' || hostname === '127.0.0.1') && port && port !== '8000') {
      return `http://${hostname}:8000/api`;
    }

    // 4. Integrated FastAPI hosting on port 8000 or same-origin local hosting
    if (port === '8000' || hostname === 'localhost' || hostname === '127.0.0.1') {
      return '/api';
    }

    // 5. Remote production deployment (e.g. GitHub Pages) with no configured backend URL
    return null;
  }

  return '/api';
};

const API_BASE = getApiBase();

function ensureApiConfigured() {
  if (!API_BASE) {
    throw new Error(
      'OrgIntel backend API endpoint is not configured for this remote deployment. ' +
      'Please set window.ORGINTEL_API_BASE or localStorage.setItem("ORGINTEL_API_BASE", "https://your-backend.url/api") with your deployed FastAPI backend URL.'
    );
  }
}

const OrgIntelAPI = {
  async checkHealth() {
    if (!API_BASE) {
      return {
        status: 'unconfigured',
        database_connected: false,
        message: 'Backend URL not configured on GitHub Pages. Set window.ORGINTEL_API_BASE with your deployed backend URL.',
      };
    }
    try {
      const res = await fetch(`${API_BASE}/health`);
      if (!res.ok) throw new Error('Health check failed');
      return await res.json();
    } catch (err) {
      console.warn('Backend offline:', err);
      return { status: 'offline', database_connected: false };
    }
  },

  async researchCompany(orgNumber, forceRefresh = false) {
    ensureApiConfigured();
    const res = await fetch(`${API_BASE}/research`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        organization_number: orgNumber,
        force_refresh: forceRefresh,
      }),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Research failed to resolve company.');
    }
    return data;
  },

  async getCompany(orgNumber) {
    ensureApiConfigured();
    const res = await fetch(`${API_BASE}/companies/${orgNumber}`);
    if (!res.ok) throw new Error(`Company ${orgNumber} not found.`);
    return await res.json();
  },

  async getRecentCompanies(limit = 50) {
    ensureApiConfigured();
    const res = await fetch(`${API_BASE}/companies?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to load recent companies.');
    return await res.json();
  },

  async getCompanyHistory(orgNumber) {
    ensureApiConfigured();
    const res = await fetch(`${API_BASE}/companies/${orgNumber}/history`);
    if (!res.ok) throw new Error('Failed to fetch snapshot history.');
    return await res.json();
  },

  async runBatchResearch(orgNumbers, concurrency = 5) {
    ensureApiConfigured();
    const res = await fetch(`${API_BASE}/research/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        organization_numbers: orgNumbers,
        concurrency: concurrency,
      }),
    });
    if (!res.ok) throw new Error('Batch research execution failed.');
    return await res.json();
  },
};
