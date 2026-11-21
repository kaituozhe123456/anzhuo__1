import flet as ft
from tkinter import messagebox, filedialog
from datetime import datetime
import json
from pathlib import Path
import uuid
import os
import time  

# ================= 配色与主题 =================
ctk.set_appearance_mode("light")
COLOR_BG = "#F2F4F7"  
COLOR_CARD = "#FFFFFF"  
COLOR_TEXT = "#1A1A1A"  
COLOR_TEXT_GRAY = "#8E8E93"  
COLOR_RED = "#FF3B30"  
COLOR_ORANGE = "#FFB300"  
COLOR_BLUE = "#007AFF"  

# ================= 路径配置 =================
NOTES_DIR = Path("my_notes")
NOTES_DIR.mkdir(exist_ok=True)
ALARMS_FILE = Path("alarms.json")

# =====================================================================
# 🌟 性能丝滑版：带长按连发功能的滚轮选择器 🌟
# =====================================================================
class TimeWheel(ctk.CTkFrame):
    def __init__(self, master, values, font_size=36, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.values = values
        self.index = 0
        
        self.repeat_job = None
        self.repeat_dir = 0

        self.btn_up = ctk.CTkButton(self, text="▲", width=30, height=20, fg_color="transparent", 
                                    text_color="#C7C7CC", hover_color="#E0E0E0")
        self.btn_up.pack()
        
        self.lbl = ctk.CTkLabel(self, text=values[self.index], font=("Consolas", font_size, "bold"), 
                                text_color=COLOR_TEXT, width=60, height=45)
        self.lbl.pack()
        
        self.btn_down = ctk.CTkButton(self, text="▼", width=30, height=20, fg_color="transparent", 
                                      text_color="#C7C7CC", hover_color="#E0E0E0")
        self.btn_down.pack()

        for widget in [self, self.lbl, self.btn_up, self.btn_down]:
            widget.bind("<MouseWheel>", self.on_mousewheel)

        self.btn_up.bind("<ButtonPress-1>", lambda e: self.start_repeat(1))
        self.btn_up.bind("<ButtonRelease-1>", self.stop_repeat)
        self.btn_up.bind("<Leave>", self.stop_repeat) 
        
        self.btn_down.bind("<ButtonPress-1>", lambda e: self.start_repeat(-1))
        self.btn_down.bind("<ButtonRelease-1>", self.stop_repeat)
        self.btn_down.bind("<Leave>", self.stop_repeat)

    def up(self):
        self.index = (self.index + 1) % len(self.values)
        self.lbl.configure(text=self.values[self.index])

    def down(self):
        self.index = (self.index - 1) % len(self.values)
        self.lbl.configure(text=self.values[self.index])

    def on_mousewheel(self, event):
        if event.delta > 0: self.up()
        else: self.down()

    def start_repeat(self, direction):
        self.stop_repeat() 
        self.repeat_dir = direction
        if direction == 1: self.up()
        else: self.down()
        self.repeat_job = self.after(250, self.do_repeat)

    def do_repeat(self):
        if self.repeat_dir == 1: self.up()
        else: self.down()
        self.repeat_job = self.after(40, self.do_repeat)

    def stop_repeat(self, event=None):
        if self.repeat_job:
            self.after_cancel(self.repeat_job)
            self.repeat_job = None
        self.repeat_dir = 0
            
    def get(self): return self.values[self.index]

    def set(self, val):
        if val in self.values:
            self.index = self.values.index(val)
            self.lbl.configure(text=val)
        elif len(self.values) > 0:
            self.index = 0
            self.lbl.configure(text=self.values[self.index])
# =====================================================================


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("尚上签")
        self.geometry("420x750")
        self.configure(fg_color=COLOR_BG)

        # --- 全局数据 ---
        self.alarms = self.load_alarms()
        self.last_triggered = ""
        self.selected_file_path = ""

        # --- 便签数据 ---
        self.current_note_file = None
        self.is_selection_mode = False
        self.selected_notes = set() 

        # --- 长按检测变量 ---
        self.press_time = 0
        self.press_target = None

        # --- 主框架 ---
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, pady=(0, 60))

        # 构建各个页面
        self.build_today_pages() 
        self.build_note_pages()  
        self.build_nav_bar()  

        # 初始加载数据（只在启动时刷新一次）
        self.refresh_today_list()
        self.refresh_note_list()

        # 默认启动页面
        self.show_page("today")
        self.check_alarms()  

    def load_alarms(self):
        if ALARMS_FILE.exists():
            try: return json.loads(ALARMS_FILE.read_text(encoding="utf-8"))
            except: return []
        return []

    def save_alarms(self):
        ALARMS_FILE.write_text(json.dumps(self.alarms, ensure_ascii=False), encoding="utf-8")

    # =====================================================================
    # ======================= 页面导航与全局框架 ===========================
    # =====================================================================
    def build_nav_bar(self):
        self.nav_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD, height=60, corner_radius=0)
        self.nav_frame.pack(side="bottom", fill="x")
        self.nav_frame.pack_propagate(False)

        self.btn_nav_today = ctk.CTkButton(self.nav_frame, text="⏰\n今日", font=("微软雅黑", 12),
                                           fg_color="transparent", text_color=COLOR_RED, hover_color="#E0E0E0",
                                           command=lambda: self.show_page("today"))
        self.btn_nav_today.pack(side="left", expand=True, pady=10)

        self.btn_nav_note = ctk.CTkButton(self.nav_frame, text="📝\n签签", font=("微软雅黑", 12), fg_color="transparent",
                                          text_color=COLOR_TEXT_GRAY, hover_color="#E0E0E0",
                                          command=lambda: self.show_page("note"))
        self.btn_nav_note.pack(side="left", expand=True, pady=10)

    def show_page(self, page_name):
        # 隐藏所有页面
        self.page_today.pack_forget()
        self.page_today_edit.pack_forget()
        self.page_note_list.pack_forget()
        self.page_note_edit.pack_forget()

        # 🌟 性能优化：去掉了这里的 refresh_xxx，直接显示，瞬间秒切！🌟
        if page_name == "today":
            self.btn_nav_today.configure(text_color=COLOR_RED)
            self.btn_nav_note.configure(text_color=COLOR_TEXT_GRAY)
            self.page_today.pack(fill="both", expand=True)
        elif page_name == "note":
            self.btn_nav_today.configure(text_color=COLOR_TEXT_GRAY)
            self.btn_nav_note.configure(text_color=COLOR_RED)
            self.exit_selection_mode()  
            self.page_note_list.pack(fill="both", expand=True)

    # =====================================================================
    # =========================== 今日 功能 ===============================
    # =====================================================================
    def build_today_pages(self):
        self.page_today = ctk.CTkFrame(self.container, fg_color="transparent")

        header = ctk.CTkFrame(self.page_today, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(header, text="今日提醒", font=("微软雅黑", 28, "bold"), text_color=COLOR_TEXT).pack(side="left")

        self.scroll_today = ctk.CTkScrollableFrame(self.page_today, fg_color="transparent")
        self.scroll_today.pack(fill="both", expand=True, padx=15, pady=10)

        self.add_btn_today = ctk.CTkButton(self.page_today, text="+", width=64, height=64, corner_radius=32,
                                           font=("微软雅黑", 32), fg_color=COLOR_RED, hover_color="#D62C22",
                                           command=self.show_today_edit)
        self.add_btn_today.place(relx=0.85, rely=0.85, anchor="center")

        self.page_today_edit = ctk.CTkFrame(self.container, fg_color=COLOR_BG)

        top_nav = ctk.CTkFrame(self.page_today_edit, fg_color="transparent")
        top_nav.pack(fill="x", padx=15, pady=15)
        ctk.CTkButton(top_nav, text="取消", width=60, fg_color="transparent", text_color=COLOR_RED,
                      font=("微软雅黑", 16), command=lambda: self.show_page("today")).pack(side="left")
        ctk.CTkLabel(top_nav, text="新建提醒", font=("微软雅黑", 18, "bold")).pack(side="left", expand=True)
        ctk.CTkButton(top_nav, text="完成", width=60, fg_color="transparent", text_color=COLOR_RED,
                      font=("微软雅黑", 16, "bold"), command=self.save_from_today_edit).pack(side="right")

        time_frame = ctk.CTkFrame(self.page_today_edit, fg_color=COLOR_CARD, corner_radius=15)
        time_frame.pack(fill="x", padx=15, pady=10, ipady=10)
        inner_time = ctk.CTkFrame(time_frame, fg_color="transparent")
        inner_time.pack(pady=10)
        
        self.hour_picker = TimeWheel(inner_time, values=[f"{i:02d}" for i in range(24)])
        self.hour_picker.pack(side="left")
        ctk.CTkLabel(inner_time, text="时", font=("微软雅黑", 18), text_color=COLOR_TEXT_GRAY).pack(side="left", padx=(5, 15))
        
        self.min_picker = TimeWheel(inner_time, values=[f"{i:02d}" for i in range(0, 60, 5)])
        self.min_picker.pack(side="left")
        ctk.CTkLabel(inner_time, text="分", font=("微软雅黑", 18), text_color=COLOR_TEXT_GRAY).pack(side="left", padx=(5, 0))

        file_frame = ctk.CTkFrame(self.page_today_edit, fg_color="transparent")
        file_frame.pack(fill="x", padx=15, pady=(10, 5))
        ctk.CTkButton(file_frame, text="📁 选择提醒文档", width=140, fg_color=COLOR_CARD, text_color=COLOR_RED,
                      border_width=1, border_color=COLOR_RED, hover_color="#FFE5E5",
                      command=self.select_today_file).pack(side="left")
        self.file_label = ctk.CTkLabel(file_frame, text="未选择", font=("微软雅黑", 12), text_color=COLOR_TEXT_GRAY)
        self.file_label.pack(side="left", padx=10)

        self.today_textbox = ctk.CTkTextbox(self.page_today_edit, height=100, font=("微软雅黑", 16), corner_radius=10,
                                            border_width=1)
        self.today_textbox.pack(fill="x", padx=15, pady=5)

        self.mode_var = ctk.StringVar(value="仅弹窗")
        ctk.CTkSegmentedButton(self.page_today_edit, values=["仅弹窗", "响铃提醒"], variable=self.mode_var, height=40,
                               font=("微软雅黑", 14), selected_color=COLOR_RED).pack(fill="x", padx=15, pady=15)

    def refresh_today_list(self):
        for widget in self.scroll_today.winfo_children(): widget.destroy()
        self.alarms.sort(key=lambda x: x["time"])

        for alarm in self.alarms:
            card = ctk.CTkFrame(self.scroll_today, fg_color=COLOR_CARD, corner_radius=15)
            card.pack(fill="x", pady=8, ipady=8)

            left = ctk.CTkFrame(card, fg_color="transparent")
            left.pack(side="left", padx=15, fill="y")
            ctk.CTkLabel(left, text=alarm["time"], font=("微软雅黑", 26, "bold"),
                         text_color=COLOR_TEXT if alarm["active"] else COLOR_TEXT_GRAY).pack(anchor="w")
            ctk.CTkLabel(left, text=f"{alarm['period']} | {'🔔' if alarm['mode'] == 'alarm' else '💬'}",
                         font=("微软雅黑", 12), text_color=COLOR_TEXT_GRAY).pack(anchor="w")

            file_path = alarm.get("file_path")
            if file_path:
                lbl = ctk.CTkLabel(card, text=f"📄 {alarm['content']}", font=("微软雅黑", 15, "bold", "underline"),
                                   text_color=COLOR_BLUE if alarm["active"] else COLOR_TEXT_GRAY, wraplength=160,
                                   justify="left", cursor="hand2")
                lbl.bind("<Button-1>", lambda e, p=file_path: os.startfile(p) if os.path.exists(p) else None)
            else:
                ctk.CTkLabel(card, text=alarm["content"], font=("微软雅黑", 15, "bold"),
                             text_color=COLOR_TEXT if alarm["active"] else COLOR_TEXT_GRAY, wraplength=160,
                             justify="left").pack(side="left", padx=5, expand=True, fill="x")
            if file_path: lbl.pack(side="left", padx=5, expand=True, fill="x")

            right = ctk.CTkFrame(card, fg_color="transparent")
            right.pack(side="right", padx=10, fill="y")
            ctk.CTkButton(right, text="✕", width=24, height=24, fg_color="transparent", text_color=COLOR_TEXT_GRAY,
                          hover_color="#FFE5E5", command=lambda a=alarm: self.delete_alarm(a["id"])).pack(anchor="e")
            sw = ctk.CTkSwitch(right, text="", width=40, progress_color=COLOR_RED,
                               command=lambda a=alarm: self.toggle_alarm(a["id"]))
            sw.pack(anchor="e", pady=(5, 0))
            if alarm["active"]: sw.select()

    def show_today_edit(self):
        self.page_today.pack_forget()
        self.page_today_edit.pack(fill="both", expand=True)
        self.today_textbox.delete("0.0", "end")
        
        self.hour_picker.set("08")
        self.min_picker.set("00")
        
        self.mode_var.set("仅弹窗")
        self.selected_file_path = ""
        self.file_label.configure(text="未选择", text_color=COLOR_TEXT_GRAY)

    def select_today_file(self):
        path = filedialog.askopenfilename(filetypes=[("所有文档", "*.*")])
        if path:
            self.selected_file_path = path
            self.file_label.configure(text=f"已选: {Path(path).name}", text_color=COLOR_BLUE)

    def save_from_today_edit(self):
        content = self.today_textbox.get("0.0", "end").strip()
        if not content and not self.selected_file_path:
            return messagebox.showwarning("提示", "请输入内容或选择文档")
        if not content: content = Path(self.selected_file_path).name

        h_val = int(self.hour_picker.get())
        m_val = self.min_picker.get()
        period = "早" if 5 <= h_val < 11 else ("午" if 11 <= h_val < 18 else "晚")

        self.alarms.append({
            "id": str(uuid.uuid4()), 
            "time": f"{h_val:02d}:{m_val}",
            "period": period,
            "content": content, 
            "mode": "alarm" if self.mode_var.get() == "响铃提醒" else "popup",
            "file_path": self.selected_file_path, 
            "active": True
        })
        self.save_alarms()
        
        self.refresh_today_list() # 🌟 添加完成后，手动刷新一次
        self.show_page("today")

    def delete_alarm(self, aid):
        self.alarms = [a for a in self.alarms if a["id"] != aid]
        self.save_alarms()
        self.refresh_today_list()

    def toggle_alarm(self, aid):
        for a in self.alarms:
            if a["id"] == aid: a["active"] = not a["active"]
        self.save_alarms()
        self.refresh_today_list()

    def check_alarms(self):
        now = datetime.now().strftime("%H:%M")
        if now != self.last_triggered:
            for a in self.alarms:
                if a["active"] and a["time"] == now:
                    self.attributes('-topmost', True)
                    import winsound
                    winsound.Beep(1000, 800) if a["mode"] == "alarm" else None
                    messagebox.showinfo("时间到", f"【{a['period']}】\n\n{a['content']}")
                    self.attributes('-topmost', False)
                    self.last_triggered = now
                    break
        self.after(1000, self.check_alarms)

    # =====================================================================
    # =========================== 签签 功能 ===============================
    # =====================================================================
    def build_note_pages(self):
        self.page_note_list = ctk.CTkFrame(self.container, fg_color="transparent")

        self.note_top_nav = ctk.CTkFrame(self.page_note_list, fg_color="transparent")
        self.note_top_nav.pack(fill="x", padx=15, pady=(20, 10))

        self.lbl_note_title = ctk.CTkLabel(self.note_top_nav, text="签签", font=("微软雅黑", 28, "bold"))
        self.lbl_note_title.pack(side="left")

        self.btn_select_all = ctk.CTkButton(self.note_top_nav, text="全选", width=50, fg_color="transparent",
                                            text_color=COLOR_ORANGE, hover_color="#FFF3E0",
                                            command=self.toggle_select_all)
        self.lbl_selected_count = ctk.CTkLabel(self.note_top_nav, text="已选择 0 项", font=("微软雅黑", 18, "bold"))
        self.btn_cancel_select = ctk.CTkButton(self.note_top_nav, text="取消", width=50, fg_color="transparent",
                                               text_color=COLOR_ORANGE, hover_color="#FFF3E0",
                                               command=self.exit_selection_mode)

        self.scroll_notes = ctk.CTkScrollableFrame(self.page_note_list, fg_color="transparent")
        self.scroll_notes.pack(fill="both", expand=True, padx=15, pady=10)

        self.add_btn_note = ctk.CTkButton(self.page_note_list, text="+", width=64, height=64, corner_radius=32,
                                          font=("微软雅黑", 32), fg_color=COLOR_RED, hover_color="#D62C22",
                                          command=self.show_note_edit)
        self.add_btn_note.place(relx=0.85, rely=0.85, anchor="center")

        self.toolbar_frame = ctk.CTkFrame(self.page_note_list, fg_color=COLOR_CARD, corner_radius=20)
        ctk.CTkButton(self.toolbar_frame, text="🗑️\n删除", fg_color="transparent", text_color=COLOR_RED,
                      font=("微软雅黑", 14), hover_color="#FFE5E5", width=80, command=self.delete_selected_notes).pack(
            padx=20, pady=10)

        self.page_note_edit = ctk.CTkFrame(self.container, fg_color=COLOR_BG)

        edit_nav = ctk.CTkFrame(self.page_note_edit, fg_color="transparent")
        edit_nav.pack(fill="x", padx=15, pady=15)
        ctk.CTkButton(edit_nav, text="< 返回", width=60, fg_color="transparent", text_color=COLOR_BLUE,
                      font=("微软雅黑", 16), command=self.save_and_back_note).pack(side="left")
        ctk.CTkButton(edit_nav, text="保存", width=60, fg_color="transparent", text_color=COLOR_RED,
                      font=("微软雅黑", 16, "bold"), command=lambda: self.save_note(True)).pack(side="right")

        self.note_textbox = ctk.CTkTextbox(self.page_note_edit, font=("微软雅黑", 16), fg_color=COLOR_CARD,
                                           corner_radius=15)
        self.note_textbox.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    def refresh_note_list(self):
        for widget in self.scroll_notes.winfo_children(): widget.destroy()

        files = sorted(NOTES_DIR.glob("*.txt"), key=lambda f: f.stat().st_mtime, reverse=True)

        if not files:
            ctk.CTkLabel(self.scroll_notes, text="暂无便签", text_color=COLOR_TEXT_GRAY).pack(pady=50)
            return

        for f in files:
            # 🌟 性能优化：只读取前500个字符用于预览，防止大文件卡顿 🌟
            try:
                with open(f, "r", encoding="utf-8") as file:
                    content = file.read(500)
            except Exception:
                content = ""
                
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            title = lines[0] if lines else "无标题"
            preview = " ".join(lines[1:]) if len(lines) > 1 else "无更多内容..."
            date_str = datetime.fromtimestamp(f.stat().st_mtime).strftime("%m月%d日")

            card = ctk.CTkFrame(self.scroll_notes, fg_color=COLOR_CARD, corner_radius=15)
            card.pack(fill="x", pady=5, ipady=10)

            text_frame = ctk.CTkFrame(card, fg_color="transparent")
            text_frame.pack(side="left", fill="x", expand=True, padx=(15, 5))

            ctk.CTkLabel(text_frame, text=title, font=("微软雅黑", 16, "bold"), text_color=COLOR_TEXT, anchor="w").pack(fill="x")
            ctk.CTkLabel(text_frame, text=preview, font=("微软雅黑", 13), text_color=COLOR_TEXT_GRAY, anchor="w").pack(fill="x", pady=(2, 5))
            ctk.CTkLabel(text_frame, text=date_str, font=("微软雅黑", 11), text_color="#C7C7CC", fg_color="#F2F4F7",
                         corner_radius=5, padx=5).pack(anchor="w")

            if self.is_selection_mode:
                cb_var = ctk.BooleanVar(value=(f.name in self.selected_notes))
                cb = ctk.CTkCheckBox(card, text="", width=24, variable=cb_var, fg_color=COLOR_ORANGE,
                                     hover_color=COLOR_ORANGE,
                                     command=lambda name=f.name, var=cb_var: self.toggle_select_note(name, var))
                cb.pack(side="right", padx=(5, 15)) 

            widgets_to_bind = [card, text_frame] + text_frame.winfo_children()
            for w in widgets_to_bind:
                w.bind("<ButtonPress-1>", lambda e, name=f.name: self.on_mouse_press(name))
                w.bind("<ButtonRelease-1>", lambda e, name=f.name: self.on_mouse_release(name))

    def on_mouse_press(self, note_name):
        self.press_time = time.time()
        self.press_target = note_name

    def on_mouse_release(self, note_name):
        if self.press_target == note_name:
            duration = time.time() - self.press_time
            if duration >= 0.5:  
                if not self.is_selection_mode:
                    self.enter_selection_mode(note_name)
            else:  
                if self.is_selection_mode:
                    if note_name in self.selected_notes:
                        self.selected_notes.remove(note_name)
                    else:
                        self.selected_notes.add(note_name)
                    self.update_selection_ui()
                    self.refresh_note_list()
                else:
                    self.open_note_editor(NOTES_DIR / note_name)
            self.press_target = None

    def enter_selection_mode(self, first_note):
        self.is_selection_mode = True
        self.selected_notes.add(first_note)
        self.update_selection_ui()
        self.refresh_note_list()

    def exit_selection_mode(self):
        # 🌟 性能优化：如果本来就没在多选模式，直接 return，千万别再重新画列表了！🌟
        if not self.is_selection_mode:
            return

        self.is_selection_mode = False
        self.selected_notes.clear()

        self.btn_select_all.pack_forget()
        self.lbl_selected_count.pack_forget()
        self.btn_cancel_select.pack_forget()
        self.lbl_note_title.pack(side="left")
        self.add_btn_note.place(relx=0.85, rely=0.85, anchor="center")
        self.toolbar_frame.place_forget()

        self.refresh_note_list()

    def update_selection_ui(self):
        if not self.is_selection_mode: return

        self.lbl_note_title.pack_forget()
        self.add_btn_note.place_forget()

        self.btn_select_all.pack(side="left", padx=5)
        self.lbl_selected_count.pack(side="left", expand=True)
        self.lbl_selected_count.configure(text=f"已选择 {len(self.selected_notes)} 项")
        self.btn_cancel_select.pack(side="right", padx=5)

        self.toolbar_frame.place(relx=0.5, rely=0.9, anchor="center")

    def toggle_select_all(self):
        files = list(NOTES_DIR.glob("*.txt"))
        if len(self.selected_notes) == len(files):
            self.selected_notes.clear()
        else:
            self.selected_notes = {f.name for f in files}
        self.update_selection_ui()
        self.refresh_note_list()

    def toggle_select_note(self, name, var):
        if var.get():
            self.selected_notes.add(name)
        else:
            self.selected_notes.remove(name)
        self.update_selection_ui()

    def delete_selected_notes(self):
        if not self.selected_notes: return
        if not messagebox.askyesno("确认删除", f"确定要删除选中的 {len(self.selected_notes)} 项吗？"): return

        for name in self.selected_notes:
            file = NOTES_DIR / name
            if file.exists(): file.unlink()

        self.exit_selection_mode()

    def show_note_edit(self):
        self.current_note_file = NOTES_DIR / f"便签_{time.strftime('%H点%M分%S秒')}.txt"
        self.current_note_file.touch()
        self.note_textbox.delete("0.0", "end")

        self.page_note_list.pack_forget()
        self.page_note_edit.pack(fill="both", expand=True)
        self.note_textbox.focus_set()

    def open_note_editor(self, file_path):
        self.current_note_file = file_path
        self.note_textbox.delete("0.0", "end")
        self.note_textbox.insert("0.0", file_path.read_text(encoding="utf-8"))

        self.page_note_list.pack_forget()
        self.page_note_edit.pack(fill="both", expand=True)

    def save_note(self, show_msg=False):
        if self.current_note_file:
            content = self.note_textbox.get("0.0", "end-1c")
            self.current_note_file.write_text(content, encoding="utf-8")
            if show_msg:
                messagebox.showinfo("提示", "已保存")

    def save_and_back_note(self):
        self.save_note()
        self.page_note_edit.pack_forget()
        self.page_note_list.pack(fill="both", expand=True)
        self.refresh_note_list() # 🌟 退出编辑返回列表时，刷新一次，展示最新数据

if __name__ == "__main__":
    app = App()
    app.mainloop()
