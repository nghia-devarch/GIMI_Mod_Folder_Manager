import os
import re
import shutil
import zipfile
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import patoolib
    HAS_PATOOL = True
except ImportError:
    HAS_PATOOL = False

# --- CÁC HÀM TIỆN ÍCH CHO TAG ---
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

# --- MODULE GIMI MOD WORKSPACE ---
class GimiWorkspace(tk.Toplevel):
    def __init__(self, parent, app_instance):
        super().__init__(parent)
        self.app = app_instance
        self.title("GIMI Mod Workspace")
        self.geometry("600x450")
        self.grab_set()

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # TAB 1: Auto-Deploy Mod (Tool 1 + Tool 2 + Rule 2)
        tab_deploy = ttk.Frame(notebook)
        notebook.add(tab_deploy, text="Triển khai File Mod (Auto-Route)")

        ttk.Label(tab_deploy, text="Hệ thống tự nhận diện file nén -> Chuyển vào folder -> Giải nén -> Khử lồng & Xoá file ZIP/RAR gốc.", wraplength=550).pack(pady=10, padx=10, anchor="w")
        
        self.btn_deploy = ttk.Button(tab_deploy, text="Chọn File Nén Cần Chuyển (Zip/Rar)", command=self.run_auto_deploy)
        self.btn_deploy.pack(pady=5, fill="x", padx=10)

        self.log_txt = tk.Text(tab_deploy, height=15, font=("Consolas", 9), state="disabled")
        self.log_txt.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        # TAB 2: Batch Creator (Tool 3)
        tab_batch = ttk.Frame(notebook)
        notebook.add(tab_batch, text="Tạo Thư Mục Hàng Loạt (Batch Creator)")

        ttk.Label(tab_batch, text="Nhập danh sách tên nhân vật/thư mục (mỗi tên 1 dòng, ngăn bằng Enter):").pack(pady=10, padx=10, anchor="w")
        self.txt_batch = tk.Text(tab_batch, height=15, font=("Segoe UI", 10))
        self.txt_batch.pack(fill="both", expand=True, padx=10)
        
        ttk.Button(tab_batch, text="Tạo Các Thư Mục Này", command=self.run_batch_create).pack(pady=10, padx=10, fill="x")

    def log(self, message):
        self.log_txt.config(state="normal")
        self.log_txt.insert(tk.END, message + "\n")
        self.log_txt.see(tk.END)
        self.log_txt.config(state="disabled")
        self.update_idletasks()

    def apply_rule_2(self, base_folder):
        """Khử lồng thư mục: Tìm file .ini, kéo toàn bộ cấp thư mục chứa nó ra ngoài cùng."""
        ini_path = None
        for root, dirs, files in os.walk(base_folder):
            if any(f.lower().endswith('.ini') for f in files):
                ini_path = root
                break
        
        base_folder_norm = os.path.normpath(base_folder)
        
        if ini_path:
            ini_path_norm = os.path.normpath(ini_path)
            if ini_path_norm != base_folder_norm:
                self.log(f"   -> [Rule 2] Đang gỡ lồng thư mục cho Mod này...")
                temp_dir = base_folder_norm + "_temp_deploy"
                os.rename(base_folder_norm, temp_dir) # Đổi tên folder gốc thành tạm
                
                # Tìm đường dẫn tương đối để lôi file ra
                rel_path = os.path.relpath(ini_path_norm, base_folder_norm)
                new_ini_path = os.path.join(temp_dir, rel_path)
                
                os.rename(new_ini_path, base_folder_norm) # Đổi tên folder chứa mod thực sự thành folder gốc
                shutil.rmtree(temp_dir, ignore_errors=True) # Dọn rác
                self.log(f"   -> [Rule 2] Hoàn tất gỡ lồng.")

    def run_auto_deploy(self):
        files = filedialog.askopenfilenames(title="Chọn các file Mod (.zip, .rar)", filetypes=[("Archive Files", "*.zip *.rar")])
        if not files: return

        self.log("Bắt đầu quy trình Deploy...")
        for file in files:
            basename = os.path.basename(file)
            name_no_ext, ext = os.path.splitext(basename)
            ext = ext.lower()
            self.log(f"\nĐang xử lý: {basename}")

            # [Tool 2: VẬN CHUYỂN / ĐỐI SÁNH]
            target_char = None
            for folder_name in self.app.folders:
                _, char_name = get_tags_and_basename(folder_name)
                # Check nếu tên nhân vật xuất hiện trong tên file nén
                if char_name.lower() in name_no_ext.lower():
                    target_char = folder_name
                    break
            
            if not target_char:
                target_char = "Uncategorized_Mods" # Dự phòng nếu ko khớp nhân vật nào
                self.log(f"   -> Cảnh báo: Không tìm thấy nhân vật khớp, đưa vào '{target_char}'")
                uncat_path = os.path.join(self.app.root_dir, target_char)
                if not os.path.exists(uncat_path): os.makedirs(uncat_path)

            # [Tool 1: TẠO FOLDER ĐÍCH VÀ GIẢI NÉN]
            dest_path = os.path.join(self.app.root_dir, target_char, name_no_ext)
            if not os.path.exists(dest_path):
                os.makedirs(dest_path)
                self.log(f"   -> Tạo thư mục: {target_char}/{name_no_ext}")

            try:
                expected_files = 0
                if ext == '.zip':
                    with zipfile.ZipFile(file, 'r') as zf:
                        expected_files = len([f for f in zf.namelist() if not f.endswith('/')])
                        zf.extractall(dest_path)
                elif ext == '.rar':
                    if HAS_PATOOL:
                        patoolib.extract_archive(file, outdir=dest_path, interactive=False, verbosity=-1)
                    else:
                        raise Exception("Thiếu thư viện patool. Hãy chạy lệnh 'pip install patool'.")
                
                # [XÁC MINH CÓ ĐỦ FILE SAU GIẢI NÉN KHÔNG]
                extracted_files = sum(len(fs) for _, _, fs in os.walk(dest_path))
                
                if extracted_files == 0:
                    raise Exception("Lỗi: Thư mục đích bị trống sau khi giải nén!")
                if ext == '.zip' and extracted_files < expected_files:
                    raise Exception(f"Lỗi: Thiếu file! Gốc có {expected_files}, giải nén ra {extracted_files}")

                self.log("   -> Giải nén và Xác minh dữ liệu: THÀNH CÔNG.")
                
                # [Rule 2: GỠ LỒNG THƯ MỤC]
                self.apply_rule_2(dest_path)

                # [XOÁ FILE NÉN GỐC SAU KHI MỌI THỨ HOÀN TẤT]
                os.remove(file)
                self.log("   -> Đã xoá file nén gốc.")

            except Exception as e:
                self.log(f"   -> LỖI: {e}")
                # Nếu lỗi xảy ra giữa chừng, xoá folder giải nén hỏng đi
                if os.path.exists(dest_path):
                    shutil.rmtree(dest_path, ignore_errors=True)
        
        self.app.scan_directories()
        self.log("\n=== TẤT CẢ QUY TRÌNH HOÀN TẤT ===")

    def run_batch_create(self):
        text = self.txt_batch.get("1.0", tk.END).strip()
        if not text: return
        folders = [f.strip() for f in text.split('\n') if f.strip()]
        if not folders: return
        
        confirm = messagebox.askyesno("Xác nhận", f"Hệ thống sẽ tạo {len(folders)} thư mục nhân vật vào trong Root.\nTiếp tục?")
        if confirm:
            count = 0
            for f in folders:
                path = os.path.join(self.app.root_dir, f)
                if not os.path.exists(path):
                    os.makedirs(path)
                    count += 1
            messagebox.showinfo("Hoàn tất", f"Đã tạo thành công {count} thư mục!")
            self.txt_batch.delete("1.0", tk.END)
            self.app.scan_directories()

# --- APP CHÍNH ---
class TagManagerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Quản Lý Tag & GIMI Workspace")
        self.geometry("900x600")
        self.minsize(800, 500)

        self.root_dir = ""
        self.folders = []
        self.all_tags = set()
        self.current_selected = ""
        self.tag_vars = {}

        self.create_menu()
        self.create_widgets()

    def create_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Tags Management", command=self.open_tag_manager)
        tools_menu.add_separator()
        tools_menu.add_command(label="GIMI Mod Workspace", command=self.open_gimi_workspace)

    def create_widgets(self):
        top_frame = ttk.Frame(self, padding=10)
        top_frame.pack(side="top", fill="x")

        btn_select_root = ttk.Button(top_frame, text="Choose Folder", command=self.load_root_dir)
        btn_select_root.pack(side="left", padx=(0, 10))
        self.lbl_root_path = ttk.Label(top_frame, text="Chưa chọn thư mục nào...", foreground="gray")
        self.lbl_root_path.pack(side="left", fill="x", expand=True)

        main_pane = ttk.PanedWindow(self, orient="horizontal")
        main_pane.pack(fill="both", expand=True, padx=10, pady=10)

        left_frame = ttk.Frame(main_pane)
        main_pane.add(left_frame, weight=1)

        search_sort_frame = ttk.Frame(left_frame)
        search_sort_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(search_sort_frame, text="Tìm:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda name, index, mode: self.update_folder_list())
        search_entry = ttk.Entry(search_sort_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=5)

        self.sort_var = tk.StringVar(value="Sắp xếp A-Z")
        sort_combo = ttk.Combobox(search_sort_frame, textvariable=self.sort_var, 
                                  values=["Sắp xếp A-Z", "Sắp xếp Z-A"], state="readonly", width=12)
        sort_combo.bind("<<ComboboxSelected>>", lambda e: self.update_folder_list())
        sort_combo.pack(side="right")

        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(list_frame, font=("Segoe UI", 10), selectbackground="#0078D7")
        self.listbox.pack(side="left", fill="both", expand=True)
        list_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        list_scroll.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=list_scroll.set)
        self.listbox.bind("<<ListboxSelect>>", self.on_folder_select)

        self.right_frame = ttk.Frame(main_pane)
        main_pane.add(self.right_frame, weight=1)

        self.lbl_selected_folder = ttk.Label(self.right_frame, text="Vui lòng chọn một thư mục", font=("Segoe UI", 11, "bold"))
        self.lbl_selected_folder.pack(anchor="w", pady=(0, 10))

        btn_explorer = ttk.Button(self.right_frame, text="Reveal in File Explorer", command=self.open_in_explorer)
        btn_explorer.pack(anchor="w", fill="x", pady=(0, 15))

        tag_control_frame = ttk.LabelFrame(self.right_frame, text="Edit Wizard", padding=10)
        tag_control_frame.pack(fill="both", expand=True)

        add_frame = ttk.Frame(tag_control_frame)
        add_frame.pack(fill="x", pady=(0, 10))
        self.new_tag_var = tk.StringVar()
        entry_new_tag = ttk.Entry(add_frame, textvariable=self.new_tag_var)
        entry_new_tag.pack(side="left", fill="x", expand=True, padx=(0, 5))
        entry_new_tag.bind("<Return>", lambda event: self.add_new_tag())
        btn_add_tag = ttk.Button(add_frame, text="New Tag", command=self.add_new_tag)
        btn_add_tag.pack(side="right")

        btn_clear_all = ttk.Button(tag_control_frame, text="Untick all Tags", command=self.clear_all_tags)
        btn_clear_all.pack(fill="x", pady=(0, 10))

        ttk.Label(tag_control_frame, text="List of all Tag", font=("Segoe UI", 9, "italic")).pack(anchor="w", pady=(5, 5))
        self.checklist_frame = ScrollableFrame(tag_control_frame)
        self.checklist_frame.pack(fill="both", expand=True)

        self.disable_right_panel()

    def load_root_dir(self):
        folder_path = filedialog.askdirectory(title="Choose Folder")
        if folder_path:
            self.root_dir = folder_path
            self.lbl_root_path.config(text=self.root_dir, foreground="black")
            self.scan_directories()

    def scan_directories(self):
        if not self.root_dir: return
        try:
            items = os.listdir(self.root_dir)
            self.folders = [f for f in items if os.path.isdir(os.path.join(self.root_dir, f))]
        except Exception as e:
            return

        self.all_tags.clear()
        for folder in self.folders:
            tags, _ = get_tags_and_basename(folder)
            self.all_tags.update(tags)
            
        self.update_folder_list()
        self.disable_right_panel()

    def update_folder_list(self):
        search_term = self.search_var.get().lower()
        sort_mode = self.sort_var.get()
        filtered = [f for f in self.folders if search_term in f.lower()]
        
        if sort_mode == "Sắp xếp A-Z": filtered.sort()
        else: filtered.sort(reverse=True)

        self.listbox.delete(0, tk.END)
        for f in filtered: self.listbox.insert(tk.END, f)

    def on_folder_select(self, event):
        selection = self.listbox.curselection()
        if not selection: return
        selected_idx = selection[0]
        self.current_selected = self.listbox.get(selected_idx)
        self.lbl_selected_folder.config(text=f"Đang chọn: {self.current_selected}")
        self.enable_right_panel()
        self.refresh_checklist()

    def refresh_checklist(self):
        for widget in self.checklist_frame.scrollable_frame.winfo_children(): widget.destroy()
        if not self.current_selected: return
        current_tags, _ = get_tags_and_basename(self.current_selected)
        self.tag_vars.clear()
        for tag in sorted(list(self.all_tags)):
            var = tk.BooleanVar(value=(tag in current_tags))
            self.tag_vars[tag] = var
            chk = ttk.Checkbutton(self.checklist_frame.scrollable_frame, text=f"[{tag}]", variable=var,
                                  command=lambda t=tag, v=var: self.on_checkbox_toggle(t, v))
            chk.pack(anchor="w", padx=5, pady=2)

    def on_checkbox_toggle(self, tag, var):
        if not self.current_selected: return
        current_tags, _ = get_tags_and_basename(self.current_selected)
        if var.get():
            if tag not in current_tags: current_tags.append(tag)
        else:
            if tag in current_tags: current_tags.remove(tag)
        self.rename_folder(current_tags)

    def add_new_tag(self):
        new_tag = self.new_tag_var.get().strip().replace("[", "").replace("]", "")
        if not new_tag: return
        self.all_tags.add(new_tag)
        self.new_tag_var.set("")
        if self.current_selected:
            current_tags, _ = get_tags_and_basename(self.current_selected)
            if new_tag not in current_tags:
                current_tags.append(new_tag)
                self.rename_folder(current_tags)
        else:
            self.refresh_checklist()

    def clear_all_tags(self):
        if not self.current_selected: return
        self.rename_folder([])

    def rename_folder(self, new_tags):
        old_name = self.current_selected
        _, base_name = get_tags_and_basename(old_name)
        new_name = format_folder_name(new_tags, base_name)
        if old_name == new_name: return

        old_path = os.path.join(self.root_dir, old_name)
        new_path = os.path.join(self.root_dir, new_name)
        try:
            os.rename(old_path, new_path)
            if old_name in self.folders:
                idx = self.folders.index(old_name)
                self.folders[idx] = new_name
            self.current_selected = new_name
            self.lbl_selected_folder.config(text=f"Đang chọn: {self.current_selected}")
            self.update_folder_list()
            self.refresh_checklist()
            
            items = self.listbox.get(0, tk.END)
            if new_name in items:
                idx = items.index(new_name)
                self.listbox.selection_set(idx)
                self.listbox.see(idx)
        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

    def open_in_explorer(self):
        if not self.root_dir or not self.current_selected: return
        folder_path = os.path.join(self.root_dir, self.current_selected)
        try: subprocess.Popen(f'explorer /select,"{os.path.normpath(folder_path)}"')
        except Exception as e: messagebox.showerror("Lỗi", str(e))

    def open_tag_manager(self):
        if not self.root_dir:
            messagebox.showinfo("Thông báo", "Vui lòng 'Choose Folder' trước!")
            return
        top = tk.Toplevel(self)
        top.title("Tags Management")
        top.geometry("400x350")
        top.grab_set()
        
        ttk.Label(top, text="Chọn Tag bên dưới để XOÁ khỏi TOÀN BỘ thư mục:", font=("Segoe UI", 10)).pack(pady=10, padx=10, anchor="w")
        listbox_tags = tk.Listbox(top, font=("Segoe UI", 11))
        listbox_tags.pack(fill="both", expand=True, padx=10)
        for tag in sorted(list(self.all_tags)): listbox_tags.insert(tk.END, tag)
            
        def apply_global_delete():
            selection = listbox_tags.curselection()
            if not selection: return
            target_tag = listbox_tags.get(selection[0])
            if not messagebox.askyesno("Cảnh báo", f"Xoá tag [{target_tag}] khỏi TOÀN BỘ thư mục?"): return
            
            count = 0
            for old_name in list(self.folders):
                tags, base_name = get_tags_and_basename(old_name)
                if target_tag in tags:
                    tags.remove(target_tag)
                    new_name = format_folder_name(tags, base_name)
                    old_path = os.path.join(self.root_dir, old_name)
                    new_path = os.path.join(self.root_dir, new_name)
                    try:
                        os.rename(old_path, new_path)
                        self.folders[self.folders.index(old_name)] = new_name
                        count += 1
                    except: pass
            messagebox.showinfo("Thành công", f"Đã xoá tag khỏi {count} thư mục!")
            self.scan_directories()
            top.destroy()
        ttk.Button(top, text="Xoá Tag Đã Chọn Trền Mọi Thư Mục", command=apply_global_delete).pack(fill="x", padx=10, pady=10)

    def open_gimi_workspace(self):
        if not self.root_dir:
            messagebox.showinfo("Lỗi", "Vui lòng 'Choose Folder' (Thư mục Mods) để làm Root trước khi dùng GIMI Workspace.")
            return
        GimiWorkspace(self, self)

    def disable_right_panel(self):
        for child in self.right_frame.winfo_children():
            if isinstance(child, (ttk.Button, ttk.LabelFrame, tk.Frame)):
                for subchild in child.winfo_children():
                    try: subchild.configure(state="disabled")
                    except: pass
            try: child.configure(state="disabled")
            except: pass

    def enable_right_panel(self):
        for child in self.right_frame.winfo_children():
            if isinstance(child, (ttk.Button, ttk.LabelFrame, tk.Frame)):
                for subchild in child.winfo_children():
                    try: subchild.configure(state="normal")
                    except: pass
            try: child.configure(state="normal")
            except: pass

if __name__ == "__main__":
    app = TagManagerApp()
    app.mainloop()
