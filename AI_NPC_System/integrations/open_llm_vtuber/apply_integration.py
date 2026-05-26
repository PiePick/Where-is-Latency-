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
STYLEBERT_TTS_SRC = INTEGRATION_DIR / "stylebert_vits2_tts.py"


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
    character_name: str = Field("Professor's Lab Maid", alias="character_name")
    fast_track_enabled: bool = Field(True, alias="fast_track_enabled")
    use_fast_audio: bool = Field(True, alias="use_fast_audio")
    slow_enabled: bool = Field(True, alias="slow_enabled")
    slow_tts_mode: str = Field("open_llm", alias="slow_tts_mode")
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
            en="Slow response TTS mode: open_llm uses the configured StyleBERT Open-LLM TTS engine; credo_fish_speech is archival",
            zh="慢速回应 TTS 模式：open_llm 使用配置的 StyleBERT Open-LLM TTS 引擎；credo_fish_speech 仅保留用于历史实验",
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
    if "import os\n" not in text:
        text = text.replace("import json\n", "import json\nimport os\n", 1)
    text = text.replace(
        "        return await tts_engine.async_generate_audio(\n"
        "            text=text,\n"
        "            file_name_no_ext=f\"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}\",\n"
        "        )\n",
        "        return await asyncio.wait_for(\n"
        "            tts_engine.async_generate_audio(\n"
        "                text=text,\n"
        "                file_name_no_ext=f\"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}\",\n"
        "            ),\n"
        "            timeout=float(os.getenv(\"EDGE_TTS_REQUEST_TIMEOUT_SECONDS\", \"12\")),\n"
        "        )\n",
        1,
    )
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


def patch_edge_tts_timeouts(vendor: Path) -> None:
    """Bound native Edge requests so a network stall cannot freeze live speech."""
    path = vendor / "src" / "open_llm_vtuber" / "tts" / "edge_tts.py"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "            communicate = edge_tts.Communicate(text, self.voice)\n",
        "            communicate = edge_tts.Communicate(\n"
        "                text,\n"
        "                self.voice,\n"
        "                connect_timeout=int(os.getenv(\"EDGE_TTS_CONNECT_TIMEOUT\", \"4\")),\n"
        "                receive_timeout=int(os.getenv(\"EDGE_TTS_RECEIVE_TIMEOUT\", \"12\")),\n"
        "            )\n",
        1,
    )
    path.write_text(text, encoding="utf-8")


def patch_tts_factory(vendor: Path) -> None:
    """Register the CREDO Style-Bert-VITS2 adapter as an Open-LLM TTS engine."""
    path = vendor / "src" / "open_llm_vtuber" / "tts" / "tts_factory.py"
    text = path.read_text(encoding="utf-8")
    if 'engine_type == "stylebert_vits2"' in text:
        return

    branch = '''        elif engine_type == "stylebert_vits2":
            from .stylebert_vits2_tts import TTSEngine as StyleBertVITS2TTSEngine

            return StyleBertVITS2TTSEngine(**kwargs)
'''
    text = replace_once(
        text,
        '        elif engine_type == "pyttsx3_tts":\n',
        branch + '        elif engine_type == "pyttsx3_tts":\n',
        "tts_factory stylebert branch",
    )
    path.write_text(text, encoding="utf-8")


def patch_tts_config(vendor: Path) -> None:
    """Teach the Open-LLM config schema about the CREDO Style-Bert-VITS2 engine."""
    path = vendor / "src" / "open_llm_vtuber" / "config_manager" / "tts.py"
    text = path.read_text(encoding="utf-8")

    class_block = '''
class StyleBertVITS2Config(I18nMixin):
    """Configuration for a local CREDO Style-Bert-VITS2 FastAPI server."""

    base_url: str = Field("http://127.0.0.1:5000", alias="base_url")
    voice_url: Optional[str] = Field(None, alias="voice_url")
    health_url: Optional[str] = Field(None, alias="health_url")
    output_dir: str = Field("AI_NPC_System/tts_outputs/stylebert_open_llm", alias="output_dir")
    timeout: float = Field(30.0, alias="timeout")
    model_id: int = Field(0, alias="model_id")
    model_name: str = Field("credo_voice_sample_en", alias="model_name")
    speaker_id: int = Field(0, alias="speaker_id")
    style: str = Field("Neutral", alias="style")
    style_weight: float = Field(1.0, alias="style_weight")
    sdp_ratio: float = Field(0.1, alias="sdp_ratio")
    noise: float = Field(0.35, alias="noise")
    noisew: float = Field(0.45, alias="noisew")
    length: float = Field(0.95, alias="length")
    language: str = Field("EN", alias="language")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "base_url": Description(
            en="Base URL of the local Style-Bert-VITS2 server",
            zh="本地 Style-Bert-VITS2 服务基础 URL",
        ),
        "model_name": Description(
            en="Style-Bert-VITS2 model asset name, e.g. credo_voice_sample_en",
            zh="Style-Bert-VITS2 模型资源名称，例如 credo_voice_sample_en",
        ),
        "language": Description(
            en="Synthesis language code, e.g. EN",
            zh="合成语言代码，例如 EN",
        ),
    }


'''
    if "class StyleBertVITS2Config" not in text:
        text = replace_once(
            text,
            "\n\nclass CosyvoiceTTSConfig",
            "\n\n" + class_block + "class CosyvoiceTTSConfig",
            "StyleBertVITS2Config class",
        )
    if '        "stylebert_vits2",\n' not in text:
        text = text.replace(
            '        "edge_tts",\n',
            '        "edge_tts",\n        "stylebert_vits2",\n',
            1,
        )
    if 'stylebert_vits2: Optional[StyleBertVITS2Config]' not in text:
        text = text.replace(
            '    edge_tts: Optional[EdgeTTSConfig] = Field(None, alias="edge_tts")\n',
            '    edge_tts: Optional[EdgeTTSConfig] = Field(None, alias="edge_tts")\n'
            '    stylebert_vits2: Optional[StyleBertVITS2Config] = Field(None, alias="stylebert_vits2")\n',
            1,
        )
    if '"stylebert_vits2": Description(' not in text:
        text = text.replace(
            '        "edge_tts": Description(en="Configuration for Edge TTS", zh="Edge TTS 配置"),\n',
            '        "edge_tts": Description(en="Configuration for Edge TTS", zh="Edge TTS 配置"),\n'
            '        "stylebert_vits2": Description(\n'
            '            en="Configuration for CREDO Style-Bert-VITS2",\n'
            '            zh="CREDO Style-Bert-VITS2 配置",\n'
            '        ),\n',
            1,
        )
    if 'tts_model == "stylebert_vits2"' not in text:
        text = text.replace(
            '        elif tts_model == "edge_tts" and values.edge_tts is not None:\n'
            '            values.edge_tts.model_validate(values.edge_tts.model_dump())\n',
            '        elif tts_model == "edge_tts" and values.edge_tts is not None:\n'
            '            values.edge_tts.model_validate(values.edge_tts.model_dump())\n'
            '        elif tts_model == "stylebert_vits2" and values.stylebert_vits2 is not None:\n'
            '            values.stylebert_vits2.model_validate(values.stylebert_vits2.model_dump())\n',
            1,
        )
    path.write_text(text, encoding="utf-8")


def copy_files(vendor: Path) -> None:
    """Copy the custom agent, character config, and Live2D assets."""
    cfg = load_credo_config()
    agent_dst = vendor / "src" / "open_llm_vtuber" / "agent" / "agents" / "credo_latency_cover_agent.py"
    shutil.copy2(INTEGRATION_DIR / "credo_latency_cover_agent.py", agent_dst)
    shutil.copy2(STYLEBERT_TTS_SRC, vendor / "src" / "open_llm_vtuber" / "tts" / STYLEBERT_TTS_SRC.name)

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
    stylebert_config = tts_config.setdefault("stylebert_vits2", {})
    stylebert_config["base_url"] = cfg.STYLEBERT_VITS2_BASE_URL
    stylebert_config["voice_url"] = cfg.STYLEBERT_VITS2_VOICE_URL
    stylebert_config["health_url"] = cfg.STYLEBERT_VITS2_HEALTH_URL
    stylebert_config["output_dir"] = str(cfg.STYLEBERT_VITS2_OUTPUT_DIR)
    stylebert_config["timeout"] = cfg.STYLEBERT_VITS2_TIMEOUT
    stylebert_config["model_id"] = cfg.STYLEBERT_VITS2_MODEL_ID
    stylebert_config["model_name"] = cfg.STYLEBERT_VITS2_MODEL_NAME
    stylebert_config["speaker_id"] = cfg.STYLEBERT_VITS2_SPEAKER_ID
    stylebert_config["style"] = cfg.STYLEBERT_VITS2_STYLE
    stylebert_config["style_weight"] = cfg.STYLEBERT_VITS2_STYLE_WEIGHT
    stylebert_config["sdp_ratio"] = cfg.STYLEBERT_VITS2_SDP_RATIO
    stylebert_config["noise"] = cfg.STYLEBERT_VITS2_NOISE
    stylebert_config["noisew"] = cfg.STYLEBERT_VITS2_NOISEW
    stylebert_config["length"] = cfg.STYLEBERT_VITS2_LENGTH
    stylebert_config["language"] = cfg.STYLEBERT_VITS2_LANGUAGE

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
    text = text.replace(
        '"AI_NPC_System" / "expressive_interjection_bundle" / "manifest.json"',
        '"AI_NPC_System" / "fasttrack_assets" / "audio" / "expressive_interjection_bundle" / "manifest.json"',
    )
    text = text.replace(
        '"AI_NPC_System" / "fasttrack_assets" / "text" / "interjection_carriers" / "manifest.json"',
        '"AI_NPC_System" / "fasttrack_assets" / "audio" / "expressive_interjection_bundle" / "manifest.json"',
    )
    if "from .utils.stream_audio import prepare_audio_payload" not in text:
        text = text.replace(
            "from .proxy_handler import ProxyHandler\n",
            "from .proxy_handler import ProxyHandler\n"
            "from .utils.stream_audio import prepare_audio_payload\n",
            1,
        )
    text = text.replace(
        "from starlette.responses import JSONResponse\n",
        "from starlette.responses import JSONResponse, FileResponse\n",
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
            '            if (root / "AI_NPC_System" / "fasttrack_assets" / "audio" / "expressive_interjection_bundle" / "manifest.json").exists():\n'
        '                return root\n'
        '        return Path.cwd().resolve().parents[1]\n',
    )
    if '"experiment_mode": "edge_async_cover",' not in text and '"experiment_mode": "fish_cover",' not in text:
        text = text.replace(
            '        "last_prompt": "",\n'
            '    }\n',
            '        "last_prompt": "",\n'
            '        "experiment_mode": "edge_async_cover",\n'
            '    }\n'
            '    experiment_modes = {\n'
            '        "edge_no_cover": {\n'
            '            "label": "StyleBERT SlowTrack only",\n'
            '            "fast_track_enabled": False,\n'
            '            "use_fast_audio": False,\n'
            '            "slow_tts_mode": "open_llm",\n'
            '            "open_llm_tts_fallback": True,\n'
            '            "prefetch_enabled": False,\n'
            '        },\n'
            '        "edge_fasttrack": {\n'
            '            "label": "StyleBERT realtime FastTrack",\n'
            '            "fast_track_enabled": True,\n'
            '            "use_fast_audio": True,\n'
            '            "slow_tts_mode": "open_llm",\n'
            '            "open_llm_tts_fallback": True,\n'
            '            "prefetch_enabled": False,\n'
            '        },\n'
            '        "edge_async_cover": {\n'
            '            "label": "StyleBERT realtime FastTrack + async prefetch",\n'
            '            "fast_track_enabled": True,\n'
            '            "use_fast_audio": True,\n'
            '            "slow_tts_mode": "open_llm",\n'
            '            "open_llm_tts_fallback": True,\n'
            '            "prefetch_enabled": True,\n'
            '        },\n'
            '    }\n',
            1,
        )
    text = text.replace(
        '        "experiment_mode": "fish_cover",\n',
        '        "experiment_mode": "edge_async_cover",\n',
        1,
    )
    text = text.replace('"experiment_mode": "live_edge_cover"', '"experiment_mode": "edge_async_cover"')
    if '"live_edge_cover": {' in text:
        start = text.index('        "live_edge_cover": {')
        end = text.index('        "fast_no_cover": {', start)
        replacement = (
            '        "edge_async_cover": {\n'
            '            "label": "StyleBERT realtime FastTrack + async prefetch",\n'
            '            "fast_track_enabled": True,\n'
            '            "use_fast_audio": True,\n'
            '            "slow_tts_mode": "open_llm",\n'
            '            "open_llm_tts_fallback": True,\n'
            '            "prefetch_enabled": True,\n'
            '        },\n'
        )
        text = text[:start] + replacement + text[end:]
    text = text.replace(
        '        "fast_no_cover": {\n'
        '            "label": "Fast low-quality TTS / no cover",\n'
        '            "fast_track_enabled": False,\n'
        '            "use_fast_audio": False,\n'
        '            "slow_tts_mode": "open_llm",\n'
        '            "open_llm_tts_fallback": False,\n'
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
        '        },\n',
        '        "edge_no_cover": {\n'
        '            "label": "StyleBERT SlowTrack only",\n'
        '            "fast_track_enabled": False,\n'
        '            "use_fast_audio": False,\n'
        '            "slow_tts_mode": "open_llm",\n'
        '            "open_llm_tts_fallback": True,\n'
        '            "prefetch_enabled": False,\n'
        '        },\n'
        '        "edge_fasttrack": {\n'
        '            "label": "StyleBERT realtime FastTrack",\n'
        '            "fast_track_enabled": True,\n'
        '            "use_fast_audio": True,\n'
        '            "slow_tts_mode": "open_llm",\n'
        '            "open_llm_tts_fallback": True,\n'
        '            "prefetch_enabled": False,\n'
        '        },\n',
    )
    text = text.replace("Edge realtime FastTrack + async prefetch", "StyleBERT realtime FastTrack + async prefetch")
    text = text.replace("Edge SlowTrack only", "StyleBERT SlowTrack only")
    text = text.replace("Edge realtime FastTrack", "StyleBERT realtime FastTrack")
    text = text.replace('"slow_tts_mode": "edge_tts"', '"slow_tts_mode": "open_llm"')
    text = text.replace('"open_llm_tts_fallback": False', '"open_llm_tts_fallback": True')

    replacements = [
        (
            '        prompt = (\n'
            '            "VTuber stream idle segment. "\n'
            '            f"{beat} "\n'
            '            "Speak in natural English as Usada Pekora. Do not force catchphrases or suffixes. "\n'
            '            "Do not say you are waiting for input unless it sounds like a streamer joking with chat. "\n'
            '            "Do not mention systems, prompts, tests, models, or implementation. "\n'
            '            "Aim for 12 to 22 spoken words so live speech stays responsive."\n'
            '        )\n',
            '        instruction = (\n'
            '            "VTuber stream idle segment. "\n'
            '            f"{beat} "\n'
            '            "Speak in natural English as Professor\\\'s Lab Maid. Use cute lab-maid and graduate-school comedy naturally. "\n'
            '            "Do not say you are waiting for input unless it sounds like a streamer joking with chat. "\n'
            '            "Do not mention systems, prompts, tests, models, or implementation. "\n'
            '            "Aim for 12 to 22 spoken words so live speech stays responsive."\n'
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
            '            "Aim for 12 to 22 spoken words so live speech stays responsive."\n',
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
            '            "Aim for 12 to 22 spoken words so live speech stays responsive."\n'
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
            '        return _credo_root() / "AI_NPC_System" / "fasttrack_assets" / "audio" / "expressive_interjection_bundle" / "manifest.json"\n'
            '\n'
            '    def _load_interjection_items() -> list[dict]:\n'
            '        """Load selectable prebuilt Fish interjection audio for live tests."""\n'
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
    if "def _donation_sfx_path(" not in text:
        text = text.replace(
            '    def _load_interjection_items() -> list[dict]:\n',
            '    def _donation_sfx_path() -> Path | None:\n'
            '        """Return the donation SFX audio file used by the browser overlay."""\n'
            '        candidates = [\n'
            '            _credo_root() / "AI_NPC_System" / "fasttrack_assets" / "Donatiion_SFX",\n'
            '            _credo_root() / "AI_NPC_System" / "fasttrack_assets" / "audio" / "Donatiion_SFX.mp3",\n'
            '        ]\n'
            '        for candidate in candidates:\n'
            '            if candidate.is_file():\n'
            '                return candidate\n'
            '            if candidate.is_dir():\n'
            '                for suffix in ("*.mp3", "*.wav", "*.ogg"):\n'
            '                    match = next(candidate.glob(suffix), None)\n'
            '                    if match and match.is_file():\n'
            '                        return match\n'
            '        return None\n'
            '\n'
            '    def _load_interjection_items() -> list[dict]:\n',
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
            '                setattr(\n'
            '                    agent._credo_config,\n'
            '                    "CREDO_VTUBER_SLOW_PREFETCH_ENABLED",\n'
            '                    bool(mode.get("prefetch_enabled", True)),\n'
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
    if '"CREDO_VTUBER_SLOW_PREFETCH_ENABLED"' not in text and '"SLOW_TRACK_ALLOW_OPEN_LLM_TTS_FALLBACK"' in text:
        text = text.replace(
            '                    bool(mode["open_llm_tts_fallback"]),\n'
            '                )\n',
            '                    bool(mode["open_llm_tts_fallback"]),\n'
            '                )\n'
            '                setattr(\n'
            '                    agent._credo_config,\n'
            '                    "CREDO_VTUBER_SLOW_PREFETCH_ENABLED",\n'
            '                    bool(mode.get("prefetch_enabled", True)),\n'
            '                )\n',
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
            '        """Force-play one prebuilt Fish interjection with its motion tags."""\n'
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
            '            display_text={"text": "", "name": os.getenv("OPEN_LLM_VTUBER_CHARACTER_NAME", "Professor\\\'s Lab Maid"), "avatar": None},\n'
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
    text = text.replace(
        '        """Load selectable interjection text and motion metadata for live tests."""\n',
        '        """Load selectable prebuilt StyleBERT interjection audio for live tests."""\n',
    )
    current_item_loop = (
        '        items = []\n'
        '        for item in manifest.get("items", []):\n'
        '            items.append(\n'
        '                {\n'
        '                    "id": str(item.get("id") or ""),\n'
        '                    "emotion": str(item.get("emotion") or "neutral"),\n'
        '                    "style_tag": str(item.get("style_tag") or "steady"),\n'
        '                    "event": str(item.get("event") or "thinking"),\n'
        '                    "carrier": str(item.get("carrier") or item.get("plain_tts_text") or ""),\n'
        '                }\n'
        '            )\n'
        '        return items\n'
    )
    prebuilt_item_loop = (
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
    )
    text = text.replace(current_item_loop, prebuilt_item_loop)
    text = text.replace(
        '        """Force-synthesize one interjection with the live TTS and motion tags."""\n',
        '        """Force-play one prebuilt StyleBERT interjection with its motion tags."""\n',
    )
    text = text.replace(
        '        carrier = str(item.get("carrier") or "hm.").strip()\n'
        '        audio_path = await default_context_cache.tts_engine.async_generate_audio(\n'
        '            carrier, file_name_no_ext=f"credo_manual_{uuid4().hex[:8]}"\n'
        '        )\n'
        '        try:\n'
        '            audio_payload = prepare_audio_payload(\n'
        '                audio_path=audio_path,\n'
        '                display_text={"text": "", "name": os.getenv("OPEN_LLM_VTUBER_CHARACTER_NAME", "Professor\\\'s Lab Maid"), "avatar": None},\n'
        '                actions={"expressions": expressions},\n'
        '            )\n'
        '        finally:\n'
        '            if audio_path:\n'
        '                default_context_cache.tts_engine.remove_file(audio_path, verbose=False)\n',
        '        audio_payload = prepare_audio_payload(\n'
        '            audio_path=item["audio_path"],\n'
        '            display_text={"text": "", "name": os.getenv("OPEN_LLM_VTUBER_CHARACTER_NAME", "Professor\\\'s Lab Maid"), "avatar": None},\n'
        '            actions={"expressions": expressions},\n'
        '        )\n',
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
    if '"component_mode": "both",' not in text:
        text = text.replace(
            '        "experiment_mode": "edge_async_cover",\n'
            '    }\n',
            '        "experiment_mode": "edge_async_cover",\n'
            '        "component_mode": "both",\n'
            '        "selection_policy": "grounded",\n'
            '        "scheduling_mode": "parallel",\n'
            '    }\n',
            1,
        )
    if "def _apply_experiment_factors(" not in text:
        text = text.replace(
            '    def _build_idle_prompt(topic: str, silence_seconds: float) -> tuple[str, dict]:\n',
            '    def _apply_experiment_factors(payload: dict) -> dict:\n'
            '        """Apply mapping-basis and scheduling factors without dynamic A/B/C assembly."""\n'
            '        component_mode = str(payload.get("component_mode") or vtuber_mode.get("component_mode") or "both")\n'
            '        selection_policy = str(payload.get("selection_policy") or vtuber_mode.get("selection_policy") or "grounded")\n'
            '        scheduling_mode = str(payload.get("scheduling_mode") or vtuber_mode.get("scheduling_mode") or "parallel")\n'
            '        if component_mode not in {"both", "none"}:\n'
            '            raise ValueError("unknown component mode")\n'
            '        if selection_policy not in {"grounded", "emotion_only", "response_act_only"}:\n'
            '            raise ValueError("unknown selection policy")\n'
            '        if scheduling_mode not in {"parallel", "serial"}:\n'
            '            raise ValueError("unknown scheduling mode")\n'
            '        vtuber_mode["component_mode"] = component_mode\n'
            '        vtuber_mode["selection_policy"] = selection_policy\n'
            '        vtuber_mode["scheduling_mode"] = scheduling_mode\n'
            '        updated = 0\n'
            '        for agent in _iter_credo_agents():\n'
            '            agent.fast_track_enabled = component_mode != "none"\n'
            '            agent.settings["fast_track_enabled"] = agent.fast_track_enabled\n'
            '            if hasattr(agent, "_credo_config"):\n'
            '                setattr(agent._credo_config, "CREDO_FASTTRACK_COMPONENT_MODE", component_mode)\n'
            '                setattr(agent._credo_config, "CREDO_FASTTRACK_SELECTION_POLICY", selection_policy)\n'
            '                setattr(agent._credo_config, "CREDO_CONTEXT_SCHEDULING_MODE", scheduling_mode)\n'
            '                setattr(agent._credo_config, "CREDO_VTUBER_SLOW_PREFETCH_ENABLED", scheduling_mode == "parallel")\n'
            '            if scheduling_mode == "serial":\n'
            '                task = getattr(agent, "_vtuber_slow_prefetch_task", None)\n'
            '                if task is not None and not task.done():\n'
            '                    task.cancel()\n'
            '                agent._vtuber_slow_prefetch_task = None\n'
            '            updated += 1\n'
            '        return {\n'
            '            "component_mode": component_mode,\n'
            '            "selection_policy": selection_policy,\n'
            '            "scheduling_mode": scheduling_mode,\n'
            '            "updated_agents": updated,\n'
            '        }\n'
            '\n'
            '    def _build_idle_prompt(topic: str, silence_seconds: float) -> tuple[str, dict]:\n',
            1,
        )
    text = text.replace(
        '        """Apply orthogonal FastTrack and scheduling factors without changing the pipeline."""\n',
        '        """Apply mapping-basis and scheduling factors without dynamic A/B/C assembly."""\n',
    )
    text = text.replace(
        '        if component_mode not in {"both", "language_only", "nonverbal_only", "none"}:\n',
        '        if component_mode not in {"both", "none"}:\n',
    )
    text = text.replace(
        '        if selection_policy not in {"grounded", "random"}:\n',
        '        if selection_policy not in {"grounded", "emotion_only", "response_act_only"}:\n',
    )
    if '"component_mode": vtuber_mode["component_mode"],' not in text:
        text = text.replace(
            '            "experiment_label": experiment_modes[vtuber_mode["experiment_mode"]]["label"],\n'
            '        }\n',
            '            "experiment_label": experiment_modes[vtuber_mode["experiment_mode"]]["label"],\n'
            '            "component_mode": vtuber_mode["component_mode"],\n'
            '            "selection_policy": vtuber_mode["selection_policy"],\n'
            '            "scheduling_mode": vtuber_mode["scheduling_mode"],\n'
            '        }\n',
            1,
        )
    if '"mode": "direct_chat",' not in text:
        text = text.replace(
            '        "scheduling_mode": "parallel",\n',
            '        "scheduling_mode": "parallel",\n'
            '        "mode": "direct_chat",\n',
            1,
        )
    if '"mode": vtuber_mode["mode"],' not in text:
        text = text.replace(
            '            "scheduling_mode": vtuber_mode["scheduling_mode"],\n'
            '        }\n',
            '            "scheduling_mode": vtuber_mode["scheduling_mode"],\n'
            '            "mode": vtuber_mode["mode"],\n'
            '        }\n',
            1,
        )
    if 'factors = _apply_experiment_factors(payload)' not in text:
        text = text.replace(
            '        mode_key = str(payload.get("mode") or "")\n'
            '        try:\n'
            '            result = _apply_experiment_mode(mode_key)\n'
            '        except KeyError:\n'
            '            return JSONResponse({"ok": False, "error": "unknown experiment mode"}, status_code=404)\n'
            '        return {"ok": True, **result}\n',
            '        mode_key = str(payload.get("mode") or "")\n'
            '        try:\n'
            '            result = _apply_experiment_mode(mode_key) if mode_key else {}\n'
            '            factors = _apply_experiment_factors(payload)\n'
            '        except (KeyError, ValueError) as exc:\n'
            '            return JSONResponse({"ok": False, "error": str(exc)}, status_code=404)\n'
            '        return {"ok": True, **result, **factors}\n',
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
    if 'requested_mode = str(payload.get("mode") or "virtual_broadcast")' not in text:
        text = text.replace(
            '    async def credo_vtuber_mode_start(request: Request):\n'
            '        """Enable proactive VTuber monologue and optional YouTube chat reading."""\n'
            '        payload = await request.json()\n',
            '    async def credo_vtuber_mode_start(request: Request):\n'
            '        """Enable proactive VTuber monologue and optional YouTube chat reading."""\n'
            '        payload = await request.json()\n'
            '        requested_mode = str(payload.get("mode") or "virtual_broadcast")\n'
            '        if requested_mode not in {"youtube_live", "virtual_broadcast"}:\n'
            '            return JSONResponse({"active": False, "error": "unknown VTuber runtime mode"}, status_code=404)\n',
            1,
        )
    start_anchor = '    async def credo_vtuber_mode_start(request: Request):\n'
    start_index = text.find(start_anchor)
    start_end = text.find('\n    @router.', start_index + len(start_anchor)) if start_index >= 0 else -1
    start_body = text[start_index:start_end] if start_index >= 0 and start_end >= 0 else ""
    if '_apply_experiment_factors(payload)' not in start_body:
        text = text.replace(
            '        vtuber_mode["active"] = True\n',
            '        try:\n'
            '            _apply_experiment_factors(payload)\n'
            '        except ValueError as exc:\n'
            '            return JSONResponse({"active": False, "error": str(exc)}, status_code=404)\n'
            '        vtuber_mode["active"] = True\n',
            1,
        )
    factor_block = (
        '        try:\n'
        '            _apply_experiment_factors(payload)\n'
        '        except ValueError as exc:\n'
        '            return JSONResponse({"active": False, "error": str(exc)}, status_code=404)\n'
    )
    while factor_block + factor_block in text:
        text = text.replace(factor_block + factor_block, factor_block, 1)
    if 'vtuber_mode["mode"] = requested_mode' not in text:
        text = text.replace(
            '        vtuber_mode["active"] = True\n',
            '        vtuber_mode["active"] = True\n'
            '        vtuber_mode["mode"] = requested_mode\n',
            1,
        )
    if 'ws_handler.enqueue_vtuber_chat_context(text)' not in text:
        text = text.replace(
            '        text = f"Viewer {author} says: {message}"\n'
            '        ok = await ws_handler.trigger_text_input(\n',
            '        text = f"Viewer {author} says: {message}"\n'
            '        if vtuber_mode["active"] and vtuber_mode.get("mode") == "virtual_broadcast":\n'
            '            ws_handler.enqueue_vtuber_chat_context(text)\n'
            '            return {"queued": True, "buffered": True}\n'
            '        if vtuber_mode.get("mode") == "youtube_live":\n'
            '            return JSONResponse(\n'
            '                {"queued": False, "error": "virtual chat is disabled in YouTube live mode"},\n'
            '                status_code=409,\n'
            '            )\n'
            '        ok = await ws_handler.trigger_text_input(\n',
            1,
        )
    else:
        text = text.replace('        if vtuber_mode["active"]:\n            ws_handler.enqueue_vtuber_chat_context(text)\n', '        if vtuber_mode["active"] and vtuber_mode.get("mode") == "virtual_broadcast":\n            ws_handler.enqueue_vtuber_chat_context(text)\n')
    if '"virtual chat is disabled in YouTube live mode"' not in text:
        text = text.replace(
            '        if vtuber_mode["active"] and vtuber_mode.get("mode") == "virtual_broadcast":\n'
            '            ws_handler.enqueue_vtuber_chat_context(text)\n'
            '            return {"queued": True, "buffered": True}\n'
            '        ok = await ws_handler.trigger_text_input(\n',
            '        if vtuber_mode["active"] and vtuber_mode.get("mode") == "virtual_broadcast":\n'
            '            ws_handler.enqueue_vtuber_chat_context(text)\n'
            '            return {"queued": True, "buffered": True}\n'
            '        if vtuber_mode.get("mode") == "youtube_live":\n'
            '            return JSONResponse(\n'
            '                {"queued": False, "error": "virtual chat is disabled in YouTube live mode"},\n'
            '                status_code=409,\n'
            '            )\n'
            '        ok = await ws_handler.trigger_text_input(\n',
            1,
        )
    if '"/credo/vtuber-mode/donation-sfx"' not in text:
        text = text.replace(
            '    @router.post("/credo/vtuber-mode/start")\n',
            '    @router.get("/credo/vtuber-mode/donation-sfx")\n'
            '    async def credo_vtuber_mode_donation_sfx():\n'
            '        """Serve the local donation SFX for the browser donation overlay."""\n'
            '        sfx_path = _donation_sfx_path()\n'
            '        if not sfx_path:\n'
            '            return JSONResponse({"error": "donation SFX not found"}, status_code=404)\n'
            '        return FileResponse(sfx_path)\n'
            '\n'
            '    @router.post("/credo/vtuber-mode/start")\n',
            1,
        )
    if 'if requested_mode == "youtube_live":' not in text:
        text = text.replace(
            '        bridge = vtuber_mode.get("bridge")\n'
            '        if bridge is None or bridge.poll() is not None:\n'
            '            vtuber_mode["bridge"] = _start_youtube_bridge(payload)\n',
            '        bridge = vtuber_mode.get("bridge")\n'
            '        if requested_mode == "youtube_live":\n'
            '            if bridge is None or bridge.poll() is not None:\n'
            '                vtuber_mode["bridge"] = _start_youtube_bridge(payload)\n'
            '        elif bridge and bridge.poll() is None:\n'
            '            bridge.terminate()\n'
            '            vtuber_mode["bridge"] = None\n',
            1,
        )
    if 'vtuber_mode["mode"] = "direct_chat"' not in text:
        text = text.replace(
            '        vtuber_mode["active"] = False\n',
            '        vtuber_mode["active"] = False\n'
            '        vtuber_mode["mode"] = "direct_chat"\n',
            1,
        )
    if '        vtuber_mode["bridge"] = None\n        return await credo_vtuber_mode_status()' not in text:
        text = text.replace(
            '        if bridge and bridge.poll() is None:\n'
            '            bridge.terminate()\n'
            '        return await credo_vtuber_mode_status()\n',
            '        if bridge and bridge.poll() is None:\n'
            '            bridge.terminate()\n'
            '        vtuber_mode["bridge"] = None\n'
            '        return await credo_vtuber_mode_status()\n',
            1,
        )
    text = text.replace(
        '        name = str(payload.get("name") or "a viewer")\n'
        '        amount = str(payload.get("amount") or "")\n'
        '        message = str(payload.get("message") or "")\n',
        '        name = _clean_prompt_piece(payload.get("name") or "a viewer", 48)\n'
        '        amount = _clean_prompt_piece(payload.get("amount") or "", 32)\n'
        '        message = _clean_prompt_piece(payload.get("message") or "", 360)\n',
    )
    text = text.replace(
        "React warmly in the language requested by the broadcast direction or stream context, then naturally fold back into the stream. "
        "Do not write bracketed style tags or switch languages. ",
        "This donation is the highest-priority counseling question. Answer it before buffered live chat. "
        "React warmly in the language requested by the broadcast direction or stream context, then naturally fold back into the stream. "
        "Do not answer unrelated chat in this donation turn; a later live-chat batch turn will summarize surrounding chat. "
        "Do not write bracketed style tags or switch languages. ",
    )
    if "CREDO donation priority cancelled the active VTuber turn" not in text:
        text = text.replace(
            '        text = _clean_prompt_piece(f"{name} sent support. {message}", 220)\n'
            '        ok = await ws_handler.trigger_text_input(\n',
            '        text = _clean_prompt_piece(f"{name} sent support. {message}", 220)\n'
            '        target_uid = ws_handler.first_client_uid()\n'
            '        if payload.get("priority", True) and target_uid:\n'
            '            active_task = ws_handler.current_conversation_tasks.get(target_uid)\n'
            '            if active_task and not active_task.done():\n'
            '                active_task.cancel()\n'
            '                logger.info("CREDO donation priority cancelled the active VTuber turn before answering donation.")\n'
            '        ok = await ws_handler.trigger_text_input(\n',
            1,
        )
    text = text.replace(
        '            await ws_handler.trigger_text_input(prompt)\n            await asyncio.sleep(float(vtuber_mode["interval"]))\n',
        '            target_uid = ws_handler.first_client_uid()\n            active_task = ws_handler.current_conversation_tasks.get(target_uid) if target_uid else None\n            if active_task and not active_task.done():\n                logger.info("CREDO VTuber idle monologue skipped because a conversation is still running.")\n            else:\n                await ws_handler.trigger_text_input(prompt)\n            await asyncio.sleep(float(vtuber_mode["interval"]))\n',
    )
    text = text.replace(
        "Speak in natural English as CREDO. ",
        "Speak in natural English as Professor's Lab Maid. Use cute lab-maid and graduate-school comedy naturally. ",
    )
    legacy_forced_suffix_prompt = (
        "Speak in natural English as Usada Pekora. Every sentence should include "
        "pe"
        "ko naturally. "
    )
    text = text.replace(
        legacy_forced_suffix_prompt,
        "Speak in natural English as Professor's Lab Maid. Use cute lab-maid and graduate-school comedy naturally. ",
    )
    text = text.replace(
        'os.getenv("OPEN_LLM_VTUBER_CHARACTER_NAME", "Lera Mei")',
        'os.getenv("OPEN_LLM_VTUBER_CHARACTER_NAME", "Professor\\\'s Lab Maid")',
    )
    text = text.replace(
        'os.getenv("OPEN_LLM_VTUBER_CHARACTER_NAME", "Usada Pekora")',
        'os.getenv("OPEN_LLM_VTUBER_CHARACTER_NAME", "Professor\\\'s Lab Maid")',
    )
    text = text.replace(
        "Speak in natural English as Usada Pekora. Do not force catchphrases or suffixes. ",
        "Speak in natural English as Professor's Lab Maid. Use cute lab-maid and graduate-school comedy naturally. ",
    )
    if '"broadcast_direction": "",' not in text:
        text = text.replace(
            '        "mode": "direct_chat",\n',
            '        "mode": "direct_chat",\n'
            '        "broadcast_direction": "",\n',
            1,
        )
    if '"experiment_run_id": "",' not in text:
        text = text.replace(
            '        "broadcast_direction": "",\n',
            '        "broadcast_direction": "",\n'
            '        "experiment_run_id": "",\n'
            '        "experiment_factor": "",\n'
            '        "scenario": "",\n',
            1,
        )
    if "def _broadcast_direction(" not in text:
        text = text.replace(
            '    def _clean_prompt_piece(value: object, limit: int = 500) -> str:\n'
            '        """Keep server-generated stream context compact and safe for prompts."""\n'
            '        text = " ".join(str(value or "").split())\n'
            '        return text[:limit]\n',
            '    def _clean_prompt_piece(value: object, limit: int = 500) -> str:\n'
            '        """Keep server-generated stream context compact and safe for prompts."""\n'
            '        text = " ".join(str(value or "").split())\n'
            '        return text[:limit]\n'
            '\n'
            '    def _broadcast_direction(payload: dict | None = None) -> str:\n'
            '        """Return the active operator direction for stream topic steering."""\n'
            '        if payload and "broadcast_direction" in payload:\n'
            '            vtuber_mode["broadcast_direction"] = _clean_prompt_piece(payload.get("broadcast_direction"), 700)\n'
            '        return _clean_prompt_piece(vtuber_mode.get("broadcast_direction"), 700)\n'
            '\n'
            '    def _with_broadcast_direction(instruction: str, payload: dict | None = None) -> str:\n'
            '        """Append the optional operator direction without replacing persona rules."""\n'
            '        direction = _broadcast_direction(payload)\n'
            '        if not direction:\n'
            '            return instruction\n'
            '        return (\n'
            '            f"{instruction} "\n'
            '            f"Operator broadcast direction: {direction} "\n'
            '            "Use it to steer the stream topic and tone unless it conflicts with persona or safety rules."\n'
            '        )\n',
            1,
        )
    if 'scheduling_mode in {"no_fasttrack", "none"}' not in text:
        text = text.replace(
            '        scheduling_mode = str(payload.get("scheduling_mode") or vtuber_mode.get("scheduling_mode") or "parallel")\n'
            '        if component_mode not in {"both", "none"}:\n',
            '        scheduling_mode = str(payload.get("scheduling_mode") or vtuber_mode.get("scheduling_mode") or "parallel")\n'
            '        if scheduling_mode in {"no_fasttrack", "none"}:\n'
            '            component_mode = "none"\n'
            '            scheduling_mode = "serial"\n'
            '        if selection_policy == "none":\n'
            '            component_mode = "none"\n'
            '            scheduling_mode = "serial"\n'
            '        if component_mode == "none":\n'
            '            selection_policy = "none"\n'
            '            scheduling_mode = "serial"\n'
            '        if component_mode not in {"both", "none"}:\n',
            1,
        )
    if '        if selection_policy == "none":\n' not in text:
        text = text.replace(
            '        if component_mode == "none":\n'
            '            scheduling_mode = "serial"\n',
            '        if selection_policy == "none":\n'
            '            component_mode = "none"\n'
            '            scheduling_mode = "serial"\n'
            '        if component_mode == "none":\n'
            '            selection_policy = "none"\n'
            '            scheduling_mode = "serial"\n',
            1,
        )
    elif '        if component_mode == "none":\n            selection_policy = "none"\n' not in text:
        text = text.replace(
            '        if component_mode == "none":\n'
            '            scheduling_mode = "serial"\n',
            '        if component_mode == "none":\n'
            '            selection_policy = "none"\n'
            '            scheduling_mode = "serial"\n',
            1,
        )
    if "experiment_run_id = _clean_prompt_piece(" not in text:
        text = text.replace(
            '        scheduling_mode = str(payload.get("scheduling_mode") or vtuber_mode.get("scheduling_mode") or "parallel")\n',
            '        scheduling_mode = str(payload.get("scheduling_mode") or vtuber_mode.get("scheduling_mode") or "parallel")\n'
            '        experiment_run_id = _clean_prompt_piece(\n'
            '            payload.get("experiment_run_id") if "experiment_run_id" in payload else vtuber_mode.get("experiment_run_id"),\n'
            '            96,\n'
            '        )\n'
            '        experiment_factor = _clean_prompt_piece(\n'
            '            payload.get("experiment_factor") if "experiment_factor" in payload else vtuber_mode.get("experiment_factor"),\n'
            '            96,\n'
            '        )\n'
            '        scenario = _clean_prompt_piece(\n'
            '            payload.get("scenario") if "scenario" in payload else vtuber_mode.get("scenario"),\n'
            '            96,\n'
            '        )\n',
            1,
        )
    text = text.replace(
        '        if selection_policy not in {"grounded", "emotion_only", "response_act_only"}:\n',
        '        if selection_policy not in {"grounded", "emotion_only", "response_act_only", "neutral_random", "none"}:\n',
    )
    text = text.replace(
        '        if selection_policy not in {"grounded", "emotion_only", "response_act_only", "neutral_random"}:\n',
        '        if selection_policy not in {"grounded", "emotion_only", "response_act_only", "neutral_random", "none"}:\n',
    )
    if '        vtuber_mode["experiment_run_id"] = experiment_run_id\n' not in text:
        text = text.replace(
            '        vtuber_mode["scheduling_mode"] = scheduling_mode\n',
            '        vtuber_mode["scheduling_mode"] = scheduling_mode\n'
            '        vtuber_mode["experiment_run_id"] = experiment_run_id\n'
            '        vtuber_mode["experiment_factor"] = experiment_factor\n'
            '        vtuber_mode["scenario"] = scenario\n',
            1,
        )
    if 'setattr(agent._credo_config, "CREDO_EXPERIMENT_RUN_ID", experiment_run_id)' not in text:
        text = text.replace(
            '                setattr(agent._credo_config, "CREDO_VTUBER_SLOW_PREFETCH_ENABLED", scheduling_mode == "parallel")\n',
            '                setattr(agent._credo_config, "CREDO_VTUBER_SLOW_PREFETCH_ENABLED", scheduling_mode == "parallel")\n'
            '                setattr(agent._credo_config, "CREDO_EXPERIMENT_RUN_ID", experiment_run_id)\n'
            '                setattr(agent._credo_config, "CREDO_EXPERIMENT_FACTOR", experiment_factor)\n'
            '                setattr(agent._credo_config, "CREDO_EXPERIMENT_SCENARIO", scenario)\n',
            1,
        )
    if '            "experiment_run_id": experiment_run_id,\n' not in text:
        text = text.replace(
            '            "scheduling_mode": scheduling_mode,\n'
            '            "updated_agents": updated,\n',
            '            "scheduling_mode": scheduling_mode,\n'
            '            "experiment_run_id": experiment_run_id,\n'
            '            "experiment_factor": experiment_factor,\n'
            '            "scenario": scenario,\n'
            '            "updated_agents": updated,\n',
            1,
        )
    text = text.replace(
        '        instruction = (\n'
        '            "VTuber stream idle segment. "\n',
        '        instruction = _with_broadcast_direction(\n'
        '            "VTuber stream idle segment. "\n',
    )
    text = text.replace(
        '            "Aim for 12 to 24 spoken words so live TTS does not block chat."\n'
        '        )\n',
        '            "Speak at least 50 characters, usually 18 to 40 spoken words."\n'
        '        )\n',
    )
    text = text.replace(
        '        instruction = (\n'
        '            "VTuber live chat batch segment. Recent chat has been buffered while the stream was speaking. "\n',
        '        instruction = _with_broadcast_direction(\n'
        '            "VTuber live chat batch segment. Recent chat has been buffered while the stream was speaking. "\n',
    )
    text = text.replace(
        '            "Aim for 14 to 28 spoken words so Fish Speech does not block the stream."\n'
        '        )\n',
        '            "Speak at least 50 characters, usually 18 to 40 spoken words."\n'
        '        )\n',
    )
    text = text.replace(
        '            "topic": topic,\n'
        '            "last_chat":',
        '            "topic": topic,\n'
        '            "broadcast_direction": _broadcast_direction(),\n'
        '            "last_chat":',
    )
    if '"broadcast_direction": vtuber_mode["broadcast_direction"],' not in text:
        text = text.replace(
            '            "mode": vtuber_mode["mode"],\n'
            '        }\n',
            '            "mode": vtuber_mode["mode"],\n'
            '            "broadcast_direction": vtuber_mode["broadcast_direction"],\n'
            '        }\n',
            1,
        )
    if '"experiment_run_id": vtuber_mode["experiment_run_id"],' not in text:
        text = text.replace(
            '            "broadcast_direction": vtuber_mode["broadcast_direction"],\n'
            '        }\n',
            '            "broadcast_direction": vtuber_mode["broadcast_direction"],\n'
            '            "experiment_run_id": vtuber_mode["experiment_run_id"],\n'
            '            "experiment_factor": vtuber_mode["experiment_factor"],\n'
            '            "scenario": vtuber_mode["scenario"],\n'
            '        }\n',
            1,
        )
    if '@router.post("/credo/vtuber-mode/config")' not in text:
        text = text.replace(
            '    @router.get("/credo/interjections")\n',
            '    @router.post("/credo/vtuber-mode/config")\n'
            '    async def credo_vtuber_mode_config(request: Request):\n'
            '        """Update operator-provided VTuber broadcast settings."""\n'
            '        payload = await request.json()\n'
            '        _broadcast_direction(payload)\n'
            '        if "topic" in payload:\n'
            '            vtuber_mode["topic"] = _clean_prompt_piece(payload.get("topic") or "", 180)\n'
            '        return await credo_vtuber_mode_status()\n'
            '\n'
            '    @router.get("/credo/interjections")\n',
            1,
        )
    if '_broadcast_direction(payload)\n        vtuber_mode["interval"]' not in text:
        text = text.replace(
            '        vtuber_mode["topic"] = _clean_prompt_piece(payload.get("topic") or vtuber_mode["topic"] or "", 180)\n'
            '        vtuber_mode["interval"]',
            '        vtuber_mode["topic"] = _clean_prompt_piece(payload.get("topic") or vtuber_mode["topic"] or "", 180)\n'
            '        _broadcast_direction(payload)\n'
            '        vtuber_mode["interval"]',
            1,
        )
    text = text.replace(
        '            "Do not write bracketed style tags or switch languages."\n'
        '        )\n'
        '        text = "Let\\\'s do a quick stream monologue."\n',
        '            "Do not write bracketed style tags or switch languages. "\n'
        '            "Speak at least 50 characters, usually 18 to 40 spoken words."\n'
        '        )\n'
        '        instruction = _with_broadcast_direction(instruction, payload)\n'
        '        text = "Let\\\'s do a quick stream monologue."\n',
    )
    text = text.replace(
        '            "Do not write bracketed style tags or switch languages."\n'
        '        )\n'
        '        text = _clean_prompt_piece(f"{name} sent support. {message}", 220)\n',
        '            "Do not write bracketed style tags or switch languages. "\n'
        '            "Speak at least 50 characters, usually 18 to 40 spoken words."\n'
        '        )\n'
        '        instruction = _with_broadcast_direction(instruction, payload)\n'
        '        text = _clean_prompt_piece(f"{name} sent support. {message}", 220)\n',
    )
    text = text.replace(
        '                "topic": topic,\n'
        '                "last_chat":',
        '                "topic": topic,\n'
        '                "broadcast_direction": _broadcast_direction(),\n'
        '                "last_chat":',
    )
    text = text.replace(
        '                "topic": _clean_prompt_piece(vtuber_mode["topic"], 180),\n'
        '                "last_chat":',
        '                "topic": _clean_prompt_piece(vtuber_mode["topic"], 180),\n'
        '                "broadcast_direction": _broadcast_direction(),\n'
        '                "last_chat":',
    )
    text = text.replace(
        "Speak in natural English as Professor's Lab Maid. Use cute lab-maid and graduate-school comedy naturally. ",
        "Speak in the language requested by the broadcast direction or recent chat; otherwise use natural English as Professor's Lab Maid. "
        "Use cute lab-maid and graduate-school comedy naturally. ",
    )
    text = text.replace(
        "Keep continuity with the current topic, stay in natural English, and end with a light hook for chat. ",
        "Keep continuity with the current topic, use the language requested by the broadcast direction or recent chat, and end with a light hook for chat. ",
    )
    text = text.replace(
        "VTuber mode manual monologue. Speak naturally to the audience in English only. ",
        "VTuber mode manual monologue. Speak naturally to the audience in the language requested by the broadcast direction or stream context. ",
    )
    text = text.replace(
        "React warmly in English only, then naturally fold back into the stream. ",
        "React warmly in the language requested by the broadcast direction or stream context, then naturally fold back into the stream. ",
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
    patch_edge_tts_timeouts(vendor)
    patch_tts_factory(vendor)
    patch_tts_config(vendor)
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
