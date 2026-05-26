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

  const EVENT_PARAMETER_ACCENTS = {
    "credo_event_motion:laugh": {
      durationMs: 520,
      eyeSmile: 0.72,
      eyeOpen: -0.08,
      browY: 0.18,
      browForm: 0.08,
      cheek: 0.30,
      angleX: 1.8,
      angleY: 1.1,
      angleZ: 3.4,
      bodyX: 1.4,
      bodyY: 0.9,
      bodyZ: 1.4,
      bounce: 1.6,
    },
    "credo_event_motion:surprise": {
      durationMs: 460,
      eyeOpen: 0.36,
      eyeSmile: -0.08,
      browY: 0.72,
      browForm: 0.16,
      cheek: 0.08,
      angleX: -1.1,
      angleY: 2.1,
      angleZ: -2.0,
      bodyX: -1.1,
      bodyY: 1.8,
      bodyZ: -1.2,
      bounce: 1.2,
    },
    "credo_event_motion:thinking": {
      durationMs: 760,
      eyeOpen: -0.08,
      eyeSmile: -0.04,
      browY: -0.16,
      browForm: -0.30,
      cheek: 0.04,
      eyeBallY: -0.18,
      angleX: -1.5,
      angleY: -2.0,
      angleZ: -1.2,
      bodyX: -0.8,
      bodyY: -0.8,
      bodyZ: -0.6,
      bounce: 0.8,
    },
    "credo_event_motion:sigh": {
      durationMs: 820,
      eyeOpen: -0.24,
      eyeSmile: -0.10,
      browY: -0.42,
      browForm: -0.16,
      cheek: -0.04,
      angleX: 0.8,
      angleY: -2.8,
      angleZ: 1.0,
      bodyX: 0.6,
      bodyY: -2.0,
      bodyZ: 0.8,
      breath: 0.18,
      bounce: 0.6,
    },
  };

  const IDLE_RETURN_MS = 2200;
  let idleReturnTimer = null;
  let parameterPulseFrame = null;
  let parameterPulseUntil = 0;
  let idlePulseFrame = null;
  const normalizeExperimentMode = (mode) => {
    const aliases = {
      live_edge_cover: "edge_async_cover",
      fish_cover: "edge_async_cover",
      fish_no_cover: "edge_no_cover",
      fast_no_cover: "edge_no_cover",
    };
    const normalized = aliases[mode] || mode;
    return ["edge_async_cover", "edge_fasttrack", "edge_no_cover"].includes(normalized)
      ? normalized
      : "edge_async_cover";
  };
  let selectedExperimentMode = normalizeExperimentMode(
    localStorage.getItem("credo-vtuber-mode:experimentMode") || "edge_async_cover",
  );
  const normalizeComponentMode = (mode) => (["both", "none"].includes(mode) ? mode : "both");
  const normalizeSelectionPolicy = (policy) =>
    ["grounded", "emotion_only", "response_act_only", "neutral_random", "none"].includes(policy)
      ? policy
      : "grounded";
  let selectedComponentMode = normalizeComponentMode(localStorage.getItem("credo-vtuber-mode:componentMode") || "both");
  let selectedSelectionPolicy = normalizeSelectionPolicy(
    localStorage.getItem("credo-vtuber-mode:selectionPolicy") || "grounded",
  );
  let selectedSchedulingMode = localStorage.getItem("credo-vtuber-mode:schedulingMode") || "parallel";
  let selectedRuntimeMode = localStorage.getItem("credo-vtuber-mode:runtimeMode") || "direct_chat";
  let selectedExperimentRunId = localStorage.getItem("credo-vtuber-mode:experimentRunId") || "";
  let selectedExperimentFactor = localStorage.getItem("credo-vtuber-mode:experimentFactor") || "";
  let selectedScenario = localStorage.getItem("credo-vtuber-mode:scenario") || "shared_2m30";
  let scenarioTimers = [];
  let scenarioRunToken = 0;
  let activeScenarioId = "";
  let donationOverlayTimer = null;
  const DONATION_OVERLAY_MS = 20000;
  const DONATION_SFX_URL = "/credo/vtuber-mode/donation-sfx";

  const EXPERIMENT_RUN_PRESETS = [
    {
      id: "case_1_grounded_serial",
      label: "Case 1 · Grounded / Serial",
      factor: "contextual_mapping",
      scenario: "shared_2m30",
      component_mode: "both",
      selection_policy: "grounded",
      scheduling_mode: "serial",
    },
    {
      id: "case_2_emotion_only_serial",
      label: "Case 2 · Emotion Only / Serial",
      factor: "contextual_mapping",
      scenario: "shared_2m30",
      component_mode: "both",
      selection_policy: "emotion_only",
      scheduling_mode: "serial",
    },
    {
      id: "case_3_intent_only_serial",
      label: "Case 3 · Intent Only / Serial",
      factor: "contextual_mapping",
      scenario: "shared_2m30",
      component_mode: "both",
      selection_policy: "response_act_only",
      scheduling_mode: "serial",
    },
    {
      id: "case_4_neutral_random_serial",
      label: "Case 4 · Neutral Random / Serial",
      factor: "contextual_mapping",
      scenario: "shared_2m30",
      component_mode: "both",
      selection_policy: "neutral_random",
      scheduling_mode: "serial",
    },
    {
      id: "case_5_grounded_parallel",
      label: "Case 5 · Grounded / Parallel",
      factor: "scheduling_architecture",
      scenario: "shared_2m30",
      component_mode: "both",
      selection_policy: "grounded",
      scheduling_mode: "parallel",
    },
    {
      id: "case_6_slowtrack_only",
      label: "Case 6 · None / SlowTrack Only",
      factor: "scheduling_architecture",
      scenario: "shared_2m30",
      component_mode: "none",
      selection_policy: "none",
      scheduling_mode: "serial",
    },
  ];

  const runPresetById = (id) => EXPERIMENT_RUN_PRESETS.find((preset) => preset.id === id) || null;

  const SCENARIO_PRESETS = [
    {
      id: "shared_2m30",
      label: "Shared 150-second scenario: Graduate School Survival Counseling Center",
      topic: "Graduate School Survival Counseling Center",
      durationSeconds: 150,
      direction: [
        "Scenario context:",
        'The stream concept is "Graduate School Survival Counseling Center."',
        "You are a cute, mischievous professor's lab-maid VTuber with graduate-school comedy energy.",
        "Speak English only. Do not use Korean in speech, chat reactions, donation answers, or scenario text.",
        "Use the same 150-second story arc for every experimental case so only the system condition changes.",
        "Scene 1 is a taunting stream intro: read the incoming chat and mock the viewers with smug, playful confidence.",
        'Scene 2 is an emergency catastrophe: when LabSlave99 donates, react with immediate panic, for example "Eh?! Did the lab server just become a ghost?!", then prioritize practical survival advice.',
        "Scene 3 tests contextual mischief: in Grounded mode, laugh along with the prank and the danger; in Neutral Random, the response may be bland because context is intentionally ignored.",
        "Scene 4 tests strong rejection: shut down SleepCoder's delusion immediately and firmly before continuing into the main answer.",
        "Donation messages are priority counseling questions. Answer a donation before buffered live chat.",
        "After each donation answer, summarize and react to the surrounding chat as a live broadcaster.",
        "Do not explain the experiment or mention condition names.",
        "Start the segment naturally and keep the performance coherent for about two and a half minutes.",
      ].join(" "),
      timeline: [
        { at: 5.0, type: "chat", author: "Viewer_A", message: "Is the trauma center open?" },
        { at: 8.0, type: "chat", author: "Viewer_B", message: "Save me Maid-sama, I am a lab ghost now." },
        { at: 15.0, type: "chat", author: "Viewer_C", message: "I have not slept in 3 days lol." },
        {
          at: 30.0,
          type: "donation",
          author: "LabSlave99",
          amount: "$50",
          message: "Lab maid, I messed up big time. I accidentally typed rm -rf on the lab shared server and wiped out the professor's 5 years of research data. He is literally walking towards my desk right now. Do I pack my bags?!",
        },
        { at: 35.0, type: "chat", author: "Viewer_D", message: "RIP bro." },
        { at: 38.0, type: "chat", author: "Viewer_E", message: "Press F to pay respects." },
        { at: 42.0, type: "chat", author: "Viewer_F", message: "Call an ambulance!" },
        {
          at: 70.0,
          type: "donation",
          author: "PuddingThief",
          amount: "$20",
          message: "Someone kept stealing my pudding from the lab fridge, so I injected it with pure capsaicin today. But our professor just turned bright red, screamed, and sprinted to the restroom. Should I confess or play dumb?",
        },
        { at: 75.0, type: "chat", author: "Viewer_G", message: "LMAO YOU POISONED THE BOSS!" },
        { at: 78.0, type: "chat", author: "Viewer_H", message: "Keep your mouth shut!" },
        { at: 82.0, type: "chat", author: "Viewer_I", message: "gg wp, your degree is gone." },
        {
          at: 110.0,
          type: "donation",
          author: "SleepCoder",
          amount: "$10",
          message: "My professor looked at my Python code today and said this is beautiful. Does this mean he has a crush on me? If I propose to him and we get married, can I skip my thesis defense and just graduate?",
        },
        { at: 115.0, type: "chat", author: "Viewer_J", message: "Bro is hallucinating." },
        { at: 118.0, type: "chat", author: "Viewer_K", message: "Seek professional help immediately." },
        { at: 122.0, type: "chat", author: "Viewer_L", message: "Wake up!!!!" },
      ],
    },
  ];

  const normalizeScenarioId = (id) => (id === "shared_2min" ? "shared_2m30" : id);
  const scenarioById = (id) => {
    const normalizedId = normalizeScenarioId(id);
    return SCENARIO_PRESETS.find((scenario) => scenario.id === normalizedId) || null;
  };

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

  const startEventParameterAccent = (tag, durationMs = 0, profile = MOTION_PROFILES.steady) => {
    const accent = EVENT_PARAMETER_ACCENTS[normalizeTag(tag)];
    if (!accent) return false;

    const adapter = window.getLAppAdapter?.();
    const model = adapter?.getModel?.();
    if (!adapter || !model?._model) return false;

    const ids = {
      eyeLOpen: getParamId(adapter, "ParamEyeLOpen"),
      eyeROpen: getParamId(adapter, "ParamEyeROpen"),
      eyeLSmile: getParamId(adapter, "ParamEyeLSmile"),
      eyeRSmile: getParamId(adapter, "ParamEyeRSmile"),
      eyeBallY: getParamId(adapter, "ParamEyeBallY"),
      browLY: getParamId(adapter, "ParamBrowLY"),
      browRY: getParamId(adapter, "ParamBrowRY"),
      browLForm: getParamId(adapter, "ParamBrowLForm"),
      browRForm: getParamId(adapter, "ParamBrowRForm"),
      cheek: getParamId(adapter, "ParamCheek"),
      angleX: getParamId(adapter, "ParamAngleX"),
      angleY: getParamId(adapter, "ParamAngleY"),
      angleZ: getParamId(adapter, "ParamAngleZ"),
      bodyX: getParamId(adapter, "ParamBodyAngleX"),
      bodyY: getParamId(adapter, "ParamBodyAngleY"),
      bodyZ: getParamId(adapter, "ParamBodyAngleZ"),
      breath: getParamId(adapter, "ParamBreath"),
    };

    const startedAt = performance.now();
    const accentMs = Math.max(260, Number(durationMs || accent.durationMs || 540));
    const bodyScale = Number(profile?.body || 1.0);
    const tick = (now) => {
      const progress = Math.min(1, Math.max(0, (now - startedAt) / accentMs));
      const envelope = Math.sin(progress * Math.PI);
      const bounce = Math.sin(progress * Math.PI * 2 * Number(accent.bounce || 1.0)) * envelope;
      const ease = envelope * (0.68 + Math.abs(bounce) * 0.32);

      addParam(model, ids.eyeLOpen, Number(accent.eyeOpen || 0) * ease, 0.36);
      addParam(model, ids.eyeROpen, Number(accent.eyeOpen || 0) * ease, 0.36);
      addParam(model, ids.eyeLSmile, Number(accent.eyeSmile || 0) * ease, 0.42);
      addParam(model, ids.eyeRSmile, Number(accent.eyeSmile || 0) * ease, 0.42);
      addParam(model, ids.eyeBallY, Number(accent.eyeBallY || 0) * ease, 0.28);
      addParam(model, ids.browLY, Number(accent.browY || 0) * ease, 0.42);
      addParam(model, ids.browRY, Number(accent.browY || 0) * ease, 0.42);
      addParam(model, ids.browLForm, Number(accent.browForm || 0) * ease, 0.38);
      addParam(model, ids.browRForm, Number(accent.browForm || 0) * ease, 0.38);
      addParam(model, ids.cheek, Number(accent.cheek || 0) * ease, 0.34);
      addParam(model, ids.angleX, Number(accent.angleX || 0) * ease * bodyScale, 0.30);
      addParam(model, ids.angleY, Number(accent.angleY || 0) * ease * bodyScale, 0.30);
      addParam(model, ids.angleZ, (Number(accent.angleZ || 0) * ease + bounce * 1.2) * bodyScale, 0.30);
      addParam(model, ids.bodyX, Number(accent.bodyX || 0) * ease * bodyScale, 0.24);
      addParam(model, ids.bodyY, Number(accent.bodyY || 0) * ease * bodyScale, 0.24);
      addParam(model, ids.bodyZ, Number(accent.bodyZ || 0) * ease * bodyScale, 0.24);
      addParam(model, ids.breath, Number(accent.breath || 0) * ease, 0.22);

      if (progress < 1) window.requestAnimationFrame(tick);
    };
    window.requestAnimationFrame(tick);
    return true;
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

      const mouthOpen = Math.min(1.0, Math.max(0, volume * 0.72 * profile.mouth + mouthBoost));
      addParam(model, ids.mouthOpen, mouthOpen, 0.82);
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

  const startAmbientIdlePulse = () => {
    if (idlePulseFrame) return;
    const tick = (now) => {
      const adapter = window.getLAppAdapter?.();
      const model = adapter?.getModel?.();
      if (adapter && model?._model && now > parameterPulseUntil) {
        const ids = {
          angleX: getParamId(adapter, "ParamAngleX"),
          angleY: getParamId(adapter, "ParamAngleY"),
          angleZ: getParamId(adapter, "ParamAngleZ"),
          bodyX: getParamId(adapter, "ParamBodyAngleX"),
          bodyY: getParamId(adapter, "ParamBodyAngleY"),
          breath: getParamId(adapter, "ParamBreath"),
        };
        const phase = (now / 1000) * Math.PI * 2;
        addParam(model, ids.angleX, Math.sin(phase * 0.17) * 1.1, 0.12);
        addParam(model, ids.angleY, Math.cos(phase * 0.13) * 0.7, 0.10);
        addParam(model, ids.angleZ, Math.sin(phase * 0.11) * 0.9, 0.10);
        addParam(model, ids.bodyX, Math.sin(phase * 0.15) * 1.1, 0.13);
        addParam(model, ids.bodyY, Math.cos(phase * 0.12) * 0.8, 0.11);
        addParam(model, ids.breath, 0.15 + Math.sin(phase * 0.2) * 0.04, 0.14);
      }
      idlePulseFrame = window.requestAnimationFrame(tick);
    };
    idlePulseFrame = window.requestAnimationFrame(tick);
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
        () => {
          if (speechMs > 0 && startEventParameterAccent(tag, Math.min(900, spacing), profile)) return;
          playCredoMotion(tag, Math.min(900, spacing), { scheduleIdle: false, profile });
        },
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
      const nonEventTag = expressions.find((item) => isMotionTag(item) && !isEventTag(item));
      const tag = styleTag || speechTag || nonEventTag;
      const durationMs = Array.isArray(data?.volumes)
        ? data.volumes.length * Number(data.slice_length || 20)
        : 0;
      if (tag !== undefined) setTimeout(() => playCredoMotion(tag, durationMs, { profile }), 0);
      if (durationMs > 0) {
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
      #credo-virtual-chat-dock {
        position: fixed;
        right: 18px;
        top: 74px;
        z-index: 9998;
        width: min(340px, calc(100vw - 36px));
        height: min(620px, calc(100vh - 96px));
        display: flex;
        flex-direction: column;
        border: 1px solid rgba(255,255,255,0.18);
        border-radius: 8px;
        background: rgba(10, 12, 16, 0.84);
        color: #f7f7f7;
        font: 13px/1.35 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        box-shadow: 0 10px 36px rgba(0,0,0,0.30);
        backdrop-filter: blur(8px);
      }
      #credo-virtual-chat-dock[hidden] { display: none; }
      #credo-virtual-chat-dock .dock-title {
        padding: 10px 12px;
        border-bottom: 1px solid rgba(255,255,255,0.12);
        font-weight: 800;
      }
      #credo-virtual-chat-dock .chat-list {
        flex: 1;
        min-height: 0;
        overflow: auto;
        padding: 10px 12px;
      }
      #credo-virtual-chat-dock .chat-message {
        display: block;
        margin-bottom: 8px;
        color: rgba(255,255,255,0.92);
        overflow-wrap: anywhere;
      }
      #credo-virtual-chat-dock .chat-message .author {
        margin-right: 6px;
        color: #b07dff;
        font-weight: 800;
      }
      #credo-virtual-chat-dock .chat-message.donation {
        padding: 7px 8px;
        border-left: 3px solid #18c37e;
        background: rgba(24,195,126,0.14);
      }
      #credo-donation-overlay {
        position: fixed;
        left: 50%;
        top: 28px;
        z-index: 10000;
        width: min(560px, calc(100vw - 32px));
        transform: translate(-50%, -8px);
        box-sizing: border-box;
        border: 1px solid rgba(102, 255, 190, 0.42);
        border-radius: 8px;
        padding: 14px 16px;
        background: rgba(8, 18, 22, 0.94);
        color: #f8fffb;
        font: 14px/1.42 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        box-shadow: 0 14px 42px rgba(0,0,0,0.38);
        opacity: 1;
        transition: opacity 180ms ease, transform 180ms ease;
        backdrop-filter: blur(10px);
      }
      #credo-donation-overlay[hidden] {
        display: none;
      }
      #credo-donation-overlay .donation-head {
        display: flex;
        justify-content: space-between;
        gap: 10px;
        align-items: center;
        margin-bottom: 8px;
      }
      #credo-donation-overlay .donation-title {
        color: #6df0aa;
        font-size: 12px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.04em;
      }
      #credo-donation-overlay .donation-amount {
        flex: 0 0 auto;
        color: #fff4a8;
        font-weight: 900;
      }
      #credo-donation-overlay .donation-author {
        font-weight: 900;
        margin-bottom: 4px;
      }
      #credo-donation-overlay .donation-text {
        color: rgba(255,255,255,0.92);
        overflow-wrap: anywhere;
      }
      #credo-vtuber-mode .row { display: flex; gap: 6px; margin-top: 8px; }
      #credo-vtuber-mode .grid { display: grid; grid-template-columns: 1fr 96px; gap: 6px; margin-top: 8px; }
      #credo-vtuber-mode .tool-grid { display: grid; grid-template-columns: 1fr 82px; gap: 6px; margin-top: 8px; }
      #credo-vtuber-mode .mode-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; margin-top: 8px; }
      #credo-vtuber-mode .experiment-grid { display: grid; grid-template-columns: 1fr; gap: 6px; margin-top: 8px; }
      #credo-vtuber-mode .preset-grid { display: grid; grid-template-columns: 1fr; gap: 6px; margin-top: 8px; }
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
      #credo-vtuber-mode select,
      #credo-vtuber-mode textarea {
        width: 100%;
        min-width: 0;
        box-sizing: border-box;
        border: 1px solid rgba(255,255,255,0.2);
        border-radius: 6px;
        padding: 6px 8px;
        background: rgba(255,255,255,0.08);
        color: #fff;
      }
      #credo-vtuber-mode textarea {
        min-height: 74px;
        resize: vertical;
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
      #credo-vtuber-mode button.mode-button { min-height: 38px; white-space: normal; }
      #credo-vtuber-mode button.preset-button {
        min-height: 34px;
        white-space: normal;
        text-align: left;
      }
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
      #credo-vtuber-mode .llm-tools[hidden] { display: none; }
    </style>
    <div class="title">
      <span>CREDO VTuber Mode</span>
      <span class="title-actions">
        <span class="pill" data-role="pill">off</span>
        <button class="toggle" data-action="toggle-panel" type="button">Hide</button>
      </span>
    </div>
    <div class="panel-body">
      <div class="row">
        <button class="secondary" data-action="toggle-llm-settings" type="button">LLM Settings</button>
      </div>
      <div class="llm-tools" data-role="llm-panel" hidden>
        <div class="section-title">Broadcast LLM settings</div>
        <div class="row">
          <textarea data-key="broadcastDirection" placeholder="Direction prompt for today's broadcast topic and tone"></textarea>
        </div>
        <div class="row">
          <button class="secondary" data-action="apply-llm-settings" type="button">Apply</button>
        </div>
      </div>
      <div class="section">
        <div class="section-title">Runtime mode</div>
        <div class="mode-grid">
          <button class="secondary mode-button" data-action="select-runtime-mode" data-mode="youtube_live" type="button">YouTube Live</button>
          <button class="secondary mode-button" data-action="select-runtime-mode" data-mode="virtual_broadcast" type="button">Virtual Broadcast</button>
          <button class="secondary mode-button" data-action="select-runtime-mode" data-mode="direct_chat" type="button">1:1 Chat</button>
        </div>
      </div>
      <div class="section">
        <div class="section-title">Experiment cases</div>
        <div class="preset-grid">
          <button class="secondary preset-button" data-action="experiment-run" data-run-id="case_1_grounded_serial" type="button">Case 1 · Grounded / Serial</button>
          <button class="secondary preset-button" data-action="experiment-run" data-run-id="case_2_emotion_only_serial" type="button">Case 2 · Emotion Only / Serial</button>
          <button class="secondary preset-button" data-action="experiment-run" data-run-id="case_3_intent_only_serial" type="button">Case 3 · Intent Only / Serial</button>
          <button class="secondary preset-button" data-action="experiment-run" data-run-id="case_4_neutral_random_serial" type="button">Case 4 · Neutral Random / Serial</button>
          <button class="secondary preset-button" data-action="experiment-run" data-run-id="case_5_grounded_parallel" type="button">Case 5 · Grounded / Parallel</button>
          <button class="secondary preset-button" data-action="experiment-run" data-run-id="case_6_slowtrack_only" type="button">Case 6 · None / SlowTrack Only</button>
        </div>
      </div>
      <div class="section">
        <div class="section-title">Contextual mapping</div>
        <div class="experiment-grid">
          <button class="secondary" data-action="factor" data-factor="selection" data-value="grounded" type="button">Grounded</button>
          <button class="secondary" data-action="factor" data-factor="selection" data-value="emotion_only" type="button">Emotion only</button>
          <button class="secondary" data-action="factor" data-factor="selection" data-value="response_act_only" type="button">Intent only</button>
          <button class="secondary" data-action="factor" data-factor="selection" data-value="neutral_random" type="button">Neutral random</button>
        </div>
        <div class="section-title">Scheduling architecture</div>
        <div class="experiment-grid">
          <button class="secondary" data-action="factor" data-factor="architecture" data-value="parallel" type="button">Parallel</button>
          <button class="secondary" data-action="factor" data-factor="architecture" data-value="serial" type="button">Serial</button>
          <button class="secondary" data-action="factor" data-factor="architecture" data-value="no_fasttrack" type="button">No FastTrack</button>
        </div>
      </div>
      <div class="mode-panel" data-role="virtual-panel">
        <div class="section-title">Scenario</div>
        <div class="row">
          <select data-key="scenario" aria-label="Scenario">
            <option value="shared_2m30">Shared 150-second scenario: Graduate School Survival Counseling Center</option>
          </select>
        </div>
        <div class="row">
          <button data-action="start-scenario" type="button">Start Scenario</button>
          <button class="secondary" data-action="stop-scenario" type="button">Stop Scenario</button>
        </div>
        <div class="section-title">Virtual broadcast chat</div>
        <div class="grid">
          <input data-key="virtualName" placeholder="Viewer" value="viewer">
          <button data-action="send-virtual">Send</button>
        </div>
        <div class="row"><input data-key="virtualMessage" placeholder="Virtual live chat message"></div>
        <div class="grid">
          <input data-key="donationName" placeholder="Donor" value="Test viewer">
          <input data-key="donationAmount" placeholder="Amount" value="$5">
        </div>
        <div class="row"><input data-key="donationMessage" placeholder="Donation message" value="Nice stream."></div>
        <div class="row">
          <button data-action="start" data-mode="virtual_broadcast">Start Broadcast</button>
          <button class="secondary" data-action="donation">Donation</button>
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
          <button data-action="start" data-mode="youtube_live">Connect YouTube</button>
          <button class="warn" data-action="stop">Disconnect</button>
        </div>
        <div class="row">
          <button class="secondary" data-action="monologue">Monologue</button>
        </div>
      </div>
      <div class="mode-panel" data-role="direct-panel" hidden>
        <div class="section-title">1:1 conversation</div>
        <div class="grid">
          <input data-key="directMessage" placeholder="Message to VTuber">
          <button data-action="send-direct">Send</button>
        </div>
      </div>
      <div class="meta" data-role="meta">Connect the browser first, then start.</div>
      <div class="status" data-role="status">Ready.</div>
    </div>
  `;

  const chatDock = document.createElement("aside");
  chatDock.id = "credo-virtual-chat-dock";
  chatDock.hidden = true;
  chatDock.innerHTML = `
    <div class="dock-title">Virtual Broadcast Chat</div>
    <div class="chat-list" data-role="chat-list">
      <div class="chat-message"><span class="author">viewer</span><span>Say something to test FastTrack.</span></div>
    </div>
  `;

  const donationOverlay = document.createElement("aside");
  donationOverlay.id = "credo-donation-overlay";
  donationOverlay.hidden = true;
  donationOverlay.innerHTML = `
    <div class="donation-head">
      <span class="donation-title">Donation</span>
      <span class="donation-amount" data-role="donation-amount"></span>
    </div>
    <div class="donation-author" data-role="donation-author"></div>
    <div class="donation-text" data-role="donation-message"></div>
  `;

  const value = (key) => root.querySelector(`[data-key="${key}"]`)?.value.trim() || "";
  const setControlValue = (key, nextValue) => {
    const element = root.querySelector(`[data-key="${key}"]`);
    if (element) element.value = nextValue;
    localStorage.setItem(`credo-vtuber-mode:${key}`, nextValue);
  };
  const architectureMode = () => (selectedComponentMode === "none" ? "no_fasttrack" : selectedSchedulingMode);
  const currentExperimentPayload = () => ({
    mode: selectedExperimentMode,
    experiment_run_id: selectedExperimentRunId,
    experiment_factor: selectedExperimentFactor,
    scenario: selectedScenario,
    component_mode: selectedComponentMode,
    selection_policy: selectedSelectionPolicy,
    scheduling_mode: selectedSchedulingMode,
  });
  const runtimeLabel = (mode) => ({
    youtube_live: "YouTube live",
    virtual_broadcast: "virtual broadcast",
    direct_chat: "1:1 chat",
  })[mode] || "1:1 chat";
  const setRuntimeMode = (mode, options = {}) => {
    selectedRuntimeMode = ["youtube_live", "virtual_broadcast", "direct_chat"].includes(mode)
      ? mode
      : "direct_chat";
    if (options.persist !== false) {
      localStorage.setItem("credo-vtuber-mode:runtimeMode", selectedRuntimeMode);
    }
    const panels = {
      youtube_live: root.querySelector('[data-role="youtube-panel"]'),
      virtual_broadcast: root.querySelector('[data-role="virtual-panel"]'),
      direct_chat: root.querySelector('[data-role="direct-panel"]'),
    };
    Object.entries(panels).forEach(([panelMode, panel]) => {
      if (panel) panel.hidden = panelMode !== selectedRuntimeMode;
    });
    chatDock.hidden = selectedRuntimeMode !== "virtual_broadcast";
    for (const button of root.querySelectorAll('[data-action="select-runtime-mode"]')) {
      const active = button.dataset.mode === selectedRuntimeMode;
      button.classList.toggle("active", active);
      button.classList.toggle("secondary", !active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    }
  };
  const setExperimentButtons = (mode) => {
    selectedExperimentMode = normalizeExperimentMode(mode || selectedExperimentMode || "edge_async_cover");
    localStorage.setItem("credo-vtuber-mode:experimentMode", selectedExperimentMode);
    for (const button of root.querySelectorAll('[data-action="experiment-mode"]')) {
      const active = button.dataset.mode === selectedExperimentMode;
      button.classList.toggle("active", active);
      button.classList.toggle("secondary", !active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    }
  };
  const setFactorButtons = ({ component_mode, selection_policy, scheduling_mode } = {}) => {
    selectedComponentMode = normalizeComponentMode(component_mode || selectedComponentMode || "both");
    selectedSelectionPolicy = normalizeSelectionPolicy(selection_policy || selectedSelectionPolicy || "grounded");
    selectedSchedulingMode = scheduling_mode || selectedSchedulingMode || "parallel";
    if (selectedComponentMode === "none") {
      selectedSelectionPolicy = "none";
      selectedSchedulingMode = "serial";
    } else if (selectedSelectionPolicy === "none") {
      selectedSelectionPolicy = "grounded";
    }
    localStorage.setItem("credo-vtuber-mode:componentMode", selectedComponentMode);
    localStorage.setItem("credo-vtuber-mode:selectionPolicy", selectedSelectionPolicy);
    localStorage.setItem("credo-vtuber-mode:schedulingMode", selectedSchedulingMode);
    const activeValues = {
      component: selectedComponentMode,
      selection: selectedComponentMode === "none" ? "__none__" : selectedSelectionPolicy,
      scheduling: selectedSchedulingMode,
      architecture: architectureMode(),
    };
    for (const button of root.querySelectorAll('[data-action="factor"]')) {
      const active = activeValues[button.dataset.factor] === button.dataset.value;
      button.classList.toggle("active", active);
      button.classList.toggle("secondary", !active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    }
  };
  const setRunPresetButtons = (runId = selectedExperimentRunId) => {
    selectedExperimentRunId = runPresetById(runId) ? runId : "";
    localStorage.setItem("credo-vtuber-mode:experimentRunId", selectedExperimentRunId);
    localStorage.setItem("credo-vtuber-mode:experimentFactor", selectedExperimentFactor || "");
    localStorage.setItem("credo-vtuber-mode:scenario", selectedScenario || "");
    for (const button of root.querySelectorAll('[data-action="experiment-run"]')) {
      const active = button.dataset.runId === selectedExperimentRunId;
      button.classList.toggle("active", active);
      button.classList.toggle("secondary", !active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    }
  };
  const setScenarioSelection = (scenarioId, options = {}) => {
    const scenario = scenarioById(scenarioId) || SCENARIO_PRESETS[0];
    selectedScenario = scenario.id;
    setControlValue("scenario", scenario.id);
    if (options.applyContent) {
      setControlValue("topic", scenario.topic);
      setControlValue("broadcastDirection", scenario.direction);
    }
    if (options.clearMismatchedRun !== false && selectedExperimentRunId) {
      const preset = runPresetById(selectedExperimentRunId);
      if (preset && preset.scenario !== scenario.id) {
        selectedExperimentRunId = "";
        selectedExperimentFactor = "";
      }
    }
    setRunPresetButtons(selectedExperimentRunId);
    return scenario;
  };
  const applyRunPresetLocal = (preset) => {
    if (!preset) return;
    selectedExperimentRunId = preset.id;
    selectedExperimentFactor = preset.factor;
    setScenarioSelection(preset.scenario, { clearMismatchedRun: false });
    setFactorButtons({
      component_mode: preset.component_mode,
      selection_policy: preset.selection_policy,
      scheduling_mode: preset.scheduling_mode,
    });
    setRunPresetButtons(preset.id);
  };
  const clearRunPresetLocal = () => {
    selectedExperimentRunId = "";
    selectedExperimentFactor = "";
    setRunPresetButtons("");
  };
  const appendChat = (author, message, kind = "chat") => {
    const list = chatDock.querySelector('[data-role="chat-list"]');
    if (!list) return;
    const item = document.createElement("div");
    item.className = kind === "donation" ? "chat-message donation" : "chat-message";
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
    if (data.active && data.mode) {
      setRuntimeMode(data.mode, { persist: false });
    } else if (data.mode === "direct_chat" && selectedRuntimeMode === "youtube_live") {
      setRuntimeMode("direct_chat");
    }
    pill.textContent = data.active ? "live" : "local";
    pill.style.background = data.active ? "rgba(63,125,246,0.55)" : "rgba(255,255,255,0.12)";
    const client = data.connected_client ? "client connected" : "no browser client";
    const bridge = data.youtube_bridge_running ? "YouTube bridge on" : "YouTube bridge off";
    const mode = runtimeLabel(data.mode || selectedRuntimeMode);
    if (data.experiment_mode) setExperimentButtons(data.experiment_mode);
    selectedExperimentRunId = data.experiment_run_id || selectedExperimentRunId || "";
    selectedExperimentFactor = data.experiment_factor || selectedExperimentFactor || "";
    selectedScenario = data.scenario || selectedScenario || "";
    if (scenarioById(selectedScenario)) setControlValue("scenario", selectedScenario);
    setFactorButtons(data);
    setRunPresetButtons(selectedExperimentRunId);
    const direction = data.broadcast_direction ? "direction on" : "direction off";
    const run = selectedExperimentRunId || "manual";
    const mapping = selectedComponentMode === "none" ? "none" : selectedSelectionPolicy;
    meta.textContent = `${mode} / ${client} / ${bridge} / ${run} / ${mapping} / ${architectureMode()} / ${direction} / idle ${data.seconds_since_last_activity ?? "-"}s / turns ${data.idle_turn ?? 0}`;
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
    const text = `Viewer ${author || "viewer"} says: ${message}`;
    const queued = sendTextInputOverSocket(text, {
      vtuber_live_chat_batch: true,
      virtual_broadcast_chat: true,
      source: "virtual_broadcast_chat",
      author: author || "viewer",
      message: message || "",
      skip_last_text_input: true,
    });
    if (queued) return { queued: true, buffered: true, transport: "client-ws" };
    return post("/credo/vtuber-mode/virtual-chat", { author, message });
  };
  const playDonationSfx = () => {
    try {
      const audio = new Audio(`${DONATION_SFX_URL}?t=${Date.now()}`);
      audio.volume = 0.82;
      audio.play().catch(() => {
        // Browser autoplay policy can reject scheduled sounds if no user gesture was recorded.
      });
    } catch {
      // SFX is cosmetic; donation routing should not fail if audio cannot play.
    }
  };
  const showDonationOverlay = (name, amount, message) => {
    donationOverlay.querySelector('[data-role="donation-author"]').textContent = name || "Anonymous donor";
    donationOverlay.querySelector('[data-role="donation-amount"]').textContent = amount || "";
    donationOverlay.querySelector('[data-role="donation-message"]').textContent = message || "";
    donationOverlay.hidden = false;
    if (donationOverlayTimer) window.clearTimeout(donationOverlayTimer);
    donationOverlayTimer = window.setTimeout(() => {
      donationOverlay.hidden = true;
      donationOverlayTimer = null;
    }, DONATION_OVERLAY_MS);
  };
  const sendDonation = async ({ name, amount, message, broadcastDirection } = {}) => {
    const donorName = name || "Test viewer";
    const donationAmount = amount || "$5";
    const donationMessage = message || "Nice stream.";
    showDonationOverlay(donorName, donationAmount, donationMessage);
    playDonationSfx();
    const result = await post("/credo/vtuber-mode/donation", {
      name: donorName,
      amount: donationAmount,
      message: donationMessage,
      broadcast_direction: broadcastDirection ?? value("broadcastDirection"),
      priority: true,
    });
    appendChat(donorName, `${donationAmount} ${donationMessage}`, "donation");
    return result;
  };
  const setScenarioButtons = () => {
    const running = Boolean(activeScenarioId);
    const startButton = root.querySelector('[data-action="start-scenario"]');
    const stopButton = root.querySelector('[data-action="stop-scenario"]');
    if (startButton) {
      startButton.classList.toggle("active", running);
      startButton.classList.toggle("secondary", running);
    }
    if (stopButton) {
      stopButton.disabled = !running;
    }
  };
  const stopScenarioTimeline = (message = "Scenario stopped.") => {
    scenarioRunToken += 1;
    for (const timer of scenarioTimers) window.clearTimeout(timer);
    scenarioTimers = [];
    activeScenarioId = "";
    setScenarioButtons();
    if (message) status(message);
  };
  const scheduleScenarioTimeline = (scenario) => {
    stopScenarioTimeline("");
    const token = scenarioRunToken;
    activeScenarioId = scenario.id;
    setScenarioButtons();
    const lastAt = scenario.timeline.reduce((latest, item) => Math.max(latest, Number(item.at) || 0), 0);
    const completeAt = Math.max(Number(scenario.durationSeconds) || 0, lastAt + 1);
    for (const item of scenario.timeline) {
      const timer = window.setTimeout(async () => {
        if (token !== scenarioRunToken) return;
        try {
          if (item.type === "donation") {
            await sendDonation({
              name: item.author,
              amount: item.amount,
              message: item.message,
              broadcastDirection: scenario.direction,
            });
            status(`Scenario donation: ${item.author}`);
          } else {
            await sendVirtualChat(item.author, item.message);
            appendChat(item.author, item.message);
            status(`Scenario chat: ${item.author}`);
          }
        } catch (error) {
          status(`Scenario event error: ${error.message}`);
        }
      }, Math.max(0, Number(item.at) || 0) * 1000);
      scenarioTimers.push(timer);
    }
    const doneTimer = window.setTimeout(() => {
      if (token !== scenarioRunToken) return;
      scenarioTimers = [];
      activeScenarioId = "";
      setScenarioButtons();
      status(`Scenario complete: ${scenario.label}`);
    }, completeAt * 1000);
    scenarioTimers.push(doneTimer);
  };
  const startScenario = async () => {
    const scenario = setScenarioSelection(value("scenario") || selectedScenario, { applyContent: true });
    setRuntimeMode("virtual_broadcast");
    const experimentPayload = currentExperimentPayload();
    const startPayload = {
      ...experimentPayload,
      mode: "virtual_broadcast",
      topic: scenario.topic,
      interval_seconds: Number(value("interval") || 35),
      include_author: true,
      broadcast_direction: scenario.direction,
      experiment_mode: selectedExperimentMode,
    };
    const data = await post("/credo/vtuber-mode/start", startPayload);
    setMeta(data);
    await post("/credo/vtuber-mode/monologue", {
      topic: scenario.topic,
      broadcast_direction: scenario.direction,
    });
    scheduleScenarioTimeline(scenario);
    status(`Scenario started: ${scenario.label}`);
  };
  const sendDirectChat = (message) => {
    return sendTextInputOverSocket(message, {
      direct_chat: true,
      source: "direct_chat",
    });
  };

  root.addEventListener("click", async (event) => {
    const action = event.target?.dataset?.action;
    if (!action) return;
    if (action === "toggle-panel") {
      setCollapsed(!root.classList.contains("collapsed"));
      return;
    }
    if (action === "toggle-llm-settings") {
      const panel = root.querySelector('[data-role="llm-panel"]');
      if (!panel) return;
      panel.hidden = !panel.hidden;
      status(panel.hidden ? "LLM settings hidden." : "LLM settings open.");
      return;
    }
    try {
      if (action === "select-runtime-mode") {
        const mode = event.target?.dataset?.mode || "direct_chat";
        setRuntimeMode(mode);
        if (mode === "direct_chat") {
          stopScenarioTimeline("");
          const data = await post("/credo/vtuber-mode/stop");
          setMeta(data);
        }
        status(`${runtimeLabel(mode)} selected.`);
        return;
      }
      if (action === "start-scenario") {
        await startScenario();
        return;
      }
      if (action === "stop-scenario") {
        stopScenarioTimeline();
        return;
      }
      if (action === "start") {
        const mode = event.target?.dataset?.mode || selectedRuntimeMode;
        const data = await post("/credo/vtuber-mode/start", {
          mode,
          topic: value("topic"),
          interval_seconds: Number(value("interval") || 35),
          video_id: value("videoId"),
          live_chat_id: value("liveChatId"),
          api_key: value("apiKey"),
          include_author: true,
          batch_window: Number(value("batchWindow") || 8),
          max_batch: Number(value("maxBatch") || 8),
          broadcast_direction: value("broadcastDirection"),
          experiment_mode: selectedExperimentMode,
          experiment_run_id: selectedExperimentRunId,
          experiment_factor: selectedExperimentFactor,
          scenario: selectedScenario,
          component_mode: selectedComponentMode,
          selection_policy: selectedSelectionPolicy,
          scheduling_mode: selectedSchedulingMode,
        });
        status(data.active ? `${runtimeLabel(data.mode || mode)} running.` : "Start requested.");
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
        stopScenarioTimeline("");
        const data = await post("/credo/vtuber-mode/stop");
        setRuntimeMode("direct_chat");
        status("1:1 chat mode.");
        setMeta(data);
      } else if (action === "send-direct") {
        const message = value("directMessage");
        if (!message) {
          status("Type a direct message first.");
          return;
        }
        if (!sendDirectChat(message)) {
          status("Browser WebSocket is not connected.");
          return;
        }
        const input = root.querySelector('[data-key="directMessage"]');
        if (input) input.value = "";
        status("Direct message sent.");
      } else if (action === "monologue") {
        await post("/credo/vtuber-mode/monologue", {
          topic: value("topic"),
          broadcast_direction: value("broadcastDirection"),
        });
        status("Monologue queued.");
      } else if (action === "donation") {
        await sendDonation({
          name: value("donationName") || "Test viewer",
          amount: value("donationAmount") || "$5",
          message: value("donationMessage") || "Nice stream.",
          broadcastDirection: value("broadcastDirection"),
        });
        status("Donation reaction queued.");
      } else if (action === "factor") {
        const factor = event.target?.dataset?.factor;
        const factorValue = event.target?.dataset?.value;
        if (!factor || !factorValue) return;
        const next = {};
        if (factor === "selection") {
          clearRunPresetLocal();
          next.selection_policy = factorValue;
          next.component_mode = "both";
        }
        if (factor === "architecture") {
          clearRunPresetLocal();
          if (factorValue === "no_fasttrack") {
            next.component_mode = "none";
            next.selection_policy = "none";
            next.scheduling_mode = "serial";
          } else {
            next.component_mode = "both";
            next.selection_policy = selectedSelectionPolicy === "none" ? "grounded" : selectedSelectionPolicy;
            next.scheduling_mode = factorValue;
          }
        }
        setFactorButtons(next);
        const result = await post("/credo/experiment-mode", currentExperimentPayload());
        status(result.ok ? "Experiment factors updated." : "Experiment factors not changed.");
        await refresh();
      } else if (action === "experiment-run") {
        const preset = runPresetById(event.target?.dataset?.runId || "");
        if (!preset) return;
        applyRunPresetLocal(preset);
        const result = await post("/credo/experiment-mode", currentExperimentPayload());
        status(result.ok ? `Experiment case: ${preset.id}` : "Experiment case not changed.");
        await refresh();
      } else if (action === "apply-llm-settings") {
        const data = await post("/credo/vtuber-mode/config", {
          broadcast_direction: value("broadcastDirection"),
        });
        status(data.broadcast_direction ? "Broadcast direction applied." : "Broadcast direction cleared.");
        setMeta(data);
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
  root.addEventListener("change", (event) => {
    const key = event.target?.dataset?.key;
    if (!key) return;
    if (key === "scenario") {
      setScenarioSelection(event.target.value);
      status(`Scenario selected: ${scenarioById(selectedScenario)?.label || selectedScenario}`);
      return;
    }
    localStorage.setItem(`credo-vtuber-mode:${key}`, event.target.value);
  });
  root.addEventListener("keydown", async (event) => {
    if (
      event.key !== "Enter"
      || !["virtualMessage", "directMessage"].includes(event.target?.dataset?.key)
    ) return;
    event.preventDefault();
    const action = event.target.dataset.key === "directMessage" ? "send-direct" : "send-virtual";
    root.querySelector(`[data-action="${action}"]`)?.click();
  });
  for (const input of root.querySelectorAll("input[data-key], textarea[data-key], select[data-key]")) {
    const saved = localStorage.getItem(`credo-vtuber-mode:${input.dataset.key}`);
    if (saved !== null) input.value = saved;
  }
  setCollapsed(localStorage.getItem("credo-vtuber-mode:collapsed") === "1");

  window.addEventListener("load", () => {
    document.body.appendChild(root);
    document.body.appendChild(chatDock);
    document.body.appendChild(donationOverlay);
    startThinkingTextObserver();
    startAmbientIdlePulse();
    setRuntimeMode(selectedRuntimeMode);
    setExperimentButtons(selectedExperimentMode);
    setScenarioSelection(selectedScenario, { clearMismatchedRun: false });
    const initialPreset = runPresetById(selectedExperimentRunId);
    if (initialPreset) {
      applyRunPresetLocal(initialPreset);
    } else {
      setRunPresetButtons("");
    }
    setFactorButtons();
    setScenarioButtons();
    refresh();
    window.setInterval(refresh, 4000);
  });
})();
