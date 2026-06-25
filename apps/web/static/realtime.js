class RealtimeProgress {
  constructor(config = {}) {
    this.endpoint = config.endpoint || "/api/realtime/progress";
    this.pollInterval = config.pollInterval || 1500;
    this.isPolling = false;
  }

  start() {
    if (this.isPolling) return;
    this.isPolling = true;
    this.poll();
  }

  stop() {
    this.isPolling = false;
  }

  async poll() {
    while (this.isPolling) {
      try {
        const resp = await fetch(this.endpoint, { cache: "no-store" });
        if (resp.ok) {
          const data = await resp.json();
          this.render(data || {});
        }
      } catch (err) {
        console.warn("Realtime polling failed:", err);
      }
      await this.sleep(this.pollInterval);
    }
  }

  sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  render(data) {
    this.renderState(data.state || "idle");
    this.renderRun(data);
    this.renderCurrentJob(data);
    this.renderActivities(data.activities || []);
    this.renderLogsFallback(data.recent_logs || []);
  }

  renderState(state) {
    const topPill = document.getElementById("state-pill");
    const currentRunState = document.getElementById("current-run-state");
    const elapsed = document.getElementById("processing-elapsed");
    const label = (state || "idle").toUpperCase();

    if (topPill) {
      topPill.className = `state-badge state-${state || "idle"}`;
      topPill.innerHTML = `<span class="state-dot"></span>${label}`;
    }
    if (currentRunState) {
      currentRunState.className = `state-badge state-${state || "idle"}`;
      currentRunState.textContent = label;
    }
    if (typeof window.renderTopControls === "function") {
      window.renderTopControls(state || "idle");
    }
    if (typeof window.renderPlatformControlState === "function") {
      window.renderPlatformControlState(state || "idle");
    }
  }

  renderRun(data) {
    const subtitle = document.getElementById("run-progress-subtitle");
    const eta = document.getElementById("run-eta");
    const elapsed = document.getElementById("processing-elapsed");

    if (subtitle) {
      subtitle.textContent = data.run_subtitle || "0 / 0";
    }
    if (eta) {
      if ((data.state || "idle") === "running") {
        eta.textContent = data.eta_min ? `~${data.eta_min} min` : "~running";
      } else {
        eta.textContent = data.run_target ? "Done" : "—";
      }
    }
    if (elapsed) {
      elapsed.textContent = data.elapsed_label || "—";
    }
    if (typeof window.renderRunDonut === "function") {
      window.renderRunDonut(data.run_applied || 0, data.run_target || 0);
    }
  }

  renderCurrentJob(data) {
    const job = data.current_job || null;
    const state = data.state || "idle";
    const title = document.getElementById("current-job-title");
    const company = document.getElementById("current-job-company");
    const platform = document.getElementById("current-job-platform");
    const step = document.getElementById("current-job-step");
    const stepPct = document.getElementById("step-progress-percentage");
    const stepBar = document.getElementById("progress-step");
    const note = document.getElementById("processing-status-note");
    const fitWrap = document.getElementById("current-job-fit-wrap");
    const fit = document.getElementById("current-job-fit");

    if (title) title.textContent = job?.title || (state === "running" ? "Loading next job..." : "Idle");
    if (company) company.textContent = job?.company || "—";
    if (platform) platform.textContent = (job?.platform || "—").toUpperCase();
    if (step) step.textContent = job?.step || data.current_step || "Idle";

    const pct = Number(data.step_progress || 0);
    if (stepPct) stepPct.textContent = `${pct}%`;
    if (stepBar) stepBar.style.width = `${pct}%`;

    if (fitWrap && fit) {
      const hasFit = job && job.fit_score !== null && job.fit_score !== undefined;
      fitWrap.classList.toggle("d-none", !hasFit);
      if (hasFit) fit.textContent = String(job.fit_score);
    }

    if (note) {
      if (state === "running") {
        note.textContent = job?.title ? "Actively processing current job." : "Loading next job...";
      } else if (state === "paused") {
        note.innerHTML = '<i class="bi bi-pause-circle"></i> Bot is paused.';
      } else if (state === "error") {
        note.innerHTML = '<i class="bi bi-exclamation-triangle"></i> Run ended with an error.';
      } else {
        note.innerHTML = '<i class="bi bi-pause-circle"></i> Bot is idle. Click Start to begin a new run.';
      }
    }
  }

  renderActivities(items) {
    const container = document.getElementById("activity-feed");
    if (!container) return;
    if (!items.length) {
      container.innerHTML = "";
      return;
    }

    const levelClass = {
      success: "bg-success",
      warning: "bg-warning",
      error: "bg-danger",
      info: "bg-info",
    };

    container.innerHTML = items
      .map((item) => {
        const css = levelClass[item.level] || "bg-info";
        return `
          <div class="activity-item">
            <span class="activity-dot ${css}"></span>
            <div class="activity-text">${escapeHtml(item.text || "")}</div>
            <div class="activity-time">${escapeHtml(item.display_time || "")}</div>
          </div>
        `;
      })
      .join("");
  }

  renderLogsFallback(lines) {
    const logBox = document.getElementById("logbox");
    if (!logBox || !Array.isArray(lines) || !lines.length) return;
    const current = (logBox.textContent || "").trim();
    if (!current || current === "(loading logs...)" || current === "(streaming...)") {
      logBox.textContent = lines.join("\n");
    }
  }
}

function dataOrDash(value) {
  return value || "—";
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

document.addEventListener("DOMContentLoaded", () => {
  if (!document.querySelector('[data-realtime="true"]')) return;
  const rt = new RealtimeProgress({ pollInterval: 1500 });
  rt.start();
  window.realtimeProgress = rt;
});
