/**
 * widget.js — AcmeAcademy floating chat widget (LangGraph Platform deploy)
 *
 * Drops a self-contained floating action button + chat panel onto any page.
 * Consumes the platform's SSE API.
 *
 * Usage:
 *   <script src="/widget.js" data-api="/api/chat" data-brand="AcmeAcademy"></script>
 *
 * Zero dependencies. CSS injected at init. Namespace prefix: .lp- (LangGraph Platform)
 */
(function () {
  'use strict';

  // ─── Config (from <script data-*> attributes or defaults) ────────
  const scriptEl = document.currentScript;
  const API_URL = scriptEl?.dataset?.api || '/api/chat';
  const BRAND = scriptEl?.dataset?.brand || 'Ask AI';
  const SESSION_KEY = 'lp_session_id';

  function getSessionId() {
    let sid = localStorage.getItem(SESSION_KEY);
    if (!sid) {
      sid = 's_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 8);
      localStorage.setItem(SESSION_KEY, sid);
    }
    return sid;
  }

  // ─── Suggested questions (vertical-specific via data-attr in future) ─
  const SUGGESTIONS = [
    "What's the difference between AMC and AIMO?",
    "How does the Family Plan discount work?",
    "I want to switch from M3 to M4",
    "Can I get a refund on my annual plan?",
  ];

  // ─── CSS (namespaced .lp-*) ───────────────────────────────────────
  const CSS = `
    .lp-fab {
      position: fixed; bottom: 24px; right: 24px; z-index: 9998;
      width: 56px; height: 56px; border-radius: 50%;
      background: linear-gradient(135deg, #0CA58E, #067F73);
      box-shadow: 0 4px 16px rgba(12,165,142,.45);
      display: flex; align-items: center; justify-content: center;
      cursor: pointer; border: none;
      transition: transform .25s cubic-bezier(.34,1.56,.64,1);
    }
    .lp-fab:hover { transform: scale(1.1); }
    .lp-fab svg { width: 26px; height: 26px; color: #fff; fill: none; stroke: currentColor; stroke-width: 2; }
    .lp-fab .lp-badge {
      position: absolute; top: -2px; right: -2px; width: 18px; height: 18px;
      background: #D4A644; border-radius: 50%; border: 2px solid #fff;
      display: flex; align-items: center; justify-content: center;
      font-size: 10px; font-weight: 700; color: #fff;
      opacity: 0; transform: scale(0);
      transition: opacity .2s, transform .2s;
    }
    .lp-fab .lp-badge.show { opacity: 1; transform: scale(1); }

    .lp-panel {
      position: fixed; bottom: 90px; right: 24px; z-index: 9999;
      width: 380px; max-width: calc(100vw - 48px);
      height: 560px; max-height: calc(100vh - 120px);
      background: #fff; border-radius: 20px;
      box-shadow: 0 20px 60px rgba(11,22,43,.18);
      display: flex; flex-direction: column; overflow: hidden;
      transform: scale(0.85) translateY(24px); opacity: 0;
      transform-origin: bottom right;
      transition: transform .3s cubic-bezier(.34,1.56,.64,1), opacity .25s;
      pointer-events: none;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    .lp-panel.open { transform: scale(1) translateY(0); opacity: 1; pointer-events: all; }

    .lp-header {
      background: linear-gradient(135deg, #0B162B 0%, #0d2040 100%);
      padding: 14px 16px; display: flex; align-items: center; gap: 10px;
    }
    .lp-avatar {
      width: 36px; height: 36px; border-radius: 50%;
      background: linear-gradient(135deg, #0CA58E, #4a78ff);
      display: flex; align-items: center; justify-content: center;
      font-weight: 800; font-size: 13px; color: #fff;
    }
    .lp-header-info { flex: 1; }
    .lp-header-name { font-weight: 700; font-size: 14px; color: #fff; }
    .lp-header-sub { font-size: 11px; color: rgba(255,255,255,.6); margin-top: 1px; }
    .lp-close {
      background: rgba(255,255,255,.1); border: none; cursor: pointer;
      width: 28px; height: 28px; border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      color: rgba(255,255,255,.7);
    }
    .lp-close svg { width: 14px; height: 14px; fill: none; stroke: currentColor; stroke-width: 2.5; }

    .lp-messages {
      flex: 1; overflow-y: auto; padding: 14px 16px;
      display: flex; flex-direction: column; gap: 12px;
    }

    .lp-msg { display: flex; gap: 8px; align-items: flex-end; }
    .lp-msg.user { flex-direction: row-reverse; }
    .lp-msg-bubble {
      max-width: 80%; padding: 10px 13px; border-radius: 16px;
      font-size: 13.5px; line-height: 1.55; color: #18181b;
    }
    .lp-msg.bot .lp-msg-bubble { background: #f4f4f5; border-bottom-left-radius: 4px; }
    .lp-msg.user .lp-msg-bubble {
      background: linear-gradient(135deg, #0CA58E, #067F73);
      color: #fff; border-bottom-right-radius: 4px;
    }
    .lp-msg-bubble p { margin: 0 0 6px; }
    .lp-msg-bubble p:last-child { margin-bottom: 0; }
    .lp-msg-bubble strong { font-weight: 700; }
    .lp-msg-bubble ul { margin: 4px 0 4px 18px; }
    .lp-msg-bubble table { width: 100%; border-collapse: collapse; font-size: 12px; margin: 4px 0; }
    .lp-msg-bubble th, .lp-msg-bubble td { padding: 4px 8px; border: 1px solid #e4e4e7; text-align: left; }
    .lp-msg-bubble th { background: #f4f4f5; font-weight: 600; }
    .lp-msg-avatar {
      width: 26px; height: 26px; border-radius: 50%;
      background: linear-gradient(135deg, #0CA58E, #4a78ff);
      display: flex; align-items: center; justify-content: center;
      font-weight: 800; font-size: 10px; color: #fff;
    }

    .lp-trace {
      font-size: 11px; color: #71717a; padding: 4px 12px;
      background: #fafafa; border-left: 3px solid #0CA58E; border-radius: 4px;
      margin: 4px 0;
    }
    .lp-trace.tool { border-color: #f59e0b; }
    .lp-trace.human { border-color: #ef4444; background: #fef2f2; }

    .lp-suggestions { padding: 10px 12px 0; display: flex; flex-direction: column; gap: 6px; }
    .lp-suggestions-label { font-size: 11px; color: #a1a1aa; font-weight: 500; padding: 0 4px; }
    .lp-chip {
      background: #f4f4f5; border: 1px solid #e4e4e7; border-radius: 20px;
      padding: 7px 12px; font-size: 12.5px; color: #27272a;
      cursor: pointer; text-align: left;
    }
    .lp-chip:hover { background: #ecfdf5; border-color: #0CA58E; }

    .lp-input-area {
      padding: 10px 12px 12px; border-top: 1px solid #f4f4f5;
      display: flex; gap: 8px; align-items: flex-end;
    }
    .lp-input {
      flex: 1; border: 1.5px solid #e4e4e7; border-radius: 12px;
      padding: 9px 12px; font-size: 13.5px; resize: none; outline: none;
      max-height: 100px; color: #18181b; line-height: 1.45;
      background: #fafafa; font-family: inherit;
    }
    .lp-input:focus { border-color: #0CA58E; background: #fff; }
    .lp-send {
      width: 38px; height: 38px; border-radius: 50%;
      background: linear-gradient(135deg, #0CA58E, #067F73);
      border: none; cursor: pointer; color: #fff;
      display: flex; align-items: center; justify-content: center;
    }
    .lp-send:disabled { background: #d4d4d8; cursor: not-allowed; }
    .lp-send svg { width: 17px; height: 17px; fill: none; stroke: currentColor; stroke-width: 2.5; }

    @media (max-width: 480px) {
      .lp-panel { bottom: 0; right: 0; left: 0; width: 100%; max-width: 100%; height: 100vh; max-height: 100vh; border-radius: 0; }
    }
  `;

  function renderMD(text) {
    return text
      .replace(/\|(.+)\|/g, function (m) {
        const cells = m.split('|').filter(c => c.trim());
        return '<table><tr>' + cells.map(c => {
          const t = c.trim();
          return t.match(/^[-:]+$/) ? '' : `<td>${t}</td>`;
        }).join('') + '</tr></table>';
      })
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/^[\-\*•] (.+)$/gm, '<li>$1</li>')
      .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')
      .split('\n\n').map(p => p.trim() ? `<p>${p.replace(/\n/g, '<br>')}</p>` : '').join('');
  }

  class ChatWidget {
    constructor() {
      this.isOpen = false;
      this.isLoading = false;
      this.sessionId = getSessionId();
      this.suggestionsShown = true;
      this._injectCSS();
      this._buildDOM();
      this._bindEvents();
    }

    _injectCSS() {
      if (document.getElementById('lp-styles')) return;
      const s = document.createElement('style');
      s.id = 'lp-styles';
      s.textContent = CSS;
      document.head.appendChild(s);
    }

    _buildDOM() {
      this.fab = document.createElement('button');
      this.fab.className = 'lp-fab';
      this.fab.setAttribute('aria-label', 'Open chat');
      this.fab.innerHTML = `
        <svg viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/></svg>
        <span class="lp-badge">1</span>
      `;

      this.panel = document.createElement('div');
      this.panel.className = 'lp-panel';
      this.panel.innerHTML = `
        <div class="lp-header">
          <div class="lp-avatar">AA</div>
          <div class="lp-header-info">
            <div class="lp-header-name">${BRAND}</div>
            <div class="lp-header-sub">AI Parent Assistant · Powered by LangGraph</div>
          </div>
          <button class="lp-close" aria-label="Close"><svg viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg></button>
        </div>
        <div class="lp-messages">
          <div style="text-align:center;padding:8px 0">
            <div style="font-size:28px">👋</div>
            <div style="font-weight:700;font-size:14.5px;color:#18181b;margin:6px 0 4px">Hi! Ask me anything.</div>
            <div style="font-size:12.5px;color:#71717a">Pricing, plan changes, refunds, family discount — I can help with all of it.</div>
          </div>
        </div>
        <div class="lp-suggestions">
          <div class="lp-suggestions-label">Quick questions:</div>
        </div>
        <div class="lp-input-area">
          <textarea class="lp-input" placeholder="Type your question…" rows="1" maxlength="1000"></textarea>
          <button class="lp-send" aria-label="Send"><svg viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/></svg></button>
        </div>
      `;

      document.body.appendChild(this.fab);
      document.body.appendChild(this.panel);

      this.msgArea = this.panel.querySelector('.lp-messages');
      this.inputEl = this.panel.querySelector('.lp-input');
      this.sendBtn = this.panel.querySelector('.lp-send');
      this.suggestionsEl = this.panel.querySelector('.lp-suggestions');
      this.badge = this.fab.querySelector('.lp-badge');

      SUGGESTIONS.forEach(t => {
        const c = document.createElement('button');
        c.className = 'lp-chip';
        c.textContent = t;
        c.addEventListener('click', () => this._send(t));
        this.suggestionsEl.appendChild(c);
      });

      setTimeout(() => this.badge.classList.add('show'), 2000);
    }

    _bindEvents() {
      this.fab.addEventListener('click', () => this._toggle());
      this.panel.querySelector('.lp-close').addEventListener('click', () => this._close());
      this.inputEl.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          this._sendFromInput();
        }
      });
      this.inputEl.addEventListener('input', () => {
        this.inputEl.style.height = 'auto';
        this.inputEl.style.height = Math.min(this.inputEl.scrollHeight, 100) + 'px';
      });
      this.sendBtn.addEventListener('click', () => this._sendFromInput());
    }

    _toggle() { this.isOpen ? this._close() : this._open(); }
    _open() {
      this.isOpen = true;
      this.panel.classList.add('open');
      this.badge.classList.remove('show');
      this.inputEl.focus();
    }
    _close() { this.isOpen = false; this.panel.classList.remove('open'); }

    _sendFromInput() {
      const t = this.inputEl.value.trim();
      if (!t || this.isLoading) return;
      this.inputEl.value = '';
      this._send(t);
    }

    _addUserMsg(text) {
      const row = document.createElement('div');
      row.className = 'lp-msg user';
      row.innerHTML = `<div class="lp-msg-bubble">${text.replace(/</g, '&lt;')}</div>`;
      this.msgArea.appendChild(row);
      this._scroll();
    }

    _addBotBubble() {
      const row = document.createElement('div');
      row.className = 'lp-msg bot';
      row.innerHTML = `<div class="lp-msg-avatar">AA</div><div class="lp-msg-bubble"></div>`;
      this.msgArea.appendChild(row);
      this._scroll();
      return row.querySelector('.lp-msg-bubble');
    }

    _addTrace(text, kind) {
      const t = document.createElement('div');
      t.className = 'lp-trace' + (kind ? ' ' + kind : '');
      t.textContent = text;
      this.msgArea.appendChild(t);
      this._scroll();
    }

    _scroll() { this.msgArea.scrollTop = this.msgArea.scrollHeight; }

    _hideSuggestions() {
      if (this.suggestionsShown) {
        this.suggestionsEl.style.display = 'none';
        this.suggestionsShown = false;
      }
    }

    async _send(text) {
      if (this.isLoading) return;
      this.isLoading = true;
      this.sendBtn.disabled = true;
      this._hideSuggestions();
      this._addUserMsg(text);

      let bubble = null;
      let fullText = '';

      try {
        const response = await fetch(API_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: text,
            session_id: this.sessionId,
            customer_id: 'anonymous',
            vertical: 'education',
          }),
        });
        if (!response.ok) throw new Error('HTTP ' + response.status);

        const reader = response.body.getReader();
        const dec = new TextDecoder();
        let buf = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buf += dec.decode(value, { stream: true });
          const lines = buf.split('\n');
          buf = lines.pop();
          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            let ev;
            try { ev = JSON.parse(line.slice(6).trim()); } catch { continue; }

            if (ev.type === 'triage') {
              this._addTrace(`✓ Classified intent: ${ev.intent} (${(ev.confidence * 100).toFixed(0)}% confidence)`);
            } else if (ev.type === 'tool_call') {
              this._addTrace(`🔧 Calling tool: ${ev.tool}`, 'tool');
            } else if (ev.type === 'token') {
              if (!bubble) bubble = this._addBotBubble();
              fullText += ev.delta;
              bubble.innerHTML = renderMD(fullText);
              this._scroll();
            } else if (ev.type === 'human_escalation') {
              this._addTrace('⚠ Escalated to human reviewer — typical response within 1 business day', 'human');
            } else if (ev.type === 'done') {
              if (bubble) bubble.innerHTML = renderMD(fullText);
            } else if (ev.type === 'error') {
              this._addTrace('Error: ' + ev.message);
            }
          }
        }
      } catch (e) {
        this._addTrace('Network error — please email hello@acmeacademy.com.au');
      } finally {
        this.isLoading = false;
        this.sendBtn.disabled = false;
        this.inputEl.focus();
      }
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => new ChatWidget());
  } else {
    new ChatWidget();
  }
})();
