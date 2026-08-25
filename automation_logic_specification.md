# Tài Liệu Đặc Tả Logic Hệ Thống Đối Soát & Gửi Telegram Tự Động (SCM Automation)

Tài liệu này đặc tả chi tiết toàn bộ logic nghiệp vụ, quy tắc xử lý dữ liệu và cấu trúc tin nhắn gửi tự động cho cả 2 ngành hàng **Thịt Cá** và **Rau Củ**. Đây sẽ là bộ quy tắc cốt lõi (Single Source of Truth) để hệ thống chạy chính xác 100%.

---

## PHẦN 1: THU THẬP DỮ LIỆU NGUỒN (DATA INGESTION)

Hệ thống tự động tải dữ liệu thời gian thực (Real-time) từ các nguồn sau:

### 1. Ngành hàng Thịt Cá:
* **Google Sheets nguồn:** [Link Google Sheet Thịt cá](https://docs.google.com/spreadsheets/d/1wac6iEvX8FFrmOse8Hk-6e4e7pOW840lEmjuHb5M2to/edit#gid=1422896115)
* **Sheet cần đọc:** `Chênh lệch ST`
* **Các cột thông tin quan trọng:**
  * `Ngày`: Định dạng ngày giao dịch (ví dụ: `24.07.2026`).
  * `ID ST` / `Chi nhánh nhận`: Mã và tên siêu thị nhận hàng.
  * `Mã hàng`, `Tên Hàng`, `ĐVT`: Thông tin sản phẩm.
  * `Số lượng chuyển`, `Số lượng nhận`, `Chênh lệch`: Số liệu gốc.
  * `Mã thùng`, `PT chuyển hàng`, `TO`: Dữ liệu WMS đi kèm.
  * `SL trả tồn về ST` / `SL chênh lệch CXD`: Số lượng thực tế cần xử lý.
  * `DC giao thiếu` / `Hao hụt`: Trạng thái phân loại lý do lệch.
  * `Xử lý`: Trạng thái xử lý chênh lệch (`Hoàn Thành`, `Đang xử lý`...).
  * `GSM phụ trách`, `RSM phụ trách`: Thông tin nhân sự quản lý vùng để tag.

### 2. Ngành hàng Rau Củ:
* **Google Sheets nguồn:** [Link Google Sheet Rau củ](https://docs.google.com/spreadsheets/d/1suHerEzgKzxB7g1UbrGIZPNaxK5a96xFnmxcIQywpko/edit)
* **Các cột thông tin quan trọng:**
  * *(Tương tự cấu trúc Thịt cá nhưng được tách riêng theo danh mục hàng Rau củ)*
* **Dữ liệu bổ trợ chênh lệch (StarRocks DB):**
  * Lấy thông tin chênh lệch thiếu trực tiếp từ `KHO RAU CỦ` (ID: `5fdc170ebd89c10006f15b7c`).
  * Lấy thông tin hàng dư từ `KHO RAU CỦ XỬ LÝ CHÊNH LỆCH CHUYỂN HÀNG` (ID: `6a34ed8d6607ba000703e235`).

---

## PHẦN 2: QUY TẮC LỌC DỮ LIỆU CHÊNH LỆCH (DATA FILTERING RULES)

Khi hệ thống chạy hàng ngày cho một **Ngày đối soát (Target Date)** nhất định:

### Bước 1: Lọc bỏ các dòng đã hoàn thành đối soát
Hệ thống quét cột **`Xử lý`** hoặc **`Trạng thái`**:
* **BỎ QUA (Không gửi):** Nếu giá trị cột chứa cụm từ: `Hoàn Thành`, `hoàn thành`, `Đã xử lý`, `Đã bù trừ`, `Đã lập phiếu`.
* **GIỮ LẠI:** Các dòng trống hoặc có trạng thái khác các từ khóa trên.

### Bước 2: Loại trừ Hao hụt tự nhiên (Chỉ áp dụng với hàng ĐVT là "KG")
Hệ thống tính toán tỷ lệ chênh lệch:
$$\text{Tỷ lệ lệch} = \frac{\text{Chênh lệch (Thiếu)}}{\text{Số lượng chuyển gốc}}$$

* **Đối với Thịt Cá:**
  * Nếu $\text{Tỷ lệ lệch} \le 2.0\%$ (0.02) và ĐVT là `KG` $\rightarrow$ **BỎ QUA** (Tự động chuyển trạng thái thành `"Hao hụt"`, không gửi siêu thị).
* **Đối với Rau Củ:**
  * Nếu $\text{Tỷ lệ lệch} \le 10.0\%$ (0.10) và ĐVT là `KG` $\rightarrow$ **BỎ QUA** (Tự động chuyển trạng thái thành `"Hao hụt"`, không gửi siêu thị).
* Các trường hợp hàng đóng gói (**ĐVT: Khay, Vỉ, Gói, Chai...**) lệch bất kỳ số lượng nào đều **GIỮ LẠI** để đối soát.

### Bước 3: Lọc người tạo và Ghi chú (Chỉ áp dụng với chênh lệch DƯ):
* Giữ lại toàn bộ phiếu dư tạo bởi `User Hệ Thống`.
* Đối với các User khác, hệ thống quét cột **`Ghi chú chuyển (phiếu)`** hoặc **`Ghi chú`**:
  * Nếu tìm thấy ký tự ngày tháng dạng `DD/MM` hoặc `MM/DD` (ví dụ `22/07`, `22-07`, `22.07`) mà **khác với ngày chạy đối soát** $\rightarrow$ **BỎ QUA** (đây là hàng dư của ngày khác nhập bù, loại trừ để tránh lệch số liệu).

---

## PHẦN 3: LOGIC KHỚP CHÉO & BÙ TRỪ TỰ ĐỘNG (MATCHING ENGINE)

Trước khi gửi tin nhắn cho từng Siêu thị, hệ thống chạy thuật toán đối chiếu chéo để triệt tiêu các lỗi cơ học:

### 1. Khớp nội bộ (Internal Match):
* Điều kiện: Cùng Siêu thị + Cùng Mã hàng phát sinh cả dòng Thiếu (Chênh lệch) và dòng Dư (Nhận dư) trong cùng ngày.
* Hành động: Tự động khấu trừ chéo lượng chênh lệch $\text{Matched} = \min(\text{Thiếu}, \text{Dư})$. Phần khớp này được gán lỗi là "DC thao tác sai / Khớp nội bộ" và **không gửi siêu thị**. Chỉ giữ lại lượng dư/thiếu ròng còn lại (nếu có).

### 2. Khớp chéo liên siêu thị (Cross-Store Match):
* Điều kiện: Siêu thị A thiếu lượng $N$, Siêu thị B thừa lượng $N$ cùng một mã hàng, cùng ngày.
* Hành động: 
  * Tra cứu khoảng cách vị trí của hai siêu thị trên file sơ đồ **`Layout Rau.xlsx`** hoặc **`LayoutImportThitCa.xlsx`**.
  * Nếu khoảng cách vị trí kề nhau (Layout distance $\le 5$) $\rightarrow$ Gán nhãn nguyên nhân là **`Giao nhầm cửa hàng`**.
  * Hệ thống tự động gom thông tin này vào báo cáo chéo và **không gửi yêu cầu kiểm kho thông thường**, chỉ gửi tin nhắn thông báo: *"ST A và ST B đã khớp chéo giao nhầm mã hàng X, số lượng N"*.

---

## PHẦN 4: GỒM NHÓM & GỬI THÔNG TIN CHO TỪNG SIÊU THỊ

### 1. Gom nhóm dữ liệu theo từng Siêu thị
Hệ thống lấy toàn bộ các dòng chênh lệch thực tế còn lại (sau khi đã loại bỏ Hao hụt và Khớp chéo), nhóm theo cột **`Chi nhánh nhận`** (hoặc `ID ST`).

### 2. Định vị nhóm chat và Tag nhân sự phụ trách
* Tra cứu file **`store_chat_mapping.xlsx`** bằng mã `ID ST` để lấy **Chat ID** của nhóm Telegram tương ứng.
* Tra cứu cột `GSM phụ trách` / `RSM phụ trách` của dòng chênh lệch. Hệ thống tự động ánh xạ tên nhân sự sang **Telegram Username** tương ứng (ví dụ: `SC005479 - Anh Lê` $\rightarrow$ `@HCM8_LVT_TC_AnhLe_SC005479`) để tag trực tiếp vào tin nhắn.

### 3. Mẫu Tin Nhắn Gửi Siêu Thị (Chi tiết nhất)

#### 🥩 Tin nhắn mẫu đối soát THỊT CÁ:
```html
🛒 <b>BÁO CÁO CHÊNH LỆCH THỊT CÁ - [Tên Siêu Thị]</b>
📅 <i>Ngày giao dịch: [DD/MM/YYYY]</i>

ST kiểm tra lại giúp Hà sáng nay có nhập sót SL các mã hàng trên do đếm sót/hàng không đạt chất lượng ST tự trừ thực nhận mà không nhập bên hàng hư hỏng:

❌ <b>DANH SÁCH THIẾU HÀNG:</b>
• <code>[Mã hàng]</code> [Tên hàng] [ĐVT] - Số lượng: <b>[SL_Lệch]</b> (Thùng: <code>[Mã Thùng]</code>)
  <i>[Nếu có ghi chú: Ghi chú chuyển]</i>

- Với mã hàng nhận thiếu item (nếu có chụp hình QUÊN up trong phiếu): cung cấp hình ảnh SL thực nhận.

*NOTE*:
Với hàng dư ST add trực tiếp trong phiếu HẬU KIỂM.
[Tag GSM phụ trách] [Tag RSM phụ trách]
```

#### 🥦 Tin nhắn mẫu đối soát RAU CỦ:
```html
🛒 <b>BÁO CÁO CHÊNH LỆCH RAU CỦ - [Tên Siêu Thị]</b>
📅 <i>Ngày giao dịch: [DD/MM/YYYY]</i>

ST kiểm tra lại giúp Hà chênh lệch hàng rau củ giao ngày hôm nay:

❌ <b>DANH SÁCH THIẾU HÀNG:</b>
• <code>[Mã hàng]</code> [Tên hàng] [ĐVT] - Số lượng: <b>[SL_Lệch]</b> (Thùng: <code>[Mã Thùng]</code>)
  <i>[Nếu có ghi chú: Ghi chú chuyển]</i>

➕ <b>DANH SÁCH THỪA HÀNG:</b>
• <code>[Mã hàng]</code> [Tên hàng] [ĐVT] - Số lượng: <b>[SL_Dư]</b> (Phiếu chuyển: <code>[Mã Phiếu]</code>)

[Tag GSM phụ trách] [Tag RSM phụ trách]
```

---

## PHẦN 5: XỬ LÝ NGOẠI LỆ (EXCEPTION HANDLING)

1. **Siêu thị không có chênh lệch thực tế:** Hệ thống sẽ **không gửi tin nhắn** vào nhóm của siêu thị đó (tránh làm phiền cửa hàng).
2. **Không tìm thấy Chat ID của Siêu thị:** Hệ thống sẽ gom các chênh lệch của cửa hàng này vào một báo cáo tổng hợp gửi vào nhóm chat quản trị **`SCM - KRC Nội bộ`** kèm cảnh báo: *"Chưa cấu hình nhóm Telegram cho cửa hàng [Tên ST]"*.
3. **Mã thùng WMS bị trống:** Hệ thống sẽ hiển thị là `Không có thông tin thùng` hoặc lấy mã phiếu chuyển hàng thay thế.
