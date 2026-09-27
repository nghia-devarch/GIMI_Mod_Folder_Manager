import os
import re
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

def get_tags_and_basename(folder_name):
    """Phân tích tên thư mục để lấy danh sách tag và tên gốc (base name)"""
    tags = []
    base_name = folder_name.strip()
    
    # Vòng lặp bóc tách các tag ở đầu chuỗi dạng [Tag1] [Tag2]...
    while True:
        match = re.match(r'^\[(.*?)\]\s*(.*)', base_name)
        if match:
            tags.append(match.group(1).strip())
            base_name = match.group(2).strip()
        else:
            break
    return tags, base_name

def format_folder_name(tags, base_name):
    """Ghép danh sách tag và tên gốc thành tên thư mục chuẩn"""
    if not tags:
        return base_name
    # Lọc các tag rỗng và ghép lại
    valid_tags = [f"[{t}]" for t in tags if t]
    if not valid_tags:
        return base_name
    return " ".join(valid_tags) + " " + base_name

class ScrollableFrame(ttk.Frame):
    """Component hỗ trợ cuộn cho danh sách tag (Mục 2)"""
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
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

        # Biến trạng thái
        self.root_dir = ""
        self.folders = []             # Danh sách tất cả thư mục
        self.all_tags = set()         # Tập hợp tất cả các tag có trong hệ thống
        self.current_selected = ""    # Tên thư mục đang được chọn
        self.tag_vars = {}            # Lưu trữ các biến Checkbox (tag -> BooleanVar)

        self.create_widgets()

    def create_widgets(self):
        # --- TOP FRAME: Chọn thư mục gốc ---
        top_frame = ttk.Frame(self, padding=10)
        top_frame.pack(side="top", fill="x")

        btn_select_root = ttk.Button(top_frame, text="Chọn Thư Mục Root (B1)", command=self.load_root_dir)
        btn_select_root.pack(side="left", padx=(0, 10))

        self.lbl_root_path = ttk.Label(top_frame, text="Chưa chọn thư mục nào...", foreground="gray")
        self.lbl_root_path.pack(side="left", fill="x", expand=True)

        # --- MAIN FRAME: Chia đôi màn hình ---
        main_pane = ttk.PanedWindow(self, orient="horizontal")
        main_pane.pack(fill="both", expand=True, padx=10, pady=10)

        # ====== TRÁI: DANH SÁCH THƯ MỤC ======
        left_frame = ttk.Frame(main_pane)
        main_pane.add(left_frame, weight=1)

        # Tìm kiếm & Sắp xếp
        search_sort_frame = ttk.Frame(left_frame)
        search_sort_frame.pack(fill="x", pady=(0, 5))

        ttk.Label(search_sort_frame, text="Tìm:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda name, index, mode: self.update_folder_list())
        search_entry = ttk.Entry(search_sort_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=5)

        self.sort_var = tk.StringVar(value="Sắp xếp A-Z")
        sort_combo = ttk.Combobox(search_sort_frame, textvariable=self.sort_var, 
                                  values=["Sắp xếp A-Z", "Sắp xếp Z-A"], state="readonly", width=12)
        sort_combo.bind("<<ComboboxSelected>>", lambda e: self.update_folder_list())
        sort_combo.pack(side="right")

        # Listbox danh sách thư mục (B2)
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill="both", expand=True)
        
        self.listbox = tk.Listbox(list_frame, font=("Segoe UI", 10), selectbackground="#0078D7")
        self.listbox.pack(side="left", fill="both", expand=True)
        list_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        list_scroll.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=list_scroll.set)
        self.listbox.bind("<<ListboxSelect>>", self.on_folder_select)

        # ====== PHẢI: BẢNG ĐIỀU KHIỂN TAG (B3) ======
        self.right_frame = ttk.Frame(main_pane)
        main_pane.add(self.right_frame, weight=1)

        self.lbl_selected_folder = ttk.Label(self.right_frame, text="Vui lòng chọn một thư mục", font=("Segoe UI", 11, "bold"))
        self.lbl_selected_folder.pack(anchor="w", pady=(0, 10))

        # Mục 3: Mở File Explorer
        btn_explorer = ttk.Button(self.right_frame, text="Mở trong File Explorer (Mục 3)", command=self.open_in_explorer)
        btn_explorer.pack(anchor="w", fill="x", pady=(0, 15))

        # Khung Quản lý Tag
        tag_control_frame = ttk.LabelFrame(self.right_frame, text="Mục 1 & 2: Thao tác chỉnh sửa & Danh sách Tag", padding=10)
        tag_control_frame.pack(fill="both", expand=True)

        # Thêm Tag mới
        add_frame = ttk.Frame(tag_control_frame)
        add_frame.pack(fill="x", pady=(0, 10))
        self.new_tag_var = tk.StringVar()
        entry_new_tag = ttk.Entry(add_frame, textvariable=self.new_tag_var)
        entry_new_tag.pack(side="left", fill="x", expand=True, padx=(0, 5))
        btn_add_tag = ttk.Button(add_frame, text="Thêm Tag Mới", command=self.add_new_tag)
        btn_add_tag.pack(side="right")

        # Xoá tất cả tag
        btn_clear_all = ttk.Button(tag_control_frame, text="Xoá TẤT CẢ Tag của thư mục này", command=self.clear_all_tags)
        btn_clear_all.pack(fill="x", pady=(0, 10))

        # Multichecklist (Danh sách tag hiện có)
        ttk.Label(tag_control_frame, text="Danh sách Tag hệ thống (Tick để Thêm/Xoá lẻ):", font=("Segoe UI", 9, "italic")).pack(anchor="w", pady=(5, 5))
        self.checklist_frame = ScrollableFrame(tag_control_frame)
        self.checklist_frame.pack(fill="both", expand=True)

        self.disable_right_panel() # Vô hiệu hoá lúc đầu vì chưa chọn thư mục

    def load_root_dir(self):
        folder_path = filedialog.askdirectory(title="Chọn Thư Mục Root")
        if folder_path:
            self.root_dir = folder_path
            self.lbl_root_path.config(text=self.root_dir, foreground="black")
            self.scan_directories()

    def scan_directories(self):
        """Quét toàn bộ thư mục và thu thập tag hiện có"""
        if not self.root_dir: return
        try:
            items = os.listdir(self.root_dir)
            self.folders = [f for f in items if os.path.isdir(os.path.join(self.root_dir, f))]
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể đọc thư mục: {e}")
            return

        # Thu thập toàn bộ các tag đã từng được sử dụng để hiển thị lên Mục 2
        self.all_tags.clear()
        for folder in self.folders:
            tags, _ = get_tags_and_basename(folder)
            self.all_tags.update(tags)
            
        self.update_folder_list()
        self.disable_right_panel()

    def update_folder_list(self):
        """Lọc, sắp xếp và cập nhật danh sách hiển thị"""
        search_term = self.search_var.get().lower()
        sort_mode = self.sort_var.get()

        filtered = [f for f in self.folders if search_term in f.lower()]
        
        if sort_mode == "Sắp xếp A-Z":
            filtered.sort()
        else:
            filtered.sort(reverse=True)

        self.listbox.delete(0, tk.END)
        for f in filtered:
            self.listbox.insert(tk.END, f)

    def on_folder_select(self, event):
        """Xử lý khi click chọn thư mục từ Listbox"""
        selection = self.listbox.curselection()
        if not selection:
            return
        
        selected_idx = selection[0]
        self.current_selected = self.listbox.get(selected_idx)
        
        self.lbl_selected_folder.config(text=f"Đang chọn: {self.current_selected}")
        self.enable_right_panel()
        self.refresh_checklist()

    def refresh_checklist(self):
        """Tạo lại giao diện Multichecklist (Mục 2) dựa trên tag của thư mục đang chọn"""
        # Xoá các checkbox cũ
        for widget in self.checklist_frame.scrollable_frame.winfo_children():
            widget.destroy()
            
        if not self.current_selected: return

        current_tags, _ = get_tags_and_basename(self.current_selected)
        self.tag_vars.clear()

        # Sắp xếp tag alphabet cho dễ nhìn
        sorted_all_tags = sorted(list(self.all_tags))
        
        for tag in sorted_all_tags:
            var = tk.BooleanVar(value=(tag in current_tags))
            self.tag_vars[tag] = var
            chk = ttk.Checkbutton(
                self.checklist_frame.scrollable_frame, 
                text=f"[{tag}]", 
                variable=var,
                command=lambda t=tag, v=var: self.on_checkbox_toggle(t, v)
            )
            chk.pack(anchor="w", padx=5, pady=2)

    def on_checkbox_toggle(self, tag, var):
        """Xử lý khi click vào Checkbox để Xoá lẻ / Thêm nhiều"""
        if not self.current_selected: return
        
        current_tags, base_name = get_tags_and_basename(self.current_selected)
        
        if var.get(): # Check -> Thêm
            if tag not in current_tags:
                current_tags.append(tag)
        else: # Uncheck -> Xoá lẻ
            if tag in current_tags:
                current_tags.remove(tag)
                
        self.rename_folder(current_tags)

    def add_new_tag(self):
        """Thêm 1 tag mới vào hệ thống và áp dụng ngay cho thư mục hiện hành"""
        new_tag = self.new_tag_var.get().strip().replace("[", "").replace("]", "")
        if not new_tag:
            return
            
        self.all_tags.add(new_tag)
        self.new_tag_var.set("") # Xoá trắng ô nhập
        
        if self.current_selected:
            current_tags, _ = get_tags_and_basename(self.current_selected)
            if new_tag not in current_tags:
                current_tags.append(new_tag)
                self.rename_folder(current_tags)
        else:
            self.refresh_checklist() # Chỉ cập nhật UI nếu chưa chọn folder

    def clear_all_tags(self):
        """Xoá toàn bộ tag của thư mục đang chọn"""
        if not self.current_selected: return
        self.rename_folder([]) # Đưa mảng tag rỗng vào

    def rename_folder(self, new_tags):
        """Lõi đổi tên thư mục và cập nhật lại dữ liệu"""
        old_name = self.current_selected
        _, base_name = get_tags_and_basename(old_name)
        new_name = format_folder_name(new_tags, base_name)

        if old_name == new_name:
            return # Không có gì thay đổi

        old_path = os.path.join(self.root_dir, old_name)
        new_path = os.path.join(self.root_dir, new_name)

        try:
            os.rename(old_path, new_path)
            
            # Cập nhật danh sách nội bộ
            if old_name in self.folders:
                idx = self.folders.index(old_name)
                self.folders[idx] = new_name
            
            self.current_selected = new_name
            self.lbl_selected_folder.config(text=f"Đang chọn: {self.current_selected}")
            
            # Cập nhật UI
            self.update_folder_list()
            self.refresh_checklist()
            
            # Chọn lại item mới trong Listbox
            items = self.listbox.get(0, tk.END)
            if new_name in items:
                idx = items.index(new_name)
                self.listbox.selection_set(idx)
                self.listbox.see(idx)
                
        except PermissionError:
            messagebox.showerror("Lỗi Cấp Phép", "Thư mục đang được mở bởi ứng dụng khác. Hãy đóng nó lại rồi thử lại.")
        except Exception as e:
            messagebox.showerror("Lỗi Đổi Tên", str(e))

    def open_in_explorer(self):
        """Mục 3: Mở thư mục trong File Explorer"""
        if not self.root_dir or not self.current_selected:
            return
        folder_path = os.path.join(self.root_dir, self.current_selected)
        
        try:
            # Mở thư mục và tô sáng thư mục đó
            subprocess.Popen(f'explorer /select,"{os.path.normpath(folder_path)}"')
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể mở File Explorer: {e}")

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
