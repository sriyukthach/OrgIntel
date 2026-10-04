/**
 * OrgIntel Frontend API Client
 * Manages REST communication with backend services.
 */

const API_BASE = (typeof window !== 'undefined' && window.location.port && window.location.port !== '8000')
  ? `http://${window.location.hostname || 'localhost'}:8000/api`
  : '/api';

const OrgIntelAPI = {
  async checkHealth() {
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
    const res = await fetch(`${API_BASE}/companies/${orgNumber}`);
    if (!res.ok) throw new Error(`Company ${orgNumber} not found.`);
    return await res.json();
  },

  async getRecentCompanies(limit = 50) {
    const res = await fetch(`${API_BASE}/companies?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to load recent companies.');
    return await res.json();
  },

  async getCompanyHistory(orgNumber) {
    const res = await fetch(`${API_BASE}/companies/${orgNumber}/history`);
    if (!res.ok) throw new Error('Failed to fetch snapshot history.');
    return await res.json();
  },

  async runBatchResearch(orgNumbers, concurrency = 5) {
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
