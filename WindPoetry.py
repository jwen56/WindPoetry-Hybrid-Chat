
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, simpledialog
import requests
import threading
import json
from pathlib import Path
from datetime import datetime
import re
from GPTSoVITSTTSEngine import GPTSoVITSTTSEngine
import os
import json
import time
# 插入位置映射表
INSERT_POSITIONS = [
    "无 (已禁用)",
    "在故事字符串/提示词管理器中",
    "作者注的顶部",
    "作者注的底部",
    "聊天的特定深度"
]
class WindPoetry:
    def __init__(self, root):
        self.root = root
        self.root.title("风之诗篇 v2.8")
        self.root.geometry("1350x900")
        self.root.configure(bg="#f5f5f5")
        
        self.config_data = {}
        self.module_controls = [] 
        self.preset_data_list = []
        self.chat_history = []
        # 本地聊天持久化配置
        self.chat_dir = "chat_history"
        self.current_chat = None  # 当前聊天会话名字
        os.makedirs(self.chat_dir, exist_ok=True)
        # 如果已有会话文件，默认使用最近的一个；否则创建一个临时会话
        try:
            existing = [f for f in os.listdir(self.chat_dir) if f.endswith('.json')]
            if existing:
                existing = sorted(existing, key=lambda p: os.path.getmtime(os.path.join(self.chat_dir, p)), reverse=True)
                self.current_chat = os.path.splitext(existing[0])[0]
            else:
                default_name = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                self.current_chat = default_name
                path = os.path.join(self.chat_dir, f"{self.current_chat}.json")
                payload = {"name": self.current_chat, "created_at": datetime.now().isoformat(), "last_modified": datetime.now().isoformat(), "messages": []}
                try:
                    with open(path, 'w', encoding='utf-8') as f:
                        json.dump(payload, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass
        except Exception:
            self.current_chat = None
        self.tts_engine = None  # TTS引擎实例
        self.tts_enabled = False
        self.available_models = []  # 动态获取的模型列表
        self.user_dir = "profiles/users"
        self.char_dir = "profiles/personas"
        os.makedirs(self.user_dir, exist_ok=True)
        os.makedirs(self.char_dir, exist_ok=True)
        
        # 初始化正则规则列表
        self.regex_rules_list = []
        self.regex_rules_data = []
                
        self.setup_ui()
        self.load_session_state()  # 应用启动时加载上次的状态

    def setup_ui(self):
        # --- 顶部功能栏 ---
        top_bar = tk.Frame(self.root, bg="#eee", pady=5)
        top_bar.pack(side=tk.TOP, fill=tk.X)
        tk.Button(top_bar, text="📂 导入预设 JSON", command=self.import_json, bg="#e1f5fe").pack(side=tk.LEFT, padx=10)
        tk.Button(top_bar, text="💾 导出完整配置", command=self.save_json).pack(side=tk.LEFT, padx=10)
        # 左侧面板显示/隐藏切换按钮
        tk.Button(top_bar, text="切换侧栏", command=self.toggle_sidebar, bg="#f0f0f0").pack(side=tk.LEFT, padx=6)

        # --- 主布局 ---
        self.main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=4)
        self.main_paned.pack(fill=tk.BOTH, expand=True)

        # ================= 左侧：配置中心 (Notebook) =================
        self.sidebar = ttk.Notebook(self.main_paned, width=640)
        self.main_paned.add(self.sidebar)

        # 1. API 连通页
        self.tab_api = tk.Frame(self.sidebar, padx=10, pady=10); self.sidebar.add(self.tab_api, text="基础连接")
        self.build_api_tab()

        # 2. 角色设定页
        self.tab_persona = tk.Frame(self.sidebar, padx=10, pady=10, bg="#f9f9f9")
        self.sidebar.add(self.tab_persona, text="角色设定")
        self.build_persona_tab()

        # 3. 预设开关页
        self.tab_modules = tk.Frame(self.sidebar, padx=5, pady=5); self.sidebar.add(self.tab_modules, text="预设管理")
        self.build_modules_tab()

        # 4. 采样参数页
        self.tab_params = tk.Frame(self.sidebar, padx=10, pady=10); self.sidebar.add(self.tab_params, text="参数调节")
        self.build_params_tab()

        # 5. GPT-SoVITS TTS 配置页
        self.tab_tts = tk.Frame(self.sidebar, padx=10, pady=10); self.sidebar.add(self.tab_tts, text="TTS配置")
        self.build_tts_tab()

        self.tab_regex = tk.Frame(self.sidebar, padx=10, pady=10)
        self.sidebar.add(self.tab_regex, text="正则过滤")
        self.build_regex_tab()

        # ================= 右侧：聊天中心 =================
        self.chat_frame = tk.Frame(self.main_paned, bg="white")
        self.main_paned.add(self.chat_frame)
        self.build_chat_ui()

    def build_api_tab(self):
        self.api_entries = {}
        fields = [("API 地址", "api_url", ""),
                  ("API 密钥", "api_key", "")]
        for label, key, default in fields:
            tk.Label(self.tab_api, text=label).pack(anchor="w", pady=(5,0))
            if key == "api_key":
                ent = tk.Entry(self.tab_api, font=("Consolas", 10), show="*")
            else:
                ent = tk.Entry(self.tab_api, font=("Consolas", 10))
            ent.insert(0, default); ent.pack(fill=tk.X, pady=(0, 10))
            self.api_entries[key] = ent
        
        tk.Label(self.tab_api, text="模型名称").pack(anchor="w")
        self.model_combo = ttk.Combobox(self.tab_api, values=[], state="readonly")
        self.model_combo.pack(fill=tk.X, pady=(0, 10))
        
        # 添加获取模型列表按钮
        btn_frame = tk.Frame(self.tab_api)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Button(btn_frame, text="🔄 获取模型列表", command=self.fetch_models_from_api, bg="#87CEEB", fg="white", relief="flat", font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="✅ 测试连接", command=self.test_api_connection, bg="#90EE90", relief="flat", font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=5)
        
        self.model_status_label = tk.Label(self.tab_api, text="● 未连接", fg="gray", font=("微软雅黑", 9))
        self.model_status_label.pack(anchor="w", pady=(5, 0))

    def fetch_models_from_api(self):
        """从 API 获取可用的模型列表"""
        api_url = self.api_entries['api_url'].get().strip()
        api_key = self.api_entries['api_key'].get().strip()
        
        if not api_url or not api_key:
            messagebox.showwarning("警告", "请先输入 API 地址和密钥")
            return
        
        self.model_status_label.config(text="● 获取中...", fg="orange")
        self.root.update()
        
        threading.Thread(target=self._fetch_models_thread, args=(api_url, api_key), daemon=True).start()
    
    def _fetch_models_thread(self, api_url: str, api_key: str):
        """在线程中获取模型列表"""
        try:
            # 确保URL正确格式
            if not api_url.endswith('/'):
                api_url = api_url + '/'
            models_url = api_url + "models"
            
            headers = {"Authorization": f"Bearer {api_key}"}
            response = requests.get(models_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                models = []
                
                # 处理不同 API 的响应格式
                if "data" in data:
                    models = [item.get("id", item.get("name", "")) for item in data["data"]]
                elif "models" in data:
                    models = [item.get("id", item.get("name", "")) for item in data["models"]]
                else:
                    models = [str(item) for item in data]
                
                # 过滤掉空字符串
                models = [m for m in models if m]
                
                self.available_models = sorted(models)
                
                # 在主线程中更新 UI
                self.root.after(0, self._update_model_combo, models)
                self.root.after(0, lambda: self.model_status_label.config(text=f"● 已连接 (找到 {len(models)} 个模型)", fg="green"))
            else:
                self.root.after(0, lambda: messagebox.showerror("错误", f"获取模型失败: {response.status_code}"))
                self.root.after(0, lambda: self.model_status_label.config(text="● 连接失败", fg="red"))
        except requests.exceptions.Timeout:
            self.root.after(0, lambda: messagebox.showerror("错误", "请求超时"))
            self.root.after(0, lambda: self.model_status_label.config(text="● 连接超时", fg="red"))
        except requests.exceptions.ConnectionError:
            self.root.after(0, lambda: messagebox.showerror("错误", "无法连接到 API 服务器"))
            self.root.after(0, lambda: self.model_status_label.config(text="● 连接失败", fg="red"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"获取模型列表失败: {str(e)}"))
            self.root.after(0, lambda: self.model_status_label.config(text="● 错误", fg="red"))
    
    def _update_model_combo(self, models: list):
        """更新模型下拉菜单"""
        self.model_combo.config(values=models)
        if models:
            self.model_combo.set(models[0])  # 设置第一个模型为默认值
    
    def test_api_connection(self):
        """测试 API 连接"""
        api_url = self.api_entries['api_url'].get().strip()
        api_key = self.api_entries['api_key'].get().strip()
        
        if not api_url or not api_key:
            messagebox.showwarning("警告", "请先输入 API 地址和密钥")
            return
        
        self.append_chat("System", "🔄 正在测试 API 连接...")
        threading.Thread(target=self._test_api_thread, args=(api_url, api_key), daemon=True).start()
    
    def _test_api_thread(self, api_url: str, api_key: str):
        """在线程中测试 API 连接"""
        try:
            if not api_url.endswith('/'):
                api_url = api_url + '/'
            models_url = api_url + "models"
            
            headers = {"Authorization": f"Bearer {api_key}"}
            response = requests.get(models_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                self.root.after(0, self.append_chat, "System", "✅ API 连接成功！可以开始使用。")
            else:
                self.root.after(0, self.append_chat, "System", f"❌ API 返回错误: {response.status_code}")
        except Exception as e:
            self.root.after(0, self.append_chat, "System", f"❌ 错误: {str(e)}")

    def build_persona_tab(self):
        
        def create_label(parent, text):
            return tk.Label(parent, text=text, bg="#f9f9f9", font=("微软雅黑", 9, "bold"))

        # --- 1. AI 角色配置区 ---
        char_frame = tk.LabelFrame(self.tab_persona, text=" AI 角色管理 ", bg="#f9f9f9", padx=10, pady=5)
        char_frame.pack(fill=tk.BOTH, pady=5, expand=True)
        
        # 角色选择与保存按钮
        char_top = tk.Frame(char_frame, bg="#f9f9f9")
        char_top.pack(fill=tk.X, pady=2)
        self.char_combo = ttk.Combobox(char_top, state="readonly")
        self.char_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.char_combo.bind("<<ComboboxSelected>>", lambda e: self.load_profile("char"))
        tk.Button(char_top, text="💾 保存角色", command=lambda: self.save_profile("char"), bg="#e1f5fe").pack(side=tk.RIGHT, padx=5)

        create_label(char_frame, "AI 名字:").pack(anchor="w")
        self.entry_char_name = tk.Entry(char_frame)
        self.entry_char_name.pack(fill=tk.X, pady=2)

        create_label(char_frame, "人设描述:").pack(anchor="w")
        self.text_char_bio = scrolledtext.ScrolledText(char_frame, height=7, font=("微软雅黑", 9))
        self.text_char_bio.pack(fill=tk.BOTH, expand=True, pady=2)

        # 新增：第一条信息 (First Message)
        create_label(char_frame, "第一条信息 (First Message):").pack(anchor="w")
        self.text_first_msg = scrolledtext.ScrolledText(char_frame, height=5, font=("微软雅黑", 9), fg="#555")
        self.text_first_msg.pack(fill=tk.BOTH, expand=True, pady=2)

        # --- 2. 用户配置区 ---
        user_frame = tk.LabelFrame(self.tab_persona, text=" 用户信息管理 ", bg="#f9f9f9", padx=10, pady=5)
        user_frame.pack(fill=tk.BOTH, pady=5, expand=True)

        user_top = tk.Frame(user_frame, bg="#f9f9f9")
        user_top.pack(fill=tk.X, pady=2)
        self.user_combo = ttk.Combobox(user_top, state="readonly")
        self.user_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.user_combo.bind("<<ComboboxSelected>>", lambda e: self.load_profile("user"))
        tk.Button(user_top, text="💾 保存用户", command=lambda: self.save_profile("user"), bg="#e1f5fe").pack(side=tk.RIGHT, padx=5)

        create_label(user_frame, "用户名字:").pack(anchor="w")
        self.entry_user_name = tk.Entry(user_frame)
        self.entry_user_name.pack(fill=tk.X, pady=2)

        create_label(user_frame, "用户设定描述:").pack(anchor="w")
        self.text_user_bio = scrolledtext.ScrolledText(user_frame, height=5, font=("微软雅黑", 9))
        self.text_user_bio.pack(fill=tk.BOTH, expand=True, pady=2)

        # 新增：插入位置下拉菜单 (基于图片需求)
        pos_frame = tk.Frame(user_frame, bg="#f9f9f9")
        pos_frame.pack(fill=tk.X, pady=5)
        create_label(pos_frame, "插入位置:").pack(side=tk.LEFT)
        self.combo_insert_pos = ttk.Combobox(pos_frame, values=INSERT_POSITIONS, state="readonly", width=30)
        self.combo_insert_pos.current(1) # 默认选择第二个
        self.combo_insert_pos.pack(side=tk.LEFT, padx=10)

        # 初始刷新
        self.refresh_profile_list("char")
        self.refresh_profile_list("user")
    
    def save_profile(self, p_type):
        """保存包含新字段的配置"""
        if p_type == "char":
            name = self.entry_char_name.get().strip()
            data = {
                "name": name,
                "bio": self.text_char_bio.get("1.0", tk.END).strip(),
                "first_message": self.text_first_msg.get("1.0", tk.END).strip() # 新增
            }
            path = os.path.join(self.char_dir, f"{name}.json")
        else:
            name = self.entry_user_name.get().strip()
            data = {
                "name": name,
                "bio": self.text_user_bio.get("1.0", tk.END).strip(),
                "insertion_position": self.combo_insert_pos.get() # 新增
            }
            path = os.path.join(self.user_dir, f"{name}.json")

        if not name: return
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        messagebox.showinfo("成功", f"配置 '{name}' 已存至本地")
        self.refresh_profile_list(p_type)

    def load_profile(self, p_type):
        """从 JSON 加载配置到界面"""
        if p_type == "char":
            selected = self.char_combo.get()
            path = os.path.join(self.char_dir, f"{selected}.json")
            target_name, target_bio = self.entry_char_name, self.text_char_bio
        else:
            selected = self.user_combo.get()
            path = os.path.join(self.user_dir, f"{selected}.json")
            target_name, target_bio = self.entry_user_name, self.text_user_bio

        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if p_type == "char":
                    self.entry_char_name.delete(0, tk.END)
                    self.entry_char_name.insert(0, data.get("name", ""))
                    self.text_char_bio.delete("1.0", tk.END)
                    self.text_char_bio.insert("1.0", data.get("bio", ""))
                    # 加载第一条信息
                    self.text_first_msg.delete("1.0", tk.END)
                    self.text_first_msg.insert("1.0", data.get("first_message", ""))
                else:
                    self.entry_user_name.delete(0, tk.END)
                    self.entry_user_name.insert(0, data.get("name", ""))
                    self.text_user_bio.delete("1.0", tk.END)
                    self.text_user_bio.insert("1.0", data.get("bio", ""))
                    # 加载插入位置
                    pos = data.get("insertion_position", INSERT_POSITIONS[1])
                    if pos in INSERT_POSITIONS:
                        self.combo_insert_pos.set(pos)

    def refresh_profile_list(self, p_type):
        """刷新下拉列表内容"""
        directory = self.char_dir if p_type == "char" else self.user_dir
        files = [f.replace(".json", "") for f in os.listdir(directory) if f.endswith(".json")]
        
        combo = self.char_combo if p_type == "char" else self.user_combo
        combo['values'] = files
        if files and not combo.get():
            combo.current(0)
            self.load_profile(p_type)

    # ================= 预设管理核心功能重写 =================

    def build_modules_tab(self):
        """构建预设管理页面（带新增/删除功能）"""
        # 1. 顶部工具栏
        tool_bar = tk.Frame(self.tab_modules, pady=5, bg="#f0f0f0")
        tool_bar.pack(side=tk.TOP, fill=tk.X)
        
        tk.Button(tool_bar, text="➕ 新增预设", command=self.add_new_module, bg="#87CEEB", fg="white", relief="flat").pack(side=tk.LEFT, padx=10)
        tk.Label(tool_bar, text="提示：点击预设名称可编辑详细内容", fg="gray", bg="#f0f0f0").pack(side=tk.LEFT, padx=10)

        # 分类行（单独占一行，避免挤占顶部工具栏空间）
        category_bar = tk.Frame(self.tab_modules, pady=4, bg="#f7f7f7")
        category_bar.pack(side=tk.TOP, fill=tk.X)
        # 左右两栏：左侧放分类下拉，右侧放操作按钮（导入/导出/启用/禁用）
        left_frame = tk.Frame(category_bar, bg="#f7f7f7")
        left_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        right_frame = tk.Frame(category_bar, bg="#f7f7f7")
        right_frame.pack(side=tk.RIGHT)

        tk.Label(left_frame, text="分类:", bg="#f7f7f7").pack(side=tk.LEFT, padx=(10,5))
        self.module_category_combo = ttk.Combobox(left_frame, values=[], state="readonly", width=24)
        self.module_category_combo.pack(side=tk.LEFT, padx=(0,10), fill=tk.X, expand=True)
        # 当用户选择分类时，刷新模块列表以只显示该分类下的预设
        self.module_category_combo.bind("<<ComboboxSelected>>", lambda e: (self.refresh_modules_ui(), self.save_session_state()))

        # 操作菜单（启用/禁用）
        menu_btn = tk.Menubutton(right_frame, text="操作 ▾", relief="raised")
        menu = tk.Menu(menu_btn, tearoff=0)
        menu.add_command(label="启用分类", command=self.enable_selected_category)
        menu.add_command(label="禁用分类", command=self.disable_selected_category)
        menu_btn.config(menu=menu)
        menu_btn.pack(side=tk.LEFT, padx=6)

        # 将导入/导出按钮放到分类下方的单独一行，随宽度自适应
        import_export_bar = tk.Frame(self.tab_modules, pady=4, bg="#fafafa")
        import_export_bar.pack(side=tk.TOP, fill=tk.X)

        # 三个按钮横向均分，随宽度伸缩
        btn_import = tk.Button(import_export_bar, text="⬆️ 导入预设", command=self.import_exported_presets, bg="#e1f5fe")
        btn_export = tk.Button(import_export_bar, text="⬇️ 导出预设", command=self.export_presets, bg="#D3F8D3")
        btn_delete = tk.Button(import_export_bar, text="🗑️ 删除所选", command=self.delete_selected_presets, bg="#FFDDDD")

        btn_import.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6, pady=2)
        btn_export.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6, pady=2)
        btn_delete.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6, pady=2)

        # 2. 列表区域
        self.canvas = tk.Canvas(self.tab_modules, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.tab_modules, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)
        
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        def on_canvas_configure(event):
            # 当画布大小时，强制设置内部窗口宽度等于画布宽度
            self.canvas.itemconfig(self.canvas_window, width=event.width)
        
        self.canvas.bind("<Configure>", on_canvas_configure)
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        # ==========================================

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        # 鼠标进入时绑定滚轮到该画布，离开时解绑，支持 Windows 与 Linux
        self.canvas.bind("<Enter>", lambda e: (self.canvas.bind_all("<MouseWheel>", self._on_mousewheel_modules), self.canvas.bind_all("<Button-4>", self._on_mousewheel_modules), self.canvas.bind_all("<Button-5>", self._on_mousewheel_modules)))
        self.canvas.bind("<Leave>", lambda e: (self.canvas.unbind_all("<MouseWheel>"), self.canvas.unbind_all("<Button-4>"), self.canvas.unbind_all("<Button-5>")))

    def refresh_modules_ui(self):
        """刷新预设列表 UI"""
        # 清空旧控件
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.module_controls = []
        # 根据所选分类过滤要显示的预设
        selected_cat = None
        default_none_label = "None"
        if hasattr(self, 'module_category_combo'):
            selected_cat = self.module_category_combo.get()
        if not selected_cat:
            selected_cat = default_none_label

        def is_in_none_category(p):
            c = p.get('category')
            return (c is None) or (str(c).strip() == "") or (str(c) == "None") or (str(c) == "未分类")

        if selected_cat == default_none_label:
            items_to_show = [item for item in self.preset_data_list if is_in_none_category(item)]
        else:
            items_to_show = [item for item in self.preset_data_list if str(item.get('category')) == str(selected_cat)]

        for item in items_to_show:
            self.add_module_to_ui(item)
        # 刷新分类下拉
        try:
            self.refresh_category_combo()
        except Exception:
            pass
        # 重新绑定/清理拖动状态
        try:
            self._drag_data = None
        except Exception:
            pass

    def refresh_category_combo(self):
        """刷新顶部分类下拉列表，基于当前 preset_data_list 中的 category 字段"""
        default_none_label = "None"
        cats = set()
        for p in self.preset_data_list:
            c = p.get('category')
            if c and str(c).strip() and str(c) not in ("None", "未分类"):
                cats.add(str(c))
        cats_list = [default_none_label] + sorted(cats)
        if hasattr(self, 'module_category_combo'):
            current = self.module_category_combo.get()
            self.module_category_combo.config(values=cats_list)
            # 保留当前选择（如果仍然有效），否则设为默认 none
            if current and current in cats_list:
                self.module_category_combo.set(current)
            else:
                self.module_category_combo.set(default_none_label)

    def _on_mousewheel_modules(self, event):
        """处理模块列表的滚轮事件，兼容 Windows 和 X11 (Button-4/5)"""
        try:
            # X11 鼠标按钮事件
            if hasattr(event, 'num') and event.num in (4, 5):
                if event.num == 4:
                    self.canvas.yview_scroll(-1, 'units')
                else:
                    self.canvas.yview_scroll(1, 'units')
                return
        except Exception:
            pass

        # Windows / 通用处理
        try:
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        except Exception:
            pass

    # --- 拖拽重排功能 ---
    def _start_drag(self, event, frame, item_data):
        """开始拖拽某一项"""
        try:
            self._drag_data = {
                'frame': frame,
                'data': item_data,
            }
            # 视觉标识
            frame.config(bg="#eef")
        except Exception:
            self._drag_data = None

    def _on_drag_motion(self, event):
        # 可选：可以实现悬浮拖动提示，目前只需动态显示位置反馈
        return

    def _on_drag_release(self, event):
        """在释放鼠标时根据指针位置计算目标索引并移动数据列表"""
        if not hasattr(self, '_drag_data') or not self._drag_data:
            return
        try:
            data = self._drag_data.get('data')
            frame = self._drag_data.get('frame')

            # 计算指针在 scrollable_frame 的相对 y
            rel_y = self.scrollable_frame.winfo_pointery() - self.scrollable_frame.winfo_rooty()

            # 获取当前可见子项顺序
            children = [c for c in self.scrollable_frame.winfo_children() if c.winfo_ismapped()]

            target_index = None
            for i, child in enumerate(children):
                mid = child.winfo_y() + child.winfo_height() / 2
                if rel_y < mid:
                    target_index = i
                    break
            if target_index is None:
                target_index = len(children) - 1

            # 找到 data 在 preset_data_list 中的旧位置
            old_idx = self._find_preset_index(data)
            if old_idx is None:
                # 清理样式
                try: frame.config(bg="#ffffff")
                except: pass
                self._drag_data = None
                return

            # children order matches current preset_data_list order, so use target_index as insertion position
            item = self.preset_data_list.pop(old_idx)
            insert_at = target_index
            # after popping an earlier item, the target index shifts left by 1
            if old_idx < target_index:
                insert_at = target_index - 1
            # clamp insert position
            if insert_at < 0:
                insert_at = 0
            if insert_at > len(self.preset_data_list):
                insert_at = len(self.preset_data_list)
            self.preset_data_list.insert(insert_at, item)

            self.refresh_modules_ui()
            self.save_session_state()

        except Exception as e:
            print(f"拖拽重排错误: {e}")
        finally:
            try:
                if frame:
                    frame.config(bg="#ffffff")
            except Exception:
                pass
            self._drag_data = None

    def enable_selected_category(self):
        """将所选分类下的所有预设启用"""
        cat = None
        if hasattr(self, 'module_category_combo'):
            cat = self.module_category_combo.get()
        if not cat:
            messagebox.showwarning("提示", "请先选择一个分类")
            return
        for item in self.preset_data_list:
            if item.get('category', '未分类') == cat:
                item['enabled'] = True
        # 同步 UI 开关
        for m in self.module_controls:
            try:
                if m.get('data', {}).get('category', '未分类') == cat:
                    m.get('var').set(True)
            except Exception:
                pass
        self.refresh_modules_ui()
        self.save_session_state()

    def disable_selected_category(self):
        """将所选分类下的所有预设禁用"""
        cat = None
        if hasattr(self, 'module_category_combo'):
            cat = self.module_category_combo.get()
        if not cat:
            messagebox.showwarning("提示", "请先选择一个分类")
            return
        for item in self.preset_data_list:
            if item.get('category', '未分类') == cat:
                item['enabled'] = False
        # 同步 UI 开关
        for m in self.module_controls:
            try:
                if m.get('data', {}).get('category', '未分类') == cat:
                    m.get('var').set(False)
            except Exception:
                pass
        self.refresh_modules_ui()
        self.save_session_state()

    def _find_preset_index(self, item_data):
        """通过对象或 identifier 查找 preset_data_list 中的索引，找不到返回 None"""
        try:
            for i, item in enumerate(self.preset_data_list):
                if item is item_data:
                    return i
                try:
                    if item.get('identifier') and item_data.get('identifier') and item.get('identifier') == item_data.get('identifier'):
                        return i
                except Exception:
                    pass
        except Exception:
            pass
        return None

    def move_module_up(self, item_data):
        idx = self._find_preset_index(item_data)
        if idx is None or idx <= 0:
            return
        self.preset_data_list[idx-1], self.preset_data_list[idx] = self.preset_data_list[idx], self.preset_data_list[idx-1]
        self.refresh_modules_ui()
        self.save_session_state()

    def move_module_down(self, item_data):
        idx = self._find_preset_index(item_data)
        if idx is None or idx >= len(self.preset_data_list)-1:
            return
        self.preset_data_list[idx+1], self.preset_data_list[idx] = self.preset_data_list[idx], self.preset_data_list[idx+1]
        self.refresh_modules_ui()
        self.save_session_state()


    def export_presets(self):
        """导出当前预设为标准化 JSON（包含 metadata）"""
        if not self.preset_data_list:
            messagebox.showinfo("提示", "当前没有预设可导出")
            return
        default_name = f"presets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")], initialfile=default_name)
        if not file_path:
            return
        payload = {
            "__exported_by": "venti",
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "presets": self.preset_data_list
        }
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("导出成功", f"已将 {len(self.preset_data_list)} 个预设导出到:\n{file_path}")
        except Exception as e:
            messagebox.showerror("导出失败", f"写入文件失败: {e}")

    def import_exported_presets(self):
        """导入由本程序导出的预设文件，支持替换或追加"""
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if not file_path:
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("读取失败", f"无法读取文件: {e}")
            return

        # 支持两种格式：{presets: [...] } 或 直接传入 presets 列表
        if isinstance(data, dict) and 'presets' in data and isinstance(data['presets'], list):
            incoming = data['presets']
        elif isinstance(data, list):
            incoming = data
        else:
            messagebox.showerror("格式错误", "该文件不是有效的导出预设文件（缺少 'presets' 列表）")
            return

        # 兼容性修正：确保有 category 字段
        for p in incoming:
            if 'category' not in p:
                p['category'] = '未分类'

        # 提示用户选择替换或追加
        if messagebox.askyesno("导入方式", f"导入文件包含 {len(incoming)} 个预设。\n选择 是 = 替换当前预设；否 = 追加到当前预设。\n要继续吗？"):
            # Yes -> 替换
            self.preset_data_list = incoming
        else:
            # No -> 追加
            self.preset_data_list.extend(incoming)

        self.refresh_modules_ui()
        self.save_session_state()
        messagebox.showinfo("导入成功", f"已导入 {len(incoming)} 个预设")

    def delete_selected_presets(self):
        """删除用户在 UI 中勾选的预设（多选）"""
        to_delete = []
        # 使用唯一的复选框（var）作为选中标志
        for m in list(self.module_controls):
            v = m.get('var')
            if v and v.get():
                to_delete.append(m.get('data'))

        if not to_delete:
            messagebox.showinfo("提示", "未选中任何预设")
            return

        if not messagebox.askyesno("确认删除", f"确定要删除选中的 {len(to_delete)} 个预设吗？"):
            return

        for item in to_delete:
            try:
                if item in self.preset_data_list:
                    self.preset_data_list.remove(item)
            except Exception:
                pass

        self.refresh_modules_ui()
        self.save_session_state()
        messagebox.showinfo("已删除", f"已删除 {len(to_delete)} 个预设")

    def add_new_module(self):
        """添加一个新的空白预设"""
        new_module = {
            "name": "新预设模块",
            "content": "在此输入预设内容...",
            "enabled": True,
            "injection_depth": 0,
            "category": "未分类",
            "identifier": f"preset_{int(time.time()*1000)}" # 生成唯一ID
        }
        self.preset_data_list.append(new_module)
        self.refresh_modules_ui()
        self.save_session_state()

        # 自动打开编辑器以便选择或创建分类
        var = tk.BooleanVar(value=True)
        self.open_module_editor(new_module, var)

    def delete_module(self, item_data):
        """删除指定的预设"""
        if messagebox.askyesno("确认删除", f"确定要删除预设 '{item_data.get('name')}' 吗？"):
            if item_data in self.preset_data_list:
                self.preset_data_list.remove(item_data)
                self.refresh_modules_ui()
                self.save_session_state()

    def remove_module(self, frame, item_data):
        """从 UI 和内存中移除指定模块（用于模块列表右侧的删除按钮）"""
        if not messagebox.askyesno("确认删除", f"确定要删除预设 '{item_data.get('name')}' 吗？"):
            return
        # 从 module_controls 中删除对应项
        for m in list(self.module_controls):
            if m.get('data') is item_data or m.get('data') == item_data:
                try:
                    # 销毁 UI
                    if m.get('frame'):
                        m['frame'].destroy()
                except Exception:
                    pass
                try:
                    self.module_controls.remove(m)
                except ValueError:
                    pass
        # 同步到 preset_data_list（如果存在）
        try:
            if item_data in self.preset_data_list:
                self.preset_data_list.remove(item_data)
        except Exception:
            pass
        # 保存状态
        self.save_session_state()

    def add_module_to_ui(self, item_data):
        """添加单个预设条目到 UI"""
        module_name = item_data.get('name', '未命名模块')
        
        # 外框
        frame = tk.Frame(self.scrollable_frame, bg="#ffffff", pady=5, padx=5, relief=tk.RAISED, borderwidth=1)
        frame.pack(fill=tk.X, pady=2)
        
        # 启用开关
        var = tk.BooleanVar(value=item_data.get('enabled', False))
        
        def on_check_toggle():
            item_data['enabled'] = var.get() # 实时同步数据
            self.root.after(100, self.save_session_state)

        # 拖拽把手
        handle = tk.Label(frame, text="☰", bg="#ffffff", cursor="fleur")
        handle.pack(side=tk.LEFT, padx=(0,6))

        # 唯一复选框（用于启用/选中），放在把手右边
        tk.Checkbutton(frame, variable=var, bg="#ffffff", command=on_check_toggle).pack(side=tk.LEFT, padx=(2,4))

        # 模块名称按钮（点击进入编辑器）
        btn = tk.Button(frame, text=module_name, relief="flat", anchor="w", bg="#ffffff",
                        command=lambda: self.open_module_editor(item_data, var))
        btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # 删除按钮（单条删除）
        del_btn = tk.Button(frame, text="🗑️", command=lambda: self.delete_module(item_data), 
                            bg="#ffebee", fg="red", relief="flat", width=4)
        del_btn.pack(side=tk.RIGHT)

        # 绑定拖拽事件到把手（只在把手上触发，避免与内部控件冲突）
        handle.bind("<Button-1>", lambda e, f=frame, d=item_data: self._start_drag(e, f, d))
        handle.bind("<B1-Motion>", self._on_drag_motion)
        handle.bind("<ButtonRelease-1>", self._on_drag_release)

        # 记录控件引用（包含 frame）
        self.module_controls.append({
            'name': module_name,
            'var': var,
            'data': item_data,
            'frame': frame
        })

    def import_json(self):
        """导入 JSON 文件到预设列表"""
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if not file_path: return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 兼容不同格式
                prompts = data.get('prompts', []) if isinstance(data, dict) else data
                
                if isinstance(prompts, list):
                    # 替换当前列表
                    # Ensure imported items have a category field for compatibility
                    for p in prompts:
                        if 'category' not in p:
                            p['category'] = p.get('category', '未分类')
                    self.preset_data_list = prompts
                    self.refresh_modules_ui()
                    messagebox.showinfo("成功", f"已加载 {len(prompts)} 个预设")
                    self.save_session_state()
                else:
                    messagebox.showerror("错误", "JSON 格式不正确，需要列表格式")
        except Exception as e: 
            messagebox.showerror("错误", f"读取失败: {str(e)}")

    # ==========================================================

    def import_json(self):
        """导入 JSON 文件到预设列表"""
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if not file_path: return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 兼容不同格式
                prompts = data.get('prompts', []) if isinstance(data, dict) else data
                
                if isinstance(prompts, list):
                    # 替换当前列表
                    self.preset_data_list = prompts
                    self.refresh_modules_ui()
                    messagebox.showinfo("成功", f"已加载 {len(prompts)} 个预设")
                    self.save_session_state()
                else:
                    messagebox.showerror("错误", "JSON 格式不正确，需要列表格式")
        except Exception as e: 
            messagebox.showerror("错误", f"读取失败: {str(e)}")

    def build_params_tab(self):
        """重新初始化采样参数页的容器"""
        self.canvas_p = tk.Canvas(self.tab_params, highlightthickness=0)
        self.scrollbar_p = ttk.Scrollbar(self.tab_params, orient="vertical", command=self.canvas_p.yview)
        self.params_inner_frame = tk.Frame(self.canvas_p)

        # 将内部 frame 放入 canvas，并保持内部窗口宽度与 canvas 同步
        self.params_canvas_window = self.canvas_p.create_window((0, 0), window=self.params_inner_frame, anchor="nw")
        self.canvas_p.configure(yscrollcommand=self.scrollbar_p.set)

        # 当 canvas 大小变化时，调整内部窗口宽度使子控件能水平铺满
        def _on_canvas_p_configure(event):
            try:
                self.canvas_p.itemconfig(self.params_canvas_window, width=event.width)
            except Exception:
                pass

        self.canvas_p.bind("<Configure>", _on_canvas_p_configure)
        # 当内部 frame 内容变化时，更新滚动范围
        self.params_inner_frame.bind("<Configure>", lambda e: self.canvas_p.configure(scrollregion=self.canvas_p.bbox("all")))

        self.canvas_p.pack(side="left", fill="both", expand=True)
        self.scrollbar_p.pack(side="right", fill="y")
        
        # 初始参数绑定字典
        self.param_vars = {}
        
        # 从 config.json 加载参数定义
        self.load_params_from_config()

    def load_params_from_config(self):
        """根据定义动态加载参数调节界面，支持滑动条与输入框联动"""
        
        # 扩展参数定义：(键名, 默认值, 描述, 范围(min, max, step))
        # 如果范围为 None，则不显示滑动条
        param_definitions = [
            ("temperature", 1.0, "控制输出的随机性", (0.0, 2.0, 0.01)),
            ("frequency_penalty", 0.0, "频率惩罚", (-2.0, 2.0, 0.01)),
            ("presence_penalty", 0.0, "出现惩罚", (-2.0, 2.0, 0.01)),
            ("top_p", 1.0, "核采样概率", (0.0, 1.0, 0.01)),
            ("top_k", 60, "最高K个候选", (1, 100, 1)),
            ("repetition_penalty", 1.0, "重复惩罚", (1.0, 2.0, 0.01)),
            ("openai_max_tokens", 30000, "最大生成 token 数", (1, 30000, 1)),
            ("openai_max_context", 20000, "最大上下文 token 数", (512, 20000, 1)),
        ]
        
        tk.Label(self.params_inner_frame, text="采样参数调节", 
                 font=("微软雅黑", 12, "bold"), bg="white").pack(anchor="w", padx=10, pady=10)
        
        for param_name, default_value, description, slider_range in param_definitions:
            frame = tk.Frame(self.params_inner_frame, bg="white")
            frame.pack(fill=tk.X, padx=10, pady=8)
            
            # 标题和描述
            header_frame = tk.Frame(frame, bg="white")
            header_frame.pack(fill=tk.X)
            tk.Label(header_frame, text=self.clean_label(param_name), font=("微软雅黑", 9, "bold"), bg="white").pack(side=tk.LEFT)
            tk.Label(header_frame, text=f" - {description}", font=("微软雅黑", 8), fg="gray", bg="white").pack(side=tk.LEFT)

            # 交互区域
            controls_frame = tk.Frame(frame, bg="white")
            controls_frame.pack(fill=tk.X, padx=(20, 0), pady=5)

            # 1. 创建 Entry (手动输入框)
            entry = tk.Entry(controls_frame, font=("Consolas", 10), width=10)
            entry.insert(0, str(default_value))
            entry.pack(side=tk.RIGHT, padx=(10, 0))
            self.param_vars[param_name] = entry

            # 2. 如果有范围定义，则创建 Scale (滑动条)
            if slider_range:
                p_min, p_max, p_step = slider_range
                
                # 滑动条触发函数
                def on_scale_move(val, e=entry):
                    e.delete(0, tk.END)
                    e.insert(0, val)

                scale = tk.Scale(
                    controls_frame, 
                    from_=p_min, to=p_max, 
                    resolution=p_step,
                    orient=tk.HORIZONTAL,
                    showvalue=False, # 不显示自带数值，因为我们有 Entry 了
                    bg="white",
                    highlightthickness=0,
                    command=on_scale_move
                )
                scale.set(default_value)
                scale.pack(side=tk.LEFT, fill=tk.X, expand=True)

                # 3. 输入框反向联动滑动条
                def on_entry_change(*args, e=entry, s=scale):
                    try:
                        val = float(e.get())
                        s.set(val)
                    except ValueError:
                        pass # 用户正在输入时可能不合法，暂不处理

                # 绑定输入框修改事件
                entry.bind("<KeyRelease>", on_entry_change)

    def clean_label(self, text):
        return text.replace("_", " ").title()
    
    def _on_mousewheel_p(self, event):
        """处理参数页面的滚轮事件"""
        self.canvas_p.yview_scroll(int(-1*(event.delta/120)), "units")

    def clean_label(self, text):
        """去除下划线等特殊符号，并首字母大写"""
        # 替换下划线为空格
        text = text.replace('_', ' ')
        # 驼峰命名处理：在小写字母和大写字母之间插入空格
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        return text.title()

    def build_tts_tab(self):
        """GPT-SoVITS TTS 配置页 (参考 Open-LLM-VTuber)"""
        tk.Label(self.tab_tts, text="GPT-SoVITS TTS 配置", font=("微软雅黑", 12, "bold")).pack(anchor="w", pady=(0, 10))
        
        # 启用/禁用 TTS
        self.tts_enabled_var = tk.BooleanVar(value=False)
        tk.Checkbutton(self.tab_tts, text="启用 GPT-SoVITS TTS", variable=self.tts_enabled_var, 
                      command=self.on_tts_enable_toggle).pack(anchor="w", pady=(0, 10))
        
        # 配置框架
        self.tts_config_frame = tk.LabelFrame(self.tab_tts, text="TTS 参数设置", relief=tk.GROOVE, borderwidth=2)
        self.tts_config_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.tts_entries = {}
        
        # 核心参数
        tk.Label(self.tts_config_frame, text="【核心参数】", font=("微软雅黑", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        core_fields = [
            ("API 地址", "api_url", ""),
            ("文本语言", "text_lang", "zh"),
            ("主参考音频路径 (Ref Audio)", "ref_audio_path", ""),
            # === 👇 新增这一行 👇 ===
            ("副参考音频路径 (Aux Audio)", "aux_ref_audio_paths", ""), 
        ]
        
        for label, key, default in core_fields:
            tk.Label(self.tts_config_frame, text=label).pack(anchor="w", padx=10, pady=(5, 0))
            ent = tk.Entry(self.tts_config_frame, font=("Consolas", 9))
            ent.insert(0, default)
            ent.pack(fill=tk.X, padx=10, pady=(0, 5))
            self.tts_entries[key] = ent
        
        # 高级参数
        tk.Label(self.tts_config_frame, text="【提示参数】", font=("微软雅黑", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        prompt_fields = [
            ("提示语言", "prompt_lang", "zh"),
            ("提示文本", "prompt_text", ""),
        ]
        
        for label, key, default in prompt_fields:
            tk.Label(self.tts_config_frame, text=label).pack(anchor="w", padx=10, pady=(5, 0))
            ent = tk.Entry(self.tts_config_frame, font=("Consolas", 9))
            ent.insert(0, default)
            ent.pack(fill=tk.X, padx=10, pady=(0, 5))
            self.tts_entries[key] = ent
        
        # 处理参数
        tk.Label(self.tts_config_frame, text="【处理参数】", font=("微软雅黑", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        process_fields = [
            ("文本分割方法", "text_split_method", "cut5"),
            ("批量大小", "batch_size", "1"),
            ("媒体类型", "media_type", "wav"),
            ("流式模式", "streaming_mode", "false"),
        ]
        
        for label, key, default in process_fields:
            tk.Label(self.tts_config_frame, text=label).pack(anchor="w", padx=10, pady=(5, 0))
            ent = tk.Entry(self.tts_config_frame, font=("Consolas", 9))
            ent.insert(0, default)
            ent.pack(fill=tk.X, padx=10, pady=(0, 5))
            self.tts_entries[key] = ent
        
        # 操作按钮
        btn_frame = tk.Frame(self.tts_config_frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=15)
        
        tk.Button(btn_frame, text="🔧 测试连接", command=self.test_tts_connection, 
                 bg="#87CEEB", fg="white", relief="flat", font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="🔄 重置参数", command=self.reset_tts_config, 
                 bg="#D3D3D3", relief="flat", font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="💾 保存配置", command=self.save_tts_config, 
                 bg="#90EE90", relief="flat", font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=5)
        
        # 初始禁用
        self.on_tts_enable_toggle()

    def on_tts_enable_toggle(self):
        """TTS 启用/禁用切换"""
        state = tk.NORMAL if self.tts_enabled_var.get() else tk.DISABLED
        for widget in self.tts_config_frame.winfo_children():
            if isinstance(widget, tk.Entry):
                widget.config(state=state)
            elif isinstance(widget, tk.Button):
                widget.config(state=state)
    
    def test_tts_connection(self):
        """测试 TTS 连接"""
        if not self.tts_enabled_var.get():
            messagebox.showwarning("提示", "请先启用 TTS")
            return
        
        self.append_chat("System", "🔄 正在测试 GPT-SoVITS 连接...")
        threading.Thread(target=self._test_tts_thread, daemon=True).start()
    
    def _test_tts_thread(self):
        """TTS 测试线程"""
        try:
            engine = self._create_tts_engine()
            if engine is None:
                self.root.after(0, self.append_chat, "System", "❌ TTS 配置错误")
                return
            
            success, message = engine.test_connection()
            self.root.after(0, self.append_chat, "System", message)
            
            if success:
                self.tts_engine = engine
                self.tts_enabled = True
                self.root.after(0, self.append_chat, "System", "✅ TTS 已准备就绪")
            else:
                self.tts_enabled = False
        except Exception as e:
            self.root.after(0, self.append_chat, "System", f"❌ 错误: {str(e)}")
    
    def _create_tts_engine(self) -> GPTSoVITSTTSEngine:
        """创建 TTS 引擎实例"""
        try:
            return GPTSoVITSTTSEngine(
                api_url=self.tts_entries.get("api_url", tk.Entry()).get() or "",
                text_lang=self.tts_entries.get("text_lang", tk.Entry()).get() or "zh",
                ref_audio_path=self._normalize_audio_paths(self.tts_entries.get("ref_audio_path", tk.Entry()).get() or "",
                                                           first_only=True),
                aux_ref_audio_paths=self._normalize_audio_paths(self.tts_entries.get("aux_ref_audio_paths", tk.Entry()).get() or ""),
                prompt_lang=self.tts_entries.get("prompt_lang", tk.Entry()).get() or "zh",
                prompt_text=self.tts_entries.get("prompt_text", tk.Entry()).get() or "",
                text_split_method=self.tts_entries.get("text_split_method", tk.Entry()).get() or "cut5",
                batch_size=self.tts_entries.get("batch_size", tk.Entry()).get() or "1",
                media_type=self.tts_entries.get("media_type", tk.Entry()).get() or "wav",
                streaming_mode=self.tts_entries.get("streaming_mode", tk.Entry()).get() or "false",
            )
        except Exception as e:
            return None

    def _normalize_audio_paths(self, raw: str, first_only: bool = False) -> str:
        """Normalize user-pasted audio path text into semicolon-separated paths.

        Accepts inputs like:
        "D:\\a\\x.flac"\n"D:\\a\\y.flac"
        or paths separated by newlines, commas or semicolons. Strips surrounding quotes and whitespace.
        If first_only is True, returns only the first valid path (useful for primary ref path).
        """
        if not raw:
            return ""
        # Replace different separators with newline for uniform split
        cleaned = raw.replace(';', '\n').replace(',', '\n')
        # Split lines and strip quotes/whitespace
        parts = []
        for line in cleaned.splitlines():
            s = line.strip()
            if not s:
                continue
            # remove surrounding quotes if present
            if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
                s = s[1:-1]
            s = s.strip()
            if s:
                parts.append(s)
        if not parts:
            return ""
        if first_only:
            return parts[0]
        # join with semicolon as expected by downstream code
        return ';'.join(parts)
    
    def reset_tts_config(self):
        """重置 TTS 配置到默认值"""
        defaults = {
            "api_url": "",
            "text_lang": "zh",
            "ref_audio_path": "",
            "aux_ref_audio_paths": "",
            "prompt_lang": "zh",
            "prompt_text": "",
            "text_split_method": "cut5",
            "batch_size": "1",
            "media_type": "wav",
            "streaming_mode": "false",
        }
        
        for key, value in defaults.items():
            if key in self.tts_entries:
                self.tts_entries[key].delete(0, tk.END)
                self.tts_entries[key].insert(0, value)
        
        self.append_chat("System", "✅ TTS 配置已重置为默认值")
    
    def save_tts_config(self):
        """保存 TTS 配置到文件"""
        config = {}
        for key, entry in self.tts_entries.items():
            val = entry.get()
            if key in ("aux_ref_audio_paths", "ref_audio_path"):
                # normalize pasted paths before saving
                if key == "ref_audio_path":
                    config[key] = self._normalize_audio_paths(val, first_only=True)
                else:
                    config[key] = self._normalize_audio_paths(val, first_only=False)
            else:
                config[key] = val
        
        filename = f"tts_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self.append_chat("System", f"✅ TTS 配置已保存: {filename}")
        except Exception as e:
            self.append_chat("System", f"❌ 保存失败: {str(e)}")

    def build_chat_ui(self):
        # 创建右侧的主容器
        self.right_main_container = tk.Frame(self.chat_frame, bg="white")
        self.right_main_container.pack(fill=tk.BOTH, expand=True)

        # --- 页面 1: 聊天界面 ---
        self.chat_view = tk.Frame(self.right_main_container, bg="white")
        self.chat_view.pack(fill=tk.BOTH, expand=True)
        
        # 会话选择栏（新）
        chat_top = tk.Frame(self.chat_view, bg="white")
        chat_top.pack(fill=tk.X, padx=10, pady=(6, 0))
        tk.Label(chat_top, text="会话:", bg="white").pack(side=tk.LEFT)
        self.chat_combo = ttk.Combobox(chat_top, values=[], state="readonly", width=36)
        self.chat_combo.pack(side=tk.LEFT, padx=6)
        self.chat_combo.bind("<<ComboboxSelected>>", lambda e: self.load_chat(self.chat_combo.get()))
        # 填充已有会话列表
        self.populate_chat_list()
        tk.Button(chat_top, text="新建", command=self.new_chat, bg="#e1f5fe").pack(side=tk.LEFT, padx=3)
        tk.Button(chat_top, text="保存为", command=self.save_chat_as, bg="#90EE90").pack(side=tk.LEFT, padx=3)
        tk.Button(chat_top, text="删除", command=self.delete_chat_ui, bg="#FFDDDD").pack(side=tk.LEFT, padx=3)

        self.chat_display = scrolledtext.ScrolledText(self.chat_view, state='disabled', font=("微软雅黑", 11), padx=10, spacing1=5)
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        # 在显示创建后再加载当前会话到显示（避免 chat_display 未定义的 AttributeError）
        try:
            if self.current_chat:
                self.load_chat(self.current_chat)
        except Exception:
            pass
        
        input_area = tk.Frame(self.chat_view, pady=10)
        input_area.pack(fill=tk.X)

        # 1. 先放右边的按钮 (注意顺序：先放的最靠右)
        # 发送按钮
        tk.Button(input_area, text="发送", command=self.send_message, width=10, bg="#87CEEB", fg="white").pack(side=tk.RIGHT, padx=5)
        
        # 停止按钮 (粉色)
        tk.Button(input_area, text="🔇", command=self.stop_audio, width=8, bg="#FFB6C1", fg="black").pack(side=tk.RIGHT, padx=5)

        # 2. 最后放左边的输入框 (让它占满剩下的空间)
        self.entry_msg = tk.Entry(input_area, font=("微软雅黑", 11))
        self.entry_msg.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        self.entry_msg.bind("<Return>", lambda event: self.send_message())
        # ================================

        # 状态行
        status_frame = tk.Frame(self.chat_view)
        status_frame.pack(fill=tk.X, padx=10)
        self.status_label = tk.Label(status_frame, text="● 空闲", fg="gray", anchor="w", font=("微软雅黑", 9))
        self.status_label.pack(side=tk.LEFT)
        
        self._timer_after_id = None
        self._timer_start = None

        # --- 页面 2: 模块编辑界面 ---
        self.edit_view = tk.Frame(self.right_main_container, bg="#f5f5f5")

    def show_page(self, page_name):
        """切换右侧显示的内容"""
        if page_name == "chat":
            self.edit_view.pack_forget()
            self.chat_view.pack(fill=tk.BOTH, expand=True)
        elif page_name == "edit":
            self.chat_view.pack_forget()
            self.edit_view.pack(fill=tk.BOTH, expand=True)


    def preview_prompt(self):
        preview_win = tk.Toplevel(self.root)
        preview_win.title("发送内容预览")
        txt = scrolledtext.ScrolledText(preview_win, width=80, height=30)
        txt.insert(tk.END, self.get_final_system_prompt())
        txt.pack(padx=10, pady=10)

    def clear_history(self):
        self.chat_history = []
        self.chat_display.config(state='normal')
        self.chat_display.delete("1.0", tk.END)
        self.chat_display.insert(tk.END, "--- 对话历史已清空 ---\n\n")
        self.chat_display.config(state='disabled')

    def import_json(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if not file_path: return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 兼容不同格式，提取 prompts 列表
                prompts = data.get('prompts', []) if isinstance(data, dict) else data
                
                # 清空现有的模块
                for widget in self.scrollable_frame.winfo_children(): widget.destroy()
                self.module_controls = []
                
                for item in prompts:
                    self.add_module_to_ui(item)
                    
                messagebox.showinfo("成功", f"已加载 {len(prompts)} 个模块")
                self.save_session_state()
        except Exception as e: 
            messagebox.showerror("错误", f"读取失败: {str(e)}")

    def open_module_editor(self, data, enabled_var):
        """
        动态模块编辑器：根据 JSON 内容自动生成 UI 控件
        """
        # 1. 清空旧视图
        for widget in self.edit_view.winfo_children():
            widget.destroy()

        # 2. 顶部导航栏
        header = tk.Frame(self.edit_view, bg="#87CEEB", pady=10)
        header.pack(fill=tk.X)
        tk.Label(header, text=f"🔧 动态调节：{data.get('name', '未命名')}", 
                 fg="white", bg="#87CEEB", font=("微软雅黑", 12, "bold")).pack(side=tk.LEFT, padx=15)
        tk.Button(header, text="返回聊天", command=lambda: self.show_page("chat"), 
                  bg="#666", fg="white", relief="flat").pack(side=tk.RIGHT, padx=10)

        # 3. 创建可滚动区域（防止字段过多显示不全）
        container = tk.Frame(self.edit_view, bg="#f5f5f5")
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # 排除不需要显示的字段
        blacklist = ["identifier", "enabled"] 
        
        self.dynamic_controls = {} # 用于暂存控件引用，以便保存

        # 4. 遍历 JSON 字典的键值对
        for key, value in data.items():
            if key in blacklist:
                continue

            # 容器行
            row = tk.Frame(container, bg="#f5f5f5")
            row.pack(fill=tk.X, pady=5)
            
            # 标签：将 key 转换为易读格式 (例如 injection_depth -> Injection Depth)
            display_label = key.replace("_", " ").title()
            tk.Label(row, text=display_label, bg="#f5f5f5", width=20, anchor="w", font=("Consolas", 10, "bold")).pack(side=tk.TOP, fill=tk.X)

            # --- 根据值类型选择控件 ---
            
            # A. 多行文本 (针对 content 字段)
            if key == "content" or (isinstance(value, str) and len(value) > 50):
                box = scrolledtext.ScrolledText(row, height=10, font=("微软雅黑", 10))
                box.insert(tk.END, str(value))
                box.pack(fill=tk.X, pady=2)
                self.dynamic_controls[key] = ("text", box)
            
            # B. 布尔值 (Checkbox)
            elif isinstance(value, bool):
                var = tk.BooleanVar(value=value)
                chk = tk.Checkbutton(row, text="开启/关闭", variable=var, bg="#f5f5f5")
                chk.pack(side=tk.LEFT)
                self.dynamic_controls[key] = ("bool", var)
            
            # C. 数字或短字符串 (Entry)
            else:
                # 对 category 字段使用可编辑下拉，列出已有分类并允许手动输入新分类
                if key == 'category':
                    # 收集现有分类
                    cats = set()
                    for p in self.preset_data_list:
                        c = p.get('category')
                        if c and str(c).strip() and str(c) not in ("None", "未分类"):
                            cats.add(str(c))
                    cats_list = ["未分类"] + sorted(cats)
                    cb = ttk.Combobox(row, values=cats_list, state='normal')
                    cb.set(str(value) if value is not None else "未分类")
                    cb.pack(fill=tk.X, pady=2)
                    self.dynamic_controls[key] = ("category", cb)
                else:
                    ent = tk.Entry(row, font=("微软雅黑", 10))
                    ent.insert(0, str(value))
                    ent.pack(fill=tk.X, pady=2)
                    # 记录原始类型，方便保存时还原
                    val_type = type(value)
                    self.dynamic_controls[key] = (val_type, ent)

        # 5. 保存逻辑
        def save_dynamic_data():
            for key, (ctrl_type, ctrl_obj) in self.dynamic_controls.items():
                if ctrl_type == "text":
                    data[key] = ctrl_obj.get("1.0", tk.END).strip()
                elif ctrl_type == "bool":
                    data[key] = ctrl_obj.get()
                elif ctrl_type == "category":
                    # 可编辑下拉：获取文本并作为字符串保存
                    v = ctrl_obj.get().strip()
                    data[key] = v if v else "未分类"
                else:
                    # 尝试还原原始数据类型（如 int）
                    raw_val = ctrl_obj.get()
                    try:
                        data[key] = ctrl_type(raw_val)
                    except:
                        data[key] = raw_val # 转换失败则存为字符串
            
            messagebox.showinfo("成功", f"模块 '{data.get('name')}' 已更新")
            self.show_page("chat")
            self.refresh_modules_ui() # <--- 保存后刷新列表名字
            try:
                self.refresh_category_combo()
            except Exception:
                pass
            self.save_session_state()

        tk.Button(self.edit_view, text="💾 确认修改并保存", command=save_dynamic_data, 
                  bg="#90EE90", font=("微软雅黑", 10, "bold"), pady=8).pack(fill=tk.X, padx=20, pady=10)

        self.show_page("edit")
    
    def get_final_system_prompt(self):
        # 构建包含 persona 信息的 system_base
        ai_name = self.entry_char_name.get().strip()
        ai_bio = self.text_char_bio.get('1.0', tk.END).strip()
        ai_first_msg = self.text_first_msg.get('1.0', tk.END).strip()
        
        user_name = self.entry_user_name.get().strip()
        user_bio = self.text_user_bio.get('1.0', tk.END).strip()
        insert_pos = self.combo_insert_pos.get()
        
        # 构建 persona 信息块
        persona_info = f"[AI Character Persona]\nName: {ai_name}\nDescription: {ai_bio}"
        if ai_first_msg:
            persona_info += f"\nFirst Message: {ai_first_msg}"
        
        persona_info += f"\n\n[User Persona]\nName: {user_name}\nDescription: {user_bio}\nInsertion Position: {insert_pos}"
        
        # 使用 persona 信息作为 system_base
        system_base = persona_info
        
        # 向后兼容：如果存在 text_system，将其追加到 system_base
        if hasattr(self, 'text_system'):
            try:
                base_text = self.text_system.get("1.0", tk.END).strip()
                if base_text:
                    system_base = f"{base_text}\n\n{system_base}"
            except:
                pass

        # 遍历所有存储的模块数据
        active_modules_content = []
        for m in self.module_controls:
            if m['var'].get():  # 如果勾选了启用
                # 这里可以根据 m['data']['injection_depth'] 做排序，但目前先简单拼接
                active_modules_content.append(m['data'].get('content', ''))

        modules_part = "\n\n[Active Modules]\n" + "\n\n".join(active_modules_content) if active_modules_content else ""
        
        return f"{system_base}{modules_part}"

    def save_json(self):
        self.save_session_state()
        messagebox.showinfo("提示", "配置保存成功！")

    def send_message(self):
        text = self.entry_msg.get().strip()
        if not text: return
        self.append_chat(self.entry_user_name.get(), text)
        self.entry_msg.delete(0, tk.END)
        self.chat_history.append({"role": "user", "content": text})
        # 自动保存当前会话（如果有选中会话）
        try:
            self.auto_save_current_chat()
        except Exception:
            pass
        # 启动等待计时器并调用 API
        self.start_timer()
        threading.Thread(target=self.call_api, daemon=True).start()

    def stop_audio(self):
        """强制停止当前播放的语音"""
        try:
            import winsound
            # SND_PURGE 会立即切断所有声音
            winsound.PlaySound(None, winsound.SND_PURGE)
            self.append_chat("System", "🔇 语音已停止")
        except Exception:
            pass

    def call_api(self):
        self.save_session_state()
        payload = {
            "model": self.model_combo.get(),
            "messages": [{"role": "system", "content": self.get_final_system_prompt()}] + self.chat_history,
            "temperature": float(self.param_vars.get("temperature", tk.Entry()).get() or 1.0),
            "max_tokens": int(self.param_vars.get("openai_max_tokens", tk.Entry()).get() or 4096),
            "stream": False
        }
        # 在 call_api 内部构建采样参数
        sampling_params = {}
        for key, entry in self.param_vars.items():
            val = entry.get()
            # 尝试转为数字，转不了就保持字符串或布尔
            try:
                if '.' in val: sampling_params[key] = float(val)
                else: sampling_params[key] = int(val)
            except:
                sampling_params[key] = val

        # 将这些参数合并到 payload 中
        payload.update(sampling_params)
        print("发送的 Payload:", payload)
        try:
            headers = {"Authorization": f"Bearer {self.api_entries['api_key'].get()}"}
            # 构建完整的聊天完成端点 URL
            api_url = self.api_entries['api_url'].get()
            if not api_url.endswith('/'):
                api_url = api_url + '/'
            chat_url = api_url + "chat/completions"
            resp = requests.post(chat_url, json=payload, headers=headers, timeout=300)
            
            print("发送的 Payload:", payload)
            if resp.status_code == 200:
                ai_msg = resp.json()['choices'][0]['message']['content']
                # 核心：在此处调用多重过滤
                ai_msg = self.apply_all_regex(ai_msg)
                # 停止计时器（在主线程更新状态）
                self.root.after(0, self.stop_timer)
                self.root.after(0, self.append_chat, self.entry_char_name.get(), ai_msg)
                self.chat_history.append({"role": "assistant", "content": ai_msg})
                try:
                    self.auto_save_current_chat()
                except Exception:
                    pass
                print("AI 回复:", ai_msg)
                # 自动生成语音（如果 TTS 已启用）
                if self.tts_enabled and self.tts_engine:
                    self.root.after(0, lambda: threading.Thread(target=self.synthesize_speech, args=(ai_msg,), daemon=True).start())
            else:
                self.root.after(0, self.stop_timer)
                self.root.after(0, self.append_chat, "System", f"❌ Error: {resp.text}")
        except Exception as e: 
            self.root.after(0, self.stop_timer)
            self.root.after(0, self.append_chat, "System", f"❌ Exception: {str(e)}")

    def synthesize_speech(self, text: str):
        """合成语音（修复版）"""
        try:
            if not self.tts_engine:
                return
            
            # 1. 生成音频文件 (这里得到的是相对路径，如 tts_cache/xxx.wav)
            rel_path = self.tts_engine.generate_audio(text)
            
            if rel_path:
                # 2. === 关键修改：转为绝对路径 ===
                import os
                abs_path = os.path.abspath(rel_path)
                
                # 已移除自动显示“准备播放”提示，避免突兀的系统消息
                
                # 3. 播放音频
                try:
                    import winsound
                    # 如果没有声音，去掉 SND_ASYNC 改成 0 试试（会卡住界面但能测试是否是并发问题）
                    # SND_FILENAME: 指定文件名
                    # SND_ASYNC: 后台播放，不卡界面
                    flags = winsound.SND_FILENAME | winsound.SND_ASYNC
                    winsound.PlaySound(abs_path, flags)
                    
                except Exception as play_error:
                    print(f"播放出错: {play_error}")
                    self.root.after(0, self.append_chat, "System", f"⚠️ 播放器报错: {str(play_error)}")
            else:
                self.root.after(0, self.append_chat, "System", "❌ 语音生成失败 (文件未创建)")
                
        except Exception as e:
            self.root.after(0, self.append_chat, "System", f"⚠️ TTS 逻辑错误: {str(e)}")

    # --- 简易计时器功能 ---
    def _update_timer_label(self):
        if not self._timer_start:
            return
        elapsed = time.time() - self._timer_start
        self.status_label.config(text=f"⏳ 等待中 {elapsed:.1f}s", fg="orange")
        # 每 300ms 更新一次
        self._timer_after_id = self.root.after(300, self._update_timer_label)

    def start_timer(self):
        # 取消已有计时器
        try:
            if self._timer_after_id:
                self.root.after_cancel(self._timer_after_id)
        except Exception:
            pass
        self._timer_start = time.time()
        self.status_label.config(text="⏳ 等待中 0.0s", fg="orange")
        self._timer_after_id = self.root.after(300, self._update_timer_label)

    def stop_timer(self, final_text=None):
        try:
            if self._timer_after_id:
                self.root.after_cancel(self._timer_after_id)
        except Exception:
            pass
        if not self._timer_start:
            # 无计时器在运行
            self.status_label.config(text=final_text or "● 空闲", fg="gray")
            return
        elapsed = time.time() - self._timer_start
        self._timer_start = None
        self._timer_after_id = None
        if final_text:
            self.status_label.config(text=final_text, fg="green")
        else:
            self.status_label.config(text=f"✅ 完成 ({elapsed:.1f}s)", fg="green")

    def append_chat(self, name, text):
        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, f"【{name}】\n", "name")
        self.chat_display.insert(tk.END, f"{text}\n\n")
        self.chat_display.tag_config("name", font=("微软雅黑", 10, "bold"))
        self.chat_display.see(tk.END); self.chat_display.config(state='disabled')
    
    def build_regex_tab(self):
        """构建正则管理页面，规则列表 + 对话框编辑"""
        # 主容器
        main_frame = tk.Frame(self.tab_regex, bg="#f0f0f0")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # --- 顶部标题和按钮栏 ---
        header = tk.Frame(main_frame, bg="#f0f0f0")
        header.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(header, text="正则规则列表", font=("微软雅黑", 12, "bold"), bg="#f0f0f0").pack(side=tk.LEFT)
        
        btn_bar = tk.Frame(header, bg="#f0f0f0")
        btn_bar.pack(side=tk.RIGHT)
        # 新增：导入按钮
        tk.Button(btn_bar, text="📂 导入配置", command=self.import_regex_config, bg="#e1f5fe").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_bar, text="➕ 添加", command=self.add_new_regex, bg="#87CEEB").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_bar, text="💾 保存", command=self.save_regex_config, bg="#90EE90").pack(side=tk.LEFT, padx=5)

        # --- 规则列表容器 ---
        list_frame = tk.Frame(main_frame, bg="#ffffff", relief=tk.SUNKEN, bd=1)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建可滚动容器 - 正确的顺序很重要
        scroll_bar = tk.Scrollbar(list_frame)
        scroll_bar.pack(side=tk.RIGHT, fill=tk.Y)
        
        canvas = tk.Canvas(list_frame, bg="#ffffff", highlightthickness=0)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.scrollable_frame_regex = tk.Frame(canvas, bg="#ffffff")
        canvas_window = canvas.create_window((0, 0), window=self.scrollable_frame_regex, anchor="nw")
        # 使内部窗口宽度随画布宽度变化，从而让每条规则占满整行（与预设列表一致）
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=e.width))
        
        # 配置滚动
        scroll_bar.config(command=canvas.yview)
        canvas.configure(yscrollcommand=scroll_bar.set)
        
        def on_frame_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        self.scrollable_frame_regex.bind("<Configure>", on_frame_configure)

        # 使用已加载的规则列表刷新 UI
        print(f"DEBUG: 开始刷新 UI，当前规则数: {len(self.regex_rules_list)}")
        self.refresh_regex_ui()
        print(f"DEBUG: UI 刷新完成")

    def import_regex_config(self):
        """从 JSON 文件导入正则配置并刷新 UI"""
        file_path = filedialog.askopenfilename(
            title="选择正则配置文件",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        
        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                new_rules = json.load(f)
            
            # 简单的数据校验，确保是列表
            if isinstance(new_rules, list):
                # 1. 更新内存中的数据
                self.regex_rules_list = new_rules
                
                # 2. 刷新 UI (直接调用现有的刷新方法)
                self.refresh_regex_ui()
                
                # 3. 提示成功
                messagebox.showinfo("导入成功", f"已成功加载 {len(new_rules)} 条正则规则！")
            else:
                messagebox.showerror("格式错误", "导入的 JSON 必须是规则列表 (List) 格式。")
                
        except json.JSONDecodeError:
            messagebox.showerror("读取错误", "文件不是有效的 JSON 格式。")
        except Exception as e:
            messagebox.showerror("错误", f"导入失败: {str(e)}")

    def add_regex_item_to_ui(self, rule_data):
        """仿照 add_module_to_ui：为每条正则规则创建可点击的条目"""
        rule_name = rule_data.get('scriptName', '未命名规则')
        
        # 规则容器
        frame = tk.Frame(self.scrollable_frame_regex, bg="#ffffff", pady=5, padx=5)
        frame.pack(fill=tk.X, pady=1)
        
        # 启用勾选框（取反 disabled 字段）
        var = tk.BooleanVar(value=not rule_data.get('disabled', False))
        tk.Checkbutton(frame, variable=var, bg="#ffffff", command=lambda: self.sync_regex_checkbox(rule_data, var)).pack(side=tk.LEFT)
        
        # 规则名称按钮（点击进入编辑）
        btn = tk.Button(frame, text=rule_name, relief="flat", anchor="w",
                        command=lambda: self.open_regex_editor(rule_data, var))
        btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 删除按钮（右侧）
        del_btn = tk.Button(frame, text="🗑️", command=lambda: self.remove_regex(frame, rule_data),
                            bg="#ffebee", fg="red", relief="flat", width=4)
        del_btn.pack(side=tk.RIGHT)

        # 存储该规则的所有数据引用（包含 frame 引用用于删除）
        self.regex_rules_data.append({
            'name': rule_name,
            'var': var,  # 关联启用开关
            'data': rule_data,  # 原始完整数据
            'frame': frame
        })

    def open_regex_editor(self, rule_data, enabled_var):
        """还原图片风格的正则编辑器"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"正则表达式编辑器 - {rule_data.get('scriptName', '未命名')}")
        dialog.geometry("1000x800")
        dialog.configure(bg="#ffffff") # 使用纯白背景
        
        # 样式配置
        label_cfg = {"bg": "#ffffff", "fg": "#888888", "font": ("微软雅黑", 10)}
        entry_cfg = {"relief": "solid", "bd": 1, "highlightthickness": 1, 
                    "highlightcolor": "#a0d8ef", "highlightbackground": "#e0e0e0"}

        # 1. 顶部标题区
        header = tk.Frame(dialog, bg="#ffffff", pady=10)
        header.pack(fill=tk.X)
        tk.Label(header, text="正则表达式编辑器", font=("微软雅黑", 14, "bold"), bg="#ffffff").pack()
        tk.Label(header, text="“正则”是一个使用“正则表达式”来查找/替换字符串的工具。", 
                bg="#ffffff", fg="#999", font=("微软雅黑", 9)).pack()
        
        # 编译错误提示（如果存在）
        if rule_data.get('_compile_error'):
            error_label = tk.Label(header, 
                text=f"⚠️ 编译错误: {rule_data.get('_compile_error')}", 
                bg="#fff0f0", fg="#cc0000", font=("微软雅黑", 9), wraplength=800, justify="left")
            error_label.pack(fill=tk.X, padx=20, pady=5)

        # 主滚动容器
        canvas = tk.Canvas(dialog, bg="#ffffff", highlightthickness=0)
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg="#ffffff", padx=20)
        
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw", width=560)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=scrollbar.set)
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # 快速创建带标签输入框的函数
        def create_input_group(parent, label, key, height=1):
            tk.Label(parent, text=label, **label_cfg).pack(anchor="w", pady=(10, 2))
            if height == 1:
                widget = tk.Entry(parent, font=("Consolas", 11), **entry_cfg)
                widget.insert(0, str(rule_data.get(key, "") or ""))
            else:
                widget = scrolledtext.ScrolledText(parent, height=height, font=("Consolas", 11), **entry_cfg)
                widget.insert("1.0", str(rule_data.get(key, "") or ""))
            widget.pack(fill=tk.X)
            return widget

        # 基础字段
        ent_name = create_input_group(scroll_frame, "脚本名称", "scriptName")
        ent_find = create_input_group(scroll_frame, "查找正则表达式", "findRegex")
        txt_replace = create_input_group(scroll_frame, "替换为", "replaceString", height=4)
        txt_trim = create_input_group(scroll_frame, "修剪掉", "trimString", height=3)

        # --- 中间分栏区 (作用范围 vs 其他选项) ---
        mid_frame = tk.Frame(scroll_frame, bg="#ffffff", pady=15)
        mid_frame.pack(fill=tk.X)
        
        left_col = tk.Frame(mid_frame, bg="#ffffff")
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right_col = tk.Frame(mid_frame, bg="#ffffff")
        right_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 作用范围 (左)
        tk.Label(left_col, text="作用范围", **label_cfg).pack(anchor="w")
        scope_vars = {
            "userInput": tk.BooleanVar(value=rule_data.get("userInput", False)),
            "aiOutput": tk.BooleanVar(value=not rule_data.get("disabled", False)),
            "quickMsg": tk.BooleanVar(value=rule_data.get("quickMsg", False)),
            "worldInfo": tk.BooleanVar(value=rule_data.get("worldInfo", False)),
            "inference": tk.BooleanVar(value=rule_data.get("inference", False))
        }
        for key, text in [("userInput","用户输入"), ("aiOutput","AI输出"), ("quickMsg","快捷命令"), ("worldInfo","世界信息"), ("inference","推理")]:
            tk.Checkbutton(left_col, text=text, variable=scope_vars[key], bg="#ffffff", activebackground="#ffffff").pack(anchor="w")

        # 其他选项与宏 (右)
        tk.Label(right_col, text="其他选项", **label_cfg).pack(anchor="w")
        other_vars = {
            "disabled": tk.BooleanVar(value=rule_data.get("disabled", False)),
            "runOnEdit": tk.BooleanVar(value=rule_data.get("runOnEdit", False))
        }
        tk.Checkbutton(right_col, text="已禁用", variable=other_vars["disabled"], bg="#ffffff").pack(anchor="w")
        tk.Checkbutton(right_col, text="在编辑时运行", variable=other_vars["runOnEdit"], bg="#ffffff").pack(anchor="w")

        # 补充：正则表达式查找时的宏 (图片中缺失的部分)
        tk.Label(right_col, text="正则表达式查找时的宏", **label_cfg).pack(anchor="w", pady=(10, 0))
        macro_combo = ttk.Combobox(right_col, values=["不替换", "全局宏", "局部宏"], state="readonly")
        macro_combo.set(rule_data.get("macroMode", "不替换"))
        macro_combo.pack(fill=tk.X, pady=2)

        # 补充：短暂选项
        tk.Label(right_col, text="短暂", **label_cfg).pack(anchor="w", pady=(10, 0))
        ephemeral_vars = {
            "formatDisplay": tk.BooleanVar(value=rule_data.get("formatDisplay", False)),
            "formatPrompt": tk.BooleanVar(value=rule_data.get("formatPrompt", False))
        }
        tk.Checkbutton(right_col, text="仅格式显示", variable=ephemeral_vars["formatDisplay"], bg="#ffffff").pack(anchor="w")
        tk.Checkbutton(right_col, text="仅格式提示词", variable=ephemeral_vars["formatPrompt"], bg="#ffffff").pack(anchor="w")

        # --- 底部深度设置 ---
        depth_frame = tk.Frame(scroll_frame, bg="#ffffff", pady=10)
        depth_frame.pack(fill=tk.X)
        
        def create_depth_entry(parent, label, key):
            frame = tk.Frame(parent, bg="#ffffff")
            frame.pack(side=tk.LEFT, expand=True, fill=tk.X)
            tk.Label(frame, text=label, **label_cfg).pack(anchor="w")
            e = tk.Entry(frame, **entry_cfg, width=15)
            val = rule_data.get(key, "")
            e.insert(0, "无限" if val is None or val == "" else str(val))
            e.pack(anchor="w", pady=2)
            return e

        ent_min = create_depth_entry(depth_frame, "最小深度", "minDepth")
        ent_max = create_depth_entry(depth_frame, "最大深度", "maxDepth")

        # --- 保存/取消按钮 ---
        btn_frame = tk.Frame(dialog, bg="#ffffff", pady=20)
        btn_frame.pack(fill=tk.X)

        def do_save():
            # 更新数据对象
            rule_data["scriptName"] = ent_name.get()
            new_pattern = ent_find.get()
            rule_data["findRegex"] = new_pattern
            rule_data["replaceString"] = txt_replace.get("1.0", tk.END).strip()
            rule_data["trimString"] = txt_trim.get("1.0", tk.END).strip()
            rule_data["disabled"] = other_vars["disabled"].get()
            rule_data["runOnEdit"] = other_vars["runOnEdit"].get()
            rule_data["macroMode"] = macro_combo.get()
            rule_data["formatDisplay"] = ephemeral_vars["formatDisplay"].get()
            rule_data["formatPrompt"] = ephemeral_vars["formatPrompt"].get()
            
            # 验证正则表达式
            if new_pattern:
                try:
                    if new_pattern.startswith("/") and new_pattern.count("/") >= 2:
                        parts = new_pattern.split("/")
                        flags_str = parts[-1]
                        pure_pattern = "/".join(parts[1:-1])
                        py_flags = 0
                        if 'i' in flags_str: py_flags |= re.IGNORECASE
                        if 'm' in flags_str: py_flags |= re.MULTILINE
                        if 's' in flags_str: py_flags |= re.DOTALL
                        re.compile(pure_pattern, py_flags)
                    else:
                        re.compile(new_pattern)
                    # 编译成功，清除错误标记
                    if '_compile_error' in rule_data:
                        del rule_data['_compile_error']
                except re.error as e:
                    rule_data['_compile_error'] = str(e)
                    messagebox.showwarning("正则表达式错误", f"该正则表达式有语法错误:\n{str(e)}\n\n仍然可以保存，但该规则将被跳过。")

            # 处理深度数字
            for e, key in [(ent_min, "minDepth"), (ent_max, "maxDepth")]:
                v = e.get()
                rule_data[key] = int(v) if v.isdigit() else None

            self.refresh_regex_ui()
            dialog.destroy()
            self.save_session_state()

        tk.Button(btn_frame, text="保存", command=do_save, bg="#8c4a4a", fg="white", 
                font=("微软雅黑", 10, "bold"), relief="flat", width=12, pady=5).pack(side=tk.LEFT, padx=(180, 20))
        tk.Button(btn_frame, text="取消", command=dialog.destroy, bg="#ffffff", fg="#666",
                font=("微软雅黑", 10), relief="flat", width=10).pack(side=tk.LEFT)
        
    def sync_regex_checkbox(self, rule_data, var):
        """同步复选框状态到规则数据"""
        rule_data['disabled'] = not var.get()

    def remove_regex(self, frame, rule_data):
        """从 UI 和内存中移除指定的正则规则（带确认）"""
        if not messagebox.askyesno("确认删除", f"确定要删除正则规则 '{rule_data.get('scriptName', '')}' 吗？"):
            return

        # 从 regex_rules_data 中删除对应项并销毁 UI
        for r in list(self.regex_rules_data):
            try:
                if r.get('data') is rule_data or r.get('data') == rule_data:
                    if r.get('frame'):
                        try:
                            r['frame'].destroy()
                        except Exception:
                            pass
                    try:
                        self.regex_rules_data.remove(r)
                    except ValueError:
                        pass
            except Exception:
                pass

        # 同步到 regex_rules_list（如果存在）
        try:
            if rule_data in self.regex_rules_list:
                self.regex_rules_list.remove(rule_data)
        except Exception:
            pass

        # 保存并刷新 UI
        self.save_session_state()
        # 如果需要完整刷新（可选）
        try:
            self.refresh_regex_ui()
        except Exception:
            pass

    def refresh_regex_ui(self):
        """刷新正则规则 UI 显示"""
        
        # 清空旧的 UI 项
        if hasattr(self, 'scrollable_frame_regex'):
            for widget in self.scrollable_frame_regex.winfo_children():
                widget.destroy()
        
        self.regex_rules_data = []
        
        # 为每条规则添加到 UI
        for i, rule in enumerate(self.regex_rules_list):
            print(f"DEBUG: 添加规则 {i+1}/{len(self.regex_rules_list)}: {rule.get('scriptName', '未命名')}")
            self.add_regex_item_to_ui(rule)
        

    def load_regex_config(self):
        """从文件加载正则配置"""
        try:
            config_path = os.path.join("regex", "【象牙塔（251213-01）】正则-多合一版.json")
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.regex_rules_list = json.load(f)
                self.refresh_regex_ui()
            else:
                self.regex_rules_list = []
        except Exception as e:
            print(f"加载失败: {e}")
            self.regex_rules_list = []

    def save_regex_config(self):
        """保存正则配置到文件"""
        try:
            config_path = os.path.join("regex", "【象牙塔（251213-01）】正则-多合一版.json")
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.regex_rules_list, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("成功", "正则配置已保存")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")


    def sync_regex_data(self, key):
        """已弃用：编辑现在通过对话框进行"""
        pass

    def add_new_regex(self):
        """添加一条空规则"""
        new_rule = {
            "scriptName": "新规则",
            "findRegex": "",
            "replaceString": "",
            "disabled": False,
            "minDepth": None,
            "maxDepth": None,
            "markdownOnly": False,
            "promptOnly": False,
            "runOnEdit": False
        }
        self.regex_rules_list.append(new_rule)
        self.add_regex_item_to_ui(new_rule)
        # 自动弹出编辑对话框
        var = tk.BooleanVar(value=not new_rule.get('disabled', False))
        self.open_regex_editor(new_rule, var)
    
    def apply_all_regex(self, text):
        """
        应用所有正则规则，并生成调试日志。
        日志文件将保存在程序运行目录下：regex_debug_log.txt
        """
        processed_text = text
        errors = []
        debug_logs = [] # 用于存储调试信息
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        debug_logs.append(f"=== 正则处理报告 {timestamp} ===")
        debug_logs.append(f"【输入文本长度】: {len(text)}")
        debug_logs.append("-" * 50)

        for i, rule in enumerate(self.regex_rules_list):
            if rule.get("disabled", False):
                continue
            
            rule_name = rule.get('scriptName', f'Rule-{i}')
            raw_find = rule.get("findRegex", "")
            raw_replace = rule.get("replaceString", "")
            
            if not raw_find: continue

            # 初始化变量防止 UnboundLocalError
            py_pattern = raw_find
            py_replace = raw_replace
            py_flags = 0
            match_count = 0
            
            try:
                # 1. 转换查找模式
                py_pattern, py_flags = self._parse_js_regex(raw_find)
                
                # 2. 转换替换字符串 ($1 -> \1)
                py_replace = self._convert_js_replacement(raw_replace)
                
                # 3. 编译
                compiled_pattern = re.compile(py_pattern, py_flags)
                
                # 4. 执行替换 (同时计算匹配次数，为了调试)
                # subn 返回 (new_string, number_of_subs_made)
                new_text, count = compiled_pattern.subn(py_replace, processed_text)
                
                if count > 0:
                    processed_text = new_text
                    match_count = count
                
                # 5. 记录调试信息 (只记录发生转换或命中的关键信息)
                log_entry = [
                    f"规则: {rule_name}",
                    f"  [原始查找]: {raw_find}",
                    f"  [Python查找]: {py_pattern} (Flags: {py_flags})",
                    f"  [原始替换]: {raw_replace}",
                    f"  [Python替换]: {py_replace}",
                    f"  >> 命中次数: {match_count}"
                ]
                debug_logs.append("\n".join(log_entry))
                debug_logs.append("-" * 30)

                # 清除错误标记
                if '_compile_error' in rule: del rule['_compile_error']

            except re.error as regex_err:
                err_msg = f"❌ 编译错误 [{rule_name}]: {str(regex_err)}"
                errors.append(err_msg)
                debug_logs.append(err_msg)
                rule['_compile_error'] = str(regex_err)
            except Exception as e:
                err_msg = f"❌ 未知错误 [{rule_name}]: {str(e)}"
                errors.append(err_msg)
                debug_logs.append(err_msg)

        debug_logs.append(f"【最终文本长度】: {len(processed_text)}")
        
        # 将调试信息写入文件（覆盖模式，每次处理生成最新的）
        try:
            with open("regex_debug_log.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(debug_logs))
            # print("DEBUG: 正则调试日志已生成 -> regex_debug_log.txt") 
        except Exception as e:
            print(f"无法写入调试日志: {e}")

        if errors:
            print("\n".join(errors))
            
        return processed_text
    
    def save_session_state(self, event=None):
        """保存当前所有界面控件、模块预设和正则规则到临时文件"""
        
        # 1. 整理模块数据 (Modules/Presets)
        # 我们需要把当前内存中 module_controls 里的数据（包括是否勾选）都存下来
        current_presets = []
        for m in self.module_controls:
            data = m['data'].copy()  # 浅拷贝原始数据
            data['enabled'] = m['var'].get()  # 同步当前的勾选状态
            current_presets.append(data)

        # 2. 构建完整状态字典
        state = {
            "api": {k: v.get().strip() for k, v in self.api_entries.items()},
            "model": self.model_combo.get(),
            "persona": {
                "char_name": self.entry_char_name.get(),
                "char_bio": self.text_char_bio.get("1.0", tk.END).strip(),
                "first_msg": self.text_first_msg.get("1.0", tk.END).strip(),
                "user_name": self.entry_user_name.get(),
                "user_bio": self.text_user_bio.get("1.0", tk.END).strip(),
                "insert_pos": self.combo_insert_pos.get(),
                "selected_char_file": self.char_combo.get(),
                "selected_user_file": self.user_combo.get()
            },
            "params": {k: v.get() for k, v in self.param_vars.items()},
            "tts": {
                "enabled": self.tts_enabled_var.get(),
                "config": {k: v.get() for k, v in self.tts_entries.items()}
            },
            # --- 新增：保存完整的模块和正则列表 ---
            "presets": self.preset_data_list,       # 直接保存预设数据列表
            "regex": self.regex_rules_list    # 保存所有正则规则
            ,
            # 保存模块 UI 的当前分类选择
            "modules": {
                "selected_category": self.module_category_combo.get() if hasattr(self, 'module_category_combo') else None
            }
            # -----------------------------------
        }
        # 保存布局信息（侧边栏宽度），以便重启时恢复分割位置
        try:
            sidebar_w = self.sidebar.winfo_width() if hasattr(self, 'sidebar') else None
            state['layout'] = {"sidebar_width": sidebar_w}
        except Exception:
            pass

        try:
            with open("session_state.json", "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Auto-save failed: {e}")

    # ----------------- 聊天持久化相关方法 -----------------
    def _list_chat_files(self):
        try:
            files = [f for f in os.listdir(self.chat_dir) if f.endswith('.json')]
            # 返回文件名（去掉扩展）并按修改时间排序（最近的在前）
            files = sorted(files, key=lambda p: os.path.getmtime(os.path.join(self.chat_dir, p)), reverse=True)
            return [os.path.splitext(f)[0] for f in files]
        except Exception:
            return []

    def populate_chat_list(self):
        items = self._list_chat_files()
        try:
            self.chat_combo['values'] = items
            # 尝试恢复当前会话选择
            if self.current_chat and self.current_chat in items:
                self.chat_combo.set(self.current_chat)
            elif items and not self.chat_combo.get():
                self.chat_combo.set(items[0])
                # 不自动加载第一个，等待用户选择
        except Exception:
            pass

    def new_chat(self):
        name = simpledialog.askstring("新建会话", "请输入会话名称:")
        if not name:
            return
        safe_name = name.strip()
        if not safe_name:
            return
        path = os.path.join(self.chat_dir, f"{safe_name}.json")
        if os.path.exists(path) and not messagebox.askyesno("覆盖确认", f"会话 '{safe_name}' 已存在，是否覆盖并清空？"):
            return
        # 清空当前显示与内存
        self.chat_history = []
        self.chat_display.config(state='normal')
        self.chat_display.delete('1.0', tk.END)
        self.chat_display.config(state='disabled')
        # 创建文件
        now = datetime.now().isoformat()
        payload = {"name": safe_name, "created_at": now, "last_modified": now, "messages": []}
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("错误", f"创建会话失败: {e}")
            return
        self.current_chat = safe_name
        self.populate_chat_list()
        self.chat_combo.set(safe_name)

    def save_chat_as(self):
        # 弹出对话框让用户输入新名字并保存当前 chat_history
        name = simpledialog.askstring("保存为", "请输入会话名称:")
        if not name:
            return
        safe_name = name.strip()
        if not safe_name:
            return
        path = os.path.join(self.chat_dir, f"{safe_name}.json")
        now = datetime.now().isoformat()
        payload = {"name": safe_name, "created_at": now, "last_modified": now, "messages": self.chat_history}
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            self.current_chat = safe_name
            self.populate_chat_list()
            self.chat_combo.set(safe_name)
            messagebox.showinfo("已保存", f"会话已保存: {safe_name}")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {e}")

    def auto_save_current_chat(self):
        # 自动将当前 chat_history 写入当前 chat 文件
        if not self.current_chat:
            return
        path = os.path.join(self.chat_dir, f"{self.current_chat}.json")
        now = datetime.now().isoformat()
        payload = {}
        # 如果已有文件，尽量保留创建时间
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    payload = json.load(f)
            except Exception:
                payload = {}
        payload['name'] = self.current_chat
        payload['messages'] = self.chat_history
        payload['last_modified'] = now
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"自动保存会话失败: {e}")

    def load_chat(self, name):
        if not name:
            return
        path = os.path.join(self.chat_dir, f"{name}.json")
        if not os.path.exists(path):
            messagebox.showwarning("未找到", f"会话文件不存在: {name}")
            self.populate_chat_list()
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                payload = json.load(f)
            msgs = payload.get('messages', [])
            self.chat_history = msgs
            # 刷新显示
            self.chat_display.config(state='normal')
            self.chat_display.delete('1.0', tk.END)
            for m in msgs:
                role = m.get('role', 'user')
                content = m.get('content', '')
                name_label = self.entry_user_name.get() if role == 'user' else self.entry_char_name.get()
                if role == 'system':
                    name_label = 'System'
                self.chat_display.insert(tk.END, f"【{name_label}】\n")
                self.chat_display.insert(tk.END, f"{content}\n\n")
            self.chat_display.config(state='disabled')
            self.current_chat = name
            try:
                self.chat_combo.set(name)
            except Exception:
                pass
        except Exception as e:
            messagebox.showerror("错误", f"加载会话失败: {e}")

    def delete_chat_ui(self):
        name = self.chat_combo.get()
        if not name:
            messagebox.showinfo("提示", "请先选择要删除的会话")
            return
        if not messagebox.askyesno("确认删除", f"确定要删除会话 '{name}' 吗？此操作不可恢复。"):
            return
        path = os.path.join(self.chat_dir, f"{name}.json")
        try:
            if os.path.exists(path):
                os.remove(path)
            # 如果删除的是当前会话，清空
            if self.current_chat == name:
                self.current_chat = None
                self.chat_history = []
                self.chat_display.config(state='normal')
                self.chat_display.delete('1.0', tk.END)
                self.chat_display.config(state='disabled')
            self.populate_chat_list()
            messagebox.showinfo("已删除", f"会话 '{name}' 已删除")
        except Exception as e:
            messagebox.showerror("错误", f"删除失败: {e}")
    # ----------------- 结束 聊天持久化 -----------------

    def toggle_sidebar(self):
        """切换左侧侧边栏显示/隐藏。隐藏时保留聊天区域独占窗口，显示时恢复原始顺序。"""
        try:
            if getattr(self, 'sidebar_hidden', False):
                # show: reinsert sidebar to left of chat_frame
                try:
                    self.main_paned.forget(self.chat_frame)
                except Exception:
                    pass
                try:
                    self.main_paned.add(self.sidebar)
                except Exception:
                    pass
                try:
                    self.main_paned.add(self.chat_frame)
                except Exception:
                    pass
                self.sidebar_hidden = False
            else:
                try:
                    self.main_paned.forget(self.sidebar)
                except Exception:
                    pass
                self.sidebar_hidden = True
        except Exception as e:
            print(f"切换侧栏错误: {e}")

    def load_session_state(self):
        """应用启动时加载上次的状态（包括预设和正则）"""
        if not os.path.exists("session_state.json"):
            return

        try:
            with open("session_state.json", "r", encoding="utf-8") as f:
                state = json.load(f)
            
            # --- 1. 基础 UI 恢复 (保持原样) ---
            api_data = state.get("api", {})
            for k, v in api_data.items():
                if k in self.api_entries:
                    self.api_entries[k].delete(0, tk.END)
                    self.api_entries[k].insert(0, v)
            
            if state.get("model"): self.model_combo.set(state.get("model"))

            # 恢复布局（侧边栏宽度）
            layout = state.get('layout', {})
            if layout and layout.get('sidebar_width'):
                try:
                    w = int(layout.get('sidebar_width'))
                    # 尝试设置 notebook 宽度以恢复分割位置
                    if hasattr(self, 'sidebar'):
                        self.sidebar.configure(width=w)
                except Exception:
                    pass

            p_data = state.get("persona", {})
            self.entry_char_name.delete(0, tk.END); self.entry_char_name.insert(0, p_data.get("char_name", ""))
            self.text_char_bio.delete("1.0", tk.END); self.text_char_bio.insert("1.0", p_data.get("char_bio", ""))
            self.text_first_msg.delete("1.0", tk.END); self.text_first_msg.insert("1.0", p_data.get("first_msg", ""))
            self.entry_user_name.delete(0, tk.END); self.entry_user_name.insert(0, p_data.get("user_name", ""))
            self.text_user_bio.delete("1.0", tk.END); self.text_user_bio.insert("1.0", p_data.get("user_bio", ""))
            if p_data.get("insert_pos"): self.combo_insert_pos.set(p_data.get("insert_pos"))
            if p_data.get("selected_char_file"): self.char_combo.set(p_data.get("selected_char_file"))
            if p_data.get("selected_user_file"): self.user_combo.set(p_data.get("selected_user_file"))

            param_data = state.get("params", {})
            for k, v in param_data.items():
                if k in self.param_vars:
                    self.param_vars[k].delete(0, tk.END)
                    self.param_vars[k].insert(0, v)
                    self.param_vars[k].event_generate("<KeyRelease>") 

            tts_data = state.get("tts", {})
            self.tts_enabled_var.set(tts_data.get("enabled", False))
            self.on_tts_enable_toggle()
            for k, v in tts_data.get("config", {}).items():
                if k in self.tts_entries:
                    self.tts_entries[k].delete(0, tk.END)
                    self.tts_entries[k].insert(0, v)

            # --- 2. 恢复模块预设 (Modules) ---
            if "presets" in state and isinstance(state["presets"], list):
                # 加载数据到列表，然后尝试恢复上次选择的分类再刷新 UI
                self.preset_data_list = state["presets"]
                modules_state = state.get('modules', {})
                sel_cat = modules_state.get('selected_category')
                if sel_cat and hasattr(self, 'module_category_combo'):
                    try:
                        self.module_category_combo.set(sel_cat)
                    except Exception:
                        pass
                self.refresh_modules_ui()

            # --- 3. 恢复正则规则 (Regex) ---
            if "regex" in state and isinstance(state["regex"], list):
                self.regex_rules_list = state["regex"]
                self.refresh_regex_ui()

            print("✅ 完整会话状态（含预设与正则）已恢复")
            
        except Exception as e:
            print(f"❌ 加载会话失败: {e}")
            import traceback
            traceback.print_exc()

    def _parse_js_regex(self, regex_str):
        """
        将 JS 风格正则 (e.g., /abc/gi) 转换为 Python 风格 (abc, re.I)。
        """
        if not regex_str:
            return "", 0

        pattern = regex_str
        flags = 0
        
        # 识别 /pattern/flags 格式
        if regex_str.startswith("/") and len(regex_str) > 2:
            last_slash_index = regex_str.rfind("/")
            
            # 确保最后一个斜杠不是转义字符（例如 \/）
            # 简单的检查：看它前面是不是反斜杠。如果是，继续往前找。
            # 但为了稳健，如果倒数第二个字符不是转义符，通常就安全了。
            # 这里使用简化逻辑：只要最后一部分是纯标志位字符，就认为是结束符。
            if last_slash_index > 0:
                flag_str = regex_str[last_slash_index+1:]
                # 检查后缀是否只包含合法的 JS 标志位
                if all(c in "gimsuy" for c in flag_str):
                    pattern = regex_str[1:last_slash_index]
                    if 'i' in flag_str: flags |= re.IGNORECASE
                    if 'm' in flag_str: flags |= re.MULTILINE
                    if 's' in flag_str: flags |= re.DOTALL
                    # 'g' 在 Python re.sub 中是默认行为，无需处理
                else:
                    # 可能是路径字符串或其他，保持原样
                    pass 
        
        return pattern, flags

    def _convert_js_replacement(self, replace_str):
        """
        将 JS 风格的替换字符串 ($1, $& 等) 转换为 Python 风格，
        并对普通反斜杠进行转义保护，防止 re.sub 报 bad escape 错误。
        """
        if not replace_str:
            return ""
        
        # --- 关键修复步骤 ---
        # 1. 先将原字符串中所有的 "\" 替换为 "\\" (双反斜杠)
        # 这样 HTML/JS 代码里的 \w, \n, \s 就会变成 \\w, \\n, \\s
        # re.sub 在执行替换时，遇到 \\ 会输出为单斜杠 \，从而还原你的原始代码
        safe_replace = replace_str.replace('\\', '\\\\')
        
        # 2. 将 $1, $2 ... $99 转换为 \1, \2 ... \99
        # 此时我们引入的是 Python 正则的引用符，不需要双重转义
        new_replace = re.sub(r'\$(\d+)', r'\\\1', safe_replace)
        
        # 3. 将 $& (匹配到的整个字符串) 转换为 \g<0>
        new_replace = new_replace.replace('$&', r'\g<0>')
        
        return new_replace
if __name__ == "__main__":
    root = tk.Tk()
    app = WindPoetry(root)
    root.mainloop()
