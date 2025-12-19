###
# Knowledge Pipeline
# Copyright (c) 2025 [Felix Bois]
# 
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.
###

import os
import shutil
import logging
import json
import yaml
import re
from typing import Optional, Tuple

from src.config_loader import PipelineConfig
from src.utils.transcriber import WhisperEngine
from src.utils.llm_client import OpenWebUIClient
from src.utils.text_tools import TextProcessor

logger = logging.getLogger("Pipeline")

class KnowledgePipeline:
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.transcriber = WhisperEngine(config.whisper_model_size)
        self.llm = OpenWebUIClient(config)
        self.processor = TextProcessor(config)
        
        self.text_input_dir = config.paths.get('batch')
        if not self.text_input_dir or "_BATCH_SYNC" in self.text_input_dir:
            self.text_input_dir = os.path.join(config.paths['base'], "_INPUT_TEXT")

        for path_name, path_val in config.paths.items():
            if path_name != "base" and path_val:
                os.makedirs(path_val, exist_ok=True)
        os.makedirs(self.text_input_dir, exist_ok=True)

    def process_audio(self, filepath: str) -> Optional[str]:
        filename = os.path.basename(filepath)
        logger.info(f"🚀 Starting Audio Pipeline: {filename}")
        
        try:
            transcript_text = self.transcriber.transcribe(filepath)
            if not transcript_text:
                logger.warning("⚠️ Transcript empty. Aborting.")
                return None
        except Exception as e:
            logger.error(f"❌ Critical Transcription Failure: {e}")
            return None

        final_path = self._run_ingestion_pipeline(transcript_text, filename, filepath)
        if final_path:
            shutil.move(filepath, os.path.join(self.config.paths['archive'], filename))
        return final_path

    def process_text_file(self, filepath: str) -> Optional[str]:
        filename = os.path.basename(filepath)
        logger.info(f"📄 Processing Text Input: {filename}")
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if content.startswith('---'):
                return self._run_repair_pipeline(filepath, content)
            else:
                final_path = self._run_ingestion_pipeline(content, filename, filepath, is_text_file=True)
                if final_path:
                    try: os.remove(filepath)
                    except: pass
                return final_path      
        except Exception as e:
            logger.error(f"❌ Text Processing Error: {e}")
            return None

    def sync_existing_file(self, filepath: str):
        filename = os.path.basename(filepath)
        logger.info(f"🔄 Syncing Update: {filename}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            parts = content.split('---')
            if len(parts) < 3: return

            try: fm = yaml.safe_load(parts[1])
            except yaml.YAMLError: 
                logger.error("❌ Invalid YAML"); return

            entry_type = fm.get('type', 'journal_entry')
            tags = fm.get('tags', [])
            is_focus = fm.get('focus', False)
            
            success = self._sync_file(filepath, entry_type, tags, force_focus=is_focus)
            
            if not success:
                logger.warning(f"⚠️ Sync failed. Offloading to Input Folder for retry: {filename}")
                target = os.path.join(self.text_input_dir, filename)
                if os.path.normpath(filepath) != os.path.normpath(target):
                    shutil.copy2(filepath, target)
            
        except Exception as e:
            logger.error(f"❌ Sync Error: {e}")

    # =========================================================================
    # CORE PIPELINES
    # =========================================================================

    def _run_ingestion_pipeline(self, text: str, original_filename: str, source_path: str, is_text_file=False) -> Optional[str]:
        meta = self.processor.extract_metadata_from_text(text, source_path)
        entry_type = self.processor.determine_content_type(meta['clean_text'])
        tags = self.processor.generate_tags(meta['clean_text'], meta['spoken_tags'], entry_type)
        
        logger.info(f"🏷️  Classified as: {entry_type.upper()} | Tags: {tags}")
        logger.info("🧠 Generating Title & Summary...")
        ai_meta = self._enrich_content(meta['clean_text'])
        
        analysis_required = self.config.content_types.get(entry_type, {}).get("enable_analysis", False)
        analysis_content = ""
        if analysis_required:
            logger.info(f"🕵️ Running Analysis ({entry_type})...")
            analysis_content = self._run_analysis(entry_type, meta['clean_text'])
            
        type_config = self.config.content_types.get(entry_type, {})
        subfolder = type_config.get("target_subfolder", "Personal Diary")
        target_dir = os.path.join(self.config.paths['output'], subfolder)
        os.makedirs(target_dir, exist_ok=True)
        
        base_id = f"{meta['date']}-{entry_type}"
        counter = 1
        while True:
            final_file_id = f"{base_id}-{counter}"
            final_filename = f"{final_file_id}.md"
            final_path = os.path.join(target_dir, final_filename)
            if not os.path.exists(final_path): break
            counter += 1
            
        md_content = self._construct_markdown(
            final_file_id, meta, ai_meta, entry_type, tags, analysis_content, original_filename
        )
        
        with open(final_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        logger.info(f"💾 Saved Knowledge: {final_filename}")
        
        missing_metadata = (ai_meta.get('title') == "Untitled")
        missing_analysis = (analysis_required and not analysis_content)
        
        if missing_metadata or missing_analysis:
            reason = []
            if missing_metadata: reason.append("Missing Title")
            if missing_analysis: reason.append("Missing Analysis")
            logger.warning(f"🔄 Partial Failure ({', '.join(reason)}). Queuing in Input Folder.")
            
            if not is_text_file:
                shutil.copy2(final_path, os.path.join(self.text_input_dir, final_filename))
            
            return final_path 
        
        logger.info("☁️  Syncing...")
        self._sync_file(final_path, entry_type, tags)
        logger.info(f"✅ Ingestion Complete: {original_filename}")
        return final_path

    def _run_repair_pipeline(self, filepath: str, content: str) -> Optional[str]:
        filename = os.path.basename(filepath)
        logger.info(f"🔧 Repairing: {filename}")
        
        parts = content.split('---')
        if len(parts) < 3: return None
        frontmatter_str = parts[1]
        body_parts = parts[2].split('## Transcript')
        body_text = body_parts[-1].split('## Analysis')[0].strip() if len(body_parts) > 1 else parts[2].strip()

        try: fm = yaml.safe_load(frontmatter_str)
        except yaml.YAMLError: return None

        entry_type = fm.get('type', 'journal_entry')
        tags = fm.get('tags', [])
        current_title = fm.get('title', 'Untitled')
        file_changed = False

        if current_title in ["Untitled", None, "null"]:
            new_meta = self._enrich_content(body_text)
            
            if new_meta['title'] != 'Untitled':
                fm['title'] = new_meta['title']
                fm['summary'] = new_meta.get('summary', '')
                fm['emotions'] = new_meta.get('emotions', [])
                fm['characters'] = new_meta.get('characters', [])
                file_changed = True
            else:
                # --- FIX: Distinguish between "Bad Server" and "Bad Content" ---
                if not self.llm.check_health():
                     logger.warning("⚠️ Server offline, skipping repair.")
                     return filepath # Keep in queue
                else:
                     # Server is alive, but LLM failed to give title. Use Fallback.
                     logger.warning(f"⚠️ Could not generate title for {filename}. Using fallback.")
                     fm['title'] = f"Recovered Entry {fm.get('date', '')}".strip()
                     file_changed = True

        type_config = self.config.content_types.get(entry_type, {})
        analysis_required = type_config.get("enable_analysis", False)
        has_analysis = "## Analysis" in content
        new_analysis_section = ""

        if analysis_required and not has_analysis:
            analysis_text = self._run_analysis(entry_type, body_text)
            if analysis_text:
                new_analysis_section = f"\n\n## Analysis\n\n{analysis_text}"
                file_changed = True

        if file_changed:
            new_yaml = yaml.dump(fm, sort_keys=False, allow_unicode=True)
            new_content = f"---\n{new_yaml}---\n\n## Transcript\n\n{body_text}"
            if has_analysis:
                existing_analysis = parts[2].split('## Analysis')[-1]
                new_content += f"\n\n## Analysis{existing_analysis}"
            elif new_analysis_section:
                new_content += new_analysis_section
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            logger.info("💾 File Repaired.")

        # Sync
        success = self._sync_file(filepath, entry_type, tags, force_focus=fm.get('focus', False))
        
        is_fixed = (fm.get('title') != "Untitled") and (not analysis_required or has_analysis or new_analysis_section)
        
        if is_fixed and success:
            official_path = os.path.join(self.config.paths['output'], type_config.get("target_subfolder", "Personal Diary"), filename)
            try:
                shutil.copy2(filepath, official_path)
                os.remove(filepath)
                logger.info("✅ Repaired & Moved to Knowledge.")
                return official_path
            except Exception: pass
            
        return filepath

    def _enrich_content(self, text: str) -> dict:
        defaults = {"title": "Untitled", "language": "en", "emotions": [], "characters": [], "summary": ""}
        sys_prompt = self.config.metadata_prompt.get("system", "")
        user_prompt = f"{self.config.metadata_prompt.get('user', '')}\n\nTEXT:\n{text[:2500]}"
        response = self.llm.chat_completion(sys_prompt, user_prompt)
        if not response: return defaults
        try:
            clean = response.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean)
            if not data.get('title'): data['title'] = "Untitled"
            return {**defaults, **data}
        except: return defaults

    def _run_analysis(self, entry_type: str, text: str) -> str:
        type_cfg = self.config.content_types.get(entry_type)
        if not type_cfg: return ""
        return self.llm.chat_completion(type_cfg.get("system_prompt", ""), f"{type_cfg.get('user_prompt', '')}\n\nTRANSCRIPT:\n{text}")

    def _construct_markdown(self, file_id, meta, ai_meta, entry_type, tags, analysis, original_filename) -> str:
        # Get config for this type
        type_config = self.config.content_types.get(entry_type, {})
        
        # Prefer the "type_name" from YAML, fallback to the internal key (capitalized)
        display_type = type_config.get("type_name", entry_type.replace("_", " ").title())

        title = ai_meta.get('title', 'Untitled') or "Untitled"
        frontmatter = {
            "id": file_id,
            "language": ai_meta.get('language', 'en'),
            "title": title,
            "aliases": [original_filename],
            "date": meta['date'],
            "time": meta['time'],
            "type": display_type,
            "tags": tags,
            "emotions": ai_meta.get('emotions', []),
            "characters": ai_meta.get('characters', []),
            "summary": ai_meta.get('summary', '') or "",
            "related": "",
            "focus": False
        }
        yaml_str = yaml.dump(frontmatter, sort_keys=False, allow_unicode=True)
        md = f"---\n{yaml_str}---\n\n## Transcript\n\n{meta['clean_text']}"
        if analysis: md += f"\n\n## Analysis\n\n{analysis}"
        return md

    def _sync_file(self, filepath: str, entry_type: str, tags: list, force_focus: bool = False) -> bool:
        filename = os.path.basename(filepath)
        fid = self.llm.upload_file(filepath, filename)
        if not fid: return False 
        
        type_cfg = self.config.content_types.get(entry_type, {})
        if type_cfg.get("collection_id"): 
            self.llm.link_to_collection(fid, type_cfg["collection_id"])
        
        should_focus = force_focus or ("FOCUS" in tags)
        if should_focus and self.config.special_collections.get("focus_mode_id"):
             if self.llm.link_to_collection(fid, self.config.special_collections["focus_mode_id"]):
                 logger.info(f"🔥 Added to Focus Mode: {filename}")
        
        return True