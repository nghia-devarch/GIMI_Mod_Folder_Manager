import os
import re
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

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

class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

class TagManagerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Quản Lý Tag Thư Mục")
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

        # Menu Tools
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Tags Management", command=self.open_tag_manager)

        # Menu Advanced (Khu vực mở rộng cho Zip/Rar sau này)
        advanced_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Advanced", menu=advanced_menu)
        advanced_menu.add_command(label="Extract Archive Here (Zip/Rar)", command=self.placeholder_extract)

    def create_widgets(self):
        # TOP FRAME
        top_frame = ttk.Frame(self, padding=10)
        top_frame.pack(side="top", fill="x")

        btn_select_root = ttk.Button(top_frame, text="Choose Folder", command=self.load_root_dir)
        btn_select_root.pack(side="left", padx=(0, 10))

        self.lbl_root_path = ttk.Label(top_frame, text="Chưa chọn thư mục nào...", foreground="gray")
        self.lbl_root_path.pack(side="left", fill="x", expand=True)

        # MAIN FRAME
        main_pane = ttk.PanedWindow(self, orient="horizontal")
        main_pane.pack(fill="both", expand=True, padx=10, pady=10)

        # LEFT FRAME
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

        # RIGHT FRAME
        self.right_frame = ttk.Frame(main_pane)
        main_pane.add(self.right_frame, weight=1)

        self.lbl_selected_folder = ttk.Label(self.right_frame, text="Vui lòng chọn một thư mục", font=("Segoe UI", 11, "bold"))
        self.lbl_selected_folder.pack(anchor="w", pady=(0, 10))

        btn_explorer = ttk.Button(self.right_frame, text="Reveal in File Explorer", command=self.open_in_explorer)
        btn_explorer.pack(anchor="w", fill="x", pady=(0, 15))

        # Edit Wizard
        tag_control_frame = ttk.LabelFrame(self.right_frame, text="Edit Wizard", padding=10)
        tag_control_frame.pack(fill="both", expand=True)

        add_frame = ttk.Frame(tag_control_frame)
        add_frame.pack(fill="x", pady=(0, 10))
        self.new_tag_var = tk.StringVar()
        entry_new_tag = ttk.Entry(add_frame, textvariable=self.new_tag_var)
        entry_new_tag.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        # Bind phím Enter cho ô nhập Tag
        entry_new_tag.bind("<Return>", lambda event: self.add_new_tag())
        
        btn_add_tag = ttk.Button(add_frame, text="New Tag", command=self.add_new_tag)
        btn_add_tag.pack(side="right")

        btn_clear_all = ttk.Button(tag_control_frame, text="Untick all Tags", command=self.clear_all_tags)
        btn_clear_all.pack(fill="x", pady=(0, 10))

        ttk.Label(tag_control_frame, text="List of all Tag", font=("Segoe UI", 9, "italic")).pack(anchor="w", pady=(5, 5))
        self.checklist_frame = ScrollableFrame(tag_control_frame)
        self.checklist_frame.pack(fill="both", expand=True)

        self.disable_right_panel()

    # --- CÁC HÀM XỬ LÝ (Giữ nguyên logic cũ, thêm tag management) ---
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
            messagebox.showerror("Lỗi", f"Không thể đọc thư mục: {e}")
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

    # --- TÍNH NĂNG MỚI: TAG MANAGEMENT ---
    def open_tag_manager(self):
        if not self.root_dir:
            messagebox.showinfo("Thông báo", "Vui lòng 'Choose Folder' (Root) trước khi quản lý Tag!")
            return
            
        top = tk.Toplevel(self)
        top.title("Tags Management - Quản Lý Hàng Loạt")
        top.geometry("400x350")
        top.grab_set() # Khoá cửa sổ chính khi đang mở cửa sổ này
        
        ttk.Label(top, text="Chọn một Tag bên dưới để XOÁ khỏi TẤT CẢ thư mục:", font=("Segoe UI", 10)).pack(pady=10, padx=10, anchor="w")
        
        listbox_tags = tk.Listbox(top, font=("Segoe UI", 11))
        listbox_tags.pack(fill="both", expand=True, padx=10)
        
        for tag in sorted(list(self.all_tags)):
            listbox_tags.insert(tk.END, tag)
            
        def apply_global_delete():
            selection = listbox_tags.curselection()
            if not selection: return
            target_tag = listbox_tags.get(selection[0])
            
            confirm = messagebox.askyesno("Cảnh báo", f"Bạn sắp XOÁ tag [{target_tag}] khỏi TOÀN BỘ thư mục trong Root.\nBạn có chắc chắn không?")
            if not confirm: return
            
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
                        idx = self.folders.index(old_name)
                        self.folders[idx] = new_name
                        count += 1
                    except: pass
                    
            messagebox.showinfo("Thành công", f"Đã xoá tag [{target_tag}] khỏi {count} thư mục!")
            self.scan_directories() # Cập nhật lại toàn bộ UI chính
            top.destroy()

        btn_delete = ttk.Button(top, text=f"Xoá Tag Đã Chọn Trền Mọi Thư Mục", command=apply_global_delete)
        btn_delete.pack(fill="x", padx=10, pady=10)

    # --- TÍNH NĂNG MỚI: PLACEHOLDER ZIP/RAR ---
    def placeholder_extract(self):
        messagebox.showinfo("Tính năng nâng cao", "Hệ thống sẽ mở hộp thoại chọn file .zip/.rar, sau đó giải nén tự động vào Thư mục Root hiện tại.")

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
