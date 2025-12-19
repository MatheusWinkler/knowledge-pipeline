###
# Knowledge Pipeline
# Copyright (c) 2025 [Felix Bois]
# 
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.
###

import requests
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("LLMClient")

class OpenWebUIClient:
    def __init__(self, config):
        self.base_url = config.api_url
        self.api_key = config.api_key
        self.model = config.llm_model_id
        
        self.timeout = config.timeouts.get('llm_analysis', 300)
        if self.timeout is None: self.timeout = 300

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })

    def _handle_connection_error(self, e):
        """Helper to log clean errors without stack traces."""
        logger.error(f"⚠️ Open WebUI Unreachable: {self.base_url}")
        # logger.debug(f"Technical details: {e}") # Uncomment for debug

    def check_health(self) -> bool:
        try:
            resp = self.session.get(f"{self.base_url}/health", timeout=2)
            return resp.status_code == 200
        except Exception:
            return False

    def chat_completion(self, system_prompt: str, user_prompt: str) -> str:
        sys_content = system_prompt if system_prompt else ""
        user_content = user_prompt if user_prompt else ""

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": sys_content},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.3,
            "stream": False
        }
        
        try:
            url = f"{self.base_url}/api/chat/completions"
            resp = self.session.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            
            data = resp.json()
            if data is None: return ""
                
            if 'choices' in data and len(data['choices']) > 0:
                return data['choices'][0]['message']['content'].strip()
            return ""
            
        except requests.exceptions.ConnectionError as e:
            self._handle_connection_error(e)
            return ""
        except requests.exceptions.Timeout:
            logger.error(f"⚠️ LLM Timeout ({self.timeout}s).")
            return ""
        except Exception as e:
            logger.error(f"⚠️ LLM Request Failed: {e}")
            return ""

    def delete_file_by_name(self, filename: str) -> bool:
        list_url = f"{self.base_url}/api/v1/files/"
        try:
            resp = self.session.get(list_url, timeout=5)
            if resp.status_code != 200: return False
            
            files = resp.json()
            target_id = None
            for f in files:
                if f['filename'] == filename:
                    target_id = f['id']
                    break
            
            if target_id:
                del_url = f"{self.base_url}/api/v1/files/{target_id}"
                self.session.delete(del_url, timeout=5)
                logger.info(f"♻️  Deleted old version: {filename}")
                return True
            return False
        except requests.exceptions.ConnectionError as e:
            self._handle_connection_error(e)
            return False
        except Exception as e:
            logger.warning(f"⚠️ Error checking/deleting old file: {e}")
            return False

    def upload_file(self, filepath: str, filename: str) -> Optional[str]:
        # Attempt to delete first, but don't block upload if delete fails (unless server is down)
        if not self.delete_file_by_name(filename):
             # If delete failed due to connection, we probably shouldn't try upload
             pass 
        
        upload_url = f"{self.base_url}/api/v1/files/"
        try:
            headers = self.session.headers.copy()
            if 'Content-Type' in headers: del headers['Content-Type']
            
            with open(filepath, 'rb') as f:
                files = {'file': (filename, f)}
                resp = requests.post(upload_url, headers=headers, files=files, timeout=30)
            
            if resp.status_code == 200:
                return resp.json().get('id')
            else:
                logger.error(f"❌ Upload failed: {resp.text}")
                return None
        except requests.exceptions.ConnectionError as e:
            self._handle_connection_error(e)
            return None
        except Exception as e:
            logger.error(f"❌ Upload exception: {e}")
            return None

    def link_to_collection(self, file_id: str, collection_id: str) -> bool:
        if not collection_id: return False
        url = f"{self.base_url}/api/v1/knowledge/{collection_id}/file/add"
        payload = {"file_id": file_id}
        
        try:
            resp = self.session.post(url, json=payload, timeout=5)
            if resp.status_code == 200:
                logger.info(f"🔗 Linked to Collection: {collection_id}")
                return True
            if "Duplicate content" in resp.text: return True
            if "failed to extract enum MetadataValue" in resp.text: return True
            
            logger.warning(f"⚠️ Link warning: {resp.text}")
            return False
        except requests.exceptions.ConnectionError as e:
            self._handle_connection_error(e)
            return False
        except Exception as e:
            logger.error(f"❌ Link exception: {e}")
            return False