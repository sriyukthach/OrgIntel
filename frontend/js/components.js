/**
 * OrgIntel UI Component Renderers
 * Pure JavaScript component rendering functions aligned with Enterprise Intelligence Design System.
 */

const UIComponents = {
  renderTimelineStep(stepName, detail, status) {
    let markerClass = 'pending';
    let markerContent = '○';

    if (status === 'COMPLETED' || status === 'DONE') {
      markerClass = 'done';
      markerContent = '✓';
    } else if (status === 'RUNNING' || status === 'IN_PROGRESS') {
      markerClass = 'running';
      markerContent = '●';
    } else if (status === 'FAILED') {
      markerClass = 'pending';
      markerContent = '✕';
    }

    return `
      <div class="investigation-step">
        <div class="step-marker ${markerClass}">${markerContent}</div>
        <div class="step-content">
          <div class="step-name">${this.escapeHtml(stepName)}</div>
          <div class="step-desc">${this.escapeHtml(detail)}</div>
        </div>
      </div>
    `;
  },

  renderFactRow(fact, index) {
    let statusSlug = (fact.verification_status || 'verified').toLowerCase().replace('_', '-');
    let statusDisplay = (fact.verification_status || 'VERIFIED').replace('_', ' ');
    const confPct = Math.round((fact.confidence || 1.0) * 100);

    return `
      <tr>
        <td><code style="font-weight: 600; color: var(--text-primary);">${this.escapeHtml(fact.field)}</code></td>
        <td><strong style="color: var(--text-primary);">${this.escapeHtml(String(fact.value))}</strong></td>
        <td><span class="badge-status ${statusSlug}">${statusDisplay}</span></td>
        <td class="text-mono">${confPct}%</td>
        <td>
          <a href="${this.escapeHtml(fact.source_url)}" target="_blank" class="source-anchor" style="font-size: 0.8rem;">
            ${this.escapeHtml(fact.source_title || 'Public Source')} ↗
          </a>
        </td>
        <td>
          <button type="button" class="btn-secondary inspect-evidence-btn" data-fact-idx="${index}" style="font-size: 0.75rem; padding: 0.25rem 0.6rem;">
            View Evidence
          </button>
        </td>
      </tr>
    `;
  },

  renderLeadershipCard(person) {
    const isOrg = Boolean(person.is_organization || person.organization_number);
    return `
      <div class="person-card">
        <div class="person-role-tag">${this.escapeHtml(person.role || 'Executive / Board')}</div>
        <div class="person-name">${this.escapeHtml(person.name)}</div>
        <div class="person-meta">
          ${isOrg 
            ? `<span class="entity-type-badge">ORGANIZATION</span><span>${person.organization_number ? `Org: ${this.escapeHtml(person.organization_number)}` : 'Corporate Entity'}</span>` 
            : `<span class="entity-type-badge">PERSON</span>${person.birth_year ? `<span>Born: ${this.escapeHtml(person.birth_year)}</span>` : '<span>Verified Individual</span>'}`
          }
        </div>
      </div>
    `;
  },

  renderFinancialRow(fin) {
    const formatNumber = (val) => {
      if (val === null || val === undefined) return '<span class="text-muted">N/A</span>';
      return `${Number(val).toLocaleString('nb-NO')} ${fin.currency || 'NOK'}`;
    };

    return `
      <tr>
        <td><strong class="text-mono">FY${fin.reporting_year}</strong></td>
        <td class="text-mono">${formatNumber(fin.revenue)}</td>
        <td class="text-mono">${formatNumber(fin.operating_result)}</td>
        <td class="text-mono">${formatNumber(fin.profit_loss)}</td>
        <td class="text-mono">${formatNumber(fin.total_assets)}</td>
        <td class="text-mono">${formatNumber(fin.equity)}</td>
        <td><span class="badge-status verified">VERIFIED</span></td>
      </tr>
    `;
  },

  renderActivityItem(act) {
    return `
      <div class="source-evidence-card">
        <div class="evidence-top-bar">
          <span class="domain-pill">${this.escapeHtml(act.activity_type || 'Announcement')}</span>
          <span class="evidence-timestamp">${this.escapeHtml(act.date || 'Recent Notice')}</span>
        </div>
        <h4 class="evidence-title">${this.escapeHtml(act.title)}</h4>
        <p style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.5;">${this.escapeHtml(act.summary)}</p>
        <div class="mt-3">
          <a href="${this.escapeHtml(act.source_url)}" target="_blank" class="source-anchor" style="font-size: 0.8rem;">
            View Official Registry Notice ↗
          </a>
        </div>
      </div>
    `;
  },

  renderEvidenceCard(ev) {
    const formattedDate = ev.retrieval_timestamp ? ev.retrieval_timestamp.slice(0, 19).replace('T', ' ') : 'Live Retrieval';
    return `
      <div class="source-evidence-card">
        <div class="evidence-top-bar">
          <span class="domain-pill">${this.escapeHtml(ev.publisher_domain || 'data.brreg.no')}</span>
          <span class="evidence-timestamp text-mono">Audited: ${this.escapeHtml(formattedDate)} UTC</span>
        </div>
        <h4 class="evidence-title">
          ${this.escapeHtml(ev.source_title || ev.source_url)}
        </h4>
        <blockquote class="evidence-quote-box">
          "${this.escapeHtml(ev.evidence_excerpt || 'No specific excerpt text.')}"
        </blockquote>
        <div class="evidence-footer">
          <div class="supported-fields-tags">
            <span class="text-xs text-muted" style="align-self: center;">Supported facts:</span>
            ${(ev.supported_fields || []).map(f => `<span class="field-tag">${this.escapeHtml(f)}</span>`).join('')}
          </div>
          <a href="${this.escapeHtml(ev.source_url)}" target="_blank" class="btn-secondary" style="font-size: 0.75rem; padding: 0.25rem 0.6rem;">
            Open Public Source ↗
          </a>
        </div>
      </div>
    `;
  },

  renderSnapshotDiff(snapshot) {
    const ts = snapshot.timestamp ? snapshot.timestamp.slice(0, 19).replace('T', ' ') : 'Initial Snapshot';
    const prof = snapshot.profile || {};
    const ident = prof.canonical_identity || {};

    return `
      <div class="source-evidence-card">
        <div class="evidence-top-bar">
          <span class="badge-status verified">SNAPSHOT ${this.escapeHtml(snapshot.id || '')}</span>
          <span class="evidence-timestamp text-mono">${ts} UTC</span>
        </div>
        <div style="font-size: 0.9rem; margin-top: 0.5rem;">
          <strong>${this.escapeHtml(ident.legal_name || 'Organization')}</strong> • Status: <span class="badge-status verified">${this.escapeHtml(ident.registration_status || 'Active')}</span>
        </div>
        <div class="text-xs text-muted mt-2" style="font-family: var(--font-mono);">
          Verified Facts: ${prof.facts ? prof.facts.length : 0} | Content Hash: <code>${snapshot.content_hash || 'SHA-256'}</code>
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
