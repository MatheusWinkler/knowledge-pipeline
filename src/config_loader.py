###
# Knowledge Pipeline
# Copyright (c) 2025 [Felix Bois]
# 
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.
###

import os
import yaml
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

logger = logging.getLogger("ConfigLoader")

@dataclass
class PipelineConfig:
    app_name: str
    whisper_model_size: str
    llm_model_id: str
    timeouts: Dict[str, float]
    paths: Dict[str, str]
    content_types: Dict[str, Any]
    special_collections: Dict[str, str]
    auto_tags: Dict[str, str]
    metadata_prompt: Dict[str, str]
    api_key: str
    api_url: str

class ConfigManager:
    def __init__(self, config_path: str = "config/settings.yaml", env_path: str = "config/.env"):
        self.config_path = config_path
        self.env_path = env_path

    def load_config(self) -> PipelineConfig:
        # 1. Load Secrets
        if os.path.exists(self.env_path):
            load_dotenv(self.env_path)
            logger.info("🔐 Loaded environment secrets.")
        else:
            logger.warning(f"⚠️ No .env file found at {self.env_path}.")

        api_key = os.getenv("API_KEY")
        api_url = os.getenv("OPEN_WEBUI_URL")

        if not api_key: raise ValueError("❌ CRITICAL: 'API_KEY' missing.")
        if not api_url: raise ValueError("❌ CRITICAL: 'OPEN_WEBUI_URL' missing.")

        # 2. Load YAML
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"❌ Config missing: {self.config_path}")

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f)
                logger.info(f"📄 Loaded settings from {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"❌ Invalid YAML: {e}")

        # 3. Path Normalization
        paths = yaml_data.get("paths", {})
        base = paths.get("base", "")
        
        def resolve(p_name, fallback_key=None):
            # Try primary key, then fallback key
            raw = paths.get(p_name)
            if not raw and fallback_key:
                raw = paths.get(fallback_key)
            
            # If still nothing, default to UPPERCASE folder in base
            if not raw:
                # If p_name is 'batch', default to '_INPUT_TEXT' as per new standard
                if p_name == "input_text_folder": return os.path.join(base, "_INPUT_TEXT")
                return os.path.join(base, p_name.upper())

            if base and raw and not os.path.isabs(raw):
                return os.path.join(base, raw)
            return raw

        normalized_paths = {
            "base": base,
            "input": resolve("input_folder"),
            "archive": resolve("archive_folder"),
            "output": resolve("knowledge_folder"),
            # Look for new key 'input_text_folder', fallback to old 'batch_sync_folder'
            "batch": resolve("input_text_folder", fallback_key="batch_sync_folder")
        }

        # 4. Construct Object
        return PipelineConfig(
            app_name=yaml_data.get("app_name", "Knowledge Pipeline"),
            whisper_model_size=yaml_data.get("whisper_model_size", "base"),
            llm_model_id=yaml_data.get("llm_model_id", "gpt-3.5-turbo"),
            timeouts=yaml_data.get("timeouts", {"llm_analysis": 300}),
            paths=normalized_paths,
            content_types=yaml_data.get("content_types", {}),
            special_collections=yaml_data.get("special_collections", {}),
            auto_tags=yaml_data.get("auto_tags", {}),
            metadata_prompt=yaml_data.get("metadata_prompt", {}),
            api_key=api_key,
            api_url=api_url
        )