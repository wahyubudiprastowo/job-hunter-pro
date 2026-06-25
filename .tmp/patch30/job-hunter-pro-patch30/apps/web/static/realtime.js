/* ===================================================
   Job-Hunter Pro - Real-Time Progress (Patch 30)
   =================================================== */

class RealtimeProgress {
  constructor(config = {}) {
    this.endpoint = config.endpoint || '/api/realtime/progress';
    this.pollInterval = config.pollInterval || 1000;  // 1 sec for smooth updates
    this.handlers = {
      progress: [],
      job: [],
      log: [],
      state: [],
      error: [],
    };
    this.isPolling = false;
    this.lastState = null;
    this.animationFrames = new Map();
  }

  on(event, handler) {
    if (this.handlers[event]) {
      this.handlers[event].push(handler);
    }
    return this;
  }

  emit(event, data) {
    if (this.handlers[event]) {
      this.handlers[event].forEach(h => h(data));
    }
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
        const resp = await fetch(this.endpoint);
        if (resp.ok) {
          const data = await resp.json();
          this.handleUpdate(data);
        }
      } catch (e) {
        this.emit('error', { message: e.message });
      }
      await this.sleep(this.pollInterval);
    }
  }

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  handleUpdate(data) {
    // State change
    if (data.state !== this.lastState) {
      this.emit('state', { from: this.lastState, to: data.state });
      this.lastState = data.state;
    }
    
    // Progress updates
    if (data.progress) {
      this.emit('progress', data.progress);
    }
    
    // Current job
    if (data.current_job) {
      this.emit('job', data.current_job);
    }
    
    // Log lines
    if (data.recent_logs) {
      this.emit('log', data.recent_logs);
    }
  }

  /* ===== Animation helpers ===== */

  animateValue(element, from, to, duration = 500, formatter = null) {
    if (!element) return;
    
    // Cancel existing animation
    if (this.animationFrames.has(element)) {
      cancelAnimationFrame(this.animationFrames.get(element));
    }
    
    const start = performance.now();
    const fmt = formatter || (v => Math.round(v));
    
    const animate = (now) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      
      // Easing function
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = from + (to - from) * eased;
      
      element.textContent = fmt(current);
      
      if (progress < 1) {
        const frame = requestAnimationFrame(animate);
        this.animationFrames.set(element, frame);
      } else {
        this.animationFrames.delete(element);
      }
    };
    
    requestAnimationFrame(animate);
  }

  animateProgressBar(barElement, percentage, duration = 500) {
    if (!barElement) return;
    barElement.style.transition = `width ${duration}ms cubic-bezier(0.4, 0, 0.2, 1)`;
    barElement.style.width = `${percentage}%`;
  }

  animateProgressCircle(svgElement, percentage, radius = 80) {
    if (!svgElement) return;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (percentage / 100) * circumference;
    svgElement.style.strokeDasharray = circumference;
    svgElement.style.strokeDashoffset = offset;
  }
}

/* ===== Auto-init for dashboard pages ===== */
document.addEventListener('DOMContentLoaded', () => {
  if (!document.querySelector('[data-realtime="true"]')) return;
  
  const rt = new RealtimeProgress({ pollInterval: 1500 });
  
  // KPI updates with animation
  rt.on('progress', (data) => {
    // Animate KPI cards
    Object.entries(data.kpis || {}).forEach(([key, value]) => {
      const el = document.getElementById(`kpi-${key}`);
      if (el) {
        const current = parseInt(el.textContent) || 0;
        rt.animateValue(el, current, value, 600);
      }
    });
    
    // Animate progress bars
    Object.entries(data.bars || {}).forEach(([key, pct]) => {
      const bar = document.getElementById(`progress-${key}`);
      if (bar) rt.animateProgressBar(bar, pct);
    });
    
    // Update progress circle
    if (data.run_progress !== undefined) {
      const circle = document.querySelector('.progress-circle .fg-circle');
      const value = document.getElementById('progress-circle-value');
      const subtitle = document.getElementById('progress-circle-subtitle');
      
      if (circle) rt.animateProgressCircle(circle, data.run_progress);
      if (value) rt.animateValue(value, parseInt(value.textContent) || 0, 
                                 data.run_progress, 500, v => `${Math.round(v)}%`);
      if (subtitle && data.run_subtitle) subtitle.textContent = data.run_subtitle;
    }
  });
  
  // Current job display
  rt.on('job', (job) => {
    const titleEl = document.getElementById('current-job-title');
    const companyEl = document.getElementById('current-job-company');
    const stepEl = document.getElementById('current-job-step');
    
    if (titleEl) titleEl.textContent = job.title || '—';
    if (companyEl) companyEl.textContent = job.company || '—';
    if (stepEl) stepEl.textContent = job.step || 'Idle';
  });
  
  // Live log updates
  rt.on('log', (lines) => {
    const logBox = document.getElementById('logbox');
    if (logBox && lines.length > 0) {
      logBox.textContent = lines.join('\n');
      logBox.scrollTop = logBox.scrollHeight;  // Auto-scroll
    }
  });
  
  // State changes
  rt.on('state', (change) => {
    const badge = document.getElementById('state-pill');
    if (badge) {
      badge.className = `state-badge state-${change.to}`;
      badge.querySelector('.state-text').textContent = change.to.toUpperCase();
    }
  });
  
  // Error handling
  rt.on('error', (err) => {
    console.warn('Realtime error:', err);
  });
  
  rt.start();
  window.realtimeProgress = rt;
});
