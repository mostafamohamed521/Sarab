/* Customer-support chat: talks to the n8n AI agent.
 *
 * Config comes from the page (json_script #chat-config):
 *   mode       'server'  -> POST to Django (/pages/support/chat/), which calls n8n
 *              'browser' -> POST straight to the n8n webhook (free PythonAnywhere)
 *   serverUrl  Django endpoint
 *   webhookUrl n8n webhook (browser mode only)
 *   sessionId  conversation id, sent to n8n so its memory node can group turns
 *   user       {auth_token, user_name} for logged-in users (browser mode only)
 */
(function () {
  'use strict';

  var cfgEl = document.getElementById('chat-config');
  var chatWindow = document.getElementById('chat-window');
  var form = document.getElementById('chat-form');
  var input = document.getElementById('chat-input');
  var sendBtn = document.getElementById('chat-send');
  var chips = document.getElementById('quick-replies');
  if (!cfgEl || !chatWindow || !form) return;

  var cfg = JSON.parse(cfgEl.textContent);
  var csrfInput = form.querySelector('[name=csrfmiddlewaretoken]');
  var csrfToken = csrfInput ? csrfInput.value : '';
  var STORE_KEY = 'sarab-chat-v1:' + cfg.sessionId;
  var TIMEOUT_MS = 35000;
  var history = [];
  var busy = false;

  /* ---------- helpers ---------- */
  function timeNow() {
    return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function esc(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function inline(s) {
    return s
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/(https?:\/\/[^\s<]+[^\s<.,;:!?)])/g,
               '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
  }

  /* tiny, safe markdown: paragraphs, bullet/numbered lists, **bold**, `code`, links.
     Everything is HTML-escaped first, so model output can never inject markup. */
  function format(text) {
    var lines = esc(text).split(/\r?\n/);
    var html = '', inList = false, i, m;
    for (i = 0; i < lines.length; i++) {
      m = lines[i].match(/^\s*(?:[-*\u2022]|\d+[.)])\s+(.*)$/);
      if (m) {
        if (!inList) { html += '<ul>'; inList = true; }
        html += '<li>' + inline(m[1]) + '</li>';
      } else {
        if (inList) { html += '</ul>'; inList = false; }
        if (lines[i].trim()) html += '<p>' + inline(lines[i]) + '</p>';
      }
    }
    if (inList) html += '</ul>';
    return html || '<p></p>';
  }

  function scrollDown() {
    chatWindow.scrollTop = chatWindow.scrollHeight;
  }

  function save() {
    try { sessionStorage.setItem(STORE_KEY, JSON.stringify(history.slice(-40))); } catch (e) { /* private mode */ }
  }

  function load() {
    try { return JSON.parse(sessionStorage.getItem(STORE_KEY)) || []; } catch (e) { return []; }
  }

  /* ---------- rendering ---------- */
  function addMessage(text, sender, opts) {
    opts = opts || {};
    var row = document.createElement('div');
    row.className = 'msg-row ' + sender;

    var avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    avatar.innerHTML = sender === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-utensils"></i>';

    var col = document.createElement('div');
    col.className = 'msg-col';

    var bubble = document.createElement('div');
    bubble.className = 'msg ' + sender + (opts.error ? ' error' : '');
    if (sender === 'agent') bubble.innerHTML = format(text);
    else bubble.textContent = text;

    var time = document.createElement('span');
    time.className = 'msg-time';
    time.textContent = opts.time || timeNow();

    col.appendChild(bubble);
    col.appendChild(time);
    row.appendChild(avatar);
    row.appendChild(col);
    chatWindow.appendChild(row);
    scrollDown();

    if (!opts.restore && !opts.error) {
      history.push({ t: text, s: sender, at: time.textContent });
      save();
    }
    return row;
  }

  function addTyping() {
    var row = document.createElement('div');
    row.className = 'msg-row agent';
    row.innerHTML =
      '<div class="msg-avatar"><i class="fas fa-utensils"></i></div>' +
      '<div class="msg-col"><div class="msg agent typing-dots" aria-label="Assistant is typing">' +
      '<span></span><span></span><span></span></div></div>';
    chatWindow.appendChild(row);
    scrollDown();
    return row;
  }

  function setBusy(state) {
    busy = state;
    sendBtn.disabled = state;
    input.disabled = state;
    if (!state) input.focus();
  }

  /* ---------- network ---------- */
  function extractReply(data) {
    if (Array.isArray(data)) data = data[0] || {};
    if (data && typeof data === 'object') {
      var keys = ['reply', 'output', 'text', 'message'];
      for (var i = 0; i < keys.length; i++) {
        if (typeof data[keys[i]] === 'string' && data[keys[i]].trim()) return data[keys[i]].trim();
      }
    }
    return null;
  }

  function request(message, signal) {
    if (cfg.mode === 'browser' && cfg.webhookUrl) {
      var body = { message: message, session_id: cfg.sessionId };
      if (cfg.user) for (var k in cfg.user) body[k] = cfg.user[k];
      return fetch(cfg.webhookUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: signal
      });
    }
    return fetch(cfg.serverUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
      body: JSON.stringify({ message: message }),
      signal: signal
    });
  }

  function sendMessage(message) {
    message = (message || '').trim();
    if (!message || busy) return;
    if (cfg.maxLength) message = message.slice(0, cfg.maxLength);

    addMessage(message, 'user');
    setBusy(true);
    if (chips) chips.hidden = true;
    var typingRow = addTyping();

    var ctrl = window.AbortController ? new AbortController() : null;
    var timer = ctrl ? setTimeout(function () { ctrl.abort(); }, TIMEOUT_MS) : null;

    request(message, ctrl ? ctrl.signal : undefined)
      .then(function (res) {
        return res.json().catch(function () { return {}; }).then(function (data) {
          return { ok: res.ok, data: data };
        });
      })
      .then(function (r) {
        typingRow.remove();
        var reply = r.ok ? extractReply(r.data) : null;
        if (reply) addMessage(reply, 'agent');
        else addMessage((r.data && r.data.error) || 'Something went wrong. Please try again.', 'agent', { error: true });
      })
      .catch(function (err) {
        typingRow.remove();
        var timedOut = err && err.name === 'AbortError';
        addMessage(timedOut
          ? 'The assistant is taking too long to answer. Please try again.'
          : 'Network error \u2014 please check your connection and try again.',
          'agent', { error: true });
      })
      .then(function () {
        if (timer) clearTimeout(timer);
        setBusy(false);
      });
  }

  /* ---------- wiring ---------- */
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var message = input.value.trim();
    if (!message) return;
    input.value = '';
    sendMessage(message);
  });

  if (chips) {
    chips.addEventListener('click', function (e) {
      var chip = e.target.closest('.chip');
      if (chip) sendMessage(chip.textContent);
    });
  }

  /* restore this session's transcript after a reload / navigation */
  var saved = load();
  if (saved.length) {
    saved.forEach(function (m) { addMessage(m.t, m.s, { restore: true, time: m.at }); });
    history = saved;
    if (chips) chips.hidden = true;
  }
  scrollDown();
})();
