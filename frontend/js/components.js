/**
 * OrgIntel UI Component Renderers
 * Pure JavaScript component rendering functions.
 */

const UIComponents = {
  renderTimelineStep(stepName, detail, status) {
    let iconClass = 'step-pending';
    let iconContent = '○';

    if (status === 'COMPLETED' || status === 'DONE') {
      iconClass = 'step-done';
      iconContent = '✓';
    } else if (status === 'RUNNING' || status === 'IN_PROGRESS') {
      iconClass = 'step-running';
      iconContent = '●';
    } else if (status === 'FAILED') {
      iconClass = 'step-failed';
      iconContent = '✗';
    }

    return `
      <div class="timeline-step">
        <div class="step-icon ${iconClass}">${iconContent}</div>
        <div class="step-text">
          <div class="step-title">${this.escapeHtml(stepName)}</div>
          <div class="step-detail">${this.escapeHtml(detail)}</div>
        </div>
      </div>
    `;
  },

  renderFactRow(fact, index) {
    const vClass = `v-${(fact.verification_status || 'verified').toLowerCase().replace('_', '-')}`;
    const confPct = Math.round((fact.confidence || 1.0) * 100);

    return `
      <tr>
        <td><code class="font-semibold">${this.escapeHtml(fact.field)}</code></td>
        <td><strong>${this.escapeHtml(String(fact.value))}</strong></td>
        <td><span class="v-badge ${vClass}">${fact.verification_status}</span></td>
        <td>${confPct}%</td>
        <td>
          <a href="${this.escapeHtml(fact.source_url)}" target="_blank" class="source-link text-xs">
            ${this.escapeHtml(fact.source_title || 'Public Source')}
          </a>
        </td>
        <td>
          <button class="btn-secondary btn-sm inspect-evidence-btn" data-fact-idx="${index}">
            View Evidence
          </button>
        </td>
      </tr>
    `;
  },

  renderLeadershipCard(person) {
    return `
      <div class="leadership-card">
        <div class="lead-role">${this.escapeHtml(person.role || 'Board / Executive')}</div>
        <div class="lead-name">${this.escapeHtml(person.name)}</div>
        <div class="lead-meta">
          ${person.birth_year ? `<span>Born: ${person.birth_year}</span> • ` : ''}
          <span class="text-xs text-muted">Verified in Brreg Roller</span>
        </div>
      </div>
    `;
  },

  renderFinancialRow(fin) {
    const formatNumber = (val) => {
      if (val === null || val === undefined) return '<span class="text-muted">N/A</span>';
      return `${Number(val).toLocaleString()} ${fin.currency || 'NOK'}`;
    };

    return `
      <tr>
        <td><strong>FY${fin.reporting_year}</strong></td>
        <td>${formatNumber(fin.revenue)}</td>
        <td>${formatNumber(fin.operating_result)}</td>
        <td>${formatNumber(fin.profit_loss)}</td>
        <td>${formatNumber(fin.total_assets)}</td>
        <td>${formatNumber(fin.equity)}</td>
        <td><span class="v-badge v-verified">VERIFIED</span></td>
      </tr>
    `;
  },

  renderActivityItem(act) {
    return `
      <div class="evidence-card">
        <div class="evidence-header">
          <span class="evidence-domain">${this.escapeHtml(act.activity_type || 'Announcement')}</span>
          <span class="text-xs text-muted">${this.escapeHtml(act.date || 'Recent')}</span>
        </div>
        <h4 class="font-semibold text-slate-900">${this.escapeHtml(act.title)}</h4>
        <p class="text-sm text-slate-700 mt-2">${this.escapeHtml(act.summary)}</p>
        <div class="mt-2">
          <a href="${this.escapeHtml(act.source_url)}" target="_blank" class="source-link text-xs">View Registry Notice &rarr;</a>
        </div>
      </div>
    `;
  },

  renderEvidenceCard(ev) {
    return `
      <div class="evidence-card">
        <div class="evidence-header">
          <span class="evidence-domain">${this.escapeHtml(ev.publisher_domain || 'brreg.no')}</span>
          <span class="text-xs text-muted">Audited: ${this.escapeHtml(ev.retrieval_timestamp.slice(0, 19).replace('T', ' '))}</span>
        </div>
        <h4 class="font-semibold text-slate-900">
          <a href="${this.escapeHtml(ev.source_url)}" target="_blank" class="source-link">
            ${this.escapeHtml(ev.source_title || ev.source_url)}
          </a>
        </h4>
        <blockquote class="evidence-excerpt-quote">
          "${this.escapeHtml(ev.evidence_excerpt || 'No excerpt available')}"
        </blockquote>
        <div class="mt-2 flex gap-1 flex-wrap">
          <span class="text-xs text-muted">Supports fields:</span>
          ${(ev.supported_fields || []).map(f => `<span class="badge badge-subtle text-xs">${this.escapeHtml(f)}</span>`).join(' ')}
        </div>
      </div>
    `;
  },

  renderSnapshotDiff(snapshot) {
    const ts = snapshot.timestamp ? snapshot.timestamp.slice(0, 19).replace('T', ' ') : 'Snapshot';
    const prof = snapshot.profile || {};
    const ident = prof.canonical_identity || {};

    return `
      <div class="evidence-card">
        <div class="evidence-header">
          <span class="badge badge-confidence">${this.escapeHtml(snapshot.id)}</span>
          <span class="text-xs text-muted font-mono">${ts} UTC</span>
        </div>
        <div class="text-sm">
          <strong>${this.escapeHtml(ident.legal_name || 'Company')}</strong> • Status: ${this.escapeHtml(ident.registration_status || 'Active')}
        </div>
        <div class="text-xs text-muted mt-2">
          Verified Facts: ${prof.facts ? prof.facts.length : 0} | Content Hash: <code>${snapshot.content_hash || ''}</code>
        </div>
      </div>
    `;
  },

  escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  },
};
