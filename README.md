🌟 GIMI Mod Manager Pro (MFM)
Một công cụ giao diện đồ họa (GUI) siêu nhẹ được viết bằng Python/Tkinter, thiết kế chuyên biệt để giúp người dùng GIMI (Genshin Impact Model Importer) tự động hoá việc quản lý, phân loại và cài đặt Mod.

Thay vì phải giải nén thủ công, kéo thả từng file, hay đối mặt với lỗi mod không hoạt động do lồng nhiều thư mục, GIMI Mod Manager Pro sẽ xử lý tất cả chỉ với vài cú click.

✨ Tính năng nổi bật
1. 🏷️ Hệ thống Quản lý Tag Thư mục (Tagging System)
Đổi tên thư mục tự động theo cấu trúc chuẩn: [Tag1] [Tag2] Tên_Nhân_Vật.

Thêm, xóa, hoặc bật/tắt (tick/untick) hàng loạt tag thông qua bảng điều khiển bên phải.

Global Tag Manager: Trình quản lý cho phép xóa sạch 1 tag cụ thể trên TOÀN BỘ thư mục hệ thống chỉ bằng 1 nút bấm.

2. 🚀 Triển khai Mod Tự động (Auto-Deploy & Routing)
Công cụ mạnh mẽ nhất giải quyết 100% sự phiền toái khi tải Mod:

Nhận diện Thông minh (Exact Match Regex): Tự động đọc tên file nén (.zip, .rar, .7z) và đưa vào đúng thư mục nhân vật tương ứng (VD: file chứa từ hutao sẽ vào folder Hu Tao). Không bao giờ nhận diện nhầm chuỗi con.

Giải nén An toàn: Tự tạo thư mục riêng cho từng Mod, tránh tình trạng xả rác file đè lên nhau. Hỗ trợ xác minh toàn vẹn dữ liệu (Size Check) trước khi tiếp tục.

Smart Un-nesting (Rule 2 - Thuật toán Bóc Vỏ Hành): Tự động phát hiện các mod bị bọc trong nhiều lớp folder rác, lôi các file tài nguyên (.ini, .dds, .ib) ra ngoài đúng cấu trúc chuẩn của GIMI. An toàn tuyệt đối với các dạng Mod Gộp (Merged Mod) hoặc Đa biến thể.

Dọn dẹp: Tự động xoá file nén gốc sau khi triển khai thành công.

3. 📁 Tạo Thư Mục Hàng Loạt (Batch Creator)
Khởi tạo cấu trúc hàng chục nhân vật chỉ trong 1 giây.

Hỗ trợ copy/paste danh sách tên nhân vật, tự động lọc các ký tự cấm của Windows.

4. 🛠️ Quản lý File Tiện dụng & UI/UX Tối ưu
Menu Chuột phải (Context Menu): Xóa, đổi tên, mở thư mục trực tiếp trên danh sách.

Mute Warnings: Tính năng ngưng hỏi cảnh báo xóa/đổi tên trong vòng 5 phút, giúp thao tác rọn rác thư mục tốc độ cao.

Dark Mode Native: Giao diện tối hiện đại, bảo vệ mắt (mặc định), có thể chuyển đổi sang Light Mode trong cài đặt.

⚙️ Yêu cầu Hệ thống & Cài đặt
Ứng dụng chạy trực tiếp bằng Python, yêu cầu môi trường như sau:

Python 3.8 trở lên.

Đã cài đặt WinRAR hoặc 7-Zip trên máy tính (để giải nén .rar và .7z).

Các bước cài đặt:
Clone repository này về máy:

Bash
git clone https://github.com/your-username/GIMI_Mod_Manager_Pro.git
cd GIMI_Mod_Manager_Pro
Cài đặt thư viện xử lý giải nén patool:

Bash
pip install patool
Chạy ứng dụng:

Bash
python MFM.py
(Khuyến nghị: Bạn có thể dùng pyinstaller --noconsole --onefile MFM.py để đóng gói thành 1 file .exe duy nhất sử dụng cho tiện).

📖 Hướng dẫn Sử dụng Nhanh
Khởi động phần mềm, bấm 📂 Chọn Thư Mục Root và trỏ đến thư mục Mods của GIMI.

Danh sách nhân vật/folder sẽ hiện ở cột trái. Nhấp chuột vào 1 folder để bắt đầu gắn Tag ở cột phải.

Để giải nén nhanh các mod vừa tải về:

Chọn Toolbox Nâng cao trên thanh Menu > Mở GIMI Mod Workspace.

Chuyển sang Tab Auto-Route.

Bấm Chọn Các File Nén (hỗ trợ chọn nhiều file cùng lúc) và ngồi xem phần mềm tự động phân loại, xả nén, và tối ưu hóa cấu trúc.

⚠️ Lưu ý Cấu trúc Mod (Rule 2)
Thuật toán khử lồng (Rule 2) được thiết kế cực kỳ thận trọng:

Hệ thống sẽ chỉ lột bỏ thư mục nếu lớp bên ngoài cùng chỉ chứa ĐÚNG 1 thư mục con và KHÔNG chứa bất kỳ file nào khác (ngoại trừ file rác desktop.ini).

Nếu thư mục chứa từ 2 thư mục con trở lên (VD: Mod gộp nhiều trang phục), hệ thống sẽ nhận diện đây là chủ đích của Modder và dừng việc gỡ lồng để bảo toàn dữ liệu.

Phát triển bởi [Nghĩa Trịnh Xuân] - Tối ưu hóa trải nghiệm Mod Genshin Impact.
