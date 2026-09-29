import os
import re
import shutil
import time
import zipfile
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

try:
    import patoolib
    HAS_PATOOL = True
except ImportError:
    HAS_PATOOL = False

# --- CÁC HÀM TIỆN ÍCH ---
def get_tags_and_basename(folder_name):
    tags = []
    base_name = folder_name.strip()
    while True:
        match = re.match(r'^\[(.*?)\]\s*(.*)', base_name)
        if match:
            tags.append(match.group(1).strip())
            base_name = match.group(2).strip()
        else:
            break
    return tags, base_name

def format_folder_name(tags, base_name):
    if not tags: return base_name
    valid_tags = [f"[{t}]" for t in tags if t]
    if not valid_tags: return base_name
    return " ".join(valid_tags) + " " + base_name

def is_smart_match(char_name, target_name):
    """
    Thuật toán nhận diện thông minh (Inteli Routing): 
    Bỏ qua toàn bộ khoảng trắng/kí tự đặc biệt và tìm chuỗi con.
    """
    t_clean = re.sub(r'[^a-zA-Z0-9]', '', target_name).lower()
    c_clean = re.sub(r'[^a-zA-Z0-9]', '', char_name).lower()
    if not c_clean: return False
    return c_clean in t_clean

# --- COMPONENT UI ---
class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

# --- MODULE GIMI MOD WORKSPACE (TOOLBOX) ---
class GimiWorkspace(tk.Toplevel):
    def __init__(self, parent, app_instance):
        super().__init__(parent)
        self.app = app_instance
        self.title("GIMI Toolbox (Dùng 1 lần)")
        self.geometry("680x500")
        self.grab_set()

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # ================= TAB 1: AUTO-DEPLOY =================
        tab_deploy = ttk.Frame(notebook)
        notebook.add(tab_deploy, text="Triển khai File Mod (Auto-Route)")

        ttk.Label(tab_deploy, text="Tự nhận diện file -> Đưa vào folder nhân vật -> Giải nén (.zip/.rar/.7z) -> Khử lồng & Xoá nén gốc.", wraplength=600).pack(pady=10, padx=10, anchor="w")
        self.btn_deploy = ttk.Button(tab_deploy, text="Chọn Các File Nén (Zip/Rar/7z)", command=self.run_auto_deploy)
        self.btn_deploy.pack(pady=5, fill="x", padx=10)

        self.log_txt = tk.Text(tab_deploy, height=15, font=("Consolas", 9), state="disabled", 
                               bg=self.app.colors['field'], fg=self.app.colors['fg'], 
                               insertbackground=self.app.colors['cursor'])
        self.log_txt.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        # ================= TAB 2: BATCH CREATOR =================
        tab_batch = ttk.Frame(notebook)
        notebook.add(tab_batch, text="Tạo Thư Mục Hàng Loạt")
        
        ttk.Label(tab_batch, text="Nhập danh sách tên nhân vật (mỗi tên 1 dòng):").pack(pady=10, padx=10, anchor="w")
        self.txt_batch = tk.Text(tab_batch, height=15, font=("Segoe UI", 10), 
                                 bg=self.app.colors['field'], fg=self.app.colors['fg'], 
                                 insertbackground=self.app.colors['cursor'])
        self.txt_batch.pack(fill="both", expand=True, padx=10)
        ttk.Button(tab_batch, text="Tạo Các Thư Mục Này", command=self.run_batch_create).pack(pady=10, padx=10, fill="x")

        # ================= TAB 3: AUTO-MOVE FOLDERS =================
        tab_move = ttk.Frame(notebook)
        notebook.add(tab_move, text="Chuyển Folder (Auto-Move)")

        ttk.Label(tab_move, text="Chọn 1 Thư mục Nguồn đang chứa các folder Mod lộn xộn -> Hệ thống tự đối sánh và di chuyển chúng vào đúng folder Nhân vật.", wraplength=600).pack(pady=10, padx=10, anchor="w")
        self.btn_move = ttk.Button(tab_move, text="Chọn Thư mục chứa Mod cần chuyển", command=self.run_auto_move_folders)
        self.btn_move.pack(pady=5, fill="x", padx=10)

        self.log_txt_move = tk.Text(tab_move, height=15, font=("Consolas", 9), state="disabled", 
                               bg=self.app.colors['field'], fg=self.app.colors['fg'], 
                               insertbackground=self.app.colors['cursor'])
        self.log_txt_move.pack(fill="both", expand=True, padx=10, pady=(5, 10))

    def log(self, message, target_widget=None):
        if target_widget is None: target_widget = self.log_txt
        target_widget.config(state="normal")
        target_widget.insert(tk.END, message + "\n")
        target_widget.see(tk.END)
        target_widget.config(state="disabled")
        self.update_idletasks()

    def apply_rule_2(self, base_folder):
        base_folder_norm = os.path.normpath(base_folder)
        peeled = False
        while True:
            try: items = os.listdir(base_folder_norm)
            except Exception: break
            
            files = [f for f in items if os.path.isfile(os.path.join(base_folder_norm, f))]
            dirs = [d for d in items if os.path.isdir(os.path.join(base_folder_norm, d))]
            valid_files = [f for f in files if f.lower() not in ['desktop.ini', 'thumbs.db', '.ds_store']]
            
            if len(valid_files) > 0 or len(dirs) != 1:
                break
                
            single_sub_dir = dirs[0]
            sub_dir_path = os.path.join(base_folder_norm, single_sub_dir)
            self.log(f"   -> [Rule 2] Đang bóc lớp vỏ rác: '{single_sub_dir}'")
            
            try:
                sub_items = os.listdir(sub_dir_path)
                for item in sub_items:
                    src = os.path.join(sub_dir_path, item)
                    dst = os.path.join(base_folder_norm, item)
                    shutil.move(src, dst)
                os.rmdir(sub_dir_path)
                peeled = True
            except Exception as e:
                self.log(f"   -> [Rule 2] Bị chặn khi gỡ lồng: {e}")
                break
                
        if peeled: self.log("   -> [Rule 2] Gỡ lồng hoàn tất.")
        else: self.log("   -> [Rule 2] Cấu trúc đã chuẩn, bỏ qua gỡ lồng.")

    def run_auto_deploy(self):
        files = filedialog.askopenfilenames(title="Chọn Mod", filetypes=[("Archive Files", "*.zip *.rar *.7z")])
        if not files: return
        self.log("Bắt đầu quy trình Deploy...")
        
        # Sắp xếp nhân vật theo độ dài tên (ưu tiên Alhaitham trước Al)
        sorted_chars = sorted(self.app.folders, key=lambda f: len(get_tags_and_basename(f)[1]), reverse=True)

        for file_path in files:
            basename = os.path.basename(file_path)
            name_no_ext, ext = os.path.splitext(basename)
            ext = ext.lower()
            self.log(f"\nĐang xử lý: {basename}")

            target_char = None
            for folder_name in sorted_chars:
                _, char_name = get_tags_and_basename(folder_name)
                if is_smart_match(char_name, name_no_ext):
                    target_char = folder_name
                    break
            
            if not target_char:
                target_char = "Uncategorized_Mods"
                self.log(f"   -> Cảnh báo: Không khớp ai, đưa vào '{target_char}'")
                uncat_path = os.path.join(self.app.root_dir, target_char)
                if not os.path.exists(uncat_path): os.makedirs(uncat_path)

            dest_path = os.path.join(self.app.root_dir, target_char, name_no_ext)
            if not os.path.exists(dest_path): os.makedirs(dest_path)

            try:
                if ext == '.zip':
                    with zipfile.ZipFile(file_path, 'r') as zf:
                        zf.extractall(dest_path)
                elif ext in ['.rar', '.7z']:
                    if HAS_PATOOL:
                        patoolib.extract_archive(file_path, outdir=dest_path, interactive=False, verbosity=-1)
                    else:
                        raise Exception("Thiếu thư viện patool. Chạy 'pip install patool' và cài 7-Zip/WinRAR.")
                
                extracted_size = sum(os.path.getsize(os.path.join(dp, f)) for dp, dn, fn in os.walk(dest_path) for f in fn)
                if extracted_size == 0:
                    raise Exception("Lỗi: Giải nén xong thư mục bị rỗng (File nén có thể bị hỏng)!")

                self.log("   -> Giải nén thành công.")
                self.apply_rule_2(dest_path)
                os.remove(file_path)
                self.log("   -> Đã xoá file nén gốc.")

            except Exception as e:
                self.log(f"   -> LỖI: {e}")
                if os.path.exists(dest_path): shutil.rmtree(dest_path, ignore_errors=True)
        
        self.app.scan_directories()
        self.log("\n=== HOÀN TẤT DEPLOY ===")

    def run_auto_move_folders(self):
        source_dir = filedialog.askdirectory(title="Chọn thư mục NGUỒN chứa các Folder Mod")
        if not source_dir: return
        
        # Ngăn chặn việc chọn Root làm Nguồn gây loạn hệ thống
        if os.path.normpath(source_dir) == os.path.normpath(self.app.root_dir):
            messagebox.showerror("Lỗi", "Thư mục Nguồn không được trùng với Thư mục Root (Đích)!")
            return

        self.log("Bắt đầu quy trình Auto-Move Folders...", self.log_txt_move)
        
        try:
            items = os.listdir(source_dir)
            folders_to_move = [f for f in items if os.path.isdir(os.path.join(source_dir, f))]
        except Exception as e:
            self.log(f"-> Không thể đọc thư mục: {e}", self.log_txt_move)
            return
        
        if not folders_to_move:
            self.log("-> Không tìm thấy folder con nào trong thư mục Nguồn.", self.log_txt_move)
            return

        # Sắp xếp nhân vật theo độ dài tên
        sorted_chars = sorted(self.app.folders, key=lambda f: len(get_tags_and_basename(f)[1]), reverse=True)

        for folder_name in folders_to_move:
            src_path = os.path.join(source_dir, folder_name)
            self.log(f"\nĐang xử lý Folder: {folder_name}", self.log_txt_move)

            target_char = None
            for char_folder in sorted_chars:
                _, char_name = get_tags_and_basename(char_folder)
                if is_smart_match(char_name, folder_name):
                    target_char = char_folder
                    break
            
            if not target_char:
                target_char = "Uncategorized_Mods"
                self.log(f"   -> Không khớp ai, đưa vào '{target_char}'", self.log_txt_move)
                uncat_path = os.path.join(self.app.root_dir, target_char)
                if not os.path.exists(uncat_path): os.makedirs(uncat_path)

            dest_path = os.path.join(self.app.root_dir, target_char, folder_name)
            
            try:
                # Xử lý nếu folder đích đã tồn tại (Chống đè file)
                if os.path.exists(dest_path):
                    dest_path = dest_path + "_" + str(int(time.time()))
                
                shutil.move(src_path, dest_path)
                self.log(f"   -> Đã chuyển thành công vào: {target_char}", self.log_txt_move)
            except Exception as e:
                self.log(f"   -> LỖI: {e}", self.log_txt_move)

        self.app.scan_directories()
        self.log("\n=== HOÀN TẤT CHUYỂN FOLDER ===", self.log_txt_move)

    def run_batch_create(self):
        text = self.txt_batch.get("1.0", tk.END).strip()
        if not text: return
        folders = [f.strip() for f in text.split('\n') if f.strip()]
        if not folders: return
        
        if messagebox.askyesno("Xác nhận", f"Tạo {len(folders)} thư mục nhân vật?"):
            count = 0
            for f in folders:
                safe_f = re.sub(r'[\\/*?:"<>|]', "", f) 
                path = os.path.join(self.app.root_dir, safe_f)
                if not os.path.exists(path):
                    os.makedirs(path)
                    count += 1
            messagebox.showinfo("Thành công", f"Đã tạo {count} thư mục!")
            self.txt_batch.delete("1.0", tk.END)
            self.app.scan_directories()

# --- APP CHÍNH ---
class TagManagerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GIMI Mod Manager Pro")
        self.geometry("1000x650")
        self.minsize(900, 550)

        self.root_dir = ""
        self.folders = []
        self.all_tags = set()
        self.current_selected = ""
        self.tag_vars = {}
        self.mute_warning_until = 0 
        self.is_dark_mode = True

        self.init_theme()
        self.create_menu()
        self.create_widgets()
        self.apply_theme() 

    def init_theme(self):
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.colors = {}

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme()

    def apply_theme(self):
        if self.is_dark_mode:
            self.colors = {'bg': '#2b2d30', 'fg': '#dfdfe0', 'field': '#1e1f22', 'select': '#2f65ca', 'btn': '#43454a', 'btn_act': '#4c5052', 'danger': '#e06c75', 'tab_unsel': '#393b40', 'cursor': '#ffffff'}
        else:
            self.colors = {'bg': '#f0f0f0', 'fg': '#000000', 'field': '#ffffff', 'select': '#0078D7', 'btn': '#e1e1e1', 'btn_act': '#d1d1d1', 'danger': '#d32f2f', 'tab_unsel': '#d0d0d0', 'cursor': '#000000'}

        bg, fg, field, select = self.colors['bg'], self.colors['fg'], self.colors['field'], self.colors['select']

        self.config(bg=bg)
        
        self.style.configure(".", background=bg, foreground=fg)
        self.style.configure("TFrame", background=bg)
        self.style.configure("TLabel", background=bg, foreground=fg)
        self.style.configure("TLabelframe", background=bg, foreground=fg)
        self.style.configure("TLabelframe.Label", background=bg, foreground=fg)
        
        self.style.configure("TButton", background=self.colors['btn'], foreground=fg, borderwidth=0, padding=5)
        self.style.map("TButton", background=[("active", self.colors['btn_act'])])
        self.style.configure("Danger.TButton", foreground=self.colors['danger'], font=("Segoe UI", 9, "bold"))
        
        self.style.configure("TCheckbutton", background=bg, foreground=fg)
        self.style.map("TCheckbutton", background=[("active", bg)], foreground=[("active", fg)])

        self.style.configure("TEntry", fieldbackground=field, foreground=fg, insertcolor=self.colors['cursor'])
        self.style.configure("TCombobox", fieldbackground=field, background=self.colors['btn'], foreground=fg)
        self.style.map("TCombobox", fieldbackground=[("readonly", field)], foreground=[("readonly", fg)], selectbackground=[("readonly", select)])

        self.style.configure("TNotebook", background=bg, borderwidth=0)
        self.style.configure("TNotebook.Tab", background=self.colors['tab_unsel'], foreground=fg, padding=[10, 2])
        self.style.map("TNotebook.Tab", background=[("selected", field)], foreground=[("selected", fg)])

        try:
            self.checklist_frame.canvas.config(bg=bg)
            self.checklist_frame.scrollable_frame.config(style="TFrame")
        except: pass

        try: 
            self.listbox.config(bg=field, fg=fg, selectbackground=select, selectforeground=fg)
        except: pass

    def ask_warning(self, title, msg):
        if time.time() < self.mute_warning_until: return True
        
        res = tk.IntVar(value=0)
        dlg = tk.Toplevel(self)
        dlg.title(title)
        dlg.geometry("450x150")
        dlg.config(bg=self.colors['bg'])
        dlg.grab_set()

        ttk.Label(dlg, text=msg, wraplength=400, font=("Segoe UI", 10)).pack(pady=15)
        btn_frame = ttk.Frame(dlg)
        btn_frame.pack()

        def set_res(val, mute=False):
            if mute: self.mute_warning_until = time.time() + 300 
            res.set(val)
            dlg.destroy()

        ttk.Button(btn_frame, text="Đồng ý", command=lambda: set_res(1)).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Hủy", command=lambda: set_res(0)).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Đồng ý (Ngưng hỏi 5p)", command=lambda: set_res(1, True)).pack(side="left", padx=5)

        self.wait_window(dlg)
        return res.get() == 1

    def create_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Cài đặt (Settings)", menu=settings_menu)
        settings_menu.add_command(label="Chuyển đổi Giao diện (Dark/Light)", command=self.toggle_theme)

        toolbox_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Toolbox Nâng cao", menu=toolbox_menu)
        toolbox_menu.add_command(label="Mở GIMI Mod Workspace (Giải nén/Tạo folder)", command=self.open_gimi_workspace)

    def create_widgets(self):
        top_frame = ttk.Frame(self, padding=10)
        top_frame.pack(side="top", fill="x")

        btn_select_root = ttk.Button(top_frame, text="📂 Chọn Thư Mục Root", command=self.load_root_dir)
        btn_select_root.pack(side="left", padx=(0, 10))
        self.lbl_root_path = ttk.Label(top_frame, text="Chưa chọn thư mục nào...", foreground="gray")
        self.lbl_root_path.pack(side="left", fill="x", expand=True)

        main_pane = ttk.PanedWindow(self, orient="horizontal")
        main_pane.pack(fill="both", expand=True, padx=10, pady=10)

        left_frame = ttk.Frame(main_pane)
        main_pane.add(left_frame, weight=1)

        search_sort_frame = ttk.Frame(left_frame)
        search_sort_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(search_sort_frame, text="🔍 Tìm:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda n, i, m: self.update_folder_list())
        search_entry = ttk.Entry(search_sort_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=5)

        self.sort_var = tk.StringVar(value="Sắp xếp A-Z")
        sort_combo = ttk.Combobox(search_sort_frame, textvariable=self.sort_var, values=["Sắp xếp A-Z", "Sắp xếp Z-A"], state="readonly", width=12)
        sort_combo.bind("<<ComboboxSelected>>", lambda e: self.update_folder_list())
        sort_combo.pack(side="right")

        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(list_frame, font=("Segoe UI", 10), highlightthickness=0)
        self.listbox.pack(side="left", fill="both", expand=True)
        list_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        list_scroll.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=list_scroll.set)
        
        self.listbox.bind("<<ListboxSelect>>", self.on_folder_select)
        self.listbox.bind("<Button-3>", self.show_context_menu) 

        self.ctx_menu = tk.Menu(self, tearoff=0)
        self.ctx_menu.add_command(label="Mở trong File Explorer", command=self.open_in_explorer)
        self.ctx_menu.add_separator()
        self.ctx_menu.add_command(label="Đổi tên Thư mục", command=self.action_rename_folder)
        self.ctx_menu.add_command(label="❌ Xóa Thư mục này", command=self.action_delete_folder)

        self.right_frame = ttk.Frame(main_pane)
        main_pane.add(self.right_frame, weight=1)

        self.lbl_selected_folder = ttk.Label(self.right_frame, text="Vui lòng chọn một thư mục bên trái", font=("Segoe UI", 12, "bold"))
        self.lbl_selected_folder.pack(anchor="w", pady=(0, 10))

        tag_control_frame = ttk.LabelFrame(self.right_frame, text="Quản lý Tag Thư Mục", padding=10)
        tag_control_frame.pack(fill="both", expand=True)

        add_frame = ttk.Frame(tag_control_frame)
        add_frame.pack(fill="x", pady=(0, 10))
        self.new_tag_var = tk.StringVar()
        entry_new_tag = ttk.Entry(add_frame, textvariable=self.new_tag_var)
        entry_new_tag.pack(side="left", fill="x", expand=True, padx=(0, 5))
        entry_new_tag.bind("<Return>", lambda e: self.add_new_tag())
        ttk.Button(add_frame, text="Thêm Tag Mới", command=self.add_new_tag).pack(side="right")

        ttk.Button(tag_control_frame, text="Xoá TẤT CẢ Tag của thư mục này", command=self.clear_all_tags).pack(fill="x", pady=(0, 5))
        ttk.Button(tag_control_frame, text="⚙️ Xoá 1 Tag trên TOÀN BỘ thư mục Root", command=self.open_tag_manager).pack(fill="x", pady=(0, 10))

        ttk.Label(tag_control_frame, text="Danh sách Tag hệ thống (Tick để Gắn/Gỡ lẻ):", font=("Segoe UI", 9, "italic")).pack(anchor="w", pady=(5, 5))
        self.checklist_frame = ScrollableFrame(tag_control_frame)
        self.checklist_frame.pack(fill="both", expand=True)

        action_frame = ttk.LabelFrame(self.right_frame, text="Tuỳ chỉnh Folder", padding=10)
        action_frame.pack(fill="x", pady=(10, 0), side="bottom")

        btn_action_rename = ttk.Button(action_frame, text="Đổi tên", command=self.action_rename_folder)
        btn_action_rename.pack(side="left", fill="x", expand=True, padx=(0, 5))

        btn_action_delete = ttk.Button(action_frame, text="Xoá Folder", command=self.action_delete_folder, style="Danger.TButton")
        btn_action_delete.pack(side="left", fill="x", expand=True, padx=(5, 5))

        btn_action_exp = ttk.Button(action_frame, text="Mở Explorer", command=self.open_in_explorer)
        btn_action_exp.pack(side="left", fill="x", expand=True, padx=(5, 0))

        self.disable_right_panel()

    def show_context_menu(self, event):
        idx = self.listbox.nearest(event.y)
        if idx >= 0:
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(idx)
            self.on_folder_select(None)
            self.ctx_menu.tk_popup(event.x_root, event.y_root)

    def action_rename_folder(self):
        if not self.current_selected: return
        old_name = self.current_selected
        tags, base_name = get_tags_and_basename(old_name)

        new_base = simpledialog.askstring("Đổi tên", "Nhập tên nhân vật/thư mục mới (Sẽ giữ nguyên các Tag hiện tại):", initialvalue=base_name, parent=self)
        if not new_base or new_base.strip() == base_name: return
        
        safe_base = re.sub(r'[\\/*?:"<>|]', "", new_base.strip())
        
        if not self.ask_warning("Xác nhận đổi tên", f"Đổi tên phần gốc từ '{base_name}' thành '{safe_base}'?"): return

        new_full = format_folder_name(tags, safe_base)
        try:
            os.rename(os.path.join(self.root_dir, old_name), os.path.join(self.root_dir, new_full))
            idx = self.folders.index(old_name)
            self.folders[idx] = new_full
            self.current_selected = new_full
            self.update_folder_list()
            self.refresh_checklist()
            
            items = self.listbox.get(0, tk.END)
            if new_full in items:
                self.listbox.selection_set(items.index(new_full))
        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

    def action_delete_folder(self):
        if not self.current_selected: return
        
        if not self.ask_warning("CẢNH BÁO XOÁ", f"Bạn sắp XOÁ VĨNH VIỄN toàn bộ thư mục và mod bên trong:\n'{self.current_selected}'\n\nHành động này không thể hoàn tác. Tiếp tục?"): return

        target = os.path.join(self.root_dir, self.current_selected)
        try:
            shutil.rmtree(target)
            self.folders.remove(self.current_selected)
            self.current_selected = ""
            self.update_folder_list()
            self.disable_right_panel()
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể xoá: {e}")

    def load_root_dir(self):
        fp = filedialog.askdirectory(title="Chọn Thư Mục Root")
        if fp:
            self.root_dir = fp
            self.lbl_root_path.config(text=self.root_dir, foreground=self.colors['fg'])
            self.scan_directories()

    def scan_directories(self):
        if not self.root_dir: return
        try: items = os.listdir(self.root_dir)
        except Exception: return
        self.folders = [f for f in items if os.path.isdir(os.path.join(self.root_dir, f))]
        self.all_tags.clear()
        for f in self.folders:
            t, _ = get_tags_and_basename(f)
            self.all_tags.update(t)
        self.update_folder_list()
        self.disable_right_panel()

    def update_folder_list(self):
        term = self.search_var.get().lower()
        filtered = [f for f in self.folders if term in f.lower()]
        if self.sort_var.get() == "Sắp xếp A-Z": filtered.sort()
        else: filtered.sort(reverse=True)
        self.listbox.delete(0, tk.END)
        for f in filtered: self.listbox.insert(tk.END, f)

    def on_folder_select(self, event):
        sel = self.listbox.curselection()
        if not sel: return
        self.current_selected = self.listbox.get(sel[0])
        self.lbl_selected_folder.config(text=f"📂 Đang chọn: {self.current_selected}")
        self.enable_right_panel()
        self.refresh_checklist()

    def refresh_checklist(self):
        for w in self.checklist_frame.scrollable_frame.winfo_children(): w.destroy()
        if not self.current_selected: return
        cur_tags, _ = get_tags_and_basename(self.current_selected)
        self.tag_vars.clear()
        for t in sorted(list(self.all_tags)):
            var = tk.BooleanVar(value=(t in cur_tags))
            self.tag_vars[t] = var
            ttk.Checkbutton(self.checklist_frame.scrollable_frame, text=f"[{t}]", variable=var,
                            command=lambda t=t, v=var: self.on_checkbox_toggle(t, v)).pack(anchor="w", padx=5, pady=2)

    def on_checkbox_toggle(self, tag, var):
        if not self.current_selected: return
        cur_tags, _ = get_tags_and_basename(self.current_selected)
        if var.get():
            if tag not in cur_tags: cur_tags.append(tag)
        else:
            if tag in cur_tags: cur_tags.remove(tag)
        self.rename_folder(cur_tags)

    def add_new_tag(self):
        nt = self.new_tag_var.get().strip().replace("[", "").replace("]", "")
        if not nt: return
        self.all_tags.add(nt)
        self.new_tag_var.set("")
        if self.current_selected:
            cur, _ = get_tags_and_basename(self.current_selected)
            if nt not in cur:
                cur.append(nt)
                self.rename_folder(cur)
        else: self.refresh_checklist()

    def clear_all_tags(self):
        if self.current_selected: self.rename_folder([])

    def rename_folder(self, new_tags):
        old = self.current_selected
        _, base = get_tags_and_basename(old)
        new_name = format_folder_name(new_tags, base)
        if old == new_name: return
        try:
            os.rename(os.path.join(self.root_dir, old), os.path.join(self.root_dir, new_name))
            self.folders[self.folders.index(old)] = new_name
            self.current_selected = new_name
            self.lbl_selected_folder.config(text=f"📂 Đang chọn: {self.current_selected}")
            self.update_folder_list()
            self.refresh_checklist()
            
            items = self.listbox.get(0, tk.END)
            if new_name in items: self.listbox.selection_set(items.index(new_name))
        except Exception as e: messagebox.showerror("Lỗi", str(e))

    def open_in_explorer(self):
        if self.root_dir and self.current_selected:
            subprocess.Popen(f'explorer /select,"{os.path.normpath(os.path.join(self.root_dir, self.current_selected))}"')

    def open_tag_manager(self):
        if not self.root_dir: return messagebox.showinfo("Thông báo", "Vui lòng chọn Thư mục Root trước!")
        top = tk.Toplevel(self)
        top.title("Global Tag Manager")
        top.geometry("400x350")
        top.config(bg=self.colors['bg'])
        top.grab_set()
        
        ttk.Label(top, text="Chọn Tag bên dưới để XOÁ khỏi TOÀN BỘ thư mục:").pack(pady=10, padx=10, anchor="w")
        lbox = tk.Listbox(top, font=("Segoe UI", 11), bg=self.colors['field'], fg=self.colors['fg'])
        lbox.pack(fill="both", expand=True, padx=10)
        for t in sorted(list(self.all_tags)): lbox.insert(tk.END, t)
            
        def apply_global_delete():
            sel = lbox.curselection()
            if not sel: return
            tgt = lbox.get(sel[0])
            if not messagebox.askyesno("Cảnh báo", f"Xoá [{tgt}] khỏi TOÀN BỘ thư mục?"): return
            
            c = 0
            for old in list(self.folders):
                ts, base = get_tags_and_basename(old)
                if tgt in ts:
                    ts.remove(tgt)
                    nn = format_folder_name(ts, base)
                    try:
                        os.rename(os.path.join(self.root_dir, old), os.path.join(self.root_dir, nn))
                        self.folders[self.folders.index(old)] = nn
                        c += 1
                    except: pass
            messagebox.showinfo("Thành công", f"Đã xoá khỏi {c} thư mục!")
            self.scan_directories()
            top.destroy()
            
        ttk.Button(top, text="Thực thi Xóa Tag", command=apply_global_delete, style="Danger.TButton").pack(fill="x", padx=10, pady=10)

    def open_gimi_workspace(self):
        if not self.root_dir: return messagebox.showinfo("Lỗi", "Vui lòng Chọn Root trước.")
        GimiWorkspace(self, self)

    def disable_right_panel(self):
        for c in self.right_frame.winfo_children():
            if isinstance(c, (ttk.Button, ttk.LabelFrame, tk.Frame)):
                for sc in c.winfo_children():
                    try: sc.configure(state="disabled")
                    except: pass
            try: c.configure(state="disabled")
            except: pass

    def enable_right_panel(self):
        for c in self.right_frame.winfo_children():
            if isinstance(c, (ttk.Button, ttk.LabelFrame, tk.Frame)):
                for sc in c.winfo_children():
                    try: sc.configure(state="normal")
                    except: pass
            try: c.configure(state="normal")
            except: pass

if __name__ == "__main__":
    app = TagManagerApp()
    app.mainloop()
