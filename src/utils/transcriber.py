###
# Knowledge Pipeline
# Copyright (c) 2025 [Felix Bois]
# 
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.
###

import logging
import os
# REMOVED: import whisper (This caused the hang)

logger = logging.getLogger("Transcriber")

class WhisperEngine:
    def __init__(self, model_size: str):
        self.model_size = model_size
        self.model = None
        
    def load_model(self):
        """Loads the model into memory if not already loaded."""
        if not self.model:
            logger.info(f"🎧 Loading Whisper model: '{self.model_size}'...")
            try:
                # LAZY IMPORT: Only load heavy libraries here
                import whisper 
                
                self.model = whisper.load_model(self.model_size)
                logger.info("✅ Whisper model loaded.")
            except Exception as e:
                logger.error(f"❌ Failed to load Whisper: {e}")
                raise e

    def transcribe(self, filepath: str) -> str:
        """
        Transcribes the audio file.
        Returns: Full text string.
        """
        if not self.model:
            self.load_model()
            
        logger.info(f"🎤 Transcribing: {os.path.basename(filepath)}")
        try:
            # fp16=False prevents warnings on some CPUs
            result = self.model.transcribe(filepath, beam_size=5, fp16=False)
            # Handle cases where result might be empty
            if not result or 'text' not in result:
                return ""
            return result['text'].strip()
        except Exception as e:
            logger.error(f"❌ Transcription error: {e}")
            return ""