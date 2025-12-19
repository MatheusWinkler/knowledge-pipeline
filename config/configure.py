###
# Knowledge Pipeline
# Copyright (c) 2025 [Felix Bois]
# 
# Licensed under the MIT License.
# See LICENSE file in the project root for full license information.
###

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, scrolledtext
from ruamel.yaml import YAML
import os

# --- Configuration ---
CONFIG_FILE = "settings.yaml"
ENV_FILE = ".env"
ENV_EXAMPLE = ".env.example"

# Default fallback if file is missing/empty
DEFAULT_PATHS = {
    "base": "D:\\AI Ashram", 
    "input_folder": "_INPUT_AUDIO",
    "archive_folder": "_ARCHIVE_AUDIO",
    "input_text_folder": "_INPUT_TEXT",
    "knowledge_folder": "Knowledge"
}

class SettingsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Knowledge Pipeline - Configurator")
        self.root.geometry("1100x850")
        
        # Load Data
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.data = self.load_config()
        self.env_data = self.load_env()

        # Internal state for Content Types
        self.content_types_dict = self.data.get('content_types', {})
        self.current_selected_key = None

        # --- UI Layout & Tab Order ---
        self.tabs = ttk.Notebook(root)
        self.tabs.pack(expand=1, fill="both", padx=10, pady=5)

        # Create Frames
        self.tab_readme = ttk.Frame(self.tabs)
        self.tab_paths = ttk.Frame(self.tabs)
        self.tab_creds = ttk.Frame(self.tabs)
        self.tab_content = ttk.Frame(self.tabs)
        self.tab_ai = ttk.Frame(self.tabs)
        self.tab_system = ttk.Frame(self.tabs)

        # Add Tabs in Requested Order
        self.tabs.add(self.tab_readme, text='Readme & Instructions')   # 1
        self.tabs.add(self.tab_paths, text='Folders & Paths')          # 2
        self.tabs.add(self.tab_creds, text='Credentials')              # 3
        self.tabs.add(self.tab_content, text='Content Types')          # 4
        self.tabs.add(self.tab_ai, text='AI Models')                   # 5
        self.tabs.add(self.tab_system, text='System & Timeouts')       # 6

        # Build Tabs
        self.build_readme_tab()
        self.build_paths_tab()
        self.build_credentials_tab()
        self.build_content_types_tab() 
        self.build_ai_tab()
        self.build_system_tab()

        # --- Footer ---
        frame_footer = ttk.Frame(root)
        frame_footer.pack(fill=tk.X, pady=10)
        ttk.Separator(frame_footer, orient='horizontal').pack(fill=tk.X)
        btn_save = ttk.Button(frame_footer, text="SAVE ALL SETTINGS", command=self.save_all)
        btn_save.pack(pady=10, ipadx=30, ipady=8)

    # =========================================================================
    # CORE LOGIC & LOADING
    # =========================================================================

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            return {}
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return self.yaml.load(f)

    def load_env(self):
        vals = {"API_KEY": "", "OPEN_WEBUI_URL": ""}
        target_file = ENV_FILE if os.path.exists(ENV_FILE) else ENV_EXAMPLE
        
        if os.path.exists(target_file):
            with open(target_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("API_KEY="):
                        vals["API_KEY"] = line.split("=", 1)[1].strip('"').strip("'")
                    elif line.startswith("OPEN_WEBUI_URL="):
                        vals["OPEN_WEBUI_URL"] = line.split("=", 1)[1].strip('"').strip("'")
        return vals

    def get_comment(self, keys):
        """Extracts comments from YAML to use as instructions."""
        try:
            ref = self.data
            # For root keys, we don't traverse
            if len(keys) == 1:
                target_key = keys[0]
            else:
                for k in keys[:-1]:
                    ref = ref[k]
                target_key = keys[-1]
            
            comments = ref.ca.items.get(target_key, None)
            if comments:
                text = ""
                # Comments often come in parts (before, inline), combine them
                if len(comments) > 1 and comments[1]:
                    text += comments[1].value.strip("# \n") + "\n"
                if len(comments) > 2 and comments[2]:
                    text += comments[2].value.strip("# \n")
                return text.strip()
        except:
            return None
        return None

    def get_val(self, keys, default=""):
        ref = self.data
        try:
            for k in keys:
                ref = ref[k]
            return ref
        except (KeyError, TypeError):
            return default

    def set_val(self, keys, value):
        ref = self.data
        for k in keys[:-1]:
            ref = ref.setdefault(k, {})
        current = ref.get(keys[-1])
        if isinstance(current, int) and str(value).isdigit():
             ref[keys[-1]] = int(value)
        elif isinstance(current, float):
             try: ref[keys[-1]] = float(value)
             except: ref[keys[-1]] = value
        else:
             ref[keys[-1]] = value

    # =========================================================================
    # 1. README TAB (UPDATED)
    # =========================================================================
    def build_readme_tab(self):
        frame = ttk.Frame(self.tab_readme)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        lbl = ttk.Label(frame, text="Configuration Guide", font=("Segoe UI", 14, "bold"))
        lbl.pack(anchor=tk.W, pady=(0,10))

        # Read-only text area
        txt = scrolledtext.ScrolledText(frame, wrap=tk.WORD, width=100, height=30, font=("Consolas", 10))
        txt.pack(fill=tk.BOTH, expand=True)

        # Helper to append sections
        def add_section(title, content):
            txt.insert(tk.END, f"{title}\n", "header")
            txt.insert(tk.END, f"{'-'*len(title)}\n")
            txt.insert(tk.END, f"{content}\n\n")

        txt.tag_config("header", foreground="blue", font=("Consolas", 11, "bold"))
        txt.tag_config("warning", foreground="red", font=("Consolas", 10, "bold"))

        # --- GENERATE CONTENT ---
        intro = (
            "Welcome to the Setup Tool.\n"
            "Use the tabs above to configure your application.\n"
            "This guide is auto-generated from the comments in your settings files."
        )
        add_section("GENERAL INFO", intro)

        # 1. Credentials
        creds_info = (
            "API KEY: Found in Open WebUI > Settings > API Keys.\n"
            "URL: The full URL to your instance (e.g., http://localhost:3000).\n"
            "WARNING: Never share these keys."
        )
        add_section("CREDENTIALS", creds_info)

        # 2. Paths
        paths_info = "Base Path: " + str(self.get_comment(["paths", "base"]) or "Root folder for operations.") + "\n"
        add_section("FOLDERS & PATHS", paths_info)

        # 3. Content Types (Updated Example)
        ct_info = (
            "Content Types define how files are processed based on keywords.\n"
            "You can add new types, edit prompts, and set a 'Default' type for fallback.\n\n"
            "EXAMPLE (Dream Report):\n"
            "  * Logic: If keywords ['dream', 'traum'] appear in the first 100 words.\n"
            "  * Output: Moves file to 'Knowledge/Dream Journal'.\n"
            "  * Sync: Updates Open WebUI Collection ID.\n"
            "  * AI Persona: Uses 'Five Star Method' for analysis."
        )
        add_section("CONTENT TYPES", ct_info)

        # 4. AI Models (Updated Warning)
        ai_info = ""
        ai_info += f"Whisper: {self.get_comment(['whisper_model_size']) or 'Size of audio model'}\n"
        ai_info += f"LLM ID: {self.get_comment(['llm_model_id']) or 'Model tag from Open WebUI'}\n\n"
        
        txt.insert(tk.END, "AI MODELS\n", "header")
        txt.insert(tk.END, "---------\n")
        txt.insert(tk.END, ai_info)
        txt.insert(tk.END, "CRITICAL WARNING: The fields of the JSON object (title, language, etc.) are fixed in the application code. DO NOT change the keys in the metadata prompts, only the instructions for how to fill them.\n\n", "warning")

        # 5. System (Updated Location)
        sys_desc = self.get_comment(['timeouts']) or "Prevent the pipeline from hanging on slow operations."
        sys_info = f"Description: {sys_desc}\n\n"
        sys_info += f"Analysis Timeout: {self.get_comment(['timeouts', 'llm_analysis']) or 'Seconds to wait'}\n"
        sys_info += f"File Stability: {self.get_comment(['timeouts', 'file_stability']) or 'Wait time for upload'}"
        add_section("SYSTEM & TIMEOUTS", sys_info)

        txt.configure(state='disabled') # Make read-only

    # =========================================================================
    # 2. FOLDERS & PATHS
    # =========================================================================
    def build_paths_tab(self):
        frame_base = ttk.LabelFrame(self.tab_paths, text="Base Directory")
        frame_base.pack(fill=tk.X, padx=10, pady=10)
        
        self.base_path_var = tk.StringVar(value=self.get_val(["paths", "base"], DEFAULT_PATHS["base"]))
        entry_base = ttk.Entry(frame_base, textvariable=self.base_path_var)
        entry_base.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        
        ttk.Button(frame_base, text="Browse...", command=self.browse_base_folder).pack(side=tk.RIGHT, padx=5)
        
        frame_subs = ttk.LabelFrame(self.tab_paths, text="Subfolders")
        frame_subs.pack(fill=tk.X, padx=10, pady=5)

        self.path_fields = []
        path_configs = [
            ("Input Audio:", "input_folder"),
            ("Archive Audio:", "archive_folder"),
            ("Input Text:", "input_text_folder"),
            ("Knowledge Output:", "knowledge_folder")
        ]

        for label, key in path_configs:
            val = self.get_val(["paths", key], DEFAULT_PATHS.get(key, ""))
            self.create_simple_row(frame_subs, label, ["paths", key], val, store_list=self.path_fields)

    def browse_base_folder(self):
        d = filedialog.askdirectory()
        if d:
            d = d.replace("/", "\\")
            self.base_path_var.set(d)

    # =========================================================================
    # 3. CREDENTIALS
    # =========================================================================
    def build_credentials_tab(self):
        frame = ttk.Frame(self.tab_creds)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        ttk.Label(frame, text="Security Credentials (.env)", font=("Segoe UI", 12, "bold")).pack(anchor=tk.W, pady=(0, 15))

        ttk.Label(frame, text="Open WebUI API Key:").pack(anchor=tk.W)
        self.var_api_key = tk.StringVar(value=self.env_data.get("API_KEY", ""))
        e_key = ttk.Entry(frame, textvariable=self.var_api_key, width=70)
        e_key.pack(anchor=tk.W, pady=(5, 15))

        ttk.Label(frame, text="Open WebUI URL:").pack(anchor=tk.W)
        self.var_url = tk.StringVar(value=self.env_data.get("OPEN_WEBUI_URL", ""))
        e_url = ttk.Entry(frame, textvariable=self.var_url, width=70)
        e_url.pack(anchor=tk.W, pady=(5, 15))

    # =========================================================================
    # 4. CONTENT TYPES
    # =========================================================================
    def build_content_types_tab(self):
        frame_top = ttk.Frame(self.tab_content)
        frame_top.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(frame_top, text="Focus Mode Collection ID:").pack(side=tk.LEFT)
        self.focus_mode_var = tk.StringVar(value=self.get_val(["special_collections", "focus_mode_id"]))
        e_focus = ttk.Entry(frame_top, textvariable=self.focus_mode_var, width=40)
        e_focus.pack(side=tk.LEFT, padx=10)

        paned = ttk.PanedWindow(self.tab_content, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        frame_left = ttk.Frame(paned, width=250)
        paned.add(frame_left, weight=1)

        ttk.Label(frame_left, text="Defined Types:").pack(anchor=tk.W)
        self.type_listbox = tk.Listbox(frame_left, exportselection=False, width=30)
        self.type_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        self.type_listbox.bind('<<ListboxSelect>>', self.on_type_selected)

        btn_frame = ttk.Frame(frame_left)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="+ Add New", command=self.add_new_type).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="- Delete", command=self.delete_type).pack(fill=tk.X, pady=2)

        frame_right = ttk.LabelFrame(paned, text="Edit Content Type")
        paned.add(frame_right, weight=3)

        canvas = tk.Canvas(frame_right)
        scrollbar = ttk.Scrollbar(frame_right, orient="vertical", command=canvas.yview)
        self.editor_frame = ttk.Frame(canvas)
        self.editor_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.editor_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.ct_vars = {} 
        row = 0
        
        ttk.Label(self.editor_frame, text="Internal Key (ID):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        self.lbl_current_id = ttk.Label(self.editor_frame, text="-", font=("Segoe UI", 9, "bold"))
        self.lbl_current_id.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        
        row += 1; self.create_editor_entry(row, "Type Name:", "type_name")
        row += 1; self.create_editor_entry(row, "Target Subfolder:", "target_subfolder")
        row += 1; self.create_editor_entry(row, "Collection UUID:", "collection_id")
        row += 1; self.create_editor_entry(row, "Keywords (csv):", "detection_keywords")

        row += 1
        flags_frame = ttk.Frame(self.editor_frame)
        flags_frame.grid(row=row, column=1, sticky=tk.W, padx=5, pady=10)
        
        self.ct_vars["enable_analysis"] = tk.BooleanVar()
        self.ct_vars["is_default"] = tk.BooleanVar()

        cb_ana = ttk.Checkbutton(flags_frame, text="Enable LLM Analysis", variable=self.ct_vars["enable_analysis"])
        cb_ana.pack(side=tk.LEFT, padx=(0, 20))
        
        cb_def = ttk.Checkbutton(flags_frame, text="Is Default Type (Fallback)", variable=self.ct_vars["is_default"])
        cb_def.pack(side=tk.LEFT)

        row += 1
        ttk.Label(self.editor_frame, text="System Prompt:").grid(row=row, column=0, sticky=tk.NW, padx=5, pady=5)
        self.txt_system = scrolledtext.ScrolledText(self.editor_frame, height=5, width=50)
        self.txt_system.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)

        row += 1
        ttk.Label(self.editor_frame, text="User Prompt:").grid(row=row, column=0, sticky=tk.NW, padx=5, pady=5)
        self.txt_user = scrolledtext.ScrolledText(self.editor_frame, height=5, width=50)
        self.txt_user.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)

        row += 1
        btn_box = ttk.Frame(self.editor_frame)
        btn_box.grid(row=row, column=1, sticky=tk.W, pady=20)
        ttk.Button(btn_box, text="Update / Apply", command=self.update_current_type).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_box, text="Save as New Type...", command=self.save_as_new_type).pack(side=tk.LEFT, padx=5)

        self.refresh_type_list()

    def create_editor_entry(self, row, label, key):
        ttk.Label(self.editor_frame, text=label).grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        var = tk.StringVar()
        self.ct_vars[key] = var
        entry = ttk.Entry(self.editor_frame, textvariable=var, width=50)
        entry.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)

    def refresh_type_list(self):
        self.type_listbox.delete(0, tk.END)
        for key, val in self.content_types_dict.items():
            display_text = key
            if val.get('is_default', False):
                display_text += " (default)"
            self.type_listbox.insert(tk.END, display_text)

    def on_type_selected(self, event):
        selection = self.type_listbox.curselection()
        if not selection: return
        
        display_text = self.type_listbox.get(selection[0])
        key = display_text.split(" (")[0]
        
        self.current_selected_key = key
        data = self.content_types_dict[key]

        self.lbl_current_id.config(text=key)
        self.ct_vars["type_name"].set(data.get("type_name", ""))
        self.ct_vars["target_subfolder"].set(data.get("target_subfolder", ""))
        self.ct_vars["collection_id"].set(data.get("collection_id", ""))
        self.ct_vars["enable_analysis"].set(data.get("enable_analysis", False))
        self.ct_vars["is_default"].set(data.get("is_default", False))
        
        kw = data.get("detection_keywords", [])
        self.ct_vars["detection_keywords"].set(", ".join(kw) if isinstance(kw, list) else str(kw))

        self.txt_system.delete("1.0", tk.END); self.txt_system.insert("1.0", data.get("system_prompt", ""))
        self.txt_user.delete("1.0", tk.END); self.txt_user.insert("1.0", data.get("user_prompt", ""))

    def ensure_single_default(self, active_key):
        if self.ct_vars["is_default"].get():
            for k in self.content_types_dict:
                if k != active_key and "is_default" in self.content_types_dict[k]:
                    self.content_types_dict[k]["is_default"] = False

    def get_data_from_editor(self):
        kw_str = self.ct_vars["detection_keywords"].get()
        kw_list = [x.strip() for x in kw_str.split(",") if x.strip()]
        
        return {
            "type_name": self.ct_vars["type_name"].get(),
            "target_subfolder": self.ct_vars["target_subfolder"].get(),
            "collection_id": self.ct_vars["collection_id"].get(),
            "detection_keywords": kw_list,
            "enable_analysis": self.ct_vars["enable_analysis"].get(),
            "is_default": self.ct_vars["is_default"].get(),
            "system_prompt": self.txt_system.get("1.0", tk.END).strip(),
            "user_prompt": self.txt_user.get("1.0", tk.END).strip(),
        }

    def update_current_type(self):
        if not self.current_selected_key: return
        self.ensure_single_default(self.current_selected_key)
        new_data = self.get_data_from_editor()
        if not new_data['is_default']:
            if 'is_default' in new_data: del new_data['is_default']
        
        self.content_types_dict[self.current_selected_key].update(new_data)
        if not self.ct_vars["is_default"].get() and "is_default" in self.content_types_dict[self.current_selected_key]:
             del self.content_types_dict[self.current_selected_key]["is_default"]

        self.refresh_type_list()
        try:
            items = self.type_listbox.get(0, tk.END)
            idx = [i for i, x in enumerate(items) if x.startswith(self.current_selected_key)][0]
            self.type_listbox.selection_set(idx)
        except: pass
        messagebox.showinfo("Updated", f"Updated '{self.current_selected_key}'. Don't forget to Save All.")

    def add_new_type(self):
        new_key = simpledialog.askstring("New Type", "Enter internal ID:")
        if new_key:
            if new_key in self.content_types_dict:
                messagebox.showerror("Error", "Key exists!")
                return
            self.content_types_dict[new_key] = {
                "type_name": "New Type",
                "detection_keywords": [],
                "target_subfolder": "New",
                "enable_analysis": True,
                "system_prompt": "",
                "user_prompt": ""
            }
            self.refresh_type_list()

    def delete_type(self):
        if not self.current_selected_key: return
        if messagebox.askyesno("Confirm", f"Delete '{self.current_selected_key}'?"):
            del self.content_types_dict[self.current_selected_key]
            self.current_selected_key = None
            self.refresh_type_list()
            self.lbl_current_id.config(text="-")

    def save_as_new_type(self):
        new_key = simpledialog.askstring("Save As", "Enter new unique ID:")
        if new_key:
            if new_key in self.content_types_dict:
                messagebox.showerror("Error", "Key exists!")
                return
            self.ensure_single_default(new_key) 
            data = self.get_data_from_editor()
            self.content_types_dict[new_key] = data
            self.refresh_type_list()

    # =========================================================================
    # 5. AI MODELS
    # =========================================================================
    def build_ai_tab(self):
        self.ai_fields = []
        
        frame_models = ttk.LabelFrame(self.tab_ai, text="Model Configuration")
        frame_models.pack(fill=tk.X, padx=10, pady=10)
        
        self.create_simple_row(frame_models, "Whisper Model Size:", "whisper_model_size", 
                               self.get_val(["whisper_model_size"]), store_list=self.ai_fields)
        
        self.create_simple_row(frame_models, "LLM Model ID:", "llm_model_id", 
                               self.get_val(["llm_model_id"]), store_list=self.ai_fields)

        frame_meta = ttk.LabelFrame(self.tab_ai, text="Metadata Extraction Prompts")
        frame_meta.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ttk.Label(frame_meta, text="Metadata System Prompt (JSON rules):").pack(anchor=tk.W, padx=5, pady=(5,0))
        self.txt_meta_sys = scrolledtext.ScrolledText(frame_meta, height=6)
        self.txt_meta_sys.pack(fill=tk.X, padx=5, pady=(0,10))
        self.txt_meta_sys.insert("1.0", self.get_val(["metadata_prompt", "system"], ""))
        
        ttk.Label(frame_meta, text="Metadata User Prompt (Fields to extract):").pack(anchor=tk.W, padx=5, pady=(0,0))
        self.txt_meta_user = scrolledtext.ScrolledText(frame_meta, height=8)
        self.txt_meta_user.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0,5))
        self.txt_meta_user.insert("1.0", self.get_val(["metadata_prompt", "user"], ""))

    # =========================================================================
    # 6. SYSTEM & TIMEOUTS
    # =========================================================================
    def build_system_tab(self):
        self.system_fields = []
        frame_time = ttk.LabelFrame(self.tab_system, text="Timeouts (Seconds)")
        frame_time.pack(fill=tk.X, padx=10, pady=10)

        timeouts = [
            ("LLM Analysis:", "llm_analysis"),
            ("File Stability:", "file_stability"),
            ("HTTP Connect:", "http_connect"),
            ("HTTP Read:", "http_read")
        ]
        for label, key in timeouts:
            val = self.get_val(["timeouts", key], 0)
            self.create_simple_row(frame_time, label, ["timeouts", key], val, store_list=self.system_fields)

    # =========================================================================
    # HELPERS & SAVE
    # =========================================================================
    def create_simple_row(self, parent, label, key_path_or_str, initial_val, store_list=None):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=5)
        ttk.Label(frame, text=label, width=20).pack(side=tk.LEFT)
        
        var = tk.StringVar(value=str(initial_val))
        ttk.Entry(frame, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        if store_list is not None:
            store_list.append((key_path_or_str, var))

    def save_env_file(self):
        new_key = self.var_api_key.get()
        new_url = self.var_url.get()
        output_lines = []
        
        src_file = None
        if os.path.exists(ENV_EXAMPLE): src_file = ENV_EXAMPLE
        elif os.path.exists(ENV_FILE): src_file = ENV_FILE
        
        if src_file:
            with open(src_file, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped.startswith("API_KEY="):
                        output_lines.append(f'API_KEY="{new_key}"\n')
                    elif stripped.startswith("OPEN_WEBUI_URL="):
                        output_lines.append(f'OPEN_WEBUI_URL="{new_url}"\n')
                    else:
                        output_lines.append(line)
        else:
            output_lines.append(f'API_KEY="{new_key}"\n')
            output_lines.append(f'OPEN_WEBUI_URL="{new_url}"\n')

        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.writelines(output_lines)

    def save_all(self):
        try:
            # 1. Save Settings.yaml
            base_val = self.base_path_var.get().replace("/", "\\")
            self.set_val(["paths", "base"], base_val)

            all_simple = self.path_fields + self.system_fields + self.ai_fields
            for key_ref, var in all_simple:
                if isinstance(key_ref, list): self.set_val(key_ref, var.get())
                else: self.data[key_ref] = var.get()

            # Metadata Prompts
            self.set_val(["metadata_prompt", "system"], self.txt_meta_sys.get("1.0", tk.END).strip())
            self.set_val(["metadata_prompt", "user"], self.txt_meta_user.get("1.0", tk.END).strip())

            self.set_val(["special_collections", "focus_mode_id"], self.focus_mode_var.get())
            self.data['content_types'] = self.content_types_dict

            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                self.yaml.dump(self.data, f)

            # 2. Save .env
            self.save_env_file()
            
            messagebox.showinfo("Success", "Configuration & Credentials saved successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save:\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    
    app = SettingsApp(root)
    root.mainloop()