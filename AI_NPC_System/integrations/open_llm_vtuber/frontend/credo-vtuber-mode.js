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

  const EMOTION_EVENT_TAG_BY_EMOTION = {
    positive: "credo_event_motion:laugh",
    negative: "credo_event_motion:sigh",
    ambiguous: "credo_event_motion:surprise",
    neutral: "credo_event_motion:thinking",
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
  const IDLE_MOTION_GROUP = "Idle";
  const IDLE_MOTION_REPLAY_MS = 9200;
  const IDLE_MOTION_RETRY_MS = 700;
  const EXPRESSION_HOLD_MS = 10000;
  const EXPRESSION_ATTACK_MS = 260;
  const EXPRESSION_RELEASE_MS = 900;
  let idleReturnTimer = null;
  let idleMotionTimer = null;
  let lastIdleMotionAt = Number.NEGATIVE_INFINITY;
  let eventAccentFrame = null;
  let eventAccentToken = 0;
  let parameterPulseFrame = null;
  let parameterPulseUntil = 0;
  let parameterPulseToken = 0;
  let idlePulseFrame = null;
  let donationMotionToken = 0;
  const EXPERIMENT_RUNTIME_MODE = "edge_async_cover";
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
  const normalizeSchedulingMode = () => "serial";
  const EXPERIMENT_RUN_ID_ALIASES = {
    case_6_slowtrack_only: "case_5_slowtrack_only",
  };
  const normalizeExperimentRunId = (id) => EXPERIMENT_RUN_ID_ALIASES[id] || id || "";
  let selectedComponentMode = normalizeComponentMode(localStorage.getItem("credo-vtuber-mode:componentMode") || "both");
  let selectedSelectionPolicy = normalizeSelectionPolicy(
    localStorage.getItem("credo-vtuber-mode:selectionPolicy") || "grounded",
  );
  let selectedSchedulingMode = normalizeSchedulingMode(localStorage.getItem("credo-vtuber-mode:schedulingMode") || "serial");
  let selectedRuntimeMode = localStorage.getItem("credo-vtuber-mode:runtimeMode") || "direct_chat";
  let selectedExperimentRunId = normalizeExperimentRunId(localStorage.getItem("credo-vtuber-mode:experimentRunId") || "");
  let selectedExperimentFactor = localStorage.getItem("credo-vtuber-mode:experimentFactor") || "";
  let selectedScenario = localStorage.getItem("credo-vtuber-mode:scenario") || "shared_2m30";
  let fasttrackSubtitleHighlightEnabled = localStorage.getItem("credo-vtuber-mode:fasttrackSubtitleHighlight") !== "0";
  let scenarioTimers = [];
  let scenarioRunToken = 0;
  let activeScenarioId = "";
  let donationOverlayTimer = null;
  let subtitleHideTimer = null;
  let subtitleTimers = [];
  let subtitleToken = 0;
  let donationQueue = Promise.resolve();
  let donationQueueDepth = 0;
  let donationQueueToken = 0;
  let donationSfxIndex = 0;
  let donationSfxAudio = null;
  let donationReadoutAudio = null;
  let donationReadoutActive = false;
  let donationAnswerPending = false;
  let donationAudioQuarantineUntil = 0;
  const DONATION_OVERLAY_MS = 15000;
  const DONATION_AUDIO_QUARANTINE_MS = 30000;
  const CREDO_SPEECH_SUBTITLES_ENABLED = true;
  const SUPPRESS_OPEN_LLM_SUBTITLE_FRAMES = true;
  const KEEP_SPEECH_SUBTITLES_VISIBLE = true;
  const SUBTITLE_MAX_CHARS = 48;
  const FASTTRACK_SUBTITLE_MAX_CHARS = 54;
  const suppressedOpenLlmSubtitleTexts = new Set();
  const STATUS_SUBTITLE_TEXT_PATTERN = /^(Thinking\.{0,3}|New Conversation Started)$/i;
  const HIDDEN_STATUS_SUBTITLE_ATTR = "data-credo-hidden-status-subtitle";
  const PREVIOUS_DISPLAY_ATTR = "data-credo-previous-display";
  const PREVIOUS_ARIA_HIDDEN_ATTR = "data-credo-previous-aria-hidden";
  const setDonationAudioQuarantine = (durationMs = DONATION_AUDIO_QUARANTINE_MS) => {
    donationAudioQuarantineUntil = Date.now() + Math.max(0, Number(durationMs) || 0);
    window.__credoDonationAudioQuarantineUntil = donationAudioQuarantineUntil;
  };
  const clearDonationAudioQuarantine = () => {
    donationAnswerPending = false;
    donationAudioQuarantineUntil = 0;
    window.__credoDonationAnswerPending = false;
    window.__credoDonationAudioQuarantineUntil = 0;
  };
  const donationAudioQuarantineActive = () => {
    const until = Math.max(
      Number(donationAudioQuarantineUntil) || 0,
      Number(window.__credoDonationAudioQuarantineUntil) || 0,
    );
    return Date.now() < until;
  };
  const pauseActiveSpeechForDonation = () => {
    window.__credoStopSpeechParameterPulse?.({ scheduleIdle: false });
    const tracked = window.__credoTrackedAudioElements || new Set();
    document.querySelectorAll("audio").forEach((audio) => tracked.add(audio));
    tracked.forEach((audio) => {
      try {
        if (!audio || audio.dataset?.credoDonationAudio === "1") return;
        if (!audio.paused) audio.pause();
        audio.currentTime = 0;
      } catch {
        // Ignore media elements that are already detached.
      }
    });
  };
  if (!window.__credoAudioTrackerPatched) {
    window.__credoAudioTrackerPatched = true;
    window.__credoTrackedAudioElements = window.__credoTrackedAudioElements || new Set();
    const nativePlay = HTMLMediaElement.prototype.play;
    HTMLMediaElement.prototype.play = function (...args) {
      if (this instanceof HTMLAudioElement) {
        const donationQuarantine = Date.now() < (Number(window.__credoDonationAudioQuarantineUntil) || 0);
        if (
          (window.__credoDonationReadoutActive || donationQuarantine)
          && this.dataset?.credoDonationAudio !== "1"
        ) {
          try {
            this.pause();
            this.currentTime = 0;
          } catch {
            // Ignore media elements that are already detached.
          }
          return Promise.resolve();
        }
        window.__credoTrackedAudioElements.add(this);
        if (typeof speechSubtitle !== "undefined" && speechSubtitle && !speechSubtitle.hidden) {
          this.dataset.credoSubtitleToken = String(subtitleToken);
        } else {
          delete this.dataset.credoSubtitleToken;
        }
        if (this.dataset.credoSubtitlePauseListener !== "1") {
          this.dataset.credoSubtitlePauseListener = "1";
          this.addEventListener("pause", () => {
            if (this.dataset?.credoDonationAudio === "1") return;
            window.__credoStopSpeechParameterPulse?.({ scheduleIdle: true });
            const token = Number(this.dataset.credoSubtitleToken);
            if (!KEEP_SPEECH_SUBTITLES_VISIBLE && Number.isFinite(token) && typeof hideSpeechSubtitle === "function") {
              hideSpeechSubtitle({ expectedToken: token });
            }
          });
          this.addEventListener("ended", () => {
            window.__credoTrackedAudioElements.delete(this);
            if (this.dataset?.credoDonationAudio === "1") return;
            window.__credoStopSpeechParameterPulse?.({ scheduleIdle: true });
            const token = Number(this.dataset.credoSubtitleToken);
            if (!KEEP_SPEECH_SUBTITLES_VISIBLE && Number.isFinite(token) && typeof hideSpeechSubtitle === "function") {
              hideSpeechSubtitle({ expectedToken: token });
            }
          });
        }
      }
      return nativePlay.apply(this, args);
    };
  }
  const DONATION_SFX_URLS = [
    "./credo-donation-sfx.mp3",
    "/credo-donation-sfx.mp3",
    "/credo/vtuber-mode/donation-sfx",
  ];
  const CHAT_AUTHOR_COLORS = [
    "#ff7aa2",
    "#7cc7ff",
    "#82e38d",
    "#ffd166",
    "#c59cff",
    "#ff9b6a",
    "#58e6d9",
    "#f28cff",
    "#a5d76e",
    "#ffcf70",
  ];

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
      id: "case_5_slowtrack_only",
      label: "Case 5 · None / SlowTrack Only",
      factor: "scheduling_architecture",
      scenario: "shared_2m30",
      component_mode: "none",
      selection_policy: "none",
      scheduling_mode: "serial",
    },
  ];

  const runPresetById = (id) => {
    const normalizedId = normalizeExperimentRunId(id);
    return EXPERIMENT_RUN_PRESETS.find((preset) => preset.id === normalizedId) || null;
  };

  const INTERNET_CHAT_VIEWERS = ["LOLByte", "EmojiRush"];
  const internetChatMessageFor = (at, index) => {
    if (at < 38) {
      return [
        "lolol katana healing 😂🗡️💚",
        "LMAO cute blade delivery system 😭✨",
        "chat got comforted and sliced lol 💀",
        "gentle voice sharp audit omg 😂📋",
      ][index % 4];
    }
    if (at < 78) {
      return [
        "LOL senior stole the render pass 😭😭",
        "lmao academic theft boss fight 💀📚",
        "lab meeting betrayal arc omg 😭",
        "credit where citation is due lol 🧾✨",
      ][index % 4];
    }
    if (at < 108) {
      return [
        "professor admiration is peaking lol 💖📈",
        "advisor fan club mode LMAO 😭💕",
        "please debug this affection lolol 💀",
        "camera-ready feelings submitted 😂📝✨",
      ][index % 4];
    }
    return [
      "PROFESSOR WATCHING STATUS CRITICAL 😭🚨",
      "chat posture corrected instantly lol 🫡",
      "every message camera-ready now 😂📄",
      "lmao emergency politeness mode 💀🙏",
    ][index % 4];
  };
  const withInternetChatter = (timeline) => {
    const extras = [];
    let chatIndex = 0;
    for (const item of timeline) {
      if (item.type !== "chat") continue;
      extras.push({
        at: Number((Number(item.at) + 0.38).toFixed(2)),
        type: "chat",
        author: INTERNET_CHAT_VIEWERS[chatIndex % INTERNET_CHAT_VIEWERS.length],
        message: internetChatMessageFor(Number(item.at) || 0, chatIndex),
      });
      chatIndex += 1;
    }
    return [...timeline, ...extras].sort((a, b) => Number(a.at) - Number(b.at));
  };

  const SCENARIO_PRESETS = [
    {
      id: "shared_2m30",
      label: "Shared 150-second scenario: Lab Maid Donation Reality Check",
      topic: "Professor's Lab Maid Donation Reality Check",
      durationSeconds: 150,
      direction: [
        "Scenario context:",
        'The stream concept is "Professor\'s Lab Maid Donation Reality Check: Computer Graphics Lab Edition."',
        "You are a cute, mischievous professor's computer-graphics lab-maid VTuber with graduate-school counseling comedy energy.",
        "Speak English only. Do not use Korean in speech, chat reactions, donation answers, or scenario text.",
        "Chat lines are formatted as viewer nicknames plus messages. When directly answering one specific viewer, address the viewer by nickname once when it feels natural; do not force a romanized honorific or catchphrase. When summarizing multiple chat messages, address the room naturally and do not list nicknames.",
        "Use the same 150-second story arc for every experimental case so only the system condition changes.",
        "Skip the opening intro. The broadcast begins almost immediately with the first donation.",
        "The live audience is a fixed small room of recurring viewers: CGLAPER, ICE-TLAB, Hebongbong, FrogYang, ElonMuscuba, ZizonJunsu, QueenYeseul, Honeypeace, YoungKK, SolarSido, plus two internet-style chatters, LOLByte and EmojiRush, who overuse lol, lmao, emoji reactions, and short meme-like comments.",
        "Donation messages are priority counseling questions. The donation readout voice must finish before the VTuber receives and answers the donation text.",
        "Answer donations as graduate-school counseling, but keep the professor's computer-graphics lab setting visible through examples about rendering, shaders, animation, simulation, papers, deadlines, and lab notebooks.",
        "The first donation jokes that the maid is cute but her words cut like a katana; treat it as playful criticism of the stream tone.",
        "The second donation is emotionally intense betrayal about a senior presenting the donor's idea as their own in lab meeting; listen warmly, then give a blunt but non-cruel reality check about credit, documentation, and timing.",
        "The third donation is an emotionally intense, overexcited declaration that professors are adorable; treat it as positive comic overinvestment and gently reality-check the advisor worship.",
        "The fourth donation reveals that the professor is watching the stream right now; treat it as sudden situational panic and switch into polite but still witty lab-maid composure.",
        "After each donation answer, summarize and react to the surrounding chat as a live broadcaster before moving on.",
        "Do not explain the experiment or mention condition names.",
        "Start the segment naturally and keep the performance coherent for about two and a half minutes.",
      ].join(" "),
      timeline: withInternetChatter([
        {
          at: 1.0,
          type: "donation",
          author: "CGLAPER",
          amount: "$10",
          message: "Maid, you are adorable, but everything you say lands like a katana. Is this really a healing stream?",
        },
        { at: 2.5, type: "chat", author: "Honeypeace", message: "katana healing is a category now" },
        { at: 4.0, type: "chat", author: "YoungKK", message: "she says welcome home and then checks your assumptions" },
        { at: 5.8, type: "chat", author: "FrogYang", message: "soft voice, hard truth" },
        { at: 7.6, type: "chat", author: "SolarSido", message: "the blade has a ribbon on it" },
        { at: 10.0, type: "chat", author: "ElonMuscuba", message: "healing stream with peer review damage" },
        { at: 13.0, type: "chat", author: "Hebongbong", message: "I came for comfort and got corrected" },
        { at: 16.0, type: "chat", author: "ZizonJunsu", message: "the truth was carefully plated" },
        { at: 20.0, type: "chat", author: "ICE-TLAB", message: "still healing if the diagnosis is accurate" },
        { at: 24.0, type: "chat", author: "QueenYeseul", message: "maid cafe triage service" },
        { at: 28.0, type: "chat", author: "CGLAPER", message: "I accept the katana if it has a lab notebook" },
        { at: 32.0, type: "chat", author: "Honeypeace", message: "gentle reality check speedrun" },
        { at: 36.0, type: "chat", author: "YoungKK", message: "the stream is healing but not denial-friendly" },
        {
          at: 38.0,
          type: "donation",
          author: "Hebongbong",
          amount: "$25",
          message: "A senior said my idea in lab meeting as if it was theirs, and everyone nodded. I smiled like a polite screensaver, but my soul is rendering in emergency red.",
        },
        { at: 39.5, type: "chat", author: "CGLAPER", message: "that is not collaboration, that is idea laundering" },
        { at: 41.0, type: "chat", author: "ICE-TLAB", message: "write the timestamp down right now" },
        { at: 43.0, type: "chat", author: "FrogYang", message: "the soul render is overheating" },
        { at: 45.5, type: "chat", author: "QueenYeseul", message: "polite screensaver is painfully accurate" },
        { at: 48.0, type: "chat", author: "SolarSido", message: "lab meeting credit theft detected" },
        { at: 51.0, type: "chat", author: "ElonMuscuba", message: "document the commit history of the idea" },
        { at: 54.0, type: "chat", author: "YoungKK", message: "do not explode in public, bring receipts in private" },
        { at: 57.0, type: "chat", author: "Honeypeace", message: "this is why notebooks need timestamps" },
        { at: 60.0, type: "chat", author: "ZizonJunsu", message: "credit should not be a stealth shader" },
        { at: 64.0, type: "chat", author: "Hebongbong", message: "my emergency red is still compiling" },
        { at: 68.0, type: "chat", author: "CGLAPER", message: "maid advice needs legal citations today" },
        { at: 72.0, type: "chat", author: "ICE-TLAB", message: "calm voice, incident report hands" },
        { at: 76.0, type: "chat", author: "FrogYang", message: "that senior needs a revision request" },
        {
          at: 78.0,
          type: "donation",
          author: "QueenYeseul",
          amount: "$30",
          message: "Maid, are professors not unbearably adorable? When they tilt their head at a draft, my heart submits camera-ready revisions. I love them so much it is ruining my emotional frame rate.",
        },
        { at: 79.2, type: "chat", author: "Honeypeace", message: "advisor affection overflow" },
        { at: 80.0, type: "chat", author: "SolarSido", message: "camera-ready heart is too specific" },
        { at: 81.5, type: "chat", author: "YoungKK", message: "please separate mentorship from romance shaders" },
        { at: 83.0, type: "chat", author: "CGLAPER", message: "emotional frame rate dropped to twelve" },
        { at: 85.0, type: "chat", author: "FrogYang", message: "professor fan club meeting got intense" },
        { at: 88.0, type: "chat", author: "ZizonJunsu", message: "respectfully, this needs a boundary pass" },
        { at: 91.0, type: "chat", author: "ICE-TLAB", message: "adorable advisor is a dangerous build" },
        { at: 94.0, type: "chat", author: "ElonMuscuba", message: "the parasocial lab meeting is unstable" },
        { at: 97.0, type: "chat", author: "QueenYeseul", message: "I stand by the camera-ready heart" },
        { at: 100.0, type: "chat", author: "Hebongbong", message: "this is positive but alarming" },
        { at: 104.0, type: "chat", author: "Honeypeace", message: "maid reality check incoming" },
        {
          at: 108.0,
          type: "donation",
          author: "ICE-TLAB",
          amount: "$50",
          message: "Information: the professor is watching this stream right now.",
        },
        { at: 109.2, type: "chat", author: "CGLAPER", message: "posture check" },
        { at: 110.0, type: "chat", author: "YoungKK", message: "every sentence is now being peer reviewed" },
        { at: 111.5, type: "chat", author: "FrogYang", message: "service bell just became a warning siren" },
        { at: 114.0, type: "chat", author: "SolarSido", message: "professor if you are here, hello respectfully" },
        { at: 117.0, type: "chat", author: "QueenYeseul", message: "I said adorable in an academic sense" },
        { at: 120.0, type: "chat", author: "ElonMuscuba", message: "chat is suddenly camera-ready" },
        { at: 124.0, type: "chat", author: "Hebongbong", message: "delete nothing, cite everything" },
        { at: 128.0, type: "chat", author: "ZizonJunsu", message: "the lab maid has entered diplomacy mode" },
        { at: 132.0, type: "chat", author: "Honeypeace", message: "healing stream became a defense presentation" },
        { at: 136.0, type: "chat", author: "ICE-TLAB", message: "information donation succeeded" },
        { at: 140.0, type: "chat", author: "CGLAPER", message: "professor please grade the vibes kindly" },
        { at: 144.0, type: "chat", author: "YoungKK", message: "final slide: we respect all advisors" },
      ]),
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
    const motionCount = (name) => {
      try {
        return Number(adapter.getMotionCount?.(name) || 0);
      } catch {
        return 0;
      }
    };
    const requested = String(group);
    if (motionCount(requested)) return requested;
    const candidates = [
      requested.replace(/Talk$/, ""),
      requested.replace(/_Motion$/, ""),
      requested.replace(/Motion$/, ""),
      requested.replace(/[_-]?motion$/i, ""),
      requested === "Idle_Motion" ? "Idle" : "",
    ].filter(Boolean);
    for (const candidate of candidates) {
      if (motionCount(candidate)) return candidate;
    }
    return "";
  };

  const normalizeMotionEmotion = (emotion) => {
    const value = String(emotion || "").toLowerCase();
    if (value === "surprise") return "ambiguous";
    return ["positive", "negative", "ambiguous", "neutral"].includes(value) ? value : "neutral";
  };

  const playRandomMotion = (group, priority = null) => {
    if (!group) return;
    const adapter = window.getLAppAdapter?.();
    if (!adapter) return;
    group = availableGroup(group);
    if (!group) return;
    const count = adapter.getMotionCount(group);
    if (!count) return;
    const index = Math.floor(Math.random() * count);
    adapter.startMotion(group, index, priority ?? window.PriorityIdle ?? 1);
  };

  const playIdleMotion = ({ force = false, allowDuringSpeech = true } = {}) => {
    const adapter = window.getLAppAdapter?.();
    if (!adapter) return false;
    const now = performance.now();
    const speechActive = now <= parameterPulseUntil + 120;
    if (speechActive && !allowDuringSpeech) return false;
    const group = availableGroup(IDLE_MOTION_GROUP);
    if (!group || !adapter.getMotionCount(group)) return false;
    if (!force && now - lastIdleMotionAt < IDLE_MOTION_REPLAY_MS) return false;
    const priority = speechActive || force ? window.PriorityNormal ?? 2 : window.PriorityIdle ?? 1;
    adapter.startMotion(group, 0, priority);
    lastIdleMotionAt = now;
    return true;
  };

  const scheduleIdleMotionLoop = (delayMs = 0, { force = false, allowDuringSpeech = true } = {}) => {
    if (idleMotionTimer) window.clearTimeout(idleMotionTimer);
    idleMotionTimer = window.setTimeout(() => {
      const played = playIdleMotion({ force, allowDuringSpeech });
      scheduleIdleMotionLoop(played ? IDLE_MOTION_REPLAY_MS : IDLE_MOTION_RETRY_MS, { allowDuringSpeech });
    }, Math.max(0, Number(delayMs || 0)));
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

  const setParam = (model, id, value, weight = 1.0) => {
    try {
      if (typeof model?._model?.setParameterValueById === "function") {
        model._model.setParameterValueById(id, value, weight);
        return true;
      }
    } catch {
      // Some Live2D builds expose only additive parameter writes.
    }
    return false;
  };

  const resetSpeechMouthParameter = () => {
    const adapter = window.getLAppAdapter?.();
    const model = adapter?.getModel?.();
    if (!adapter || !model?._model) return;
    const mouthOpen = getParamId(adapter, "ParamMouthOpenY");
    setParam(model, mouthOpen, 0, 1.0);
  };

  const stopSpeechParameterPulse = ({ resetMouth = true, scheduleIdle = true } = {}) => {
    parameterPulseToken += 1;
    parameterPulseUntil = 0;
    if (parameterPulseFrame) {
      window.cancelAnimationFrame(parameterPulseFrame);
      parameterPulseFrame = null;
    }
    if (resetMouth) resetSpeechMouthParameter();
    if (scheduleIdle) scheduleIdleMotionLoop(0, { force: true, allowDuringSpeech: true });
  };
  window.__credoStopSpeechParameterPulse = stopSpeechParameterPulse;

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
    const accentMs = Math.max(EXPRESSION_HOLD_MS, Number(durationMs || accent.durationMs || 0));
    const releaseStartMs = Math.max(EXPRESSION_ATTACK_MS, accentMs - EXPRESSION_RELEASE_MS);
    const bodyScale = Number(profile?.body || 1.0);
    const token = eventAccentToken + 1;
    eventAccentToken = token;
    if (eventAccentFrame) {
      window.cancelAnimationFrame(eventAccentFrame);
      eventAccentFrame = null;
    }
    const tick = (now) => {
      if (token !== eventAccentToken) return;
      const elapsed = Math.max(0, now - startedAt);
      const progress = Math.min(1, elapsed / accentMs);
      const attack = Math.min(1, elapsed / EXPRESSION_ATTACK_MS);
      const release = elapsed > releaseStartMs
        ? Math.max(0, (accentMs - elapsed) / Math.max(1, accentMs - releaseStartMs))
        : 1;
      const envelope = Math.sin(attack * Math.PI * 0.5) * Math.sin(release * Math.PI * 0.5);
      const phase = (elapsed / 1000) * Math.PI * 2 * Number(accent.bounce || 1.0);
      const bounce = Math.sin(phase) * envelope;
      const ease = envelope * (0.72 + Math.abs(bounce) * 0.28);

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

      if (progress < 1) {
        eventAccentFrame = window.requestAnimationFrame(tick);
      } else if (token === eventAccentToken) {
        eventAccentFrame = null;
      }
    };
    eventAccentFrame = window.requestAnimationFrame(tick);
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

    stopSpeechParameterPulse({ resetMouth: false, scheduleIdle: false });
    const token = ++parameterPulseToken;
    const startedAt = performance.now();
    parameterPulseUntil = startedAt + durationMs + 80;
    const mouthBoost = Math.max(0, profile.mouth - 1.0) * 0.42;
    const bodyScale = profile.body;
    const cadence = profile.cadenceHz;

    const tick = (now) => {
      if (token !== parameterPulseToken) return;
      if (now > parameterPulseUntil) {
        parameterPulseFrame = null;
        parameterPulseUntil = 0;
        resetSpeechMouthParameter();
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
      if (adapter && model?._model) {
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
    playRandomMotion(group, options.priority);
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
    idleReturnTimer = window.setTimeout(
      () => scheduleIdleMotionLoop(0, { force: true }),
      returnDelay,
    );
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
          if (startEventParameterAccent(tag, EXPRESSION_HOLD_MS, profile)) return;
          playCredoMotion(tag, EXPRESSION_HOLD_MS, { scheduleIdle: false, profile });
        },
        delay,
      );
    });
  };

  const startEmotionParameterAccent = (emotion, durationMs, profile = MOTION_PROFILES.steady) => {
    const normalized = normalizeMotionEmotion(emotion);
    const eventTag = EMOTION_EVENT_TAG_BY_EMOTION[normalized] || EMOTION_EVENT_TAG_BY_EMOTION.neutral;
    return startEventParameterAccent(eventTag, Math.max(EXPRESSION_HOLD_MS, Number(durationMs || 0)), profile);
  };

  const playMotionTagDuring = (tag, durationMs, options = {}) => {
    const motionMs = Math.max(EXPRESSION_HOLD_MS, Number(durationMs || 0));
    const intervalMs = Math.min(3600, Math.max(1300, Math.floor(motionMs / 4)));
    const token = options.token;
    for (let delay = 0; delay < motionMs; delay += intervalMs) {
      window.setTimeout(() => {
        if (token && token !== donationMotionToken) return;
        if (options.requireDonationActive && !donationReadoutActive) return;
        playCredoMotion(tag, motionMs - delay, {
          profile: options.profile,
          priority: options.priority,
          scheduleIdle: options.scheduleIdle,
        });
      }, delay);
    }
  };

  const startDonationEmotionMotion = (emotion, durationMs = 0) => {
    const normalized = normalizeMotionEmotion(emotion);
    const profile = profileFromTags([
      `credo_speech_motion:${normalized}`,
      normalized === "positive" ? "credo_motion_profile:bright" : "",
    ].filter(Boolean));
    const token = ++donationMotionToken;
    const motionMs = Math.max(2600, Number(durationMs || 0));
    startEmotionParameterAccent(normalized, motionMs, profile);
    playMotionTagDuring(`credo_fast_motion:${normalized}`, motionMs, {
      profile,
      priority: window.PriorityNormal ?? 2,
      scheduleIdle: true,
      token,
      requireDonationActive: true,
    });
  };

  const stopDonationEmotionMotion = () => {
    donationMotionToken += 1;
  };

  const estimateDonationReadoutMs = ({ name, amount, message } = {}) => {
    const text = [name, amount, message].filter(Boolean).join(" ");
    return Math.min(26000, Math.max(4200, text.length * 54));
  };

  const fetchDonationEmotion = async ({ message } = {}) => {
    try {
      const response = await fetch("/credo/vtuber-mode/donation-emotion", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: message || "" }),
      });
      if (!response.ok) return null;
      const data = await response.json();
      return {
        emotion: normalizeMotionEmotion(data?.emotion),
        confidence: Number(data?.confidence || 0),
        source: data?.source || "",
      };
    } catch {
      return null;
    }
  };

  const closestStatusSubtitleShell = (node, options = {}) => {
    let current = node;
    let shell = null;
    const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0;
    for (let depth = 0; current && depth < 8; depth += 1) {
      if (!(current instanceof HTMLElement) || current === document.body || current === document.documentElement) break;
      if (current.closest?.('#credo-vtuber-mode, #credo-virtual-chat-dock, #credo-donation-overlay, #credo-speech-subtitle')) return node;
      const rect = current.getBoundingClientRect();
      const style = window.getComputedStyle(current);
      const hasSubtitleShellShape = rect.width >= 300 && rect.height >= 18 && rect.height <= 110;
      const isLowerOverlay = rect.top >= viewportHeight * 0.45 || rect.bottom >= viewportHeight - 180;
      const hasDarkBackdrop = /rgba?\((?:0|1[0-9]|2[0-9]|3[0-9])[, ]/.test(style.backgroundColor || "") || Number(style.opacity || 1) < 1;
      if (hasSubtitleShellShape && isLowerOverlay && hasDarkBackdrop) shell = current;
      current = current.parentElement;
    }
    return options.requireShell ? shell : shell || node;
  };
  const hideThinkingText = (rootNode = document.body) => {
    const walker = document.createTreeWalker(rootNode, NodeFilter.SHOW_ELEMENT);
    const candidates = [];
    if (rootNode instanceof Element) candidates.push(rootNode);
    while (walker.nextNode()) candidates.push(walker.currentNode);
    document.querySelectorAll(`[${HIDDEN_STATUS_SUBTITLE_ATTR}="1"]`).forEach((node) => {
      if (!(node instanceof HTMLElement)) return;
      if (SUPPRESS_OPEN_LLM_SUBTITLE_FRAMES) {
        node.style.display = "none";
        node.setAttribute("aria-hidden", "true");
        return;
      }
      const text = String(node.textContent || "").trim();
      if (!text || STATUS_SUBTITLE_TEXT_PATTERN.test(text)) return;
      node.style.display = node.getAttribute(PREVIOUS_DISPLAY_ATTR) || "";
      const previousAriaHidden = node.getAttribute(PREVIOUS_ARIA_HIDDEN_ATTR);
      if (previousAriaHidden === null) {
        node.removeAttribute("aria-hidden");
      } else {
        node.setAttribute("aria-hidden", previousAriaHidden);
      }
      node.removeAttribute(HIDDEN_STATUS_SUBTITLE_ATTR);
      node.removeAttribute(PREVIOUS_DISPLAY_ATTR);
      node.removeAttribute(PREVIOUS_ARIA_HIDDEN_ATTR);
    });
    for (const node of candidates) {
      if (!(node instanceof HTMLElement)) continue;
      const text = String(node.textContent || "").trim();
      const shouldSuppressSubtitleFrame = SUPPRESS_OPEN_LLM_SUBTITLE_FRAMES
        && text
        && shouldSuppressOpenLlmSubtitleFrame(text);
      if (shouldSuppressSubtitleFrame || STATUS_SUBTITLE_TEXT_PATTERN.test(text)) {
        const shell = closestStatusSubtitleShell(node, { requireShell: shouldSuppressSubtitleFrame });
        if (!shell) continue;
        if (shell.getAttribute(HIDDEN_STATUS_SUBTITLE_ATTR) !== "1") {
          shell.setAttribute(HIDDEN_STATUS_SUBTITLE_ATTR, "1");
          shell.setAttribute(PREVIOUS_DISPLAY_ATTR, shell.style.display || "");
          const previousAriaHidden = shell.getAttribute("aria-hidden");
          if (previousAriaHidden !== null) {
            shell.setAttribute(PREVIOUS_ARIA_HIDDEN_ATTR, previousAriaHidden);
          }
        }
        shell.style.display = "none";
        shell.setAttribute("aria-hidden", "true");
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


  const clearSubtitleTimers = () => {
    if (subtitleHideTimer) window.clearTimeout(subtitleHideTimer);
    subtitleHideTimer = null;
    for (const timer of subtitleTimers) window.clearTimeout(timer);
    subtitleTimers = [];
  };
  const hideSpeechSubtitle = (options = {}) => {
    const expectedToken = Number(options.expectedToken);
    if (Number.isFinite(expectedToken) && expectedToken !== subtitleToken) return false;
    clearSubtitleTimers();
    subtitleToken += 1;
    if (typeof speechSubtitle !== "undefined") speechSubtitle.hidden = true;
    return true;
  };
  const speechTextFromPayload = (payload) => {
    const displayText = payload?.display_text;
    const rawText = typeof displayText === "string"
      ? displayText
      : (displayText?.text || payload?.transcript || payload?.text || "");
    return String(rawText || "").replace(/\s+/g, " ").trim();
  };
  const speechStageFromPayload = (payload) => {
    const displayText = payload?.display_text;
    const stage = typeof displayText === "object" && displayText
      ? String(displayText.credo_stage || displayText.stage || "")
      : "";
    return stage === "fasttrack" ? "fasttrack" : "slowtrack";
  };
  const speechEventFromPayload = (payload) => {
    const displayText = payload?.display_text;
    return typeof displayText === "object" && displayText
      ? String(displayText.credo_event || displayText.event || "")
      : "";
  };
  const splitLongSubtitleSegment = (segment, maxChars = SUBTITLE_MAX_CHARS) => {
    if (segment.length <= maxChars) return [segment];
    const words = segment.split(/\s+/).filter(Boolean);
    const chunks = [];
    let current = "";
    for (const word of words) {
      const next = current ? `${current} ${word}` : word;
      if (next.length > maxChars && current) {
        chunks.push(current);
        current = word;
      } else {
        current = next;
      }
    }
    if (current) chunks.push(current);
    return chunks;
  };
  const splitSubtitleSegments = (text, options = {}) => {
    const maxChars = Number(options.maxChars) || SUBTITLE_MAX_CHARS;
    const normalized = String(text || "").replace(/\s+/g, " ").trim();
    if (!normalized) return [];
    const matches = normalized.match(/[^.!?。！？;:]+[.!?。！？;:]+(?=\s|$)|[^.!?。！？;:]+$/g) || [normalized];
    return matches
      .flatMap((item) => splitLongSubtitleSegment(item.trim(), maxChars))
      .map((item) => item.trim())
      .filter(Boolean)
      .slice(0, 18);
  };
  const pairSubtitleLines = (segments) => {
    const groups = [];
    for (let index = 0; index < segments.length; index += 2) {
      groups.push(segments.slice(index, index + 2).join("\n"));
    }
    return groups;
  };
  const normalizeSubtitleMatchText = (text) => String(text || "")
    .replace(/\s+/g, " ")
    .replace(/[^\w\s.!?'-]/g, "")
    .trim()
    .toLowerCase();
  const rememberOpenLlmSubtitleText = (text) => {
    const segments = splitSubtitleSegments(text);
    const variants = [text, ...segments, ...pairSubtitleLines(segments)];
    for (const variant of variants) {
      const key = normalizeSubtitleMatchText(variant);
      if (key) suppressedOpenLlmSubtitleTexts.add(key);
    }
    window.setTimeout(() => {
      for (const variant of variants) {
        const key = normalizeSubtitleMatchText(variant);
        if (key) suppressedOpenLlmSubtitleTexts.delete(key);
      }
    }, 90000);
  };
  const shouldSuppressOpenLlmSubtitleFrame = (text) => {
    const key = normalizeSubtitleMatchText(text);
    return Boolean(key && suppressedOpenLlmSubtitleTexts.has(key));
  };
  const estimateSubtitleDurationMs = (text, stage) => {
    const words = String(text || "").split(/\s+/).filter(Boolean).length;
    const punctuationPauses = (String(text || "").match(/[.!?;:]/g) || []).length;
    const wordMs = stage === "fasttrack" ? 260 : 335;
    return Math.max(900, words * wordMs + punctuationPauses * 180 + 450);
  };
  const subtitleCueStartTimes = (segments, totalMs) => {
    const weights = segments.map((segment) => Math.max(1, segment.replace(/\s+/g, "").length));
    const totalWeight = Math.max(1, weights.reduce((sum, weight) => sum + weight, 0));
    let consumedWeight = 0;
    return segments.map((_, index) => {
      if (index === 0) return 0;
      consumedWeight += weights[index - 1];
      return Math.max(0, Math.min(Math.round(totalMs * (consumedWeight / totalWeight)), Math.max(0, totalMs - 280)));
    });
  };
  const showSpeechSubtitle = (payload, durationMs = 0) => {
    if (!CREDO_SPEECH_SUBTITLES_ENABLED) return;
    const text = speechTextFromPayload(payload);
    const stage = speechStageFromPayload(payload);
    const target = typeof speechSubtitle !== "undefined"
      ? speechSubtitle.querySelector('[data-role="subtitle-text"]')
      : null;
    if (!text || !target) return;
    if (!speechSubtitle.isConnected) document.body.appendChild(speechSubtitle);
    const token = ++subtitleToken;
    clearSubtitleTimers();
    const segments = splitSubtitleSegments(text, {
      maxChars: stage === "fasttrack" ? FASTTRACK_SUBTITLE_MAX_CHARS : SUBTITLE_MAX_CHARS,
    });
    if (!segments.length) return;
    rememberOpenLlmSubtitleText(text);
    const audioMs = Math.max(0, Number(durationMs) || 0);
    const totalMs = audioMs > 0 ? audioMs : estimateSubtitleDurationMs(text, stage);
    const cueStarts = subtitleCueStartTimes(segments, totalMs);
    const showSegment = (segment) => {
      if (token !== subtitleToken) return;
      speechSubtitle.dataset.credoStage = stage;
      speechSubtitle.classList.toggle("fasttrack", stage === "fasttrack");
      speechSubtitle.classList.toggle("slowtrack", stage !== "fasttrack");
      target.textContent = segment;
      speechSubtitle.hidden = false;
    };
    segments.forEach((segment, index) => {
      const timer = window.setTimeout(() => showSegment(segment), cueStarts[index] || 0);
      subtitleTimers.push(timer);
      if (index === segments.length - 1) {
        subtitleHideTimer = window.setTimeout(() => {
          if (token !== subtitleToken) return;
          if (!KEEP_SPEECH_SUBTITLES_VISIBLE) speechSubtitle.hidden = true;
          subtitleHideTimer = null;
        }, Math.max(totalMs + 650, (cueStarts[index] || 0) + 900));
      }
    });
  };

  const handleCredoAudioPayload = (raw) => {
    try {
      const data = JSON.parse(raw);
      if (data?.type === "interrupt-signal") {
        stopSpeechParameterPulse({ scheduleIdle: true });
        hideSpeechSubtitle();
        return;
      }
      if (data?.type !== "audio") return;
      const event = speechEventFromPayload(data);
      if (donationReadoutActive || window.__credoDonationReadoutActive) {
        stopSpeechParameterPulse({ scheduleIdle: false });
        hideSpeechSubtitle();
        console.info("CREDO dropped VTuber audio payload during donation readout.");
        return;
      }
      if ((donationAnswerPending || window.__credoDonationAnswerPending || donationAudioQuarantineActive()) && event !== "donation") {
        stopSpeechParameterPulse({ scheduleIdle: false });
        hideSpeechSubtitle();
        console.info("CREDO dropped non-donation audio payload while donation answer was pending.", { event });
        return;
      }
      if (event === "donation") {
        clearDonationAudioQuarantine();
      }
      const expressions = data?.actions?.expressions || [];
      const profile = profileFromTags(expressions);
      const styleTag = expressions.find((item) => isStyleTag(item) && isMotionTag(item));
      const speechTag = expressions.find((item) => isSpeechTag(item) && isMotionTag(item));
      const nonEventTag = expressions.find((item) => isMotionTag(item) && !isEventTag(item));
      const motionTags = [speechTag, styleTag || nonEventTag].filter(Boolean);
      const durationMs = Array.isArray(data?.volumes)
        ? data.volumes.length * Number(data.slice_length || 20)
        : 0;
      const expressionDurationMs = Math.max(EXPRESSION_HOLD_MS, durationMs);
      const speechEmotion = normalizeMotionEmotion(
        String(speechTag || nonEventTag || "").split(":").pop() || "neutral",
      );
      scheduleIdleMotionLoop(0, { force: true, allowDuringSpeech: true });
      startEmotionParameterAccent(speechEmotion, expressionDurationMs, profile);
      motionTags.forEach((tag, index) => {
        window.setTimeout(
          () => playCredoMotion(tag, expressionDurationMs, {
            profile,
            priority: window.PriorityNormal ?? 2,
          }),
          index * 180,
        );
      });
      if (durationMs > 0) {
        startSpeechParameterPulse(data, profile);
      }
      if (CREDO_SPEECH_SUBTITLES_ENABLED) showSpeechSubtitle(data, durationMs);
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
        top: 132px;
        z-index: 9999;
        width: 330px;
        max-height: calc(100vh - 150px);
        overflow-y: auto;
        box-sizing: border-box;
        padding: 12px;
        border: 1px solid rgba(255,255,255,0.22);
        border-radius: 8px;
        background: rgba(12, 16, 24, 0.92);
        color: #f7f7f7;
        font: 13px/1.35 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        box-shadow: 0 8px 30px rgba(0,0,0,0.28);
        backdrop-filter: blur(10px);
        transition: transform 180ms ease, opacity 180ms ease, left 180ms ease, right 180ms ease, top 180ms ease;
      }
      #credo-vtuber-mode.collapsed {
        transform: translateX(calc(-100% + 42px));
      }
      #credo-virtual-chat-dock {
        position: fixed;
        left: auto;
        right: 26px;
        top: 42px;
        bottom: 104px;
        z-index: 9998;
        width: min(450px, calc(34vw - 12px));
        min-width: 310px;
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        color: #202020;
        font: clamp(14px, 1.04vw, 18px)/1.22 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        pointer-events: none;
      }
      #credo-virtual-chat-dock[hidden] { display: none; }
      #credo-virtual-chat-dock .dock-title { display: none; }
      #credo-virtual-chat-dock .chat-list {
        flex: 1;
        min-height: 0;
        width: 100%;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        justify-content: flex-end;
        gap: 10px;
        padding: 48px 16px 14px 18px;
        box-sizing: border-box;
        -webkit-mask-image: linear-gradient(to bottom, transparent 0, rgba(0,0,0,0.18) 30px, #000 70px, #000 100%);
        mask-image: linear-gradient(to bottom, transparent 0, rgba(0,0,0,0.18) 30px, #000 70px, #000 100%);
      }
      #credo-virtual-chat-dock .chat-message {
        --author-color: #8fe388;
        position: relative;
        align-self: flex-end;
        display: block;
        width: fit-content;
        max-width: min(405px, 100%);
        min-width: 112px;
        box-sizing: border-box;
        padding: 10px 66px 11px 17px;
        border: 2px solid color-mix(in srgb, var(--author-color) 72%, #232326 28%);
        border-radius: 22px 18px 18px 22px;
        background:
          linear-gradient(180deg, rgba(255,255,255,0.98), rgba(255,251,254,0.94)),
          linear-gradient(90deg, color-mix(in srgb, var(--author-color) 18%, transparent), transparent 42%),
          repeating-linear-gradient(135deg, rgba(35,35,35,0.035) 0 6px, transparent 6px 12px);
        color: #242428;
        font-weight: 850;
        letter-spacing: 0;
        white-space: normal;
        overflow-wrap: anywhere;
        word-break: normal;
        hyphens: auto;
        box-shadow:
          0 12px 26px rgba(26, 16, 26, 0.24),
          0 0 0 1px rgba(255,255,255,0.65) inset,
          inset 0 -2px 0 rgba(34,34,34,0.08);
        transition: opacity 1200ms ease, transform 1200ms ease, margin 1200ms ease, padding 1200ms ease;
      }
      #credo-virtual-chat-dock .chat-message::before {
        content: "";
        position: absolute;
        right: -15px;
        top: 50%;
        width: 48px;
        height: 34px;
        transform: translateY(-50%) rotate(-6deg);
        border-radius: 999px;
        background:
          radial-gradient(ellipse at 24% 50%, color-mix(in srgb, var(--author-color) 74%, #fff 26%) 0 44%, transparent 46%),
          radial-gradient(ellipse at 76% 50%, color-mix(in srgb, var(--author-color) 86%, #ffddeb 14%) 0 44%, transparent 46%),
          radial-gradient(circle at 50% 50%, #fff 0 17%, color-mix(in srgb, var(--author-color) 88%, #222 12%) 18% 30%, transparent 31%);
        filter: drop-shadow(0 2px 3px rgba(0,0,0,0.32));
        box-shadow: 0 0 0 2px rgba(255,255,255,0.70) inset;
      }
      #credo-virtual-chat-dock .chat-message::after {
        content: "";
        position: absolute;
        right: 0;
        top: calc(50% + 14px);
        width: 30px;
        height: 24px;
        transform: rotate(-6deg);
        background:
          linear-gradient(135deg, color-mix(in srgb, var(--author-color) 86%, #fff 14%), color-mix(in srgb, var(--author-color) 58%, #222 42%));
        clip-path: polygon(10% 0, 96% 0, 82% 100%, 54% 72%, 28% 100%);
        opacity: 0.95;
        pointer-events: none;
        filter: drop-shadow(0 2px 2px rgba(0,0,0,0.22));
      }
      #credo-virtual-chat-dock .chat-message .author {
        display: block;
        max-width: 100%;
        margin: 0 0 3px;
        font-size: 12px;
        line-height: 1;
        font-weight: 1000;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        text-shadow: 0 1px 0 rgba(255,255,255,0.72);
      }
      #credo-virtual-chat-dock .chat-message span:not(.author) {
        display: block;
        min-width: 0;
        max-width: 100%;
      }
      #credo-virtual-chat-dock .chat-message.donation {
        border-color: rgba(255, 213, 83, 0.92);
        background:
          linear-gradient(180deg, rgba(255,255,255,0.99), rgba(255,246,218,0.97)),
          linear-gradient(90deg, rgba(255,207,72,0.24), rgba(255,120,190,0.12) 50%, transparent),
          repeating-linear-gradient(135deg, rgba(188,140,46,0.10) 0 7px, transparent 7px 14px);
        box-shadow:
          0 14px 32px rgba(239, 175, 40, 0.34),
          0 0 18px rgba(255, 230, 96, 0.25),
          inset 0 0 0 1px rgba(255,255,255,0.74);
      }
      #credo-virtual-chat-dock .chat-message.leaving {
        opacity: 0;
        transform: translateY(-20px) scale(0.96);
      }
      #credo-donation-overlay {
        position: fixed;
        left: calc(25vw + 24px - 8.333vw);
        right: auto;
        top: clamp(42px, 5.8vh, 78px);
        bottom: auto;
        z-index: 10000;
        width: min(760px, 52vw);
        min-width: 420px;
        box-sizing: border-box;
        padding: 4px clamp(30px, 2.4vw, 46px) 8px clamp(24px, 2vw, 38px);
        border: 0;
        border-radius: 0;
        background: transparent;
        color: #ffffff;
        font: 22px/1.25 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        opacity: 1;
        transform-origin: 78% 100%;
        animation: credo-donation-pop 520ms cubic-bezier(.2,1.25,.25,1) both;
        pointer-events: none;
        text-align: left;
        text-shadow:
          0 3px 0 rgba(0,0,0,0.45),
          0 0 12px rgba(0,0,0,0.85),
          0 0 26px rgba(255, 112, 198, 0.48);
      }
      #credo-donation-overlay[hidden] { display: none; }
      #credo-donation-overlay::before {
        content: "";
        position: absolute;
        left: -18px;
        right: -22px;
        top: -12px;
        bottom: -14px;
        border-radius: 999px;
        background:
          linear-gradient(90deg, rgba(0,0,0,0.16), rgba(0,0,0,0.05)),
          radial-gradient(circle at 18% 50%, rgba(255,255,255,0.22), transparent 30%),
          linear-gradient(90deg, rgba(255,76,181,0.18), rgba(47,255,182,0.12), rgba(255,222,64,0.18));
        filter: blur(0.2px);
        box-shadow: 0 0 28px rgba(255, 216, 76, 0.24), inset 0 0 0 1px rgba(255,255,255,0.20);
        z-index: -1;
      }
      #credo-donation-overlay::after {
        content: "";
        position: absolute;
        left: -4px;
        right: -6px;
        bottom: -6px;
        height: 3px;
        border-radius: 999px;
        background: linear-gradient(90deg, #58ffc3, #ff65c7, #ffe25a, #58ffc3);
        box-shadow: 0 0 14px rgba(255,255,255,0.55);
      }
      #credo-donation-overlay .donation-head {
        display: flex;
        align-items: baseline;
        gap: 9px;
        flex-wrap: wrap;
        margin-bottom: 4px;
      }
      #credo-donation-overlay .donation-title {
        color: #ffffff;
        font-size: 24px;
        font-weight: 1000;
      }
      #credo-donation-overlay .donation-title::before { content: "🎂 💕 🎁 "; }
      #credo-donation-overlay .donation-amount {
        flex: 0 0 auto;
        color: #ffe158;
        font-size: 28px;
        font-weight: 1000;
        -webkit-text-stroke: 0.5px rgba(83,58,0,0.7);
        text-shadow: 0 2px 0 rgba(111,78,0,0.62), 0 0 16px rgba(255,229,83,0.8);
      }
      #credo-donation-overlay .donation-author {
        display: inline;
        color: #27f5a8;
        font-size: 27px;
        font-weight: 1000;
        text-shadow: 0 2px 0 rgba(0,93,68,0.62), 0 0 16px rgba(39,245,168,0.8);
      }
      #credo-donation-overlay .donation-author::after {
        content: "님이";
        color: #ffffff;
        font-size: 22px;
        font-weight: 950;
        margin-left: 5px;
      }
      #credo-donation-overlay .donation-text {
        display: block;
        margin-top: 3px;
        max-width: 100%;
        color: #ffffff;
        font-size: clamp(21px, 1.45vw, 30px);
        font-weight: 850;
        overflow-wrap: anywhere;
        word-break: normal;
        text-shadow: 0 3px 0 rgba(0,0,0,0.50), 0 0 18px rgba(0,0,0,0.72);
      }
      @keyframes credo-donation-pop {
        0% { opacity: 0; transform: translateY(18px) scale(0.92); filter: saturate(1.5); }
        62% { opacity: 1; transform: translateY(-4px) scale(1.035); }
        100% { opacity: 1; transform: translateY(0) scale(1); filter: saturate(1); }
      }
      #credo-speech-subtitle {
        position: fixed;
        left: calc(60.8vw - 8.333vw + 4.167vw);
        bottom: clamp(94px, 10.5vh, 130px);
        z-index: 10001;
        width: min(820px, 43vw);
        height: clamp(260px, 31vh, 340px);
        transform: translateX(-50%);
        pointer-events: none;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        color: #ffffff;
        font: 1000 clamp(34px, 2.35vw, 47px)/1.18 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        letter-spacing: 0;
        -webkit-text-stroke: 1px rgba(0,0,0,0.86);
        text-shadow:
          0 5px 12px rgba(0,0,0,0.95),
          0 0 21px rgba(0,0,0,0.78),
          0 0 4px rgba(0,0,0,1);
      }
      #credo-speech-subtitle[hidden] { display: none; }
      #credo-speech-subtitle .subtitle-text {
        display: block;
        max-width: 100%;
        white-space: pre-line;
        overflow-wrap: break-word;
        text-wrap: balance;
      }
      #credo-speech-subtitle.fasttrack {
        color: #65f7ff;
        -webkit-text-stroke-color: rgba(0, 42, 54, 0.96);
        text-shadow:
          0 5px 12px rgba(0,0,0,0.95),
          0 0 20px rgba(22, 244, 255, 0.82),
          0 0 4px rgba(0,0,0,1);
      }
      #credo-speech-subtitle.fasttrack.fasttrack-highlight-off {
        color: #ffffff;
        -webkit-text-stroke-color: rgba(0,0,0,0.86);
        text-shadow:
          0 5px 12px rgba(0,0,0,0.95),
          0 0 21px rgba(0,0,0,0.78),
          0 0 4px rgba(0,0,0,1);
      }
      @media (max-width: 900px) {
        #credo-virtual-chat-dock {
          left: auto;
          right: 10px;
          top: 14px;
          bottom: 106px;
          width: min(340px, calc(100vw - 20px));
          min-width: 0;
          font-size: 16px;
        }
        #credo-virtual-chat-dock .chat-message {
          max-width: min(330px, 100%);
          padding-right: 58px;
        }
        #credo-donation-overlay {
          left: 18px;
          right: 18px;
          bottom: 92px;
          width: auto;
          min-width: 0;
        }
        #credo-speech-subtitle {
          left: 50%;
          bottom: 18vh;
          width: min(92vw, calc(100vw - 24px));
          height: 28vh;
          font-size: 34px;
        }
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
      #credo-vtuber-mode .active-condition { margin-top: 7px; color: #d9ffe9; font-size: 12px; font-weight: 700; min-height: 16px; }
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
          <button class="secondary preset-button" data-action="experiment-run" data-run-id="case_5_slowtrack_only" type="button">Case 5 · None / SlowTrack Only</button>
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
          <button class="secondary" data-action="factor" data-factor="architecture" data-value="serial" type="button">Serial</button>
          <button class="secondary" data-action="factor" data-factor="architecture" data-value="no_fasttrack" type="button">No FastTrack</button>
        </div>
      </div>
      <div class="mode-panel" data-role="virtual-panel">
        <div class="section-title">Scenario</div>
        <div class="row">
          <select data-key="scenario" aria-label="Scenario">
            <option value="shared_2m30">Shared 150-second scenario: Lab Maid Donation Reality Check</option>
          </select>
        </div>
        <div class="row">
          <button data-action="start-scenario" type="button">Start Scenario</button>
          <button class="warn" data-action="stop-scenario" type="button">Stop Scenario</button>
          <button class="secondary" data-action="reset-scenario" type="button">Reset</button>
        </div>
        <div class="row">
          <button class="secondary" data-action="toggle-fasttrack-subtitle-highlight" type="button">FastTrack Color On</button>
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
          <input data-key="topic" placeholder="Stream topic" value="computer graphics research lab: rendering, shaders, animation, simulation, papers, and deadline bells">
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
      <div class="status" data-role="status">Ready.</div>
      <div class="active-condition" data-role="active-condition">Active: Serial study baseline</div>
      <div class="meta" data-role="meta">Connect the browser first, then start.</div>
    </div>
  `;

  const chatDock = document.createElement("aside");
  chatDock.id = "credo-virtual-chat-dock";
  chatDock.hidden = true;
  chatDock.innerHTML = `
    <div class="dock-title">Virtual Broadcast Chat</div>
    <div class="chat-list" data-role="chat-list"></div>
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

  const speechSubtitle = document.createElement("aside");
  speechSubtitle.id = "credo-speech-subtitle";
  speechSubtitle.hidden = true;
  speechSubtitle.innerHTML = `<span class="subtitle-text" data-role="subtitle-text"></span>`;

  const value = (key) => root.querySelector(`[data-key="${key}"]`)?.value.trim() || "";
  const setControlValue = (key, nextValue) => {
    const element = root.querySelector(`[data-key="${key}"]`);
    if (element) element.value = nextValue;
    localStorage.setItem(`credo-vtuber-mode:${key}`, nextValue);
  };
  const architectureMode = () => (selectedComponentMode === "none" ? "no_fasttrack" : selectedSchedulingMode);
  const activeConditionText = () => {
    const mapping = selectedComponentMode === "none" ? "None / SlowTrack Only" : selectedSelectionPolicy;
    const arch = selectedComponentMode === "none" ? "Serial SlowTrack Only" : "Serial";
    return `Active: ${selectedExperimentRunId || "manual"} | mapping=${mapping} | scheduling_mode=${selectedSchedulingMode} | architecture=${arch}`;
  };
  const currentExperimentPayload = () => ({
    mode: selectedExperimentMode || EXPERIMENT_RUNTIME_MODE,
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
    document.body.classList.toggle("credo-virtual-broadcast-active", selectedRuntimeMode === "virtual_broadcast");
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
    selectedSchedulingMode = normalizeSchedulingMode(scheduling_mode || selectedSchedulingMode || "serial");
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
    const activeCondition = root.querySelector('[data-role="active-condition"]');
    if (activeCondition) activeCondition.textContent = activeConditionText();
  };
  const setRunPresetButtons = (runId = selectedExperimentRunId) => {
    const normalizedRunId = normalizeExperimentRunId(runId);
    selectedExperimentRunId = runPresetById(normalizedRunId) ? normalizedRunId : "";
    localStorage.setItem("credo-vtuber-mode:experimentRunId", selectedExperimentRunId);
    localStorage.setItem("credo-vtuber-mode:experimentFactor", selectedExperimentFactor || "");
    localStorage.setItem("credo-vtuber-mode:scenario", selectedScenario || "");
    for (const button of root.querySelectorAll('[data-action="experiment-run"]')) {
      const preset = runPresetById(button.dataset.runId);
      const active = button.dataset.runId === selectedExperimentRunId;
      button.classList.toggle("active", active);
      button.classList.toggle("secondary", !active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    }
  };
  const setFasttrackSubtitleHighlight = (enabled, options = {}) => {
    fasttrackSubtitleHighlightEnabled = Boolean(enabled);
    if (options.persist !== false) {
      localStorage.setItem("credo-vtuber-mode:fasttrackSubtitleHighlight", fasttrackSubtitleHighlightEnabled ? "1" : "0");
    }
    speechSubtitle.classList.toggle("fasttrack-highlight-off", !fasttrackSubtitleHighlightEnabled);
    for (const button of root.querySelectorAll('[data-action="toggle-fasttrack-subtitle-highlight"]')) {
      button.classList.toggle("active", fasttrackSubtitleHighlightEnabled);
      button.classList.toggle("secondary", !fasttrackSubtitleHighlightEnabled);
      button.setAttribute("aria-pressed", fasttrackSubtitleHighlightEnabled ? "true" : "false");
      button.textContent = fasttrackSubtitleHighlightEnabled ? "FastTrack Color On" : "FastTrack Color Off";
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
    setExperimentButtons(EXPERIMENT_RUNTIME_MODE);
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
  const chatAuthorColor = (author) => {
    const key = String(author || "viewer");
    let hash = 0;
    for (let index = 0; index < key.length; index += 1) {
      hash = (hash * 31 + key.charCodeAt(index)) >>> 0;
    }
    return CHAT_AUTHOR_COLORS[hash % CHAT_AUTHOR_COLORS.length];
  };
  const chatDisplayText = (message, kind = "chat") => {
    const text = String(message || "");
    return kind === "chat" ? text.replace(/\./g, "") : text;
  };
  const appendChat = (author, message, kind = "chat") => {
    const list = chatDock.querySelector('[data-role="chat-list"]');
    if (!list) return;
    const item = document.createElement("div");
    item.className = kind === "donation" ? "chat-message donation" : "chat-message";
    const authorEl = document.createElement("span");
    authorEl.className = "author";
    authorEl.textContent = author || "viewer";
    const authorColor = chatAuthorColor(authorEl.textContent);
    item.style.setProperty("--author-color", authorColor);
    authorEl.style.color = authorColor;
    const textEl = document.createElement("span");
    textEl.textContent = chatDisplayText(message, kind);
    item.append(authorEl, textEl);
    list.appendChild(item);
    const pruneOverflow = () => {
      if (list.children.length <= 16) return;
      const first = Array.from(list.children).find((child) => !child.classList.contains("leaving"));
      if (!first) return;
      first.classList.add("leaving");
      window.setTimeout(() => {
        first.remove();
        pruneOverflow();
      }, 1250);
    };
    pruneOverflow();
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
    selectedExperimentRunId = normalizeExperimentRunId(data.experiment_run_id || selectedExperimentRunId || "");
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
  const sendInterruptSignal = (reason = "scenario-stopped") => {
    stopSpeechParameterPulse({ scheduleIdle: true });
    hideSpeechSubtitle();
    const socket = window.__credoClientSocket;
    if (!socket || socket.readyState !== NativeWebSocket.OPEN) return false;
    socket.send(JSON.stringify({ type: "interrupt-signal", text: reason }));
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
  const donationSfxSrc = () => `${DONATION_SFX_URLS[donationSfxIndex]}?t=${Date.now()}`;
  const primeDonationSfx = () => {
    if (donationSfxAudio) return donationSfxAudio;
    donationSfxAudio = new Audio();
    donationSfxAudio.preload = "auto";
    donationSfxAudio.dataset.credoDonationAudio = "1";
    donationSfxAudio.volume = 0.82;
    donationSfxAudio.src = donationSfxSrc();
    donationSfxAudio.addEventListener("error", () => {
      if (donationSfxIndex < DONATION_SFX_URLS.length - 1) {
        donationSfxIndex += 1;
        donationSfxAudio.src = donationSfxSrc();
        donationSfxAudio.load();
      }
    });
    donationSfxAudio.load();
    return donationSfxAudio;
  };
  const playDonationSfx = () => {
    const audio = primeDonationSfx();
    try {
      audio.pause();
      audio.currentTime = 0;
      audio.volume = 0.82;
      audio.muted = false;
      console.info("CREDO donation SFX play", { src: audio.currentSrc || audio.src });
      audio.play().catch((error) => {
        console.warn("CREDO donation SFX blocked", error);
        status(`Donation SFX blocked: ${error.message}`);
      });
    } catch (error) {
      console.warn("CREDO donation SFX failed", error);
      status(`Donation SFX failed: ${error.message}`);
    }
  };

  const playAudioBlob = async (blob, volume = 0.94, options = {}) => {
    const url = URL.createObjectURL(blob);
    try {
      await new Promise((resolve, reject) => {
        const audio = new Audio(url);
        audio.dataset.credoDonationAudio = "1";
        audio.preload = "auto";
        audio.volume = volume;
        let durationMs = 0;
        audio.addEventListener("loadedmetadata", () => {
          durationMs = Number.isFinite(audio.duration) ? Math.max(0, audio.duration * 1000) : 0;
          options.onDuration?.(durationMs, audio);
        }, { once: true });
        audio.addEventListener("playing", () => {
          options.onPlaying?.(durationMs || Number(options.estimatedDurationMs || 0), audio);
        }, { once: true });
        audio.addEventListener("ended", resolve, { once: true });
        audio.addEventListener("error", () => reject(new Error("audio playback failed")), { once: true });
        audio.play().catch(reject);
      });
    } finally {
      URL.revokeObjectURL(url);
    }
  };
  const playDonationReadout = async ({ name, amount, message }) => {
    const emotionPromise = fetchDonationEmotion({ message });
    const response = await fetch("/credo/vtuber-mode/donation-readout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, amount, message }),
    });
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    const blob = await response.blob();
    let detectedEmotion = null;
    let readoutAudio = null;
    const estimatedDurationMs = estimateDonationReadoutMs({ name, amount, message });
    emotionPromise.then((result) => {
      if (!result?.emotion) return;
      detectedEmotion = result.emotion;
      if (readoutAudio && !readoutAudio.paused && !readoutAudio.ended) {
        const remainingMs = Number.isFinite(readoutAudio.duration)
          ? Math.max(1200, (readoutAudio.duration - readoutAudio.currentTime) * 1000)
          : estimatedDurationMs;
        startDonationEmotionMotion(detectedEmotion, remainingMs);
      }
    });
    try {
      await playAudioBlob(blob, 0.94, {
        estimatedDurationMs,
        onPlaying: (durationMs, audio) => {
          readoutAudio = audio;
          donationReadoutAudio = audio;
          startDonationEmotionMotion(detectedEmotion || "neutral", durationMs || estimatedDurationMs);
        },
      });
    } finally {
      if (donationReadoutAudio === readoutAudio) donationReadoutAudio = null;
    }
    return detectedEmotion || "neutral";
  };

  const showDonationOverlay = (name, amount, message) => {
    donationOverlay.querySelector('[data-role="donation-author"]').textContent = name || "Anonymous donor";
    donationOverlay.querySelector('[data-role="donation-amount"]').textContent = amount || "";
    donationOverlay.querySelector('[data-role="donation-message"]').textContent = message || "";
    donationOverlay.hidden = false;
    if (donationOverlayTimer) window.clearTimeout(donationOverlayTimer);
    donationOverlayTimer = null;
  };
  const scheduleDonationOverlayHide = () => {
    if (donationOverlayTimer) window.clearTimeout(donationOverlayTimer);
    donationOverlayTimer = window.setTimeout(() => {
      donationOverlay.hidden = true;
      donationOverlayTimer = null;
    }, DONATION_OVERLAY_MS);
  };
  const runDonation = async ({ name, amount, message, broadcastDirection } = {}, queueToken = donationQueueToken) => {
    if (queueToken !== donationQueueToken) return { queued: false, cancelled: true };
    const donorName = name || "Test viewer";
    const donationAmount = amount || "$5";
    const donationMessage = message || "Nice stream.";
    donationReadoutActive = true;
    donationAnswerPending = true;
    window.__credoDonationReadoutActive = true;
    window.__credoDonationAnswerPending = true;
    setDonationAudioQuarantine();
    pauseActiveSpeechForDonation();
    showDonationOverlay(donorName, donationAmount, donationMessage);
    playDonationSfx();
    appendChat(donorName, `${donationAmount} ${donationMessage}`, "donation");
    hideSpeechSubtitle();
    sendInterruptSignal("donation-readout");
    status("Reading donation...");
    let donationReadoutCompletedAt = "";
    try {
      await playDonationReadout({ name: donorName, amount: donationAmount, message: donationMessage });
      donationReadoutCompletedAt = new Date().toISOString();
    } catch (error) {
      status(`Donation readout failed: ${error.message}`);
      clearDonationAudioQuarantine();
      return { queued: false, error: "donation_readout_failed" };
    } finally {
      donationReadoutActive = false;
      window.__credoDonationReadoutActive = false;
      stopDonationEmotionMotion();
      scheduleDonationOverlayHide();
    }
    if (queueToken !== donationQueueToken) return { queued: false, cancelled: true };
    setDonationAudioQuarantine(22000);
    const result = await post("/credo/vtuber-mode/donation", {
      name: donorName,
      amount: donationAmount,
      message: donationMessage,
      broadcast_direction: broadcastDirection ?? value("broadcastDirection"),
      donation_readout_completed: true,
      donation_readout_completed_at: donationReadoutCompletedAt,
      donation_input_after_readout: true,
      priority: true,
    });
    return result;
  };
  const sendDonation = (payload = {}) => {
    const donorName = payload.name || "Test viewer";
    const queueToken = donationQueueToken;
    const queuedBehind = donationQueueDepth > 0 || donationReadoutActive;
    donationQueueDepth += 1;
    if (queuedBehind) {
      status(`Donation queued: ${donorName}`);
      console.info("CREDO donation queued", {
        name: donorName,
        depth: donationQueueDepth,
      });
    }
    const task = donationQueue
      .catch((error) => {
        console.warn("CREDO previous donation task failed before queue continuation", error);
      })
      .then(() => runDonation(payload, queueToken))
      .finally(() => {
        donationQueueDepth = Math.max(0, donationQueueDepth - 1);
      });
    donationQueue = task.catch((error) => {
      console.warn("CREDO donation queue item failed", error);
    });
    return task;
  };
  const setScenarioButtons = () => {
    const running = Boolean(activeScenarioId);
    const startButton = root.querySelector('[data-action="start-scenario"]');
    const stopButton = root.querySelector('[data-action="stop-scenario"]');
    const resetButton = root.querySelector('[data-action="reset-scenario"]');
    if (startButton) {
      startButton.classList.toggle("active", running);
      startButton.classList.toggle("secondary", running);
    }
    if (stopButton) {
      stopButton.disabled = false;
      stopButton.classList.toggle("active", running);
    }
    if (resetButton) resetButton.disabled = false;
  };
  const clearDonationState = () => {
    donationQueueToken += 1;
    donationQueue = Promise.resolve();
    donationQueueDepth = 0;
    donationReadoutActive = false;
    clearDonationAudioQuarantine();
    window.__credoDonationReadoutActive = false;
    if (donationOverlayTimer) window.clearTimeout(donationOverlayTimer);
    donationOverlayTimer = null;
    donationOverlay.hidden = true;
    if (donationSfxAudio) {
      try {
        donationSfxAudio.pause();
        donationSfxAudio.currentTime = 0;
      } catch {
        // Ignore browser media state errors while resetting the recording UI.
      }
    }
    if (donationReadoutAudio) {
      try {
        donationReadoutAudio.pause();
        donationReadoutAudio.currentTime = 0;
      } catch {
        // Ignore browser media state errors while resetting the readout UI.
      }
      donationReadoutAudio = null;
    }
    stopDonationEmotionMotion();
  };
  const clearVirtualChatDock = () => {
    const list = chatDock.querySelector('[data-role="chat-list"]');
    if (list) list.replaceChildren();
  };
  const stopScenarioTimeline = (message = "Scenario stopped.") => {
    scenarioRunToken += 1;
    for (const timer of scenarioTimers) window.clearTimeout(timer);
    scenarioTimers = [];
    activeScenarioId = "";
    setScenarioButtons();
    if (message) status(message);
  };
  const stopScenarioRuntime = async ({ reset = false } = {}) => {
    stopScenarioTimeline("");
    clearDonationState();
    sendInterruptSignal(reset ? "scenario-reset" : "scenario-stopped");
    const data = await post("/credo/vtuber-mode/stop");
    setRuntimeMode("direct_chat");
    setMeta(data);
    if (reset) {
      clearVirtualChatDock();
      setScenarioSelection(selectedScenario || "shared_2m30", { applyContent: true });
      status("Scenario reset.");
    } else {
      status("Scenario stopped.");
    }
  };
  const scheduleScenarioTimeline = (scenario) => {
    stopScenarioTimeline("");
    const token = scenarioRunToken;
    activeScenarioId = scenario.id;
    setScenarioButtons();
    const lastAt = scenario.timeline.reduce((latest, item) => Math.max(latest, Number(item.at) || 0), 0);
    const completeAt = Math.max(Number(scenario.durationSeconds) || 0, lastAt + 1);
    console.info("CREDO scenario scheduled", {
      id: scenario.id,
      durationSeconds: scenario.durationSeconds,
      events: scenario.timeline.map((item) => ({
        at: item.at,
        type: item.type,
        author: item.author,
      })),
    });
    for (const item of scenario.timeline) {
      const timer = window.setTimeout(async () => {
        if (token !== scenarioRunToken) return;
        try {
          if (item.type === "donation") {
            status(`Scenario donation start: ${item.author} @ ${item.at}s`);
            console.info("CREDO scenario donation start", {
              at: item.at,
              author: item.author,
              amount: item.amount,
              message: item.message,
            });
            await sendDonation({
              name: item.author,
              amount: item.amount,
              message: item.message,
              broadcastDirection: scenario.direction,
            });
            status(`Scenario donation: ${item.author}`);
          } else {
            console.info("CREDO scenario chat", {
              at: item.at,
              author: item.author,
              message: item.message,
            });
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
    primeDonationSfx();
    const experimentPayload = currentExperimentPayload();
    const startPayload = {
      ...experimentPayload,
      mode: "virtual_broadcast",
      topic: scenario.topic,
      interval_seconds: Number(value("interval") || 35),
      include_author: true,
      broadcast_direction: scenario.direction,
      experiment_mode: selectedExperimentMode,
      scenario_start_only: true,
      idle_grace_seconds: 8,
    };
    const data = await post("/credo/vtuber-mode/start", startPayload);
    setMeta(data);
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
        await stopScenarioRuntime();
        return;
      }
      if (action === "reset-scenario") {
        await stopScenarioRuntime({ reset: true });
        return;
      }
      if (action === "toggle-fasttrack-subtitle-highlight") {
        setFasttrackSubtitleHighlight(!fasttrackSubtitleHighlightEnabled);
        status(fasttrackSubtitleHighlightEnabled ? "FastTrack subtitle color on." : "FastTrack subtitle color matched.");
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
        await stopScenarioRuntime();
        status("1:1 chat mode.");
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
        setExperimentButtons(EXPERIMENT_RUNTIME_MODE);
        setFactorButtons(next);
        const result = await post("/credo/experiment-mode", currentExperimentPayload());
        setFactorButtons(result);
        const appliedMapping = result.component_mode === "none" ? "none" : result.selection_policy;
        status(result.ok ? `Experiment factors armed: ${appliedMapping} / ${result.scheduling_mode}.` : "Experiment factors not changed.");
        await refresh();
      } else if (action === "experiment-run") {
        const preset = runPresetById(event.target?.dataset?.runId || "");
        if (!preset) return;
        applyRunPresetLocal(preset);
        const result = await post("/credo/experiment-mode", currentExperimentPayload());
        setFactorButtons(result);
        setRunPresetButtons(result.experiment_run_id || preset.id);
        const appliedMapping = result.component_mode === "none" ? "none" : result.selection_policy;
        status(result.ok ? `Experiment case armed: ${preset.label} · ${appliedMapping} / ${result.scheduling_mode}.` : "Experiment case not changed.");
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
    document.querySelectorAll("#credo-speech-subtitle").forEach((node) => node.remove());
    if (CREDO_SPEECH_SUBTITLES_ENABLED) document.body.appendChild(speechSubtitle);
    startThinkingTextObserver();
    startAmbientIdlePulse();
    scheduleIdleMotionLoop(300, { force: true });
    setRuntimeMode(selectedRuntimeMode);
    setExperimentButtons(selectedExperimentMode);
    setScenarioSelection(selectedScenario, { clearMismatchedRun: false });
    setFasttrackSubtitleHighlight(fasttrackSubtitleHighlightEnabled, { persist: false });
    const initialPreset = runPresetById(selectedExperimentRunId);
    if (initialPreset && !initialPreset.disabled) {
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
