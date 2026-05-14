"""Install the CREDO latency-cover adapter into a local Open-LLM-VTuber clone."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
from pathlib import Path

import yaml


INTEGRATION_DIR = Path(__file__).resolve().parent
CREDO_ROOT = INTEGRATION_DIR.parents[2]
DEFAULT_VENDOR = CREDO_ROOT / "vendor" / "open-llm-vtuber"


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
    use_fast_audio: bool = Field(True, alias="use_fast_audio")
    slow_enabled: bool = Field(True, alias="slow_enabled")
    slow_tts_mode: str = Field("credo_fish_speech", alias="slow_tts_mode")
    record_memory: bool = Field(True, alias="record_memory")
    seed: Optional[int] = Field(None, alias="seed")
    expression_map: Dict[str, List[str]] = Field(default_factory=dict, alias="expression_map")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "ai_npc_path": Description(
            en="Path to the CREDO AI_NPC_System runtime folder",
            zh="CREDO AI_NPC_System 运行目录路径",
        ),
        "use_fast_audio": Description(
            en="Use pre-generated FastTrack audio files when available",
            zh="可用时使用预生成的 FastTrack 音频",
        ),
        "slow_tts_mode": Description(
            en="Slow response TTS mode: credo_fish_speech or open_llm",
            zh="慢速回应 TTS 模式：credo_fish_speech 或 open_llm",
        ),
    }


'''
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
    agent_settings["use_fast_audio"] = cfg.OPEN_LLM_VTUBER_USE_FAST_AUDIO
    agent_settings["slow_enabled"] = cfg.OPEN_LLM_VTUBER_SLOW_ENABLED
    agent_settings["slow_tts_mode"] = cfg.OPEN_LLM_VTUBER_SLOW_TTS_MODE
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

    avatars_dst = vendor / "avatars"
    avatars_dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(live2d_src / cfg.OPEN_LLM_VTUBER_AVATAR, avatars_dst / cfg.OPEN_LLM_VTUBER_AVATAR)


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
                "sadness": 1,
                "sad": 1,
                "worried": 1,
                "negative_01": 1,
                "negative_02": 1,
                "negative_03": 1,
                "anger": 2,
                "disgust": 2,
                "joy": 3,
                "happy": 3,
                "smile": 3,
                "positive_01": 3,
                "positive_02": 3,
                "positive_03": 3,
                "surprise": 3,
                "confused": 3,
                "ambiguous_01": 3,
                "ambiguous_02": 3,
                "ambiguous_03": 3,
            },
            "tapMotions": {
                "HitAreaHead": {"": 1},
                "HitAreaBody": {"": 1},
            },
        }
    )
    path.write_text(json.dumps(models, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")


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
    patch_model_dict(vendor)
    patch_agent_factory(vendor)
    patch_agent_config(vendor)
    patch_service_context(vendor)
    patch_audio_pipeline(vendor)
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
