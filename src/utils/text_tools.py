###
# Knowledge Pipeline
# Copyright (c) 2025 [Felix Bois]
# 
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.
###

import re
import os
import datetime
import dateparser
import logging
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger("TextTools")

class TextProcessor:
    """
    Handles regex operations, date extraction, tag parsing, and content type detection.
    """
    def __init__(self, config):
        self.config = config

    def _get_date_from_filename(self, filepath: str) -> Tuple[Optional[str], Optional[str]]:
        filename = os.path.basename(filepath)
        # Match: YYMMDD_HHMMss
        match_short = re.search(r'(\d{2})(\d{2})(\d{2})_(\d{2})(\d{2})\d{2}', filename)
        if match_short:
            year, month, day, hour, minute = match_short.groups()
            return f"20{year}-{month}-{day}", f"{hour}:{minute}"
        # Match: YYYYMMDD_HHMMss
        match_long = re.search(r'(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})\d{2}', filename)
        if match_long:
            year, month, day, hour, minute = match_long.groups()
            return f"{year}-{month}-{day}", f"{hour}:{minute}"
        return None, None

    def _extract_and_remove_spoken_tags(self, text: str) -> Tuple[List[str], str]:
        if not text: return [], ""
        
        # --- 1. CONFIGURABLE SEARCH WINDOW ---
        # Get window size from config, default to 400 if missing or invalid
        window_size = getattr(self.config, 'tag_search_window', 400)
        if not isinstance(window_size, int) or window_size < 10:
            window_size = 400

        # Look at the end of the text based on the configured window
        search_window = text[-window_size:] if len(text) > window_size else text
        
        # --- 2. DYNAMIC KEYWORDS ---
        # Get triggers from config, with a runtime safety fallback
        triggers = getattr(self.config, 'tag_triggers', [])
        if not triggers: 
            triggers = ["Tag", "Tags"] 
        
        # Escape keywords to prevent regex injection (e.g. if user adds "C++")
        joined_triggers = "|".join([re.escape(t) for t in triggers])
        
        # --- 3. BUILD REGEX ---
        # (?i)          -> Case insensitive
        # (?:           -> Non-capturing group for the trigger logic
        #   \b          -> Word boundary
        #   (?:...)     -> Group for the user's dynamic list
        #   \b          -> Word boundary
        #   [:\s\.,]+   -> Followed by colon, space, dot, or comma
        #   |           -> OR
        #   [#]         -> The literal '#' symbol (hardcoded common shorthand)
        # )
        # (.*)$         -> Capture everything else until end of string (Group 1)
        pattern = fr'(?i)(?:\b(?:{joined_triggers})\b[:\s\.,]+|[#])(.*)$'
        
        match = re.search(pattern, search_window)
        
        spoken_tags = []
        clean_text = text
        
        if match:
            # Group 1 contains the text AFTER the trigger (e.g. "tag1, #tag2")
            raw_tag_string = match.group(1).strip()
            # Remove trailing punctuation (dots/exclamations at very end of file)
            raw_tag_string = re.sub(r'[\.\!\?]+$', '', raw_tag_string)
            
            if raw_tag_string:
                # Split by comma or space
                words = re.split(r'[\s,]+', raw_tag_string)
                for w in words:
                    # Clean non-word chars. 
                    # \w includes [a-zA-Z0-9_]. We also keep hyphens [-].
                    # This implicitly removes '#' from '#tag1' -> 'tag1'
                    clean_w = re.sub(r'[^\w\-]', '', w)
                    if clean_w: spoken_tags.append(clean_w)
            
            # Remove the detected tag section from the original text
            match_start_relative = search_window.find(match.group(0))
            if match_start_relative != -1:
                cut_point = (len(text) - len(search_window)) + match_start_relative
                clean_text = text[:cut_point].rstrip(' ,.')

        return spoken_tags, clean_text

    def extract_metadata_from_text(self, text: str, filepath: str) -> Dict[str, Any]:
        # 1. Clean Spoken Tags
        found_tags, cleaned_text = self._extract_and_remove_spoken_tags(text)
        
        metadata = {
            "date": None, 
            "time": None, 
            "clean_text": cleaned_text,
            "spoken_tags": found_tags
        }
        
        # --- 2. EXTRACT SPOKEN DATE ---
        match_keyword_text = re.search(r'(?:Datum|Date)[:\s]+(\d{1,2}\.?\s+[a-zA-ZäöüÄÖÜ]{3,9}\s+\d{2,4})', metadata['clean_text'], re.IGNORECASE)
        match_keyword_num = re.search(r'(?:Datum|Date)[:\s]+(\d{1,4}[-\.]\d{1,2}[-\.]\d{2,4})', metadata['clean_text'], re.IGNORECASE)
        match_direct_text = re.search(r'^\s*(\d{1,2}\.?\s+[a-zA-ZäöüÄÖÜ]{3,9}\s+\d{2,4})', metadata['clean_text'][:60])
        match_direct_num = re.search(r'^\s*(\d{1,2}\s*[\.-]\s*\d{1,2}\s*[\.-]\s*\d{2,4})', metadata['clean_text'][:60])

        found_date_str = None
        match_to_remove = None

        if match_keyword_text:
            found_date_str = match_keyword_text.group(1)
            match_to_remove = match_keyword_text.group(0)
        elif match_keyword_num:
            found_date_str = match_keyword_num.group(1)
            match_to_remove = match_keyword_num.group(0)
        elif match_direct_text:
            found_date_str = match_direct_text.group(1)
            match_to_remove = match_direct_text.group(0)
        elif match_direct_num:
            found_date_str = match_direct_num.group(1)
            match_to_remove = match_direct_num.group(0)

        if found_date_str:
            parsed = dateparser.parse(found_date_str, languages=['de', 'en'], settings={'DATE_ORDER': 'DMY'})
            if parsed:
                metadata['date'] = parsed.strftime('%Y-%m-%d')
                if match_to_remove:
                    metadata['clean_text'] = metadata['clean_text'].replace(match_to_remove, '', 1).strip()
                    metadata['clean_text'] = re.sub(r'^[\s\.,;:\-]+', '', metadata['clean_text'])

        # --- 3. EXTRACT SPOKEN TIME ---
        time_regex = r'(\d{1,2})\s*(?:[:\.]|Uhr)\s*(\d{2})(?:\s*(?:Uhr|h|am|pm))?'
        match_keyword = re.search(r'(?:Zeit|Time|Uhrzeit)[:\s]*' + time_regex, metadata['clean_text'], re.IGNORECASE)
        match_direct = re.search(r'^\s*' + time_regex, metadata['clean_text'][:30], re.IGNORECASE)

        match_time = None
        if match_keyword: match_time = match_keyword
        elif match_direct: match_time = match_direct
            
        if match_time:
            hour = match_time.group(1)
            minute = match_time.group(2)
            metadata['time'] = f"{hour.zfill(2)}:{minute.zfill(2)}"
            metadata['clean_text'] = metadata['clean_text'].replace(match_time.group(0), '', 1).strip()

        # Final Cleanup
        metadata['clean_text'] = re.sub(r'^[\s\.,;:\-]+', '', metadata['clean_text'])
        if metadata['clean_text']:
            metadata['clean_text'] = metadata['clean_text'][0].upper() + metadata['clean_text'][1:]

        # --- 4. FALLBACKS ---
        fn_date, fn_time = self._get_date_from_filename(filepath)
        if not metadata['date'] and fn_date: metadata['date'] = fn_date
        if not metadata['time'] and fn_time: metadata['time'] = fn_time

        if not metadata['date']:
            try:
                dt_obj = datetime.datetime.fromtimestamp(os.path.getctime(filepath))
                metadata['date'] = dt_obj.strftime('%Y-%m-%d')
            except Exception:
                metadata['date'] = datetime.datetime.now().strftime('%Y-%m-%d')
        if not metadata['time']:
            metadata['time'] = "unknown"
            
        return metadata

    def determine_content_type(self, text: str) -> str:
        intro_text = " ".join(text[:500].split()[:100]).lower()
        default_type = None

        # Iterate over all types defined in YAML
        for type_key, type_data in self.config.content_types.items():
            
            # 1. Identify the default fallback from config
            if type_data.get('is_default') is True:
                default_type = type_key
            
            # 2. Check Keywords
            keywords = type_data.get('detection_keywords', [])
            if keywords and any(k.lower() in intro_text for k in keywords):
                return type_key

        # If no keywords matched, return the type marked 'is_default'
        if default_type:
            return default_type
        
        # Safety fallback if YAML is broken (use first available key or 'unknown')
        return list(self.config.content_types.keys())[0] if self.config.content_types else "unknown"

    def generate_tags(self, text: str, spoken_tags: List[str], entry_type: str) -> List[str]:
        """
        Pure pass-through of spoken tags.
        """
        final_tags = []
        for t in spoken_tags:
            if not t.strip(): continue
            final_tags.append(t.strip())
        
        return sorted(list(set(final_tags)))