(() => {
  const MOTION_GROUP_BY_TAG = {
    "credo_fast_motion:positive": "Positive",
    "credo_fast_motion:negative": "Negative",
    "credo_fast_motion:ambiguous": "Ambiguous",
    "credo_fast_motion:neutral": "Neutral",
    "credo_speech_motion:positive": "PositiveTalk",
    "credo_speech_motion:negative": "NegativeTalk",
    "credo_speech_motion:ambiguous": "AmbiguousTalk",
    "credo_speech_motion:neutral": "NeutralTalk",
    "credo_style_motion:bright": "PositiveTalk",
    "credo_style_motion:playful": "PositiveTalk",
    "credo_style_motion:energetic": "PositiveTalk",
    "credo_style_motion:smug": "NeutralTalk",
    "credo_style_motion:cute": "PositiveTalk",
    "credo_event_motion:laugh": "PositiveTalk",
    "credo_event_motion:surprise": "AmbiguousTalk",
    "credo_event_motion:thinking": "NeutralTalk",
    "credo_event_motion:sigh": "NegativeTalk",
  };

  const MOTION_PROFILE_BY_TAG = {
    "credo_motion_profile:energetic": "energetic",
    "credo_motion_profile:playful": "playful",
    "credo_motion_profile:bright": "bright",
    "credo_motion_profile:smug": "smug",
    "credo_motion_profile:cute": "cute",
    "credo_motion_profile:low": "low",
    "credo_motion_profile:alert": "alert",
    "credo_motion_profile:steady": "steady",
    "credo_style_motion:energetic": "energetic",
    "credo_style_motion:playful": "playful",
    "credo_style_motion:bright": "bright",
    "credo_style_motion:smug": "smug",
    "credo_style_motion:cute": "cute",
    "credo_speech_motion:positive": "bright",
    "credo_speech_motion:negative": "low",
    "credo_speech_motion:ambiguous": "alert",
    "credo_speech_motion:neutral": "steady",
    "credo_event_motion:laugh": "playful",
    "credo_event_motion:surprise": "alert",
    "credo_event_motion:thinking": "steady",
    "credo_event_motion:sigh": "low",
  };

  const MOTION_PROFILES = {
    energetic: { mouth: 1.38, body: 1.35, cadenceHz: 1.85, repeatMotions: 2, idleReturnMs: 1400 },
    playful: { mouth: 1.24, body: 1.22, cadenceHz: 1.55, repeatMotions: 2, idleReturnMs: 1700 },
    bright: { mouth: 1.18, body: 1.12, cadenceHz: 1.35, repeatMotions: 1, idleReturnMs: 1900 },
    alert: { mouth: 1.10, body: 1.18, cadenceHz: 1.45, repeatMotions: 1, idleReturnMs: 1700 },
    smug: { mouth: 0.96, body: 0.78, cadenceHz: 0.85, repeatMotions: 1, idleReturnMs: 2600 },
    cute: { mouth: 0.92, body: 0.88, cadenceHz: 1.05, repeatMotions: 1, idleReturnMs: 2300 },
    low: { mouth: 0.82, body: 0.70, cadenceHz: 0.75, repeatMotions: 1, idleReturnMs: 2800 },
    steady: { mouth: 0.95, body: 0.82, cadenceHz: 0.90, repeatMotions: 1, idleReturnMs: 2500 },
  };

  const IDLE_RETURN_MS = 2200;
  let idleReturnTimer = null;
  let parameterPulseFrame = null;
  let parameterPulseUntil = 0;
  let interjectionItems = [];
  let selectedExperimentMode = localStorage.getItem("credo-vtuber-mode:experimentMode") || "fish_cover";

  const availableGroup = (group) => {
    if (!group) return "";
    const adapter = window.getLAppAdapter?.();
    if (!adapter) return "";
    if (adapter.getMotionCount(group)) return group;
    const fallback = String(group).replace(/Talk$/, "");
    return adapter.getMotionCount(fallback) ? fallback : "";
  };

  const playRandomMotion = (group) => {
    if (!group) return;
    const adapter = window.getLAppAdapter?.();
    if (!adapter) return;
    group = availableGroup(group);
    if (!group) return;
    const count = adapter.getMotionCount(group);
    if (!count) return;
    const index = Math.floor(Math.random() * count);
    adapter.startMotion(group, index, window.PriorityIdle || 1);
  };

  const normalizeTag = (tag) => String(tag || "").toLowerCase();

  const isMotionTag = (tag) => Boolean(MOTION_GROUP_BY_TAG[normalizeTag(tag)]);
  const isEventTag = (tag) => normalizeTag(tag).startsWith("credo_event_motion:");
  const isStyleTag = (tag) => normalizeTag(tag).startsWith("credo_style_motion:");
  const isSpeechTag = (tag) => normalizeTag(tag).startsWith("credo_speech_motion:");
  const isProfileTag = (tag) => normalizeTag(tag).startsWith("credo_motion_profile:");

  const profileFromTags = (tags) => {
    const normalizedTags = tags.map((tag) => normalizeTag(tag));
    const profileName = normalizedTags
      .map((tag) => MOTION_PROFILE_BY_TAG[tag])
      .find(Boolean) || "steady";
    return MOTION_PROFILES[profileName] || MOTION_PROFILES.steady;
  };

  const getParamId = (adapter, name) => {
    try {
      return adapter.getIdManager?.().getId(name);
    } catch {
      return name;
    }
  };

  const addParam = (model, id, value, weight = 0.55) => {
    try {
      model?._model?.addParameterValueById(id, value, weight);
    } catch {
      // Some Live2D builds expose only a subset of the Cubism parameter API.
    }
  };

  const startSpeechParameterPulse = (payload, profile) => {
    const adapter = window.getLAppAdapter?.();
    const model = adapter?.getModel?.();
    if (!adapter || !model?._model) return;

    const volumes = Array.isArray(payload?.volumes) ? payload.volumes : [];
    const sliceLength = Number(payload?.slice_length || 20);
    const durationMs = volumes.length ? volumes.length * sliceLength : 0;
    if (durationMs <= 0) return;

    const ids = {
      mouthOpen: getParamId(adapter, "ParamMouthOpenY"),
      angleX: getParamId(adapter, "ParamAngleX"),
      angleY: getParamId(adapter, "ParamAngleY"),
      angleZ: getParamId(adapter, "ParamAngleZ"),
      bodyX: getParamId(adapter, "ParamBodyAngleX"),
      bodyY: getParamId(adapter, "ParamBodyAngleY"),
      bodyZ: getParamId(adapter, "ParamBodyAngleZ"),
      breath: getParamId(adapter, "ParamBreath"),
    };

    if (parameterPulseFrame) window.cancelAnimationFrame(parameterPulseFrame);
    const startedAt = performance.now();
    parameterPulseUntil = startedAt + durationMs + 80;
    const mouthBoost = Math.max(0, profile.mouth - 1.0) * 0.42;
    const bodyScale = profile.body;
    const cadence = profile.cadenceHz;

    const tick = (now) => {
      if (now > parameterPulseUntil) {
        parameterPulseFrame = null;
        return;
      }
      const elapsed = Math.max(0, now - startedAt);
      const volumeIndex = Math.min(volumes.length - 1, Math.floor(elapsed / sliceLength));
      const volume = Number(volumes[volumeIndex] || 0);
      const phase = (elapsed / 1000) * Math.PI * 2 * cadence;

      if (mouthBoost > 0) {
        addParam(model, ids.mouthOpen, Math.min(0.42, volume * mouthBoost), 0.65);
      }
      addParam(model, ids.angleX, Math.sin(phase) * 3.2 * bodyScale, 0.34);
      addParam(model, ids.angleY, Math.cos(phase * 0.73) * 1.8 * bodyScale, 0.30);
      addParam(model, ids.angleZ, Math.sin(phase * 0.52) * 1.6 * bodyScale, 0.24);
      addParam(model, ids.bodyX, Math.sin(phase * 0.68) * 1.8 * bodyScale, 0.28);
      addParam(model, ids.bodyY, Math.cos(phase * 0.61) * 1.2 * bodyScale, 0.24);
      addParam(model, ids.bodyZ, Math.sin(phase * 0.48) * 1.0 * bodyScale, 0.20);
      addParam(model, ids.breath, 0.18 * bodyScale + Math.max(0, volume - 0.5) * 0.15, 0.22);

      parameterPulseFrame = window.requestAnimationFrame(tick);
    };
    parameterPulseFrame = window.requestAnimationFrame(tick);
  };

  const playCredoMotion = (tag, durationMs = 0, options = {}) => {
    const { scheduleIdle = true } = options;
    const group = MOTION_GROUP_BY_TAG[normalizeTag(tag)];
    if (!group) return;
    const profile = options.profile || MOTION_PROFILES.steady;
    playRandomMotion(group);
    const repeatMotions = Math.max(1, Number(profile.repeatMotions || 1));
    if (repeatMotions > 1 && durationMs > 700) {
      for (let index = 1; index < repeatMotions; index += 1) {
        const delay = Math.round((durationMs / repeatMotions) * index);
        window.setTimeout(() => playRandomMotion(group), Math.max(300, delay));
      }
    }
    if (!scheduleIdle) return;
    const baseIdleReturnMs = Number(profile.idleReturnMs || IDLE_RETURN_MS);
    const returnDelay = Math.max(baseIdleReturnMs, Number(durationMs || 0) + 300);
    if (idleReturnTimer) window.clearTimeout(idleReturnTimer);
    idleReturnTimer = window.setTimeout(() => playRandomMotion("Idle"), returnDelay);
  };

  const scheduleEventMotions = (tags, durationMs, profile) => {
    const eventTags = tags.filter((tag) => isEventTag(tag) && isMotionTag(tag));
    if (!eventTags.length) return;
    const speechMs = Number(durationMs || 0);
    const spacing = speechMs > 0
      ? Math.min(900, Math.max(350, speechMs / (eventTags.length + 1)))
      : 500;
    eventTags.forEach((tag, index) => {
      const delay = Math.max(180, Math.round(spacing * (index + 1)));
      window.setTimeout(
        () => playCredoMotion(tag, Math.min(900, spacing), { scheduleIdle: false, profile }),
        delay,
      );
    });
  };

  const hideThinkingText = (rootNode = document.body) => {
    const walker = document.createTreeWalker(rootNode, NodeFilter.SHOW_ELEMENT);
    const candidates = [];
    if (rootNode instanceof Element) candidates.push(rootNode);
    while (walker.nextNode()) candidates.push(walker.currentNode);
    for (const node of candidates) {
      if (!(node instanceof HTMLElement)) continue;
      const text = String(node.textContent || "").trim();
      if (/^Thinking\.{0,3}$/i.test(text)) {
        node.style.display = "none";
        node.setAttribute("aria-hidden", "true");
      }
    }
  };

  const startThinkingTextObserver = () => {
    hideThinkingText();
    const observer = new MutationObserver((records) => {
      for (const record of records) {
        for (const node of record.addedNodes) {
          if (node.nodeType === Node.ELEMENT_NODE) hideThinkingText(node);
        }
        if (record.type === "characterData") {
          const parent = record.target.parentElement;
          if (parent) hideThinkingText(parent);
        }
      }
    });
    observer.observe(document.body, { childList: true, characterData: true, subtree: true });
  };

  const handleCredoAudioPayload = (raw) => {
    try {
      const data = JSON.parse(raw);
      if (data?.type !== "audio") return;
      const expressions = data?.actions?.expressions || [];
      const profile = profileFromTags(expressions);
      const styleTag = expressions.find((item) => isStyleTag(item) && isMotionTag(item));
      const speechTag = expressions.find((item) => isSpeechTag(item) && isMotionTag(item));
      const tag = styleTag || speechTag || expressions.find((item) => isMotionTag(item));
      const durationMs = Array.isArray(data?.volumes)
        ? data.volumes.length * Number(data.slice_length || 20)
        : 0;
      if (tag !== undefined) setTimeout(() => playCredoMotion(tag, durationMs, { profile }), 0);
      if (expressions.some((item) => isProfileTag(item) || isStyleTag(item) || isSpeechTag(item))) {
        startSpeechParameterPulse(data, profile);
      }
      scheduleEventMotions(expressions, durationMs, profile);
    } catch {
      // Ignore non-JSON websocket traffic.
    }
  };

  const NativeWebSocket = window.WebSocket;
  if (NativeWebSocket && !window.__credoMotionSocketPatched) {
    window.__credoMotionSocketPatched = true;
    window.WebSocket = function (...args) {
      const socket = new NativeWebSocket(...args);
      const url = String(args[0] || "");
      if (url.includes("/client-ws")) {
        window.__credoClientSocket = socket;
        socket.addEventListener("close", () => {
          if (window.__credoClientSocket === socket) window.__credoClientSocket = null;
        });
      }
      socket.addEventListener("message", (event) => handleCredoAudioPayload(event.data));
      return socket;
    };
    window.WebSocket.prototype = NativeWebSocket.prototype;
    Object.defineProperty(window.WebSocket, "CONNECTING", { value: NativeWebSocket.CONNECTING });
    Object.defineProperty(window.WebSocket, "OPEN", { value: NativeWebSocket.OPEN });
    Object.defineProperty(window.WebSocket, "CLOSING", { value: NativeWebSocket.CLOSING });
    Object.defineProperty(window.WebSocket, "CLOSED", { value: NativeWebSocket.CLOSED });
  }

  const root = document.createElement("div");
  root.id = "credo-vtuber-mode";
  root.innerHTML = `
    <style>
      #credo-vtuber-mode {
        position: fixed;
        left: 18px;
        bottom: 18px;
        z-index: 9999;
        width: 330px;
        padding: 12px;
        border: 1px solid rgba(255,255,255,0.22);
        border-radius: 8px;
        background: rgba(12, 16, 24, 0.92);
        color: #f7f7f7;
        font: 13px/1.35 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        box-shadow: 0 8px 30px rgba(0,0,0,0.28);
        backdrop-filter: blur(10px);
        transition: transform 180ms ease;
      }
      #credo-vtuber-mode.collapsed {
        transform: translateY(calc(100% - 42px));
      }
      #credo-vtuber-mode .row { display: flex; gap: 6px; margin-top: 8px; }
      #credo-vtuber-mode .grid { display: grid; grid-template-columns: 1fr 96px; gap: 6px; margin-top: 8px; }
      #credo-vtuber-mode .tool-grid { display: grid; grid-template-columns: 1fr 82px; gap: 6px; margin-top: 8px; }
      #credo-vtuber-mode .experiment-grid { display: grid; grid-template-columns: 1fr; gap: 6px; margin-top: 8px; }
      #credo-vtuber-mode .section { margin-top: 10px; }
      #credo-vtuber-mode .section-title { color: rgba(255,255,255,0.8); font-size: 12px; font-weight: 700; }
      #credo-vtuber-mode .chat-list {
        height: 132px;
        overflow: auto;
        margin-top: 7px;
        padding: 8px;
        box-sizing: border-box;
        border: 1px solid rgba(255,255,255,0.14);
        border-radius: 6px;
        background: rgba(0,0,0,0.18);
      }
      #credo-vtuber-mode .chat-message {
        display: grid;
        grid-template-columns: auto 1fr;
        gap: 6px;
        margin-bottom: 6px;
        color: rgba(255,255,255,0.9);
        overflow-wrap: anywhere;
      }
      #credo-vtuber-mode .chat-message .author { color: #95b8ff; font-weight: 700; }
      #credo-vtuber-mode .mode-panel[hidden] { display: none; }
      #credo-vtuber-mode input,
      #credo-vtuber-mode select {
        width: 100%;
        min-width: 0;
        box-sizing: border-box;
        border: 1px solid rgba(255,255,255,0.2);
        border-radius: 6px;
        padding: 6px 8px;
        background: rgba(255,255,255,0.08);
        color: #fff;
      }
      #credo-vtuber-mode select option { color: #111; }
      #credo-vtuber-mode button {
        flex: 1;
        border: 0;
        border-radius: 6px;
        padding: 7px 8px;
        color: #fff;
        background: #3f7df6;
        cursor: pointer;
        white-space: nowrap;
      }
      #credo-vtuber-mode button.secondary { background: rgba(255,255,255,0.16); }
      #credo-vtuber-mode button.warn { background: #d64b4b; }
      #credo-vtuber-mode button.active { background: #16a36b; }
      #credo-vtuber-mode .status { margin-top: 8px; color: #b7c7ff; min-height: 18px; }
      #credo-vtuber-mode .title { font-weight: 700; letter-spacing: 0; display: flex; justify-content: space-between; align-items: center; }
      #credo-vtuber-mode .title-actions { display: flex; align-items: center; gap: 6px; }
      #credo-vtuber-mode .toggle {
        flex: 0 0 auto;
        width: 46px;
        padding: 3px 6px;
        border-radius: 5px;
        font-size: 11px;
        background: rgba(255,255,255,0.16);
      }
      #credo-vtuber-mode .wide-toggle {
        width: auto;
        min-width: 78px;
      }
      #credo-vtuber-mode .pill { font-size: 11px; color: #cfd8ff; background: rgba(255,255,255,0.12); padding: 2px 6px; border-radius: 999px; }
      #credo-vtuber-mode .meta { margin-top: 7px; color: rgba(255,255,255,0.72); font-size: 12px; min-height: 16px; }
      #credo-vtuber-mode .manual-tools[hidden] { display: none; }
    </style>
    <div class="title">
      <span>CREDO VTuber Mode</span>
      <span class="title-actions">
        <span class="pill" data-role="pill">off</span>
        <button class="toggle wide-toggle" data-action="toggle-interjections" type="button">Reactions</button>
        <button class="toggle" data-action="toggle-panel" type="button">Hide</button>
      </span>
    </div>
    <div class="panel-body">
      <div class="manual-tools" data-role="interjection-panel" hidden>
        <div class="section-title">Manual interjection + motion</div>
        <div class="tool-grid">
          <select data-key="interjectionId" aria-label="Interjection and motion">
            <option value="">Loading reactions...</option>
          </select>
          <button data-action="play-interjection" type="button">Play</button>
        </div>
      </div>
      <div class="section">
        <div class="section-title">Experiment mode</div>
        <div class="experiment-grid">
          <button class="secondary" data-action="experiment-mode" data-mode="fast_no_cover" type="button">1. Fast TTS / no cover</button>
          <button class="secondary" data-action="experiment-mode" data-mode="fish_no_cover" type="button">2. Fish TTS / no cover</button>
          <button class="secondary" data-action="experiment-mode" data-mode="fish_cover" type="button">3. Fish TTS / cover</button>
        </div>
      </div>
      <div class="mode-panel" data-role="virtual-panel">
        <div class="section-title">Virtual broadcast chat</div>
        <div class="chat-list" data-role="chat-list">
          <div class="chat-message"><span class="author">viewer</span><span>Say something to test FastTrack.</span></div>
        </div>
        <div class="grid">
          <input data-key="virtualName" placeholder="Viewer" value="viewer">
          <button data-action="send-virtual">Send</button>
        </div>
        <div class="row"><input data-key="virtualMessage" placeholder="Virtual live chat message"></div>
        <div class="row">
          <button data-action="start">Switch to VTuber Mode</button>
        </div>
      </div>
      <div class="mode-panel" data-role="youtube-panel" hidden>
        <div class="section-title">YouTube live chat</div>
        <div class="grid">
          <input data-key="topic" placeholder="Stream topic" value="games, daily life, funny chat moments">
          <input data-key="interval" placeholder="Idle sec" value="35">
        </div>
        <div class="grid">
          <input data-key="batchWindow" placeholder="Chat batch sec" value="8">
          <input data-key="maxBatch" placeholder="Max chat" value="8">
        </div>
        <div class="row"><input data-key="videoId" placeholder="YouTube video ID"></div>
        <div class="row"><input data-key="liveChatId" placeholder="YouTube live chat ID"></div>
        <div class="row"><input data-key="apiKey" placeholder="YouTube API key"></div>
        <div class="row">
          <button data-action="start">Connect YouTube</button>
          <button class="warn" data-action="stop">Back to Virtual</button>
        </div>
        <div class="row">
          <button class="secondary" data-action="monologue">Monologue</button>
          <button class="secondary" data-action="donation">Donation</button>
        </div>
      </div>
      <div class="meta" data-role="meta">Connect the browser first, then start.</div>
      <div class="status" data-role="status">Ready.</div>
    </div>
  `;

  const value = (key) => root.querySelector(`[data-key="${key}"]`)?.value.trim() || "";
  const setExperimentButtons = (mode) => {
    selectedExperimentMode = mode || selectedExperimentMode || "fish_cover";
    localStorage.setItem("credo-vtuber-mode:experimentMode", selectedExperimentMode);
    for (const button of root.querySelectorAll('[data-action="experiment-mode"]')) {
      const active = button.dataset.mode === selectedExperimentMode;
      button.classList.toggle("active", active);
      button.classList.toggle("secondary", !active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    }
  };
  const optionLabel = (item) => {
    const carrier = item.carrier || item.id;
    return `${item.emotion} / ${item.style_tag} / ${item.event} / ${carrier}`;
  };
  const populateInterjections = (items) => {
    interjectionItems = Array.isArray(items) ? items : [];
    const select = root.querySelector('[data-key="interjectionId"]');
    if (!select) return;
    select.innerHTML = "";
    if (!interjectionItems.length) {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = "No reactions found";
      select.appendChild(option);
      return;
    }
    for (const item of interjectionItems) {
      const option = document.createElement("option");
      option.value = item.id;
      option.textContent = optionLabel(item);
      select.appendChild(option);
    }
  };
  const loadInterjections = async () => {
    try {
      const response = await fetch("/credo/interjections");
      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
      const data = await response.json();
      populateInterjections(data.items || []);
      return data.items || [];
    } catch (error) {
      const select = root.querySelector('[data-key="interjectionId"]');
      if (select) {
        select.innerHTML = "";
        const option = document.createElement("option");
        option.value = "";
        option.textContent = `Failed to load reactions: ${error.message}`;
        select.appendChild(option);
      }
      throw error;
    }
  };
  const appendChat = (author, message) => {
    const list = root.querySelector('[data-role="chat-list"]');
    if (!list) return;
    const item = document.createElement("div");
    item.className = "chat-message";
    const authorEl = document.createElement("span");
    authorEl.className = "author";
    authorEl.textContent = author || "viewer";
    const textEl = document.createElement("span");
    textEl.textContent = message || "";
    item.append(authorEl, textEl);
    list.appendChild(item);
    while (list.children.length > 24) list.removeChild(list.firstElementChild);
    list.scrollTop = list.scrollHeight;
  };
  const status = (text) => {
    root.querySelector('[data-role="status"]').textContent = text;
  };
  const setCollapsed = (collapsed) => {
    root.classList.toggle("collapsed", collapsed);
    const toggle = root.querySelector('[data-action="toggle-panel"]');
    toggle.textContent = collapsed ? "Show" : "Hide";
    toggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
    localStorage.setItem("credo-vtuber-mode:collapsed", collapsed ? "1" : "0");
  };
  const setMeta = (data) => {
    const pill = root.querySelector('[data-role="pill"]');
    const meta = root.querySelector('[data-role="meta"]');
    const virtualPanel = root.querySelector('[data-role="virtual-panel"]');
    const youtubePanel = root.querySelector('[data-role="youtube-panel"]');
    if (virtualPanel && youtubePanel) {
      virtualPanel.hidden = Boolean(data.active);
      youtubePanel.hidden = !data.active;
    }
    pill.textContent = data.active ? "live" : "off";
    pill.style.background = data.active ? "rgba(63,125,246,0.55)" : "rgba(255,255,255,0.12)";
    const client = data.connected_client ? "client connected" : "no browser client";
    const bridge = data.youtube_bridge_running ? "YouTube bridge on" : "YouTube bridge off";
    const mode = data.active ? "YouTube live mode" : "virtual chat mode";
    if (data.experiment_mode) setExperimentButtons(data.experiment_mode);
    const experiment = data.experiment_label || data.experiment_mode || `local ${selectedExperimentMode}`;
    meta.textContent = `${mode} / ${client} / ${bridge} / ${experiment} / idle ${data.seconds_since_last_activity ?? "-"}s / turns ${data.idle_turn ?? 0}`;
  };
  const refresh = async () => {
    try {
      const response = await fetch("/credo/vtuber-mode/status");
      if (!response.ok) return;
      setMeta(await response.json());
    } catch {
      // The overlay is optional; avoid noisy errors while the backend is booting.
    }
  };
  const ensureInterjectionsLoaded = async () => {
    if (interjectionItems.length) return interjectionItems;
    return loadInterjections();
  };
  const post = async (path, body = {}) => {
    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    return response.json();
  };
  const sendTextInputOverSocket = (text, metadata = {}) => {
    const socket = window.__credoClientSocket;
    if (!socket || socket.readyState !== NativeWebSocket.OPEN) return false;
    socket.send(JSON.stringify({ type: "text-input", text, metadata }));
    return true;
  };
  const sendVirtualChat = async (author, message) => {
    const payload = { author, message };
    try {
      return await post("/credo/vtuber-mode/virtual-chat", payload);
    } catch (error) {
      if (!String(error.message || "").startsWith("404") && !String(error.message || "").startsWith("405")) {
        throw error;
      }
      const text = `Viewer ${author || "viewer"} says: ${message}`;
      const queued = sendTextInputOverSocket(text, {
        virtual_broadcast_chat: true,
        source: "virtual_broadcast_chat",
      });
      if (!queued) throw error;
      return { queued, fallback: "client-ws" };
    }
  };

  root.addEventListener("click", async (event) => {
    const action = event.target?.dataset?.action;
    if (!action) return;
    if (action === "toggle-panel") {
      setCollapsed(!root.classList.contains("collapsed"));
      return;
    }
    if (action === "toggle-interjections") {
      const panel = root.querySelector('[data-role="interjection-panel"]');
      if (!panel) return;
      panel.hidden = !panel.hidden;
      if (!panel.hidden) {
        try {
          const items = await ensureInterjectionsLoaded();
          status(items.length ? `Loaded ${items.length} reactions.` : "No interjection audio found.");
        } catch (error) {
          status(`Error: ${error.message}`);
        }
      }
      return;
    }
    try {
      if (action === "start") {
        const data = await post("/credo/vtuber-mode/start", {
          topic: value("topic"),
          interval_seconds: Number(value("interval") || 35),
          video_id: value("videoId"),
          live_chat_id: value("liveChatId"),
          api_key: value("apiKey"),
          include_author: true,
          batch_window: Number(value("batchWindow") || 8),
          max_batch: Number(value("maxBatch") || 8),
          experiment_mode: selectedExperimentMode,
        });
        status(data.active ? "VTuber mode running." : "Start requested.");
        setMeta(data);
      } else if (action === "send-virtual") {
        const message = value("virtualMessage");
        const author = value("virtualName") || "viewer";
        if (!message) {
          status("Type a virtual chat message first.");
          return;
        }
        await sendVirtualChat(author, message);
        appendChat(author, message);
        const input = root.querySelector('[data-key="virtualMessage"]');
        if (input) input.value = "";
        status("Virtual chat sent.");
      } else if (action === "stop") {
        const data = await post("/credo/vtuber-mode/stop");
        status("Virtual broadcast chat mode.");
        setMeta(data);
      } else if (action === "monologue") {
        await post("/credo/vtuber-mode/monologue", { topic: value("topic") });
        status("Monologue queued.");
      } else if (action === "donation") {
        await post("/credo/vtuber-mode/donation", {
          name: "Test viewer",
          amount: "$5",
          message: "Nice stream.",
        });
        status("Donation reaction queued.");
      } else if (action === "play-interjection") {
        await ensureInterjectionsLoaded();
        const id = value("interjectionId");
        if (!id) {
          status("Choose a reaction first.");
          return;
        }
        const result = await post("/credo/interjections/play", { id });
        status(result.played ? `Played ${result.carrier || result.id}.` : "Reaction not played.");
      } else if (action === "experiment-mode") {
        const mode = event.target?.dataset?.mode;
        if (!mode) return;
        setExperimentButtons(mode);
        try {
          const result = await post("/credo/experiment-mode", { mode });
          status(result.ok ? `Experiment: ${result.label}` : "Experiment mode not changed.");
          await refresh();
        } catch (error) {
          if (String(error.message || "").startsWith("405")) {
            status("Experiment selected locally. Restart the CREDO stack so the backend route is active.");
            return;
          }
          throw error;
        }
      }
    } catch (error) {
      status(`Error: ${error.message}`);
    }
  });

  root.addEventListener("input", (event) => {
    const key = event.target?.dataset?.key;
    if (key) localStorage.setItem(`credo-vtuber-mode:${key}`, event.target.value);
  });
  root.addEventListener("keydown", async (event) => {
    if (event.key !== "Enter" || event.target?.dataset?.key !== "virtualMessage") return;
    event.preventDefault();
    root.querySelector('[data-action="send-virtual"]')?.click();
  });
  for (const input of root.querySelectorAll("input[data-key]")) {
    const saved = localStorage.getItem(`credo-vtuber-mode:${input.dataset.key}`);
    if (saved !== null) input.value = saved;
  }
  setCollapsed(localStorage.getItem("credo-vtuber-mode:collapsed") === "1");

  window.addEventListener("load", () => {
    document.body.appendChild(root);
    startThinkingTextObserver();
    setExperimentButtons(selectedExperimentMode);
    loadInterjections().catch((error) => status(`Reaction load error: ${error.message}`));
    refresh();
    window.setInterval(refresh, 4000);
  });
})();
