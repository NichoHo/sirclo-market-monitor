/**
 * SIRCLO Marketplace Monitor - Client Application
 * Adheres strictly to design.md (clean, muted Stripe/Vercel aesthetic, NO emojis)
 */

document.addEventListener("DOMContentLoaded", () => {
  // Application State
  let activeCOGS = [];
  let currentAnalysis = null;
  let activeAppState = "empty";
  let isAnalyzing = false;
  let rateLimitCountdownTimer = null;

  function showErrorBanner(message) {
    const errorBanner = document.getElementById("error-banner");
    const errorText = document.getElementById("error-banner-text");
    if (errorBanner && errorText) {
      errorText.textContent = message;
      errorBanner.style.display = "flex";
    }
  }

  function hideErrorBanner() {
    const errorBanner = document.getElementById("error-banner");
    if (errorBanner) {
      errorBanner.style.display = "none";
    }
  }

  // ==========================================================================
  // Helper Formatting Functions
  // ==========================================================================

  function formatRupiah(amount) {
    if (amount === null || amount === undefined || isNaN(amount)) {
      return "Rp 0";
    }
    const num = Math.round(Number(amount));
    const isNegative = num < 0;
    const absStr = Math.abs(num).toLocaleString("id-ID");
    return isNegative ? `-Rp ${absStr}` : `Rp ${absStr}`;
  }

  function escapeHTML(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Toast notification
  window.showToast = function (message, duration = 3000) {
    const toast = document.getElementById("toast");
    if (!toast) return;

    toast.textContent = message;
    toast.classList.add("show");

    if (window._toastTimeout) {
      clearTimeout(window._toastTimeout);
    }

    window._toastTimeout = setTimeout(() => {
      toast.classList.remove("show");
    }, duration);
  };

  // Safe clipboard copy
  function copyToClipboard(text, successMessage = "Pesan aksi disalin") {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text)
        .then(() => window.showToast(successMessage))
        .catch(() => fallbackCopy(text, successMessage));
    } else {
      fallbackCopy(text, successMessage);
    }
  }

  function fallbackCopy(text, successMessage) {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    try {
      document.execCommand("copy");
      window.showToast(successMessage);
    } catch (err) {
      console.error("Copy execution failed:", err);
    }
    document.body.removeChild(textarea);
  }

  // ==========================================================================
  // DOM Renderers
  // ==========================================================================

  function renderBudgetMeter(budget) {
    const budgetDisplay = document.getElementById("budget-display");
    const budgetSubtext = document.getElementById("budget-subtext");
    const budgetBar = document.getElementById("budget-progress-bar");
    const statusBadge = document.getElementById("budget-status-badge");
    const statusDot = document.getElementById("budget-status-dot");
    const statusText = document.getElementById("budget-status-text");

    if (!budgetDisplay) return;

    const totalLoss = budget ? budget.total_loss : 0;
    const campaignBudget = budget ? budget.campaign_budget : 5000000;
    const pctUsed = budget ? budget.pct_used : 0;
    const remaining = budget ? budget.remaining : campaignBudget;
    const level = budget ? budget.meter_level : "safe";

    budgetDisplay.textContent = `${formatRupiah(totalLoss)} / ${formatRupiah(campaignBudget)}`;
    budgetSubtext.textContent = `${pctUsed}% terpakai • Sisa budget ${formatRupiah(remaining)}`;

    let levelColor = "var(--meter-safe)";
    let badgeClass = "badge-safe";
    let dotClass = "dot-positive";
    let badgeLabel = "Aman";

    if (level === "caution") {
      levelColor = "var(--meter-caution)";
      badgeClass = "badge-warning";
      dotClass = "dot-warning";
      badgeLabel = "Waspada";
    } else if (level === "over") {
      levelColor = "var(--meter-over)";
      badgeClass = "badge-negative";
      dotClass = "dot-negative";
      badgeLabel = "Kritis / Over Budget";
    } else if (!budget) {
      levelColor = "var(--gray-800)";
      badgeClass = "badge-neutral";
      dotClass = "dot-neutral";
      badgeLabel = "Idle";
    }

    budgetDisplay.style.color = levelColor;
    if (budgetBar) {
      budgetBar.style.width = `${Math.min(100, Math.max(0, pctUsed))}%`;
      budgetBar.style.backgroundColor = levelColor;
    }

    if (statusBadge && statusDot && statusText) {
      statusBadge.className = `badge ${badgeClass}`;
      statusDot.className = `dot-indicator ${dotClass}`;
      statusText.textContent = badgeLabel;
    }
  }

  function renderMarginAlerts(alerts) {
    const container = document.getElementById("alerts-container");
    const countBadge = document.getElementById("count-jual-rugi");
    if (!container) return;

    if (!alerts || alerts.length === 0) {
      container.innerHTML = `
        <div class="empty-state-notice" id="empty-jual-rugi">
          Silakan upload 4 file CSV marketplace atau klik "Muat Data Sample 10.10" untuk memulai analisis.
        </div>`;
      if (countBadge) countBadge.textContent = "0";
      return;
    }

    if (countBadge) countBadge.textContent = String(alerts.length);

    let html = "";
    alerts.forEach((alert) => {
      const isNegative = alert.level === "negative";
      const levelClass = isNegative ? "negative" : "warning";
      const dotClass = isNegative ? "dot-negative" : "dot-warning";
      const overlineText = isNegative ? "Jual Rugi" : "Margin Tipis";
      const lossText = alert.margin < 0 ? formatRupiah(alert.margin) + "/unit" : "+" + formatRupiah(alert.margin) + "/unit";

      const marginStr = alert.margin < 0 ? String(alert.margin) : `-${alert.margin}`;
      const alertCopyText = `ALERT: ${alert.sku} (${alert.product_name}) jual rugi ${marginStr}/unit di ${alert.channel}. Harga jual Rp ${alert.actual_unit_price}, HPP Rp ${alert.hpp}. Segera cek voucher.`;

      html += `
        <div class="alert-card ${levelClass}" data-copy="${escapeHTML(alertCopyText)}" tabindex="0" role="button" aria-label="Salin rekomendasi aksi untuk ${escapeHTML(alert.sku)}">
          <div class="alert-card-header">
            <div class="alert-card-status">
              <span class="dot-indicator ${dotClass}" aria-hidden="true"></span>
              <span class="alert-card-overline">${overlineText}</span>
            </div>
            <span class="channel-tag">${escapeHTML(alert.channel)}</span>
          </div>
          <div class="alert-card-title">
            <span class="alert-card-sku">${escapeHTML(alert.sku)}</span>
            ${escapeHTML(alert.product_name)}
          </div>
          <div class="alert-metrics-grid">
            <div class="metric-item">
              <span class="metric-label">Harga Normal</span>
              <span class="metric-value">${formatRupiah(alert.original_price)}</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">Harga Jual</span>
              <span class="metric-value">${formatRupiah(alert.actual_unit_price)}</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">HPP / Unit</span>
              <span class="metric-value">${formatRupiah(alert.hpp)}</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">Selisih Margin</span>
              <span class="metric-value ${isNegative ? "loss" : ""}">${lossText}</span>
            </div>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;

    // Attach click listeners to cards
    container.querySelectorAll(".alert-card").forEach((card) => {
      card.addEventListener("click", () => {
        const copyText = card.getAttribute("data-copy");
        copyToClipboard(copyText, "Pesan aksi disalin");
      });
      card.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          const copyText = card.getAttribute("data-copy");
          copyToClipboard(copyText, "Pesan aksi disalin");
        }
      });
    });
  }

  function renderRunRateTable(runRates) {
    const tbody = document.getElementById("runrate-table-body");
    const countBadge = document.getElementById("count-prediksi-habis");
    if (!tbody) return;

    if (!runRates || runRates.length === 0) {
      tbody.innerHTML = `
        <tr id="empty-prediksi-habis">
          <td colspan="7" style="text-align: center; color: var(--gray-400); padding: var(--space-6);">Belum ada data analisis</td>
        </tr>`;
      if (countBadge) countBadge.textContent = "0";
      return;
    }

    const criticalCount = runRates.filter((r) => r.level === "negative" || r.level === "warning").length;
    if (countBadge) countBadge.textContent = String(criticalCount);

    let html = "";
    runRates.forEach((item) => {
      let badgeClass = "badge-safe";
      let dotClass = "dot-positive";
      let statusLabel = "Aman";

      if (item.level === "negative") {
        badgeClass = "badge-negative";
        dotClass = "dot-negative";
        statusLabel = "Kritis";
      } else if (item.level === "warning") {
        badgeClass = "badge-warning";
        dotClass = "dot-warning";
        statusLabel = "Waspada";
      }

      // Handle velocity = 0 edge case
      let timeText = "∞";
      if (item.hours_until_stockout !== Infinity && item.hours_until_stockout !== null) {
        timeText = `${item.stockout_time || ""} (${Number(item.hours_until_stockout).toFixed(1)}j lagi)`;
      }

      html += `
        <tr>
          <td class="font-mono" style="font-weight: 600;">${escapeHTML(item.sku)}</td>
          <td><span class="channel-tag">${escapeHTML(item.channel)}</span></td>
          <td class="num font-mono">${item.total_sold}</td>
          <td class="num font-mono">${Number(item.run_rate_per_hour).toFixed(1)}/jam</td>
          <td class="num font-mono">${item.channel_stock}</td>
          <td class="num font-mono" style="white-space: nowrap;">${escapeHTML(timeText)}</td>
          <td>
            <span class="badge ${badgeClass}">
              <span class="dot-indicator ${dotClass}"></span>
              ${statusLabel}
            </span>
          </td>
        </tr>
      `;
    });

    tbody.innerHTML = html;
  }

  function renderRebalancingCards(rebalanceItems) {
    const container = document.getElementById("rebalance-container");
    const countBadge = document.getElementById("count-rebalancing");
    if (!container) return;

    if (!rebalanceItems || rebalanceItems.length === 0) {
      container.innerHTML = `
        <div class="empty-state-notice" id="empty-rebalancing">
          Belum ada rekomendasi transfer stok.
        </div>`;
      if (countBadge) countBadge.textContent = "0";
      return;
    }

    if (countBadge) countBadge.textContent = String(rebalanceItems.length);

    let html = "";
    rebalanceItems.forEach((item) => {
      const recText = item.recommendations && item.recommendations[0]
        ? item.recommendations[0]
        : `Transfer stok gudang`;

      const copyText = `REBALANCING: ${item.sku} (${item.product_name}). ${recText}. Stok gudang pusat: ${item.warehouse_stock} unit (Shopee: ${item.shopee_stock}, TikTok: ${item.tiktok_stock}).`;

      html += `
        <div class="rebalance-card" data-copy="${escapeHTML(copyText)}" tabindex="0" role="button" aria-label="Salin rekomendasi rebalancing untuk ${escapeHTML(item.sku)}">
          <div class="alert-card-header">
            <div class="alert-card-status">
              <span class="dot-indicator dot-warning" aria-hidden="true"></span>
              <span class="alert-card-overline">Rebalancing Diperlukan</span>
            </div>
            <span class="channel-tag">${escapeHTML(item.channel || "multichannel")}</span>
          </div>
          <div class="alert-card-title">
            <span class="alert-card-sku">${escapeHTML(item.sku)}</span>
            ${escapeHTML(item.product_name)}
          </div>
          <div class="alert-metrics-grid">
            <div class="metric-item">
              <span class="metric-label">Stok Gudang Pusat</span>
              <span class="metric-value">${item.warehouse_stock} unit</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">Stok Shopee</span>
              <span class="metric-value">${item.shopee_stock} unit</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">Stok TikTok</span>
              <span class="metric-value">${item.tiktok_stock} unit</span>
            </div>
          </div>
          <div class="rebalance-recommendation">
            Rekomendasi: ${escapeHTML(recText)}
          </div>
        </div>
      `;
    });

    container.innerHTML = html;

    container.querySelectorAll(".rebalance-card").forEach((card) => {
      card.addEventListener("click", () => {
        const copyText = card.getAttribute("data-copy");
        copyToClipboard(copyText, "Pesan aksi disalin");
      });
      card.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          const copyText = card.getAttribute("data-copy");
          copyToClipboard(copyText, "Pesan aksi disalin");
        }
      });
    });
  }

  function renderCOGS(cogsList) {
    const tbody = document.getElementById("cogs-table-body");
    const countBadge = document.getElementById("cogs-count-badge");
    if (countBadge) {
      countBadge.textContent = `${cogsList.length} SKU Terdaftar`;
    }

    if (!tbody) return;

    let html = "";
    cogsList.forEach((row, index) => {
      html += `
        <tr data-sku="${escapeHTML(row.sku)}">
          <td class="font-mono" style="font-weight: 600;">${escapeHTML(row.sku)}</td>
          <td>${escapeHTML(row.product_name)}</td>
          <td style="text-align: right;">
            <input type="number" class="cogs-input-hpp" value="${row.hpp_per_unit}" data-index="${index}" aria-label="HPP untuk ${escapeHTML(row.sku)}">
          </td>
          <td style="text-align: center;">
            <div style="display: flex; gap: 4px; justify-content: center;">
              <button type="button" class="btn btn-secondary btn-sm btn-save-cogs" data-sku="${escapeHTML(row.sku)}" data-index="${index}">Simpan</button>
              <button type="button" class="btn btn-ghost btn-sm btn-delete-cogs" data-sku="${escapeHTML(row.sku)}" data-index="${index}" style="color: var(--status-negative-text);">Hapus</button>
            </div>
          </td>
        </tr>
      `;
    });

    tbody.innerHTML = html;

    // Attach listeners for save and delete
    tbody.querySelectorAll(".btn-save-cogs").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const idx = parseInt(btn.getAttribute("data-index"), 10);
        const sku = btn.getAttribute("data-sku");
        const input = tbody.querySelector(`input[data-index="${idx}"]`);
        if (input) {
          const newHpp = parseInt(input.value, 10);
          if (isNaN(newHpp) || newHpp < 0) {
            window.showToast("HPP harus berupa angka bulat positif");
            return;
          }
          try {
            const res = await fetch(`/api/cogs/${encodeURIComponent(sku)}`, {
              method: "PUT",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ hpp_per_unit: newHpp }),
            });
            const data = await res.json();
            if (res.ok) {
              if (activeCOGS[idx]) activeCOGS[idx].hpp_per_unit = newHpp;
              window.showToast("HPP berhasil diperbarui");
            } else {
              window.showToast(data.error || "Gagal memperbarui HPP");
            }
          } catch (err) {
            window.showToast("Koneksi gagal saat memperbarui HPP");
          }
        }
      });
    });

    tbody.querySelectorAll(".btn-delete-cogs").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const sku = btn.getAttribute("data-sku");
        try {
          const res = await fetch(`/api/cogs/${encodeURIComponent(sku)}`, {
            method: "DELETE",
          });
          const data = await res.json();
          if (res.ok) {
            activeCOGS = activeCOGS.filter((c) => c.sku !== sku);
            renderCOGS(activeCOGS);
            window.showToast(data.message || `SKU ${sku} berhasil dihapus`);
          } else {
            window.showToast(data.error || "Gagal menghapus SKU");
          }
        } catch (err) {
          window.showToast("Koneksi gagal saat menghapus SKU");
        }
      });
    });
  }

  function renderSummary(summaryText) {
    const previewEl = document.getElementById("summary-preview-text");
    if (previewEl) {
      previewEl.textContent = summaryText || "";
    }
  }

  async function loadCOGSFromBackend() {
    try {
      const res = await fetch("/api/cogs");
      if (res.ok) {
        const data = await res.json();
        if (data && Array.isArray(data.data) && data.data.length > 0) {
          activeCOGS = data.data;
          renderCOGS(activeCOGS);
          return;
        }
      }
    } catch (err) {
      console.warn("Using fallback local COGS data", err);
    }
    renderCOGS(activeCOGS);
  }

  // ==========================================================================
  // Minimalist Upload Row Helpers
  // ==========================================================================

  function updateOverallUploadStatus() {
    const slots = [
      document.getElementById("slot-shopee-orders"),
      document.getElementById("slot-tiktok-orders"),
      document.getElementById("slot-shopee-inventory"),
      document.getElementById("slot-tiktok-inventory")
    ];
    const filledCount = slots.filter((s) => s && s.classList.contains("filled")).length;
    const text = document.getElementById("upload-status-text");

    if (text) {
      text.textContent = `${filledCount} / 4 file dipilih`;
    }
  }

  function updateSlotFilled(slot, filename) {
    if (!slot) return;
    slot.classList.add("filled");
    slot.classList.remove("drag-over");

    const hint = slot.querySelector(".upload-slot-hint");
    if (hint) hint.textContent = filename;

    const filenameEl = slot.querySelector(".upload-slot-filename");
    if (filenameEl) filenameEl.textContent = filename;

    const btn = slot.querySelector(".upload-row-btn");
    if (btn) btn.textContent = "Ganti";

    const resetBtn = slot.querySelector(".btn-slot-reset");
    if (resetBtn) resetBtn.style.display = "inline-block";

    updateOverallUploadStatus();
  }

  function resetSlot(slot) {
    if (!slot) return;
    slot.classList.remove("filled", "drag-over");
    const fileInput = slot.querySelector('input[type="file"]');
    if (fileInput) fileInput.value = "";

    const hint = slot.querySelector(".upload-slot-hint");
    if (hint) {
      hint.textContent = "Pilih berkas (.csv, .xlsx)";
    }

    const filenameEl = slot.querySelector(".upload-slot-filename");
    if (filenameEl) filenameEl.textContent = "";

    const btn = slot.querySelector(".upload-row-btn");
    if (btn) btn.textContent = "Pilih File";

    const resetBtn = slot.querySelector(".btn-slot-reset");
    if (resetBtn) resetBtn.style.display = "none";

    updateOverallUploadStatus();
  }

  // ==========================================================================
  // Application State Controller
  // ==========================================================================

  function setAppState(state) {
    activeAppState = state;

    const errorBanner = document.getElementById("error-banner");
    const btnAnalyze = document.getElementById("btn-analyze");
    const dropzoneSlots = document.querySelectorAll(".upload-slot");

    if (state === "empty") {
      if (errorBanner) errorBanner.style.display = "none";
      if (btnAnalyze) {
        btnAnalyze.disabled = false;
        btnAnalyze.classList.remove("loading");
        btnAnalyze.textContent = "Analisis Sekarang";
      }

      // Reset rows to empty
      dropzoneSlots.forEach((slot) => {
        resetSlot(slot);
      });

      currentAnalysis = null;
      renderBudgetMeter(null);
      renderMarginAlerts([]);
      renderRunRateTable([]);
      renderRebalancingCards([]);
      renderSummary("");
    } else if (state === "loading") {
      if (errorBanner) errorBanner.style.display = "none";
      if (btnAnalyze) {
        btnAnalyze.disabled = true;
        btnAnalyze.classList.add("loading");
        btnAnalyze.textContent = "Menganalisis...";
      }
    } else if (state === "results") {
      if (errorBanner) errorBanner.style.display = "none";
      if (btnAnalyze) {
        btnAnalyze.disabled = false;
        btnAnalyze.classList.remove("loading");
        btnAnalyze.textContent = "Analisis Sekarang";
      }

      if (currentAnalysis) {
        renderBudgetMeter(currentAnalysis.budget_status);
        renderMarginAlerts(currentAnalysis.margin_alerts);
        renderRunRateTable(currentAnalysis.run_rate);
        renderRebalancingCards(currentAnalysis.rebalance);
        renderSummary(currentAnalysis.summary_text);
      }
    } else if (state === "error") {
      if (btnAnalyze) {
        btnAnalyze.disabled = false;
        btnAnalyze.classList.remove("loading");
        btnAnalyze.textContent = "Analisis Sekarang";
      }
      if (errorBanner) {
        errorBanner.style.display = "flex";
      }
    }
  }

  // ==========================================================================
  // Event Bindings
  // ==========================================================================

  // Tab switching
  const tabItems = document.querySelectorAll(".tab-item");
  const tabContents = document.querySelectorAll(".tab-content");

  tabItems.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabItems.forEach((t) => t.classList.remove("active"));
      tabContents.forEach((c) => c.classList.remove("active"));

      tab.classList.add("active");
      const targetId = tab.getAttribute("data-tab");
      const targetContent = document.getElementById(targetId);
      if (targetContent) {
        targetContent.classList.add("active");
      }
    });
  });

  // Dismiss error banner
  const btnDismissError = document.getElementById("btn-dismiss-error");
  if (btnDismissError) {
    btnDismissError.addEventListener("click", () => {
      const errorBanner = document.getElementById("error-banner");
      if (errorBanner) errorBanner.style.display = "none";
    });
  }

  // Toggle COGS drawer
  const btnToggleCogs = document.getElementById("btn-toggle-cogs");
  const cogsDrawer = document.getElementById("cogs-drawer");
  if (btnToggleCogs && cogsDrawer) {
    btnToggleCogs.addEventListener("click", () => {
      const isHidden = cogsDrawer.style.display === "none";
      cogsDrawer.style.display = isHidden ? "flex" : "none";
      btnToggleCogs.setAttribute("aria-expanded", String(isHidden));
    });
  }

  // Toggle Summary Preview Drawer
  const btnToggleSummary = document.getElementById("btn-toggle-summary-preview");
  const summaryContainer = document.getElementById("summary-preview-container");
  if (btnToggleSummary && summaryContainer) {
    btnToggleSummary.addEventListener("click", () => {
      const isHidden = summaryContainer.style.display === "none";
      summaryContainer.style.display = isHidden ? "block" : "none";
      btnToggleSummary.textContent = isHidden ? "Tutup Pratinjau Teks WhatsApp" : "Lihat Pratinjau Teks WhatsApp";
    });
  }

  // Copy Summary button
  const btnCopySummary = document.getElementById("btn-copy-summary");
  if (btnCopySummary) {
    btnCopySummary.addEventListener("click", () => {
      const text = currentAnalysis ? currentAnalysis.summary_text : "";
      if (!text) {
        window.showToast("Belum ada ringkasan analisis untuk disalin");
        return;
      }
      copyToClipboard(text, "Ringkasan disalin ke clipboard");
    });
  }

  // Offline & Disconnection Network Guard
  window.addEventListener("offline", () => {
    showErrorBanner("Koneksi internet bermasalah. Periksa jaringan Anda dan coba lagi.");
    window.showToast("Koneksi internet terputus");
  });

  window.addEventListener("online", () => {
    hideErrorBanner();
    window.showToast("Koneksi internet terhubung kembali");
  });

  // Load Sample Data 10.10 button
  const btnLoadSample = document.getElementById("btn-load-sample");
  if (btnLoadSample) {
    btnLoadSample.addEventListener("click", async () => {
      if (isAnalyzing) return;
      isAnalyzing = true;
      btnLoadSample.disabled = true;
      btnLoadSample.classList.add("is-loading");
      setAppState("loading");
      hideErrorBanner();

      try {
        const res = await fetch("/api/sample-data");
        const data = await res.json();
        if (res.ok) {
          currentAnalysis = data;
          const sampleFiles = {
            "slot-shopee-orders": "shopee_orders.csv",
            "slot-tiktok-orders": "tiktok_orders.csv",
            "slot-shopee-inventory": "shopee_inventory.csv",
            "slot-tiktok-inventory": "tiktok_inventory.csv"
          };

          Object.entries(sampleFiles).forEach(([slotId, filename]) => {
            const slot = document.getElementById(slotId);
            if (slot) {
              updateSlotFilled(slot, filename);
            }
          });

          const budgetInput = document.getElementById("campaign_budget");
          if (budgetInput) budgetInput.value = "5000000";

          renderBudgetMeter(currentAnalysis.budget_status);
          renderMarginAlerts(currentAnalysis.margin_alerts);
          renderRunRateTable(currentAnalysis.run_rate);
          renderRebalancingCards(currentAnalysis.rebalance);
          renderSummary(currentAnalysis.summary_text);

          await loadCOGSFromBackend();

          setAppState("results");
          if (data.unmapped_skus && data.unmapped_skus.length > 0) {
            const count = data.unmapped_skus.length;
            showErrorBanner(`${count} SKU tidak ada data HPP — margin tidak bisa dihitung`);
          } else if (data.warnings && data.warnings.length > 0) {
            showErrorBanner(`${data.warnings.length} baris data tidak valid dilewati saat membaca file`);
          }
          window.showToast("Data sample 10.10 berhasil dimuat");
        } else if (res.status === 429) {
          setAppState("error");
          const retryHeader = res.headers.get("Retry-After");
          let retryAfter = data.retry_after || (retryHeader ? parseInt(retryHeader, 10) : 6);
          const limitMsg = data.error || `Terlalu banyak permintaan. Silakan tunggu ${retryAfter} detik sebelum mencoba lagi.`;
          showErrorBanner(limitMsg);
          window.showToast(limitMsg);
        } else {
          setAppState("error");
          const errMsg = data.error || "Gagal memuat data sample";
          showErrorBanner(errMsg);
          window.showToast(errMsg);
        }
      } catch (err) {
        setAppState("error");
        let networkMsg = "Koneksi gagal saat memuat data sample";
        if (!navigator.onLine || err instanceof TypeError) {
          networkMsg = "Koneksi internet bermasalah. Periksa jaringan Anda dan coba lagi.";
        }
        showErrorBanner(networkMsg);
        window.showToast(networkMsg);
      } finally {
        isAnalyzing = false;
        btnLoadSample.disabled = false;
        btnLoadSample.classList.remove("is-loading");
      }
    });
  }

  // Analyze Form Submit with Full Operational Guardrails
  const uploadForm = document.getElementById("upload-form");
  const btnAnalyze = document.getElementById("btn-analyze");

  if (uploadForm) {
    uploadForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      // Debounce & in-flight locking guard
      if (isAnalyzing) {
        return;
      }

      const spOrders = document.getElementById("shopee_orders");
      const ttOrders = document.getElementById("tiktok_orders");
      const spInv = document.getElementById("shopee_inventory");
      const ttInv = document.getElementById("tiktok_inventory");
      const budgetInput = document.getElementById("campaign_budget");

      const hasFiles = spOrders && spOrders.files && spOrders.files[0] &&
                       ttOrders && ttOrders.files && ttOrders.files[0] &&
                       spInv && spInv.files && spInv.files[0] &&
                       ttInv && ttInv.files && ttInv.files[0];

      if (!hasFiles) {
        showErrorBanner("Pilih seluruh 4 file (Shopee Orders, TikTok Orders, Shopee Stok, TikTok Stok) sebelum analisis.");
        window.showToast("Pilih 4 file atau klik Muat Data Sample");
        return;
      }

      // Pre-flight file size check: max 10 MB per file, max 16 MB total
      const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB
      const MAX_TOTAL_SIZE = 16 * 1024 * 1024; // 16 MB
      const uploadedFiles = [
        spOrders.files[0],
        ttOrders.files[0],
        spInv.files[0],
        ttInv.files[0]
      ];

      const hasOverSingle = uploadedFiles.some((f) => f && f.size > MAX_FILE_SIZE);
      const totalSize = uploadedFiles.reduce((sum, f) => sum + (f ? f.size : 0), 0);

      if (hasOverSingle || totalSize > MAX_TOTAL_SIZE) {
        const sizeErrorMsg = "Ukuran file terlalu besar (maksimal 10 MB per file, 16 MB total).";
        showErrorBanner(sizeErrorMsg);
        window.showToast(sizeErrorMsg);
        return;
      }

      // Set in-flight lock state
      isAnalyzing = true;
      if (btnAnalyze) {
        btnAnalyze.disabled = true;
        btnAnalyze.classList.add("is-loading");
        btnAnalyze.textContent = "Memproses...";
      }

      setAppState("loading");
      hideErrorBanner();

      const formData = new FormData();
      formData.append("shopee_orders", spOrders.files[0]);
      formData.append("tiktok_orders", ttOrders.files[0]);
      formData.append("shopee_inventory", spInv.files[0]);
      formData.append("tiktok_inventory", ttInv.files[0]);
      formData.append("campaign_budget", budgetInput ? budgetInput.value : "5000000");

      const controller = new AbortController();
      const timeoutId = setTimeout(() => {
        controller.abort();
      }, 30000); // 30-second timeout limit per AC 1 & Section 9.2.1

      try {
        const res = await fetch("/api/analyze", {
          method: "POST",
          body: formData,
          signal: controller.signal,
        });
        clearTimeout(timeoutId);

        const data = await res.json();
        if (res.ok) {
          currentAnalysis = data;
          renderBudgetMeter(currentAnalysis.budget_status);
          renderMarginAlerts(currentAnalysis.margin_alerts);
          renderRunRateTable(currentAnalysis.run_rate);
          renderRebalancingCards(currentAnalysis.rebalance);
          renderSummary(currentAnalysis.summary_text);
          setAppState("results");
          if (data.unmapped_skus && data.unmapped_skus.length > 0) {
            const count = data.unmapped_skus.length;
            showErrorBanner(`${count} SKU tidak ada data HPP — margin tidak bisa dihitung`);
          } else if (data.warnings && data.warnings.length > 0) {
            showErrorBanner(`${data.warnings.length} baris data tidak valid dilewati saat membaca file`);
          }
          window.showToast("Analisis selesai");
        } else if (res.status === 429) {
          setAppState("error");
          const retryHeader = res.headers.get("Retry-After");
          let retryAfter = data.retry_after || (retryHeader ? parseInt(retryHeader, 10) : 6);
          const limitMsg = data.error || `Terlalu banyak permintaan. Silakan tunggu ${retryAfter} detik sebelum mencoba lagi.`;
          showErrorBanner(limitMsg);
          window.showToast(limitMsg);

          // 429 Rate Limit Feedback & countdown timer
          if (btnAnalyze) {
            btnAnalyze.disabled = true;
            if (rateLimitCountdownTimer) {
              clearInterval(rateLimitCountdownTimer);
            }
            let remaining = retryAfter;
            btnAnalyze.textContent = `Tunggu ${remaining}s...`;
            rateLimitCountdownTimer = setInterval(() => {
              remaining -= 1;
              if (remaining > 0) {
                btnAnalyze.textContent = `Tunggu ${remaining}s...`;
                showErrorBanner(`Terlalu banyak permintaan. Silakan tunggu ${remaining} detik sebelum mencoba lagi.`);
              } else {
                clearInterval(rateLimitCountdownTimer);
                rateLimitCountdownTimer = null;
                btnAnalyze.textContent = "Analisis Sekarang";
                btnAnalyze.disabled = false;
                hideErrorBanner();
              }
            }, 1000);
          }
        } else {
          setAppState("error");
          const errMsg = data.error || "Gagal melakukan analisis";
          showErrorBanner(errMsg);
          window.showToast(errMsg);
        }
      } catch (err) {
        clearTimeout(timeoutId);
        setAppState("error");
        let networkMsg = "Koneksi ke server gagal atau terputus.";
        if (err.name === "AbortError") {
          networkMsg = "Waktu permintaan habis (timeout 30 detik). Koneksi lambat, silakan coba lagi.";
        } else if (!navigator.onLine || err instanceof TypeError) {
          networkMsg = "Koneksi internet terputus saat menghubungi server. Periksa jaringan Anda dan coba lagi.";
        }
        showErrorBanner(networkMsg);
        window.showToast(networkMsg);
      } finally {
        isAnalyzing = false;
        if (btnAnalyze) {
          btnAnalyze.classList.remove("is-loading");
          if (!rateLimitCountdownTimer) {
            btnAnalyze.textContent = "Analisis Sekarang";
            btnAnalyze.disabled = false;
          }
        }
      }
    });
  }

  // Dropzone file drag & drop + change handlers
  const dropzones = document.querySelectorAll(".upload-slot");
  const ALLOWED_EXTS = [".csv", ".xlsx", ".xls", ".tsv"];

  function isValidTabularFile(fileName) {
    const lower = fileName.toLowerCase();
    return ALLOWED_EXTS.some((ext) => lower.endsWith(ext));
  }

  // COGS file upload handling
  const cogsInput = document.getElementById("cogs_file");
  const slotCogs = document.getElementById("slot-cogs");
  if (cogsInput && slotCogs) {
    async function handleCogsUpload(file) {
      if (!isValidTabularFile(file.name)) {
        window.showToast("Format file tidak didukung. Harap upload CSV atau Excel (.xlsx/.xls)");
        return;
      }
      const formData = new FormData();
      formData.append("cogs_file", file);
      try {
        const res = await fetch("/api/cogs/upload", { method: "POST", body: formData });
        const data = await res.json();
        if (res.ok) {
          window.showToast(data.message || `${data.inserted} SKU berhasil disimpan`);
          await loadCOGSFromBackend();
          updateSlotFilled(slotCogs, file.name);
        } else {
          window.showToast(data.error || "Gagal upload file COGS");
        }
      } catch (err) {
        window.showToast("Gagal menghubungi server saat upload COGS");
      }
    }

    cogsInput.addEventListener("change", () => {
      if (cogsInput.files && cogsInput.files[0]) {
        handleCogsUpload(cogsInput.files[0]);
      }
    });

    slotCogs.addEventListener("dragover", (e) => {
      e.preventDefault();
      slotCogs.classList.add("drag-over");
    });

    slotCogs.addEventListener("dragleave", () => {
      slotCogs.classList.remove("drag-over");
    });

    slotCogs.addEventListener("drop", (e) => {
      e.preventDefault();
      slotCogs.classList.remove("drag-over");
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) {
        handleCogsUpload(e.dataTransfer.files[0]);
      }
    });
  }

  // Marketplace order & inventory dropzones
  dropzones.forEach((slot) => {
    if (slot.id === "slot-cogs") return;
    const fileInput = slot.querySelector('input[type="file"]');
    if (!fileInput) return;

    fileInput.addEventListener("change", () => {
      if (fileInput.files && fileInput.files[0]) {
        const file = fileInput.files[0];
        if (!isValidTabularFile(file.name)) {
          window.showToast("Format file tidak didukung. Harap upload CSV atau Excel (.xlsx/.xls)");
          fileInput.value = "";
          return;
        }
        updateSlotFilled(slot, file.name);
      }
    });

    slot.addEventListener("dragover", (e) => {
      e.preventDefault();
      slot.classList.add("drag-over");
    });

    slot.addEventListener("dragleave", () => {
      slot.classList.remove("drag-over");
    });

    slot.addEventListener("drop", (e) => {
      e.preventDefault();
      slot.classList.remove("drag-over");

      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) {
        const file = e.dataTransfer.files[0];
        if (!isValidTabularFile(file.name)) {
          window.showToast("Format file tidak didukung. Harap upload CSV atau Excel (.xlsx/.xls)");
          return;
        }
        updateSlotFilled(slot, file.name);
        try {
          fileInput.files = e.dataTransfer.files;
        } catch (err) {
          // Some browsers prevent manual FileList assignment
        }
      }
    });

    // Reset button inside slot
    const resetBtn = slot.querySelector(".btn-slot-reset");
    if (resetBtn) {
      resetBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        e.preventDefault();
        resetSlot(slot);
        window.showToast("File dihapus dari slot");
      });
    }
  });

  // ==========================================================================
  // Initial Boot
  // ==========================================================================
  loadCOGSFromBackend();
  setAppState("empty");
});
