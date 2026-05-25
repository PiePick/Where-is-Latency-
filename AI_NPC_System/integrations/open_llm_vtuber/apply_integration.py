"""Install the CREDO latency-cover adapter into a local Open-LLM-VTuber clone."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
from pathlib import Path

import yaml


INTEGRATION_DIR = Path(__file__).resolve().parent
CREDO_ROOT = INTEGRATION_DIR.parents[2]
DEFAULT_VENDOR = CREDO_ROOT / "vendor" / "open-llm-vtuber"
AVATAR_MOTION_SRC = CREDO_ROOT / "reaction_sources" / "AvatarMotion"
FRONTEND_OVERLAY_SRC = INTEGRATION_DIR / "frontend" / "credo-vtuber-mode.js"


MOUTH_PARAMETER_IDS = {"ParamMouthOpenY", "ParamMouthForm"}
TALK_SAFE_MOTION_FILES = {
    "positive_1.motion3.json": "positive_1_talk.motion3.json",
    "positive_2.motion3.json": "positive_2_talk.motion3.json",
    "ambiguous_1.motion3.json": "ambiguous_1_talk.motion3.json",
    "ambiguous_2.motion3.json": "ambiguous_2_talk.motion3.json",
    "negative_1(sigh).motion3.json": "negative_1_sigh_talk.motion3.json",
    "negative_2.motion3.json": "negative_2_talk.motion3.json",
    "negative_3.motion3.json": "negative_3_talk.motion3.json",
    "netural_2.motion3.json": "netural_2_talk.motion3.json",
    "neutral_1.motion3.json": "neutral_1_talk.motion3.json",
}

CREDO_MOTION_GROUPS = {
    "Idle": [{"File": "motions/neutral_1.motion3.json"}],
    "Talk": [{"File": "motions/neutral_1_talk.motion3.json"}],
    "Positive": [
        {"File": "motions/positive_1.motion3.json"},
        {"File": "motions/positive_2.motion3.json"},
    ],
    "Negative": [
        {"File": "motions/negative_1(sigh).motion3.json"},
        {"File": "motions/negative_2.motion3.json"},
        {"File": "motions/negative_3.motion3.json"},
    ],
    "Ambiguous": [
        {"File": "motions/ambiguous_1.motion3.json"},
        {"File": "motions/ambiguous_2.motion3.json"},
    ],
    "Neutral": [
        {"File": "motions/neutral_1.motion3.json"},
        {"File": "motions/netural_2.motion3.json"},
    ],
    "PositiveTalk": [
        {"File": "motions/positive_1_talk.motion3.json"},
        {"File": "motions/positive_2_talk.motion3.json"},
    ],
    "NegativeTalk": [
        {"File": "motions/negative_1_sigh_talk.motion3.json"},
        {"File": "motions/negative_2_talk.motion3.json"},
        {"File": "motions/negative_3_talk.motion3.json"},
    ],
    "AmbiguousTalk": [
        {"File": "motions/ambiguous_1_talk.motion3.json"},
        {"File": "motions/ambiguous_2_talk.motion3.json"},
    ],
    "NeutralTalk": [
        {"File": "motions/neutral_1_talk.motion3.json"},
        {"File": "motions/netural_2_talk.motion3.json"},
    ],
}


def load_credo_config():
    """Load AI_NPC_System/config.py so generated vendor config uses one source."""
    config_path = CREDO_ROOT / "AI_NPC_System" / "config.py"
    spec = importlib.util.spec_from_file_location("credo_runtime_config", config_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load CREDO config: {config_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def replace_once(text: str, old: str, new: str, label: str) -> str:
    """Replace a marker once unless the target text already exists."""
    if new.strip() in text:
        return text
    if old not in text:
        raise RuntimeError(f"Patch marker not found: {label}")
    return text.replace(old, new, 1)


def _motion_curve_counts(curves: list[dict]) -> tuple[int, int]:
    """Return Live2D motion3 segment and point counts for Meta."""
    segment_count = 0
    point_count = 0
    for curve in curves:
        segments = curve.get("Segments") or []
        if len(segments) >= 2:
            point_count += 1
        index = 2
        while index < len(segments):
            segment_type = int(segments[index])
            index += 1
            segment_count += 1
            if segment_type == 0:
                index += 2
                point_count += 1
            elif segment_type == 1:
                index += 6
                point_count += 3
            elif segment_type in {2, 3}:
                index += 2
                point_count += 1
            else:
                raise RuntimeError(f"Unsupported motion3 segment type: {segment_type}")
    return segment_count, point_count


def write_talk_safe_motion(source: Path, destination: Path) -> None:
    """Create a speech-safe motion by stripping mouth curves for lip-sync."""
    motion = json.loads(source.read_text(encoding="utf-8"))
    curves = [
        curve
        for curve in motion.get("Curves", [])
        if not (
            curve.get("Target") == "Parameter"
            and str(curve.get("Id")) in MOUTH_PARAMETER_IDS
        )
    ]
    motion["Curves"] = curves
    meta = motion.setdefault("Meta", {})
    segment_count, point_count = _motion_curve_counts(curves)
    meta["CurveCount"] = len(curves)
    meta["TotalSegmentCount"] = segment_count
    meta["TotalPointCount"] = point_count
    destination.write_text(
        json.dumps(motion, ensure_ascii=False, indent="\t") + "\n",
        encoding="utf-8",
    )


def install_avatar_motions(model_dir: Path) -> None:
    """Install CREDO Live2D motion files and register model3 motion groups."""
    if not AVATAR_MOTION_SRC.exists():
        return

    motion_dst = model_dir / "motions"
    motion_dst.mkdir(parents=True, exist_ok=True)
    for motion_file in AVATAR_MOTION_SRC.glob("*.motion3.json"):
        shutil.copy2(motion_file, motion_dst / motion_file.name)

    for source_name, talk_safe_name in TALK_SAFE_MOTION_FILES.items():
        source_path = motion_dst / source_name
        if source_path.exists():
            write_talk_safe_motion(source_path, motion_dst / talk_safe_name)

    model3_path = model_dir / "credo_avatar.model3.json"
    if not model3_path.exists():
        return
    model3 = json.loads(model3_path.read_text(encoding="utf-8"))
    model3.setdefault("FileReferences", {})["Motions"] = CREDO_MOTION_GROUPS
    model3_path.write_text(
        json.dumps(model3, ensure_ascii=False, indent="\t") + "\n",
        encoding="utf-8",
    )


def patch_agent_factory(vendor: Path) -> None:
    """Register CredoLatencyCoverAgent in Open-LLM-VTuber's AgentFactory."""
    path = vendor / "src" / "open_llm_vtuber" / "agent" / "agent_factory.py"
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "from .agents.letta_agent import LettaAgent\n",
        "from .agents.letta_agent import LettaAgent\n"
        "from .agents.credo_latency_cover_agent import CredoLatencyCoverAgent\n",
        "agent_factory import",
    )
    branch = """        elif conversation_agent_choice == "credo_latency_cover_agent":
            settings = agent_settings.get("credo_latency_cover_agent", {})
            return CredoLatencyCoverAgent(
                settings=settings,
                system_prompt=system_prompt,
                live2d_model=live2d_model,
                character_avatar=kwargs.get("character_avatar", ""),
            )

"""
    text = replace_once(
        text,
        "        elif conversation_agent_choice == \"mem0_agent\":\n",
        branch + "        elif conversation_agent_choice == \"mem0_agent\":\n",
        "agent_factory branch",
    )
    path.write_text(text, encoding="utf-8")


def patch_agent_config(vendor: Path) -> None:
    """Teach the pydantic config schema about the CREDO agent settings."""
    path = vendor / "src" / "open_llm_vtuber" / "config_manager" / "agent.py"
    text = path.read_text(encoding="utf-8")
    class_block = '''
class CredoLatencyCoverAgentConfig(I18nMixin, BaseModel):
    """Configuration for the CREDO latency-cover research agent."""

    ai_npc_path: str = Field("../../AI_NPC_System", alias="ai_npc_path")
    character_name: str = Field("CREDO", alias="character_name")
    fast_track_enabled: bool = Field(True, alias="fast_track_enabled")
    use_fast_audio: bool = Field(True, alias="use_fast_audio")
    slow_enabled: bool = Field(True, alias="slow_enabled")
    slow_tts_mode: str = Field("credo_fish_speech", alias="slow_tts_mode")
    speech_emotion_motion_enabled: bool = Field(True, alias="speech_emotion_motion_enabled")
    record_memory: bool = Field(True, alias="record_memory")
    seed: Optional[int] = Field(None, alias="seed")
    expression_map: Dict[str, List[str]] = Field(default_factory=dict, alias="expression_map")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "ai_npc_path": Description(
            en="Path to the CREDO AI_NPC_System runtime folder",
            zh="CREDO AI_NPC_System 运行目录路径",
        ),
        "fast_track_enabled": Description(
            en="Enable CREDO FastTrack analysis and latency-cover output. Disable for SlowTrack-only ablation experiments.",
            zh="启用 CREDO FastTrack 分析和延迟遮盖输出。用于 SlowTrack-only 消融实验时可关闭。",
        ),
        "use_fast_audio": Description(
            en="Use pre-generated FastTrack audio files when available",
            zh="可用时使用预生成的 FastTrack 音频",
        ),
        "slow_tts_mode": Description(
            en="Slow response TTS mode: credo_fish_speech or open_llm",
            zh="慢速回应 TTS 模式：credo_fish_speech 或 open_llm",
        ),
        "speech_emotion_motion_enabled": Description(
            en="Use mouth-stripped emotion motion groups during spoken output so Live2D lip-sync can keep controlling the mouth",
            zh="语音输出时使用去除嘴部参数的情绪动作组，以便 Live2D 口型同步继续控制嘴部。",
        ),
    }


'''
    if "class CredoLatencyCoverAgentConfig" in text:
        start = text.index("class CredoLatencyCoverAgentConfig")
        end = text.index("class HumeAIConfig", start)
        text = text[:start] + class_block.lstrip() + text[end:]
    else:
        text = replace_once(
            text,
            "# =================================\n\n\nclass HumeAIConfig",
            "# =================================\n\n\n" + class_block + "class HumeAIConfig",
            "CredoLatencyCoverAgentConfig",
        )
    text = replace_once(
        text,
        "    letta_agent: Optional[LettaConfig] = Field(None, alias=\"letta_agent\")\n",
        "    letta_agent: Optional[LettaConfig] = Field(None, alias=\"letta_agent\")\n"
        "    credo_latency_cover_agent: Optional[CredoLatencyCoverAgentConfig] = Field(\n"
        "        None, alias=\"credo_latency_cover_agent\"\n"
        "    )\n",
        "AgentSettings field",
    )
    text = replace_once(
        text,
        "        \"basic_memory_agent\", \"mem0_agent\", \"hume_ai_agent\", \"letta_agent\"\n",
        "        \"basic_memory_agent\",\n"
        "        \"mem0_agent\",\n"
        "        \"hume_ai_agent\",\n"
        "        \"letta_agent\",\n"
        "        \"credo_latency_cover_agent\",\n",
        "conversation_agent_choice literal",
    )
    text = replace_once(
        text,
        "        \"letta_agent\": Description(\n"
        "            en=\"Configuration for Letta agent\", zh=\"Letta 代理配置\"\n"
        "        ),\n",
        "        \"letta_agent\": Description(\n"
        "            en=\"Configuration for Letta agent\", zh=\"Letta 代理配置\"\n"
        "        ),\n"
        "        \"credo_latency_cover_agent\": Description(\n"
        "            en=\"Configuration for CREDO latency-cover research agent\",\n"
        "            zh=\"CREDO 延迟遮蔽研究代理配置\",\n"
        "        ),\n",
        "AgentSettings description",
    )
    path.write_text(text, encoding="utf-8")


def patch_service_context(vendor: Path) -> None:
    """Avoid assuming every custom agent has BasicMemoryAgent settings."""
    path = vendor / "src" / "open_llm_vtuber" / "service_context.py"
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "    # ==== Initializers\n",
        "    # ==== Initializers\n"
        "    def _basic_memory_settings(self, agent_config=None):\n"
        "        \"\"\"Return BasicMemoryAgent settings when the selected agent has them.\"\"\"\n"
        "        if agent_config is None:\n"
        "            agent_config = self.character_config.agent_config\n"
        "        if not agent_config or not agent_config.agent_settings:\n"
        "            return None\n"
        "        return agent_config.agent_settings.basic_memory_agent\n\n",
        "service_context helper",
    )
    text = text.replace(
        "self.character_config.agent_config.agent_settings.basic_memory_agent.use_mcpp,\n"
        "            self.character_config.agent_config.agent_settings.basic_memory_agent.mcp_enabled_servers,",
        "(self._basic_memory_settings().use_mcpp if self._basic_memory_settings() else False),\n"
        "            (self._basic_memory_settings().mcp_enabled_servers if self._basic_memory_settings() else []),",
    )
    text = text.replace(
        "config.character_config.agent_config.agent_settings.basic_memory_agent.use_mcpp",
        "(self._basic_memory_settings(config.character_config.agent_config).use_mcpp if self._basic_memory_settings(config.character_config.agent_config) else False)",
    )
    text = text.replace(
        "config.character_config.agent_config.agent_settings.basic_memory_agent.mcp_enabled_servers",
        "(self._basic_memory_settings(config.character_config.agent_config).mcp_enabled_servers if self._basic_memory_settings(config.character_config.agent_config) else [])",
    )
    path.write_text(text, encoding="utf-8")


def patch_audio_pipeline(vendor: Path) -> None:
    """Keep direct audio outputs and fallback mp3 conversion compatible."""
    conversation_path = vendor / "src" / "open_llm_vtuber" / "conversations" / "conversation_utils.py"
    text = conversation_path.read_text(encoding="utf-8")
    text = text.replace(
        "            actions=actions.to_dict() if actions else None,\n",
        "            actions=actions,\n",
    )
    conversation_path.write_text(text, encoding="utf-8")

    tts_manager_path = vendor / "src" / "open_llm_vtuber" / "conversations" / "tts_manager.py"
    text = tts_manager_path.read_text(encoding="utf-8")
    text = text.replace(
        '                    await websocket_send(json.dumps(next_payload))\n                    self._next_sequence_to_send += 1\n',
        '                    try:\n                        await websocket_send(json.dumps(next_payload))\n                    except RuntimeError as exc:\n                        if "websocket.close" in str(exc) or "response already completed" in str(exc):\n                            logger.warning(f"Skipping queued TTS payload because websocket is closed: {exc}")\n                            return\n                        raise\n                    self._next_sequence_to_send += 1\n',
    )
    tts_manager_path.write_text(text, encoding="utf-8")

    single_path = vendor / "src" / "open_llm_vtuber" / "conversations" / "single_conversation.py"
    text = single_path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '            await websocket_send(\n                json.dumps(\n                    {\n                        "type": "error",\n                        "message": f"Error processing agent response: {str(e)}",\n                    }\n                )\n            )\n',
        '            try:\n                await websocket_send(\n                    json.dumps(\n                        {\n                            "type": "error",\n                            "message": f"Error processing agent response: {str(e)}",\n                        }\n                    )\n                )\n            except RuntimeError as send_exc:\n                logger.warning(f"Skipping agent error send because websocket is closed: {send_exc}")\n',
        "single conversation agent error websocket guard",
    )
    text = re.sub(
        r"            try:\n(?:                try:\n)+(?=                await websocket_send\(json.dumps\(\{\"type\": \"backend-synth-complete\"\}\)\)\n)",
        "            try:\n",
        text,
    )
    text = re.sub(
        r"(            except RuntimeError as send_exc:\n                logger\.warning\(f\"Skipping synth-complete send because websocket is closed: \{send_exc\}\"\)\n)+",
        '            except RuntimeError as send_exc:\n                logger.warning(f"Skipping synth-complete send because websocket is closed: {send_exc}")\n',
        text,
    )
    text = replace_once(
        text,
        '        if tts_manager.task_list:\n            await asyncio.gather(*tts_manager.task_list)\n            await websocket_send(json.dumps({"type": "backend-synth-complete"}))\n',
        '        if tts_manager.task_list:\n            await asyncio.gather(*tts_manager.task_list)\n            try:\n                await websocket_send(json.dumps({"type": "backend-synth-complete"}))\n            except RuntimeError as send_exc:\n                logger.warning(f"Skipping synth-complete send because websocket is closed: {send_exc}")\n',
        "single conversation synth complete websocket guard",
    )
    text = replace_once(
        text,
        '        await websocket_send(\n            json.dumps({"type": "error", "message": f"Conversation error: {str(e)}"})\n        )\n',
        '        try:\n            await websocket_send(\n                json.dumps({"type": "error", "message": f"Conversation error: {str(e)}"})\n            )\n        except RuntimeError as send_exc:\n            logger.warning(f"Skipping conversation error send because websocket is closed: {send_exc}")\n',
        "single conversation top-level error websocket guard",
    )
    single_path.write_text(text, encoding="utf-8")

    stream_path = vendor / "src" / "open_llm_vtuber" / "utils" / "stream_audio.py"
    text = stream_path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "import base64\n",
        "import base64\nimport io\nimport subprocess\nfrom pathlib import Path\n",
        "stream_audio conversion imports",
    )
    text = text.replace(
        "import base64\nfrom pathlib import Path\n",
        "import base64\nimport io\nimport subprocess\nfrom pathlib import Path\n",
    )
    text = text.replace(
        "from pathlib import Path\nfrom pathlib import Path\n",
        "from pathlib import Path\n",
    )
    text = text.replace(
        "        suffix = Path(str(audio_path)).suffix.lower().lstrip('.') or None\n"
        "        audio = AudioSegment.from_file(audio_path, format=suffix)\n"
        "        audio_bytes = audio.export(format=\"wav\").read()\n",
        "        suffix = Path(str(audio_path)).suffix.lower().lstrip('.')\n"
        "        if suffix == \"wav\":\n"
        "            audio = AudioSegment.from_wav(audio_path)\n"
        "            audio_bytes = audio.export(format=\"wav\").read()\n"
        "        else:\n"
        "            cmd = [\"ffmpeg\", \"-v\", \"error\", \"-i\", str(audio_path), \"-f\", \"wav\", \"pipe:1\"]\n"
        "            audio_bytes = subprocess.check_output(cmd)\n"
        "            audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format=\"wav\")\n",
    )
    text = text.replace(
        "        audio = AudioSegment.from_file(audio_path)\n"
        "        audio_bytes = audio.export(format=\"wav\").read()\n",
        "        suffix = Path(str(audio_path)).suffix.lower().lstrip('.')\n"
        "        if suffix == \"wav\":\n"
        "            audio = AudioSegment.from_wav(audio_path)\n"
        "            audio_bytes = audio.export(format=\"wav\").read()\n"
        "        else:\n"
        "            cmd = [\"ffmpeg\", \"-v\", \"error\", \"-i\", str(audio_path), \"-f\", \"wav\", \"pipe:1\"]\n"
        "            audio_bytes = subprocess.check_output(cmd)\n"
        "            audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format=\"wav\")\n",
    )
    text = text.replace(
        "            \"actions\": actions.to_dict() if actions else None,\n",
        "            \"actions\": actions.to_dict() if hasattr(actions, \"to_dict\") else actions,\n",
    )
    text = text.replace(
        "        \"actions\": actions.to_dict() if actions else None,\n",
        "        \"actions\": actions.to_dict() if hasattr(actions, \"to_dict\") else actions,\n",
    )
    stream_path.write_text(text, encoding="utf-8")


def copy_files(vendor: Path) -> None:
    """Copy the custom agent, character config, and Live2D assets."""
    cfg = load_credo_config()
    agent_dst = vendor / "src" / "open_llm_vtuber" / "agent" / "agents" / "credo_latency_cover_agent.py"
    shutil.copy2(INTEGRATION_DIR / "credo_latency_cover_agent.py", agent_dst)

    character_dst = vendor / "characters" / "credo_latency_cover.yaml"
    character = yaml.safe_load((INTEGRATION_DIR / "credo_latency_cover_character.yaml").read_text(encoding="utf-8"))
    character_config = character["character_config"]
    character_config["character_name"] = cfg.OPEN_LLM_VTUBER_CHARACTER_NAME
    character_config["human_name"] = cfg.OPEN_LLM_VTUBER_HUMAN_NAME
    character_config["live2d_model_name"] = cfg.OPEN_LLM_VTUBER_LIVE2D_MODEL_NAME
    character_config["avatar"] = cfg.OPEN_LLM_VTUBER_AVATAR
    character_config["persona_prompt"] = cfg.OPEN_LLM_VTUBER_PERSONA_PROMPT

    agent_settings = character_config["agent_config"]["agent_settings"]["credo_latency_cover_agent"]
    agent_settings["ai_npc_path"] = (CREDO_ROOT / "AI_NPC_System").as_posix()
    agent_settings["character_name"] = cfg.OPEN_LLM_VTUBER_CHARACTER_NAME
    agent_settings["fast_track_enabled"] = cfg.FAST_TRACK_ENABLED
    agent_settings["use_fast_audio"] = cfg.OPEN_LLM_VTUBER_USE_FAST_AUDIO
    agent_settings["slow_enabled"] = cfg.OPEN_LLM_VTUBER_SLOW_ENABLED
    agent_settings["slow_tts_mode"] = cfg.OPEN_LLM_VTUBER_SLOW_TTS_MODE
    agent_settings["speech_emotion_motion_enabled"] = cfg.CREDO_SPEECH_EMOTION_MOTION_ENABLED
    agent_settings["record_memory"] = cfg.OPEN_LLM_VTUBER_RECORD_MEMORY
    agent_settings["seed"] = cfg.OPEN_LLM_VTUBER_AGENT_SEED

    llm_config = character_config["agent_config"]["llm_configs"]["openai_compatible_llm"]
    llm_config["base_url"] = cfg.LOCAL_LLM_BASE_URL
    llm_config["llm_api_key"] = cfg.LOCAL_LLM_API_KEY
    llm_config["model"] = cfg.LOCAL_LLM_MODEL
    llm_config["temperature"] = cfg.LOCAL_LLM_TEMPERATURE

    tts_config = character_config["tts_config"]
    tts_config["tts_model"] = cfg.OPEN_LLM_VTUBER_TTS_MODEL
    tts_config.setdefault("edge_tts", {})["voice"] = cfg.OPEN_LLM_VTUBER_EDGE_TTS_VOICE

    character_dst.write_text(
        yaml.safe_dump(character, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    live2d_name = cfg.OPEN_LLM_VTUBER_LIVE2D_MODEL_NAME
    live2d_src = INTEGRATION_DIR / "live2d_models" / live2d_name
    live2d_dst = vendor / "live2d-models" / live2d_name
    if live2d_dst.exists():
        shutil.rmtree(live2d_dst)
    shutil.copytree(live2d_src, live2d_dst)
    install_avatar_motions(live2d_src)
    install_avatar_motions(live2d_dst)

    avatars_dst = vendor / "avatars"
    avatars_dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(live2d_src / cfg.OPEN_LLM_VTUBER_AVATAR, avatars_dst / cfg.OPEN_LLM_VTUBER_AVATAR)


def install_frontend_overlay(vendor: Path) -> None:
    """Install the CREDO frontend hook used for VTuber controls and motion intensity."""
    if not FRONTEND_OVERLAY_SRC.exists():
        return
    frontend_dir = vendor / "frontend"
    frontend_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(FRONTEND_OVERLAY_SRC, frontend_dir / FRONTEND_OVERLAY_SRC.name)

    index_path = frontend_dir / "index.html"
    if not index_path.exists():
        return
    text = index_path.read_text(encoding="utf-8")
    script = '    <script src="./credo-vtuber-mode.js"></script>\n'
    if "credo-vtuber-mode.js" in text:
        return
    if "  </body>" in text:
        text = text.replace("  </body>", f"{script}  </body>", 1)
    else:
        text += "\n" + script
    index_path.write_text(text, encoding="utf-8")


def patch_model_dict(vendor: Path) -> None:
    """Register the CREDO Live2D model in Open-LLM-VTuber's model dictionary."""
    cfg = load_credo_config()
    live2d_name = cfg.OPEN_LLM_VTUBER_LIVE2D_MODEL_NAME
    path = vendor / "model_dict.json"
    models = json.loads(path.read_text(encoding="utf-8"))
    models = [model for model in models if model.get("name") != live2d_name]
    models.append(
        {
            "name": live2d_name,
            "description": "CREDO custom Live2D avatar",
            "url": f"/live2d-models/{live2d_name}/{live2d_name}.model3.json",
            "kScale": 0.5,
            "initialXshift": 0,
            "initialYshift": 0,
            "kXOffset": 1150,
            "idleMotionGroupName": "Idle",
            "emotionMap": {
                "neutral": 0,
                "idle": 0,
                "neutral_01": 0,
                "neutral_02": 0,
                "neutral_03": 0,
                "neutral_04": 0,
                "sadness": 1,
                "sad": 1,
                "worried": 1,
                "negative_01": 1,
                "negative_02": 1,
                "negative_03": 1,
                "negative_04": 1,
                "anger": 2,
                "disgust": 2,
                "joy": 3,
                "happy": 3,
                "smile": 3,
                "positive_01": 3,
                "positive_02": 3,
                "positive_03": 3,
                "positive_04": 3,
                "surprise": 3,
                "confused": 3,
                "ambiguous_01": 3,
                "ambiguous_02": 3,
                "ambiguous_03": 3,
                "ambiguous_04": 3,
            },
            "tapMotions": {
                "HitAreaHead": {"": 1},
                "HitAreaBody": {"": 1},
            },
        }
    )
    path.write_text(json.dumps(models, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")


def patch_vtuber_routes(vendor: Path) -> None:
    """Keep CREDO VTuber route prompts aligned with output policy."""
    path = vendor / "src" / "open_llm_vtuber" / "routes.py"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    if "/credo/vtuber-mode/" not in text:
        return
    if "from .utils.stream_audio import prepare_audio_payload" not in text:
        text = text.replace(
            "from .proxy_handler import ProxyHandler\n",
            "from .proxy_handler import ProxyHandler\n"
            "from .utils.stream_audio import prepare_audio_payload\n",
            1,
        )
    text = text.replace(
        '    def _credo_root() -> Path:\n'
        '        """Resolve the CREDO workspace root from the vendored runtime."""\n'
        '        configured = os.getenv("CREDO_AI_NPC_PATH")\n'
        '        if configured:\n'
        '            return Path(configured).expanduser().resolve().parent\n'
        '        return Path.cwd().resolve().parents[1]\n',
        '    def _credo_root() -> Path:\n'
        '        """Resolve the CREDO workspace root from env, cwd, or this vendored file."""\n'
        '        configured = os.getenv("CREDO_AI_NPC_PATH")\n'
        '        if configured:\n'
        '            return Path(configured).expanduser().resolve().parent\n'
        '        roots = [Path.cwd().resolve(), Path(__file__).resolve()]\n'
        '        for root in list(roots):\n'
        '            roots.extend(root.parents)\n'
        '        for root in roots:\n'
        '            if (root / "AI_NPC_System" / "expressive_interjection_bundle" / "manifest.json").exists():\n'
        '                return root\n'
        '        return Path.cwd().resolve().parents[1]\n',
    )
    if '"experiment_mode": "fish_cover",' not in text:
        text = text.replace(
            '        "last_prompt": "",\n'
            '    }\n',
            '        "last_prompt": "",\n'
            '        "experiment_mode": "fish_cover",\n'
            '    }\n'
            '    experiment_modes = {\n'
            '        "fast_no_cover": {\n'
            '            "label": "Fast low-quality TTS / no cover",\n'
            '            "fast_track_enabled": False,\n'
            '            "use_fast_audio": False,\n'
            '            "slow_tts_mode": "open_llm",\n'
            '            "open_llm_tts_fallback": True,\n'
            '        },\n'
            '        "fish_no_cover": {\n'
            '            "label": "Fish high-quality TTS / no cover",\n'
            '            "fast_track_enabled": False,\n'
            '            "use_fast_audio": False,\n'
            '            "slow_tts_mode": "credo_fish_speech",\n'
            '            "open_llm_tts_fallback": False,\n'
            '        },\n'
            '        "fish_cover": {\n'
            '            "label": "Fish high-quality TTS / FastTrack cover",\n'
            '            "fast_track_enabled": True,\n'
            '            "use_fast_audio": True,\n'
            '            "slow_tts_mode": "credo_fish_speech",\n'
            '            "open_llm_tts_fallback": False,\n'
            '        },\n'
            '    }\n',
            1,
        )

    replacements = [
        (
            '        prompt = (\n'
            '            "VTuber stream idle segment. "\n'
            '            f"{beat} "\n'
            '            "Speak in natural English as CREDO. "\n'
            '            "Do not say you are waiting for input unless it sounds like a streamer joking with chat. "\n'
            '            "Do not mention systems, prompts, tests, models, or implementation. "\n'
            '            "Aim for 12 to 24 spoken words so live TTS does not block chat."\n'
            '        )\n',
            '        instruction = (\n'
            '            "VTuber stream idle segment. "\n'
            '            f"{beat} "\n'
            '            "Speak in natural English as CREDO. "\n'
            '            "Do not say you are waiting for input unless it sounds like a streamer joking with chat. "\n'
            '            "Do not mention systems, prompts, tests, models, or implementation. "\n'
            '            "Aim for 12 to 24 spoken words so live TTS does not block chat."\n'
            '        )\n'
            '        prompt = "Chat got quiet for a moment."\n',
        ),
        (
            '        vtuber_mode["last_prompt"] = prompt\n',
            '        vtuber_mode["last_prompt"] = instruction\n',
        ),
        (
            '        text = (\n'
            '            "VTuber mode manual monologue. Speak naturally to the audience in English only. "\n'
            '            "Make one cohesive streamer-style segment with a beginning, a small point, and a chat hook. "\n'
            '            "Do not write bracketed style tags or switch languages."\n'
            '        )\n',
            '        instruction = (\n'
            '            "VTuber mode manual monologue. Speak naturally to the audience in English only. "\n'
            '            "Make one cohesive streamer-style segment with a beginning, a small point, and a chat hook. "\n'
            '            "Do not write bracketed style tags or switch languages."\n'
            '        )\n'
            '        text = "Let\'s do a quick stream monologue."\n',
        ),
        (
            '        text = (\n'
            '            f"Donation event from {name} {amount}: {message}. "\n'
            '            "React warmly in English only, then naturally fold back into the stream. "\n'
            '            "Do not write bracketed style tags or switch languages."\n'
            '        )\n',
            '        instruction = (\n'
            '            f"Donation event from {name} {amount}: {message}. "\n'
            '            "React warmly in English only, then naturally fold back into the stream. "\n'
            '            "Do not write bracketed style tags or switch languages."\n'
            '        )\n'
            '        text = _clean_prompt_piece(f"{name} sent support. {message}", 220)\n',
        ),
        (
            '            "Aim for 45 to 80 spoken words."\n',
            '            "Aim for 12 to 24 spoken words so live TTS does not block chat."\n',
        ),
        (
            '                "Keep it under 35 words, include one approved Fish Speech tag, "\n'
            '                "and end with a light hook that invites chat."\n',
            '                "Keep it under 35 words, use natural plain English, "\n'
            '                "always answer in English only regardless of viewer language, "\n'
            '                "and end with a light hook that invites chat."\n',
        ),
        (
            '                "Keep it under 35 words, use natural plain English, "\n'
            '                "and end with a light hook that invites chat."\n',
            '                "Keep it under 35 words, use natural plain English, "\n'
            '                "always answer in English only regardless of viewer language, "\n'
            '                "and end with a light hook that invites chat."\n',
        ),
        (
            '            "VTuber mode manual monologue. Speak naturally to the audience. "\n'
            '            f"Topic anchor: {topic}. Keep it under 35 words and include one approved Fish Speech tag."\n',
            '            "VTuber mode manual monologue. Speak naturally to the audience in English only. "\n'
            '            f"Topic anchor: {topic}. Keep it under 35 words and do not write bracketed style tags. "\n'
            '            "Do not switch languages even if the topic or viewer text is multilingual."\n',
        ),
        (
            '            "VTuber mode manual monologue. Speak naturally to the audience. "\n'
            '            f"Topic anchor: {topic}. Keep it under 35 words and do not write bracketed style tags."\n',
            '            "VTuber mode manual monologue. Speak naturally to the audience in English only. "\n'
            '            f"Topic anchor: {topic}. Keep it under 35 words and do not write bracketed style tags. "\n'
            '            "Do not switch languages even if the topic or viewer text is multilingual."\n',
        ),
        (
            '            f"Donation event from {name} {amount}: {message}. "\n'
            '            "React with a bright laugh, one approved Fish Speech tag, and a short thank-you."\n',
            '            f"Donation event from {name} {amount}: {message}. "\n'
            '            "React with a bright laugh and a short thank-you in English only. "\n'
            '            "Do not write bracketed style tags or switch languages."\n',
        ),
        (
            '            f"Donation event from {name} {amount}: {message}. "\n'
            '            "React with a bright laugh and a short thank-you. Do not write bracketed style tags."\n',
            '            f"Donation event from {name} {amount}: {message}. "\n'
            '            "React with a bright laugh and a short thank-you in English only. "\n'
            '            "Do not write bracketed style tags or switch languages."\n',
        ),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    if '            "vtuber_event": "idle",\n            "vtuber_instruction": instruction,\n' not in text:
        text = text.replace(
            '            "vtuber_event": "idle",\n',
            '            "vtuber_event": "idle",\n            "vtuber_instruction": instruction,\n',
            1,
        )
    if '            "vtuber_instruction": instruction,\n            "skip_last_text_input": True,\n' not in text:
        text = text.replace(
            '            "vtuber_instruction": instruction,\n',
            '            "vtuber_instruction": instruction,\n            "skip_last_text_input": True,\n',
            1,
        )
    if '                "vtuber_event": "manual_monologue",\n                "vtuber_instruction": instruction,\n' not in text:
        text = text.replace(
            '                "vtuber_event": "manual_monologue",\n',
            '                "vtuber_event": "manual_monologue",\n                "vtuber_instruction": instruction,\n',
            1,
        )
    if '                "vtuber_instruction": instruction,\n                "skip_last_text_input": True,\n' not in text:
        text = text.replace(
            '                "vtuber_instruction": instruction,\n',
            '                "vtuber_instruction": instruction,\n                "skip_last_text_input": True,\n',
            2,
        )
    if '                "vtuber_event": "donation",\n                "vtuber_instruction": instruction,\n' not in text:
        text = text.replace(
            '                "vtuber_event": "donation",\n',
            '                "vtuber_event": "donation",\n                "vtuber_instruction": instruction,\n',
            1,
        )
    if '"/credo/vtuber-mode/virtual-chat"' not in text:
        text = text.replace(
            '    @router.post("/credo/vtuber-mode/start")\n',
            '    @router.post("/credo/vtuber-mode/virtual-chat")\n'
            '    async def credo_vtuber_mode_virtual_chat(request: Request):\n'
            '        """Send one virtual broadcast chat message through the normal CREDO pipeline."""\n'
            '        payload = await request.json()\n'
            '        author = _clean_prompt_piece(payload.get("author") or "viewer", 48)\n'
            '        message = _clean_prompt_piece(payload.get("message") or "", 360)\n'
            '        if not message:\n'
            '            return JSONResponse({"queued": False, "error": "empty message"}, status_code=400)\n'
            '        text = f"Viewer {author} says: {message}"\n'
            '        ok = await ws_handler.trigger_text_input(\n'
            '            text,\n'
            '            metadata={\n'
            '                "virtual_broadcast_chat": True,\n'
            '                "source": "virtual_broadcast_chat",\n'
            '            },\n'
            '        )\n'
            '        return {"queued": ok}\n'
            '\n'
            '    @router.post("/credo/vtuber-mode/start")\n',
            1,
        )
    if '"--batch-window", str(payload.get("batch_window")' not in text:
        text = text.replace(
            '        cmd.extend(["--proxy-url", os.getenv("YOUTUBE_CHAT_PROXY_URL", "ws://localhost:12393/proxy-ws")])\n',
            '        cmd.extend(["--proxy-url", os.getenv("YOUTUBE_CHAT_PROXY_URL", "ws://localhost:12393/proxy-ws")])\n'
            '        cmd.extend(["--batch-window", str(payload.get("batch_window") or os.getenv("YOUTUBE_CHAT_BATCH_WINDOW", "8.0"))])\n'
            '        cmd.extend(["--max-batch", str(payload.get("max_batch") or os.getenv("YOUTUBE_CHAT_MAX_BATCH", "8"))])\n',
            1,
        )
    if "def _build_chat_batch_prompt(" not in text:
        text = text.replace(
            '        vtuber_mode["last_prompt"] = instruction\n'
            '        return prompt, metadata\n'
            '\n'
            '    async def _idle_loop() -> None:\n',
            '        vtuber_mode["last_prompt"] = instruction\n'
            '        return prompt, metadata\n'
            '\n'
            '    def _build_chat_batch_prompt(topic: str, chat_context: str) -> tuple[str, dict]:\n'
            '        """Build a VTuber turn from buffered live chat instead of one-by-one replies."""\n'
            '        topic = _clean_prompt_piece(topic, 180) or "the current stream"\n'
            '        chat_context = _clean_prompt_piece(chat_context, 1200)\n'
            '        instruction = (\n'
            '            "VTuber live chat batch segment. Recent chat has been buffered while the stream was speaking. "\n'
            '            "Respond to the overall mood and one or two representative points, not every line. "\n'
            '            "Keep continuity with the current topic, stay in natural English, and end with a light hook for chat. "\n'
            '            "Aim for 14 to 28 spoken words so Fish Speech does not block the stream."\n'
            '        )\n'
            '        prompt = "Live chat is reacting right now."\n'
            '        metadata = {\n'
            '            "vtuber_mode": True,\n'
            '            "vtuber_event": "live_chat_batch",\n'
            '            "vtuber_instruction": instruction,\n'
            '            "skip_last_text_input": True,\n'
            '            "skip_history": True,\n'
            '            "skip_memory": True,\n'
            '            "topic": topic,\n'
            '            "last_chat": chat_context,\n'
            '            "style_tag": "energetic",\n'
            '            "emotion": "positive",\n'
            '        }\n'
            '        vtuber_mode["last_prompt"] = instruction\n'
            '        return prompt, metadata\n'
            '\n'
            '    async def _idle_loop() -> None:\n',
            1,
        )
    if "def _interjection_manifest_path(" not in text:
        text = text.replace(
            '    def _clean_prompt_piece(value: object, limit: int = 500) -> str:\n'
            '        """Keep server-generated stream context compact and safe for prompts."""\n'
            '        text = " ".join(str(value or "").split())\n'
            '        return text[:limit]\n'
            '\n',
            '    def _clean_prompt_piece(value: object, limit: int = 500) -> str:\n'
            '        """Keep server-generated stream context compact and safe for prompts."""\n'
            '        text = " ".join(str(value or "").split())\n'
            '        return text[:limit]\n'
            '\n'
            '    def _interjection_manifest_path() -> Path:\n'
            '        """Return the active pure interjection bundle manifest."""\n'
            '        return _credo_root() / "AI_NPC_System" / "expressive_interjection_bundle" / "manifest.json"\n'
            '\n'
            '    def _load_interjection_items() -> list[dict]:\n'
            '        """Load selectable prebuilt interjection audio items for manual motion tests."""\n'
            '        manifest_path = _interjection_manifest_path()\n'
            '        if not manifest_path.exists():\n'
            '            return []\n'
            '        try:\n'
            '            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))\n'
            '        except Exception as exc:\n'
            '            logger.warning(f"CREDO interjection manifest read failed: {exc}")\n'
            '            return []\n'
            '        items = []\n'
            '        for item in manifest.get("items", []):\n'
            '            audio_path = Path(str(item.get("audio_path") or ""))\n'
            '            if not audio_path.is_absolute():\n'
            '                audio_path = manifest_path.parent / audio_path\n'
            '            if not audio_path.exists():\n'
            '                continue\n'
            '            items.append(\n'
            '                {\n'
            '                    "id": str(item.get("id") or ""),\n'
            '                    "emotion": str(item.get("emotion") or "neutral"),\n'
            '                    "style_tag": str(item.get("style_tag") or "steady"),\n'
            '                    "event": str(item.get("event") or "thinking"),\n'
            '                    "carrier": str(item.get("carrier") or item.get("plain_tts_text") or ""),\n'
            '                    "audio_path": str(audio_path),\n'
            '                }\n'
            '            )\n'
            '        return items\n'
            '\n'
            '    def _motion_profile_for_item(item: dict) -> str:\n'
            '        """Map selected interjection metadata to a frontend motion profile."""\n'
            '        style = str(item.get("style_tag") or "").lower()\n'
            '        if style in {"energetic", "playful", "smug", "cute"}:\n'
            '            return style\n'
            '        if style in {"high-pitched", "high_pitched", "bright"}:\n'
            '            return "bright"\n'
            '        event = str(item.get("event") or "").lower()\n'
            '        if event == "surprise":\n'
            '            return "alert"\n'
            '        if event == "sigh":\n'
            '            return "low"\n'
            '        if event == "laugh":\n'
            '            return "playful"\n'
            '        return "steady"\n'
            '\n',
            1,
        )
    if "def _iter_credo_agents(" not in text:
        text = text.replace(
            '        if event == "laugh":\n'
            '            return "playful"\n'
            '        return "steady"\n'
            '\n',
            '        if event == "laugh":\n'
            '            return "playful"\n'
            '        return "steady"\n'
            '\n'
            '    def _iter_credo_agents():\n'
            '        """Yield all active CREDO agent instances that need experiment updates."""\n'
            '        seen = set()\n'
            '        candidates = [default_context_cache.agent_engine]\n'
            '        candidates.extend(context.agent_engine for context in ws_handler.client_contexts.values())\n'
            '        for agent in candidates:\n'
            '            if agent is None or id(agent) in seen:\n'
            '                continue\n'
            '            seen.add(id(agent))\n'
            '            if hasattr(agent, "fast_track_enabled") and hasattr(agent, "slow_tts_mode"):\n'
            '                yield agent\n'
            '\n'
            '    def _apply_experiment_mode(mode_key: str) -> dict:\n'
            '        """Switch current CREDO agents between ablation/runtime experiment modes."""\n'
            '        mode = experiment_modes.get(mode_key)\n'
            '        if mode is None:\n'
            '            raise KeyError(mode_key)\n'
            '        vtuber_mode["experiment_mode"] = mode_key\n'
            '        updated = 0\n'
            '        for agent in _iter_credo_agents():\n'
            '            agent.fast_track_enabled = bool(mode["fast_track_enabled"])\n'
            '            agent.use_fast_audio = bool(mode["use_fast_audio"])\n'
            '            agent.slow_tts_mode = str(mode["slow_tts_mode"])\n'
            '            agent.settings["fast_track_enabled"] = agent.fast_track_enabled\n'
            '            agent.settings["use_fast_audio"] = agent.use_fast_audio\n'
            '            agent.settings["slow_tts_mode"] = agent.slow_tts_mode\n'
            '            if hasattr(agent, "_credo_config"):\n'
            '                setattr(\n'
            '                    agent._credo_config,\n'
            '                    "SLOW_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK",\n'
            '                    bool(mode["open_llm_tts_fallback"]),\n'
            '                )\n'
            '            if agent.slow_tts_mode == "credo_fish_speech" and getattr(agent, "fish_tts", None) is None:\n'
            '                agent.fish_tts = agent._tts_client.FishSpeechTTSClient()\n'
            '            task = getattr(agent, "_vtuber_slow_prefetch_task", None)\n'
            '            if task is not None and not task.done():\n'
            '                task.cancel()\n'
            '            agent._vtuber_slow_prefetch_task = None\n'
            '            updated += 1\n'
            '        return {"mode": mode_key, **mode, "updated_agents": updated}\n'
            '\n',
            1,
        )
    if '@router.get("/credo/interjections")' not in text:
        text = text.replace(
            '    @router.post("/credo/vtuber-mode/virtual-chat")\n',
            '    @router.get("/credo/interjections")\n'
            '    async def credo_interjection_list():\n'
            '        """Return manual FastTrack interjection+motion choices."""\n'
            '        items = _load_interjection_items()\n'
            '        return {\n'
            '            "items": [\n'
            '                {key: value for key, value in item.items() if key != "audio_path"}\n'
            '                for item in items\n'
            '            ]\n'
            '        }\n'
            '\n'
            '    @router.post("/credo/interjections/play")\n'
            '    async def credo_interjection_play(request: Request):\n'
            '        """Force-play one prebuilt interjection audio clip with its Live2D motion tags."""\n'
            '        payload = await request.json()\n'
            '        item_id = str(payload.get("id") or "")\n'
            '        items = _load_interjection_items()\n'
            '        item = next((candidate for candidate in items if candidate.get("id") == item_id), None)\n'
            '        if item is None:\n'
            '            return JSONResponse({"played": False, "error": "unknown interjection id"}, status_code=404)\n'
            '        target_uid = ws_handler.first_client_uid()\n'
            '        if not target_uid or target_uid not in ws_handler.client_connections:\n'
            '            return JSONResponse({"played": False, "error": "no browser client connected"}, status_code=409)\n'
            '\n'
            '        emotion = str(item.get("emotion") or "neutral").lower()\n'
            '        style = str(item.get("style_tag") or "steady").lower()\n'
            '        event = str(item.get("event") or "thinking").lower()\n'
            '        profile = _motion_profile_for_item(item)\n'
            '        expressions = [\n'
            '            f"credo_motion_profile:{profile}",\n'
            '            f"credo_fast_motion:{emotion}",\n'
            '            f"credo_event_motion:{event}",\n'
            '            f"credo_style_motion:{style}",\n'
            '        ]\n'
            '        audio_payload = prepare_audio_payload(\n'
            '            audio_path=item["audio_path"],\n'
            '            display_text={"text": "", "name": "CREDO", "avatar": None},\n'
            '            actions={"expressions": expressions},\n'
            '        )\n'
            '        await ws_handler.client_connections[target_uid].send_text(json.dumps(audio_payload))\n'
            '        return {\n'
            '            "played": True,\n'
            '            "id": item["id"],\n'
            '            "emotion": emotion,\n'
            '            "style_tag": style,\n'
            '            "event": event,\n'
            '            "carrier": item.get("carrier", ""),\n'
            '        }\n'
            '\n'
            '    @router.post("/credo/vtuber-mode/virtual-chat")\n',
            1,
        )
    if '@router.get("/credo/experiment-modes")' not in text:
        text = text.replace(
            '    @router.get("/credo/interjections")\n',
            '    @router.get("/credo/experiment-modes")\n'
            '    async def credo_experiment_modes():\n'
            '        """Return available CREDO experiment mode presets."""\n'
            '        return {\n'
            '            "active": vtuber_mode["experiment_mode"],\n'
            '            "modes": [\n'
            '                {"id": key, **value}\n'
            '                for key, value in experiment_modes.items()\n'
            '            ],\n'
            '        }\n'
            '\n'
            '    @router.post("/credo/experiment-mode")\n'
            '    async def credo_experiment_mode(request: Request):\n'
            '        """Switch CREDO runtime experiment mode without restarting the UI."""\n'
            '        payload = await request.json()\n'
            '        mode_key = str(payload.get("mode") or "")\n'
            '        try:\n'
            '            result = _apply_experiment_mode(mode_key)\n'
            '        except KeyError:\n'
            '            return JSONResponse({"ok": False, "error": "unknown experiment mode"}, status_code=404)\n'
            '        return {"ok": True, **result}\n'
            '\n'
            '    @router.get("/credo/interjections")\n',
            1,
        )
    if '"experiment_mode": vtuber_mode["experiment_mode"],' not in text:
        text = text.replace(
            '            "last_text_input": ws_handler.last_text_input(),\n'
            '        }\n',
            '            "last_text_input": ws_handler.last_text_input(),\n'
            '            "experiment_mode": vtuber_mode["experiment_mode"],\n'
            '            "experiment_label": experiment_modes[vtuber_mode["experiment_mode"]]["label"],\n'
            '        }\n',
            1,
        )
    if "consume_vtuber_chat_context" not in text:
        text = text.replace(
            '            if active_task and not active_task.done():\n'
            '                logger.info("CREDO VTuber idle monologue skipped because a conversation is still running.")\n'
            '                await asyncio.sleep(2.0)\n'
            '                continue\n'
            '            silence_seconds = ws_handler.seconds_since_last_activity()\n',
            '            if active_task and not active_task.done():\n'
            '                logger.info("CREDO VTuber idle monologue skipped because a conversation is still running.")\n'
            '                await asyncio.sleep(2.0)\n'
            '                continue\n'
            '            chat_context = ws_handler.consume_vtuber_chat_context(\n'
            '                max_items=int(os.getenv("CREDO_VTUBER_CHAT_BATCH_MAX_ITEMS", "8"))\n'
            '            )\n'
            '            if chat_context:\n'
            '                prompt, metadata = _build_chat_batch_prompt(topic, chat_context)\n'
            '                queued = await ws_handler.trigger_text_input(prompt, metadata=metadata)\n'
            '                if queued:\n'
            '                    vtuber_mode["last_idle_at"] = time.monotonic()\n'
            '                await asyncio.sleep(1.0)\n'
            '                continue\n'
            '            silence_seconds = ws_handler.seconds_since_last_activity()\n',
            1,
        )
    if 'requested_experiment = payload.get("experiment_mode")' not in text:
        text = text.replace(
            '        payload = await request.json()\n'
            '        vtuber_mode["active"] = True\n',
            '        payload = await request.json()\n'
            '        requested_experiment = payload.get("experiment_mode")\n'
            '        if requested_experiment:\n'
            '            try:\n'
            '                _apply_experiment_mode(str(requested_experiment))\n'
            '            except KeyError:\n'
            '                return JSONResponse({"active": False, "error": "unknown experiment mode"}, status_code=404)\n'
            '        vtuber_mode["active"] = True\n',
            1,
        )
    if 'ws_handler.enqueue_vtuber_chat_context(text)' not in text:
        text = text.replace(
            '        text = f"Viewer {author} says: {message}"\n'
            '        ok = await ws_handler.trigger_text_input(\n',
            '        text = f"Viewer {author} says: {message}"\n'
            '        if vtuber_mode["active"]:\n'
            '            ws_handler.enqueue_vtuber_chat_context(text)\n'
            '            return {"queued": True, "buffered": True}\n'
            '        ok = await ws_handler.trigger_text_input(\n',
            1,
        )
    text = text.replace(
        '            await ws_handler.trigger_text_input(prompt)\n            await asyncio.sleep(float(vtuber_mode["interval"]))\n',
        '            target_uid = ws_handler.first_client_uid()\n            active_task = ws_handler.current_conversation_tasks.get(target_uid) if target_uid else None\n            if active_task and not active_task.done():\n                logger.info("CREDO VTuber idle monologue skipped because a conversation is still running.")\n            else:\n                await ws_handler.trigger_text_input(prompt)\n            await asyncio.sleep(float(vtuber_mode["interval"]))\n',
    )
    path.write_text(text, encoding="utf-8")


def patch_websocket_handler(vendor: Path) -> None:
    """Avoid treating server-injected VTuber prompts as the latest viewer chat."""
    path = vendor / "src" / "open_llm_vtuber" / "websocket_handler.py"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    old = (
        '        self._last_activity_at = time.monotonic()\n'
        '        if data.get("type") == "text-input" and data.get("text"):\n'
        '            self._last_text_input = str(data.get("text") or "")[:500]\n'
    )
    new = (
        '        self._last_activity_at = time.monotonic()\n'
        '        metadata = data.get("metadata") or {}\n'
        '        if data.get("type") == "text-input" and data.get("text") and not metadata.get("skip_last_text_input"):\n'
        '            self._last_text_input = str(data.get("text") or "")[:500]\n'
    )
    if new not in text:
        text = text.replace(old, new, 1)
    if "self._vtuber_chat_buffer" not in text:
        text = text.replace(
            '        self._last_text_input = ""\n',
            '        self._last_text_input = ""\n'
            '        self._vtuber_chat_buffer: List[str] = []\n',
            1,
        )
    if "def enqueue_vtuber_chat_context(" not in text:
        text = text.replace(
            '    def last_text_input(self) -> str:\n'
            '        """Return the latest text input observed by this handler."""\n'
            '        return self._last_text_input\n'
            '\n',
            '    def last_text_input(self) -> str:\n'
            '        """Return the latest text input observed by this handler."""\n'
            '        return self._last_text_input\n'
            '\n'
            '    def enqueue_vtuber_chat_context(self, text: str, *, max_items: int = 40) -> None:\n'
            '        """Buffer live/virtual chat while VTuber mode is speaking."""\n'
            '        cleaned = " ".join(str(text or "").split())[:1200]\n'
            '        if not cleaned:\n'
            '            return\n'
            '        self._vtuber_chat_buffer.append(cleaned)\n'
            '        if len(self._vtuber_chat_buffer) > max_items:\n'
            '            self._vtuber_chat_buffer = self._vtuber_chat_buffer[-max_items:]\n'
            '\n'
            '    def consume_vtuber_chat_context(self, *, max_items: int = 8) -> str:\n'
            '        """Return and clear a compact batch of buffered VTuber chat context."""\n'
            '        if not self._vtuber_chat_buffer:\n'
            '            return ""\n'
            '        selected = self._vtuber_chat_buffer[-max(1, max_items):]\n'
            '        self._vtuber_chat_buffer.clear()\n'
            '        return "\\n".join(selected)\n'
            '\n',
            1,
        )
    if 'metadata.get("vtuber_live_chat_batch")' not in text:
        text = text.replace(
            '        if data.get("type") == "text-input" and data.get("text") and not metadata.get("skip_last_text_input"):\n'
            '            self._last_text_input = str(data.get("text") or "")[:500]\n'
            '        await handle_conversation_trigger(\n',
            '        if data.get("type") == "text-input" and data.get("text") and not metadata.get("skip_last_text_input"):\n'
            '            self._last_text_input = str(data.get("text") or "")[:500]\n'
            '        if data.get("type") == "text-input" and metadata.get("vtuber_live_chat_batch"):\n'
            '            self.enqueue_vtuber_chat_context(str(data.get("text") or ""))\n'
            '            logger.info("CREDO buffered VTuber live chat batch instead of starting an immediate turn.")\n'
            '            return\n'
            '        await handle_conversation_trigger(\n',
            1,
        )
    path.write_text(text, encoding="utf-8")


def deep_merge(base: dict, patch: dict) -> dict:
    """Merge nested dictionaries without deleting unspecified default config."""
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def write_full_config(vendor: Path, *, activate: bool) -> None:
    """Write a runnable full config derived from Open-LLM-VTuber's default."""
    default_path = vendor / "config_templates" / "conf.default.yaml"
    character_path = vendor / "characters" / "credo_latency_cover.yaml"
    default_config = yaml.safe_load(default_path.read_text(encoding="utf-8"))
    character_patch = yaml.safe_load(character_path.read_text(encoding="utf-8"))
    merged = deep_merge(default_config, character_patch)

    full_path = vendor / "conf.credo.yaml"
    full_path.write_text(
        yaml.safe_dump(merged, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    if activate:
        conf_path = vendor / "conf.yaml"
        if conf_path.exists():
            backup_path = vendor / "conf.yaml.before_credo"
            if not backup_path.exists():
                shutil.copy2(conf_path, backup_path)
        shutil.copy2(full_path, conf_path)


def ensure_vendor(vendor: Path) -> None:
    """Check that the target clone is the expected Open-LLM-VTuber tree."""
    if not (vendor / "run_server.py").exists():
        raise FileNotFoundError(f"Open-LLM-VTuber clone not found: {vendor}")
    if not (vendor / "src" / "open_llm_vtuber").exists():
        raise FileNotFoundError(f"Unexpected Open-LLM-VTuber layout: {vendor}")


def apply(vendor: Path, *, activate: bool = False) -> None:
    """Apply all integration files and idempotent source patches."""
    ensure_vendor(vendor)
    copy_files(vendor)
    install_frontend_overlay(vendor)
    patch_model_dict(vendor)
    patch_agent_factory(vendor)
    patch_agent_config(vendor)
    patch_service_context(vendor)
    patch_audio_pipeline(vendor)
    patch_vtuber_routes(vendor)
    patch_websocket_handler(vendor)
    write_full_config(vendor, activate=activate)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vendor", type=Path, default=DEFAULT_VENDOR)
    parser.add_argument(
        "--activate",
        action="store_true",
        help="Also write conf.yaml from the generated CREDO config.",
    )
    args = parser.parse_args()
    apply(args.vendor.resolve(), activate=args.activate)
    print(f"CREDO Open-LLM-VTuber integration applied to {args.vendor.resolve()}")


if __name__ == "__main__":
    main()
