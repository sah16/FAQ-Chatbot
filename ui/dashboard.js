/**
 * Pilot Observability & Analytics Dashboard Controller
 */

document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const pilotStatusBadge = document.getElementById("pilotStatusBadge");
  const pilotStatusText = document.getElementById("pilotStatusText");
  const triggerSyncBtn = document.getElementById("triggerSyncBtn");
  const syncBanner = document.getElementById("syncBanner");
  const syncBannerText = document.getElementById("syncBannerText");
  const syncBannerClose = document.getElementById("syncBannerClose");
  const refreshLogsBtn = document.getElementById("refreshLogsBtn");

  // KPI Elements
  const kpiTotalQueries = document.getElementById("kpiTotalQueries");
  const kpiQueryBreakdown = document.getElementById("kpiQueryBreakdown");
  const kpiCitationRate = document.getElementById("kpiCitationRate");
  const kpiSentenceRate = document.getElementById("kpiSentenceRate");
  const kpiAvgLatency = document.getElementById("kpiAvgLatency");
  const kpiLatencyP95 = document.getElementById("kpiLatencyP95");
  const kpiPiiCount = document.getElementById("kpiPiiCount");
  const kpiFreshnessHealth = document.getElementById("kpiFreshnessHealth");

  // Tables & Breakdown
  const freshnessTableBody = document.getElementById("freshnessTableBody");
  const overallRefusalRate = document.getElementById("overallRefusalRate");
  const countAdvisory = document.getElementById("countAdvisory");
  const countComparative = document.getElementById("countComparative");
  const countPrediction = document.getElementById("countPrediction");
  const countOutOfCorpus = document.getElementById("countOutOfCorpus");
  const countMixed = document.getElementById("countMixed");
  const auditTableBody = document.getElementById("auditTableBody");

  // Initial Load
  loadDashboardData();

  // Auto-refresh every 15 seconds
  setInterval(loadDashboardData, 15000);

  if (refreshLogsBtn) {
    refreshLogsBtn.addEventListener("click", () => {
      loadDashboardData();
    });
  }

  if (syncBannerClose) {
    syncBannerClose.addEventListener("click", () => {
      syncBanner.style.display = "none";
    });
  }

  // Trigger Freshness Sync
  if (triggerSyncBtn) {
    triggerSyncBtn.addEventListener("click", async () => {
      triggerSyncBtn.disabled = true;
      triggerSyncBtn.innerHTML = `
        <span class="material-symbols-outlined" style="animation: spin 1s infinite linear;">sync</span>
        <span>Re-indexing Corpus...</span>
      `;

      try {
        const res = await fetch("/api/freshness/run", { method: "POST" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        syncBannerText.textContent = `Freshness Sync Complete: Checked ${data.sources_checked}/${data.total_sources} sources, verified ${data.unchanged_chunks} unchanged chunks, re-embedded ${data.updated_chunks} sections in ${data.duration_seconds}s.`;
        syncBanner.style.display = "flex";

        // Reload fresh metrics
        await loadDashboardData();
      } catch (err) {
        syncBannerText.textContent = `Freshness Sync Error: ${err.message}`;
        syncBanner.style.display = "flex";
      } finally {
        triggerSyncBtn.disabled = false;
        triggerSyncBtn.innerHTML = `
          <span class="material-symbols-outlined">sync</span>
          <span>Trigger Freshness Sync</span>
        `;
      }
    });
  }

  async function loadDashboardData() {
    try {
      const res = await fetch("/api/analytics?limit=30");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      renderDashboard(data);
    } catch (err) {
      console.error("Failed to load analytics:", err);
    }
  }

  function renderDashboard(data) {
    // Pilot Status
    if (pilotStatusText) {
      pilotStatusText.textContent = data.pilot_status;
      if (data.pilot_status.startsWith("GO")) {
        pilotStatusBadge.className = "pilot-status-badge";
      } else {
        pilotStatusBadge.className = "pilot-status-badge status-stale";
      }
    }

    // KPIs
    kpiTotalQueries.textContent = data.total_queries.toLocaleString();
    kpiQueryBreakdown.textContent = `${data.factual_queries} Factual • ${data.refusal_queries} Refusals (${data.refusal_rate_pct}%)`;

    kpiCitationRate.textContent = `${data.citation_coverage_pct}%`;
    kpiSentenceRate.textContent = `${data.sentence_compliance_pct}%`;

    const lat = data.latency || {};
    kpiAvgLatency.textContent = `${Math.round(lat.avg_ms || 0)} ms`;
    kpiLatencyP95.textContent = `p95: ${Math.round(lat.p95_ms || 0)} ms • SLA: <4,000 ms`;

    kpiPiiCount.textContent = `${data.pii_interceptions || 0}`;

    // Freshness Health
    const freshCount = (data.corpus_freshness || []).filter(s => s.is_fresh).length;
    const totalSchemes = (data.corpus_freshness || []).length;
    kpiFreshnessHealth.textContent = `${freshCount}/${totalSchemes} Fresh`;

    // Freshness Table
    renderFreshnessTable(data.corpus_freshness || []);

    // Refusal Breakdown
    overallRefusalRate.textContent = `${data.refusal_rate_pct}% Refusal Rate`;
    const rb = data.refusal_breakdown || {};
    countAdvisory.textContent = rb.advisory || 0;
    countComparative.textContent = rb.comparative || 0;
    countPrediction.textContent = rb.performance_prediction || 0;
    countOutOfCorpus.textContent = rb.out_of_corpus || 0;
    countMixed.textContent = rb.mixed_intent || 0;

    // Audit Logs
    renderAuditLogs(data.recent_logs || []);
  }

  function renderFreshnessTable(schemes) {
    if (!freshnessTableBody) return;
    if (schemes.length === 0) {
      freshnessTableBody.innerHTML = `<tr><td colspan="6" class="loading-td">No schemes registered.</td></tr>`;
      return;
    }

    freshnessTableBody.innerHTML = schemes.map(s => `
      <tr>
        <td>
          <a href="${s.source_url}" target="_blank" rel="noopener noreferrer" class="table-link font-bold">
            ${escapeHtml(s.scheme_name)} ↗
          </a>
        </td>
        <td class="mono-text">${s.chunk_count} chunks</td>
        <td class="mono-text">${escapeHtml(s.fetched_at)}</td>
        <td class="mono-text">${escapeHtml(s.last_verified_unchanged_at)}</td>
        <td>${s.age_days}d ago</td>
        <td>
          <span class="status-pill ${s.is_fresh ? "status-fresh" : "status-stale"}">
            ${s.is_fresh ? "Fresh" : "Stale"}
          </span>
        </td>
      </tr>
    `).join("");
  }

  function renderAuditLogs(logs) {
    if (!auditTableBody) return;
    if (logs.length === 0) {
      auditTableBody.innerHTML = `<tr><td colspan="7" class="loading-td">No transaction logs recorded yet. Ask a question in the chatbot to see live logs!</td></tr>`;
      return;
    }

    auditTableBody.innerHTML = logs.map(l => {
      const timeStr = l.timestamp.split("T")[1].replace("Z", "");
      const linkUrl = l.citation_url || l.educational_url;
      const linkLabel = l.citation_url ? "Groww Source ↗" : (l.educational_url ? "AMFI Education ↗" : "None");

      return `
        <tr>
          <td class="mono-text">${escapeHtml(timeStr)}</td>
          <td>${escapeHtml(l.sanitized_query)}</td>
          <td><span class="badge-blue">${escapeHtml(l.intent_category)}</span></td>
          <td>
            <span class="status-pill ${l.is_refusal ? "status-refusal" : "status-pass"}">
              ${l.is_refusal ? "Refused" : "Answered"}
            </span>
          </td>
          <td>
            ${linkUrl ? `<a href="${linkUrl}" target="_blank" rel="noopener noreferrer" class="table-link">${linkLabel}</a>` : '<span class="mono-text text-dim">N/A</span>'}
          </td>
          <td>
            <span class="status-pill ${l.formatter_passed ? "status-pass" : "status-stale"}">
              ${l.formatter_passed ? "Pass (≤3 sent)" : "Fail"}
            </span>
          </td>
          <td class="mono-text">${Math.round(l.latency_ms)} ms</td>
        </tr>
      `;
    }).join("");
  }

  function escapeHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }
});
