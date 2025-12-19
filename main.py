###
# Knowledge Pipeline
# Copyright (c) 2025 [Felix Bois]
# 
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.
###

import time
import logging
import colorama
import sys
import threading
import os
import queue

colorama.init(autoreset=True)
print(colorama.Fore.YELLOW + "⏳ Initializing System... (Lazy Loading AI)")

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from src.config_loader import ConfigManager
from src.pipeline import KnowledgePipeline

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S',
    handlers=[logging.FileHandler("pipeline.log", encoding='utf-8'), logging.StreamHandler()]
)
logger = logging.getLogger("Main")

# --- SHARED STATE ---
job_queue = queue.Queue()
processing_files = set() 
lock = threading.Lock() 

# --- PERIODIC SCANNER (RETRY MECHANISM) ---
class PeriodicScanner:
    """
    Checks the Input Text folder every 60s for stranded files 
    (e.g., failed syncs) and requeues them.
    """
    def __init__(self, folder_path, interval=60):
        self.folder = folder_path
        self.interval = interval
        self.running = True
        threading.Thread(target=self._scan, daemon=True).start()

    def _scan(self):
        while self.running:
            time.sleep(self.interval)
            if not os.path.exists(self.folder): continue
            
            try:
                files = [f for f in os.listdir(self.folder) if f.lower().endswith(('.txt', '.md'))]
                if not files: continue

                # logger.debug(f"🔄 Scanner found {len(files)} potential retries.")
                
                for f in files:
                    filepath = os.path.join(self.folder, f)
                    
                    # Prevent race conditions: Don't add if currently being processed
                    with lock:
                        if filepath in processing_files: continue
                    
                    # Check if file is stable (not currently being written)
                    try:
                        if time.time() - os.path.getmtime(filepath) < 1.0: continue
                    except OSError: continue

                    logger.info(f"🔄 Retry Processing: {f}")
                    job_queue.put(('text', filepath))
            except Exception as e:
                logger.error(f"Scanner Error: {e}")

# --- DEBOUNCE MANAGER ---
class DebounceManager:
    def __init__(self, delay_seconds=10):
        self.delay = delay_seconds
        self.pending = {} 
        self.lock = threading.Lock()
        self.running = True
        threading.Thread(target=self._monitor, daemon=True).start()

    def schedule(self, filepath, task_type):
        with self.lock:
            self.pending[filepath] = (time.time() + self.delay, task_type)

    def cancel_task(self, filepath):
        with self.lock:
            if filepath in self.pending:
                del self.pending[filepath]

    def _monitor(self):
        while self.running:
            time.sleep(1)
            now = time.time()
            to_process = []
            
            with self.lock:
                for filepath, (execute_at, task_type) in list(self.pending.items()):
                    if now >= execute_at:
                        to_process.append((filepath, task_type))
                        del self.pending[filepath]
            
            for filepath, task_type in to_process:
                with lock:
                    if filepath in processing_files: continue
                logger.info(f"⏰ Debounce complete. Syncing: {os.path.basename(filepath)}")
                job_queue.put((task_type, filepath))

# --- WORKER ---
def worker(pipeline, debouncer):
    while True:
        task_type, filepath = job_queue.get()
        
        with lock:
            processing_files.add(filepath)
            
        try:
            if os.path.exists(filepath):
                time.sleep(0.5)
                created_file = None
                
                if task_type == 'audio':
                    created_file = pipeline.process_audio(filepath)
                elif task_type == 'text':
                    created_file = pipeline.process_text_file(filepath)
                elif task_type == 'sync_update':
                    pipeline.sync_existing_file(filepath)

                if created_file:
                    debouncer.cancel_task(created_file)

        except Exception as e:
            logger.error(f"❌ Worker Error: {e}")
        finally:
            time.sleep(1.0) 
            with lock:
                if filepath in processing_files:
                    processing_files.remove(filepath)
            job_queue.task_done()

# --- WATCHDOG HANDLERS ---
class AudioHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith(('.m4a', '.mp3', '.wav')):
            logger.info(f"🎤 Audio Detected: {os.path.basename(event.src_path)}")
            job_queue.put(('audio', event.src_path))
    def on_moved(self, event):
        if not event.is_directory and event.dest_path.lower().endswith(('.m4a', '.mp3', '.wav')):
            logger.info(f"🎤 Audio Detected: {os.path.basename(event.dest_path)}")
            job_queue.put(('audio', event.dest_path))

class InputTextHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith(('.txt', '.md')):
            logger.info(f"📄 Text Input: {os.path.basename(event.src_path)}")
            job_queue.put(('text', event.src_path))
    def on_moved(self, event):
        if not event.is_directory and event.dest_path.lower().endswith(('.txt', '.md')):
            logger.info(f"📄 Text Input: {os.path.basename(event.dest_path)}")
            job_queue.put(('text', event.dest_path))

class KnowledgeHandler(FileSystemEventHandler):
    def __init__(self, debouncer):
        self.debouncer = debouncer
    def _process(self, filepath):
        if not filepath.lower().endswith('.md'): return
        with lock:
            if filepath in processing_files: return
        self.debouncer.schedule(filepath, 'sync_update')
    def on_modified(self, event):
        if not event.is_directory: self._process(event.src_path)

def main():
    print(colorama.Fore.CYAN + """
    ========================================
       KNOWLEDGE PIPELINE | OBSIDIAN MODE
    ========================================
    """)
    
    try: config = ConfigManager().load_config()
    except Exception as e: logger.critical(f"Config Fail: {e}"); return

    pipeline = KnowledgePipeline(config)
    debouncer = DebounceManager(delay_seconds=15)
    
    # 1. Start Worker
    threading.Thread(target=worker, args=(pipeline, debouncer), daemon=True).start()
    
    # 2. Start Periodic Retry Scanner (New Feature)
    PeriodicScanner(config.paths['batch'], interval=60)

    # 3. Initial Scan
    if os.path.exists(config.paths['input']):
        files = [f for f in os.listdir(config.paths['input']) if f.lower().endswith(('.m4a', '.mp3', '.wav'))]
        for f in files: job_queue.put(('audio', os.path.join(config.paths['input'], f)))
    
    if os.path.exists(config.paths['batch']):
        files = [f for f in os.listdir(config.paths['batch']) if f.lower().endswith(('.txt', '.md'))]
        if files: print(colorama.Fore.MAGENTA + f"🔄 Found {len(files)} text items for retry.")
        for f in files: job_queue.put(('text', os.path.join(config.paths['batch'], f)))

    # 4. Start Watchdogs
    observer = Observer()
    observer.schedule(AudioHandler(), path=config.paths['input'], recursive=False)
    observer.schedule(InputTextHandler(), path=config.paths['batch'], recursive=False)
    observer.schedule(KnowledgeHandler(debouncer), path=config.paths['output'], recursive=True)
    
    print(colorama.Fore.GREEN + f"👁️  Watching Audio: {config.paths['input']}")
    print(colorama.Fore.GREEN + f"👁️  Watching Text:  {config.paths['batch']} (Auto-Retry)")
    print(colorama.Fore.MAGENTA + f"💎 Watching Vault: {config.paths['output']} (Rec)")
    
    observer.start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        debouncer.running = False
        observer.stop(); observer.join(); sys.exit(0)

if __name__ == "__main__":
    main()