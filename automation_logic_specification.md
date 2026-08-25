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

---

## PHẦN 6: LOGIC BÁO CÁO TỔNG QUAN (TAB 1)

Tab này dùng để hiển thị báo cáo tổng hợp chênh lệch đối soát theo tháng hoặc toàn bộ thời gian, bao gồm các bảng số liệu chính sau:

### 1. Bảng 1: Tổng Hợp Theo Từng Ngày (Số Lượng & Giá Trị)
* **Mục tiêu:** Cung cấp góc nhìn diễn biến chênh lệch theo dòng thời gian ngày giao dịch.
* **Quy tắc tính toán số lượng:**
  * Gom nhóm dữ liệu theo cột `Ngày chuyển hàng` (Ngày_str).
  * Tính tổng số lượng: `Số lượng chuyển`, `Số lượng nhận`, `Chênh lệch`, `Số lượng hao hụt` (Hao hụt), `SL đã tạo bs cho ST` (BS_ST), `SL đã xác nhận được trả kho rau` (Kho_Rau), `Số lượng chưa xác định` (CXD).
* **Quy tắc tính toán giá trị (VNĐ):**
  * Nhân số lượng của từng dòng với giá trị đơn vị hoặc cột tổng tiền tương ứng.
  * Tính tổng giá trị: `Giá trị chênh lệch`, `Giá trị đã tạo bs cho ST`, `Giá trị đã xác nhận được trả kho rau`, `Giá trị hao hụt`, `Giá trị chưa xác định`.
* **Hiển thị:** Định dạng số kiểu Việt Nam (dấu chấm phân tách hàng nghìn, dấu phẩy phân tách thập phân).

### 2. Bảng 2: Top 5 Ngành Hàng Cấp 4 (CLV4) Chênh Lệch Lớn Nhất
* **Mục tiêu:** Cảnh báo đỏ các nhóm hàng (CLV4) bị thất thoát nghiêm trọng nhất trong kỳ.
* **Quy tắc:** Nhóm dữ liệu theo cột `CLV4`, tính tổng `Chênh lệch`, lấy trị tuyệt đối (`abs`) và sắp xếp giảm dần, lọc lấy 5 nhóm hàng đầu bảng.

### 3. Bảng 3: Tổng Hợp Theo Ngành Hàng Cấp 2 (CLV2)
* **Mục tiêu:** Tổng hợp chênh lệch theo các ngành hàng lớn (Rau củ, Trái cây, Trứng, Bánh mì...).
* **Quy tắc:** Nhóm dữ liệu theo cột `CLV2`, đếm tổng số dòng phát sinh chênh lệch (`Số lượng line`) và tính tổng `Số lượng chuyển`, `Số lượng nhận`, `Chênh lệch`.

### 4. Bảng 4, 5, 6: Chi Tiết Theo Nhóm Hàng (CLV4), Mã Hàng (SKU) & Siêu Thị
* **Mục tiêu:** Cho phép người dùng chọn bộ lọc **Ngày** cụ thể (hoặc "Tất cả các ngày") để kiểm tra chi tiết phân bổ xử lý chênh lệch theo từng sản phẩm, mã hàng, hoặc siêu thị.
* **Thông tin hiển thị:** Số lượng chuyển, nhận, chênh lệch, tỷ lệ lệch (%), lượng hàng phân bổ về Siêu thị, Kho rau, Hao hụt và Chưa xác định.

### 5. Bảng 7: Báo Cáo Lỗi Siêu Thị Nhập Thiếu
* **Mục tiêu:** Giám sát các trường hợp siêu thị báo thiếu hàng không chính xác (lỗi "ST nhập thiếu") để đánh giá năng suất và tính tuân thủ của từng siêu thị, khu vực GSM, RSM.
* **Quy tắc lọc dữ liệu:**
  * Lọc cột `Lỗi` có chứa cụm từ `"ST nhập thiếu"` (không phân biệt hoa thường).
  * Lọc theo tuần (Ví dụ: Tuần 14 đến Tuần 22).
* **Quy tắc tổng hợp:**
  * Tổng hợp theo Siêu thị, RSM, GSM để đo lường: *Số ngày phát sinh lỗi*, *Tổng số lượng đã tạo bổ sung*, *Tổng giá trị bổ sung (VNĐ)*.
  * So sánh diễn biến tăng/giảm theo từng tuần để RSM/GSM có hướng nhắc nhở kịp thời.

---

## PHẦN 7: LOGIC BÁO CÁO NĂNG SUẤT DAILY (TAB 2)

Tab này hỗ trợ người điều hành (Operations) đánh giá sâu hiệu quả xử lý chênh lệch hàng ngày, tự động tính toán tỷ lệ xử lý và đưa ra các đề xuất tự động.

### 1. Bảng 1: Đánh Giá Nhanh Tình Hình Xử Lý (Daily Summary)
* **Mục tiêu:** Đo lường tỷ lệ hoàn thành đối soát trong ngày.
* **Quy tắc phân loại trạng thái xử lý:**
  * **Đã xử lý (Processed):** Bao gồm lượng hàng đã được định đoạt nguyên nhân cụ thể:
    * `Số lượng hao hụt`: Ghi nhận hao hụt tự nhiên (cột Y là "Hao hụt").
    * `SL bs ST`: Giao bù cho Siêu thị (cột X có chữ "siêu thị").
    * `SL bs kho rau`: Trả về trách nhiệm của Kho rau (cột Y có chữ "kho rau").
  * **Tồn lại (Treo chờ xử lý):** Hàng chưa xác định được nguyên nhân (CXD > 0):
    * `Đang xử lý` (Pending): Trạng thái cột Z (`Xử lý`) là `"hoàn thành"` (Đang chờ đối soát chéo).
    * `Không xử lý (WRITE OFF)`: Trạng thái cột Z là `"đang xử lý"` (SCM phê duyệt bỏ qua).
    * `Chưa xử lý` (Unprocessed): Cột Z trống hoặc trạng thái khác.
* **Hiển thị:** Tỷ lệ phần trăm dòng đã xử lý được tính bằng:
  $$\text{Tỷ lệ line đã xử lý} = \frac{\text{Số dòng đã xử lý} + \text{Số dòng hao hụt}}{\text{Tổng số dòng chênh lệch}} \times 100\%$$

### 2. Bảng 1.1: Chi Tiết Đã Xử Lý Theo Nguồn Xác Nhận
* **Mục tiêu:** Phân loại nguồn thông tin/bằng chứng dùng để xác nhận nguyên nhân chênh lệch.
* **Quy tắc phân loại (Dựa vào từ khóa trong cột `NOTE`):**
  * `Hình ảnh ST`: Cột `NOTE` chứa chữ `"tele"`, `"kdb"`, hoặc `"hình"`.
  * `DC giao sai ST`: Cột `NOTE` chứa chữ `"st nhận"` hoặc `"giao sai"`.
  * `DC pick sai`: Cột `NOTE` chứa chữ `"pick sai"` hoặc `"lấy sai"`.
  * `Check camera`: Tất cả các trường hợp còn lại (mặc định SCM tự check camera để phân định).

### 3. Bảng 1.2: Đề Xuất Hướng Xử Lý Cho Hàng Chưa Xử Lý (Áp dụng từ 27/05/2026)
* **Mục tiêu:** Tự động hóa việc đóng các ca chênh lệch nhỏ để tối ưu hóa nguồn lực. Việc dò camera mất rất nhiều thời gian, nếu giá trị thấp sẽ không mang lại hiệu quả kinh tế.
* **Quy tắc đề xuất (Hậu kiểm khiếu nại):**
  * Nhóm dữ liệu theo Siêu thị và Ngành hàng.
  * Tính tổng `Giá trị lệch (VNĐ)` ban đầu của Siêu thị đó.
  * **Đề xuất `🟢 Bỏ qua không xử lý (WRITE OFF)`:** Nếu tổng giá trị chênh lệch ban đầu < 100.000 VNĐ.
  * **Đề xuất `🔴 Phải xử lý`:** Nếu tổng giá trị chênh lệch ban đầu $\ge$ 100.000 VNĐ.

### 4. Bảng 2: Đối Soát Hàng Theo ĐVT: KG (Nhận > 0)
* **Mục tiêu:** Đánh giá mức độ lệch của hàng cân ký (KG) để loại trừ hao hụt tự nhiên.
* **Quy tắc phân bổ chênh lệch (Hao hụt vs Lỗi chủ quan):**
  * Tính tỷ lệ % lệch thực tế của từng dòng (chỉ tính phần trả về Kho rau):
    $$\text{Tỷ lệ \% lệch} = \frac{\text{Lượng hao hụt} + \text{Lượng lỗi giao thiếu}}{\text{Số lượng chuyển}} \times 100\%$$
  * Phân chia chênh lệch vào các nhóm (buckets):
    * **Mức `<= 5%`:** Được coi là hao hụt tự nhiên trong quá trình vận chuyển (bỏ qua).
    * **Mức `5-10%`, `10-15%`, `> 15%`:** Được coi là hao hụt bất thường, bắt nguồn từ lỗi chủ quan (Kho nhặt thiếu hoặc Siêu thị đếm sai).
  * Đồng thời thống kê chi tiết lỗi của Siêu thị:
    * `Lỗi ST (Nhập thiếu)`: Cột `Siêu thị` chứa chữ "siêu thị" & cột `Lỗi` chứa chữ "thiếu".
    * `Lỗi ST (Sai QT)`: Cột `Siêu thị` chứa chữ "siêu thị" & cột `Lỗi` KHÔNG chứa chữ "thiếu".

### 5. Bảng 3 & Bảng 4: Đánh Giá Hàng Pack & Top Sản Phẩm Hao Hụt Cao Nhất
* **Hàng Pack:** Thống kê các sản phẩm đóng gói (ĐVT khác KG) phát sinh lệch. Hàng Pack không có hao hụt tự nhiên nên mọi trường hợp lệch đều phải quy trách nhiệm cụ thể.
* **Top sản phẩm hao hụt:** Liệt kê danh sách SKU có tổng lượng hao hụt (KG) cao nhất trong kỳ để SCM làm việc lại với NCC hoặc quy trình đóng gói tại DC.
