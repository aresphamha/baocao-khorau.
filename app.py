import streamlit as st
import pandas as pd
import numpy as np
import io

def get_excel_bytes(df):
    output = io.BytesIO()
    df_to_export = df.copy()
    if isinstance(df_to_export.columns, pd.MultiIndex):
        df_to_export.columns = [' - '.join(str(c) for c in col if c).strip() for col in df_to_export.columns.values]
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_to_export.to_excel(writer, index=False)
    return output.getvalue()

def display_df_with_download(styled_df, filename, height=None):
    if height:
        st.dataframe(styled_df, use_container_width=True, height=height)
    else:
        st.dataframe(styled_df, use_container_width=True)
    df_raw = styled_df.data if hasattr(styled_df, 'data') else styled_df
    try:
        excel_data = get_excel_bytes(df_raw)
        st.download_button(label="📥 Tải xuống Excel", data=excel_data, file_name=f"{filename}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=filename)
    except Exception as e:
        st.error(f"Lỗi xuất Excel: {e}")


# Cấu hình trang web
st.set_page_config(page_title="Dashboard Đối Soát Kho Rau", page_icon="🚀", layout="wide")

st.title("🚀 Báo Cáo Đối Soát Kho Rau")
st.markdown("Dữ liệu tự động cập nhật từ Hệ thống Google Sheets")

# Hàm làm sạch số liệu
def clean_number(x):
    if pd.isna(x):
        return 0.0
    if isinstance(x, str):
        x = x.replace('.', '').replace(',', '.')
    try:
        return float(x)
    except:
        return 0.0

@st.cache_data(ttl=600)  # Tự động tải lại sau mỗi 10 phút nếu có người truy cập
def load_data():
    url_may = "https://docs.google.com/spreadsheets/d/1suHerEzgKzxB7g1UbrGIZPNaxK5a96xFnmxcIQywpko/export?format=csv&gid=1422896115"
    url_apr = "https://docs.google.com/spreadsheets/d/1mYAbl4UDhjUSfr44xYdZX5YC_mG5-_9fK4tWgG8zlew/export?format=csv"
    
    df_may = pd.read_csv(url_may, skiprows=2, dtype=str)
    df_apr = pd.read_csv(url_apr, skiprows=2, dtype=str)
    
    df_may.columns = [str(c).strip() for c in df_may.columns]
    df_apr.columns = [str(c).strip() for c in df_apr.columns]
    
    # Đồng bộ tên cột Tháng 4 cho giống với Tháng 5
    df_apr.rename(columns={
        'ST': 'ID ST',
        'SL chênh lệch ĐXL': 'SL chênh lệch CXD'
    }, inplace=True)
    
    df = pd.concat([df_apr, df_may], ignore_index=True)
    
    for col in ['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Tổng GT', 'Tổng ST', 'Tổng kho rau', 'Tổng hao hụt', 'Tổng chưa xác định']:
        if col in df.columns:
            df[col] = df[col].apply(clean_number)
            
    if 'Chi nhánh nhận' in df.columns:
        df['Chi nhánh nhận'] = df['Chi nhánh nhận'].astype(str).str.replace(',', '.', regex=False)
            
    # Lọc số lượng dựa trên cột lý do W (Hao hụt), X (Siêu thị), Y (Kho rau / Chưa xác định)
    # W tương ứng N, X tương ứng O, Y tương ứng P
    df['LyDo_W'] = df['Hao hụt'].astype(str).str.strip().str.lower()
    df['LyDo_X'] = df['Siêu thị'].astype(str).str.strip().str.lower()
    df['LyDo_Y'] = df['Kho rau\nChưa xác định'].astype(str).str.strip().str.lower()
    
    df['Qty_N'] = df['Hạo hụt tự nhiên'].apply(clean_number)
    df['Qty_O'] = df['SLbổ sung cho ST'].apply(clean_number)
    df['Qty_P'] = df['SL chênh lệch CXD'].apply(clean_number)
    
    df['Hao hụt'] = np.where(df['LyDo_W'].str.contains('hao hụt'), df['Qty_N'], 0)
    df['BS_ST'] = np.where(df['LyDo_X'].str.contains('siêu thị'), df['Qty_O'], 0)
    df['Kho_Rau'] = np.where(df['LyDo_Y'].str.contains('kho rau'), df['Qty_P'], 0)
    df['CXD'] = np.where(df['LyDo_Y'].str.contains('chưa xác định'), df['Qty_P'], 0)
            
    df['Ngày'] = pd.to_datetime(df['Ngày chuyển hàng'], format='%m/%d/%Y', errors='coerce')
    df['Ngày_str'] = df['Ngày'].dt.strftime('%d/%m/%Y').fillna(df['Ngày chuyển hàng'])
    
    df = df[df['Ngày'].notna()]
    
    # Tạo cột hiển thị SKU
    df['SKU_Full'] = df['Mã hàng'].astype(str) + " - " + df['Tên hàng'].astype(str)
    
    return df

# Load Data
with st.spinner('Đang tải dữ liệu từ Google Sheets...'):
    df_all = load_data()

st.write("---")
month_filter_global = st.radio("🗓️ **CHỌN THÁNG BÁO CÁO:**", ["Tháng 4", "Tháng 5", "Cả 2 tháng (T4 & T5)"], index=1, horizontal=True)

if month_filter_global == "Tháng 4":
    df_active = df_all[df_all['Ngày'].dt.month == 4].copy()
elif month_filter_global == "Tháng 5":
    df_active = df_all[df_all['Ngày'].dt.month == 5].copy()
else:
    df_active = df_all.copy()

# Process Dataframes
# 1. Theo ngày
pivot_ngay_sum = df_active.groupby('Ngày_str')[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Tổng GT', 'Hao hụt', 'BS_ST', 'Kho_Rau', 'CXD']].sum()
pivot_ngay_count = df_active[df_active['Chênh lệch'].abs() > 0].groupby('Ngày_str').size().rename('SL line chênh lệch')
pivot_ngay_nhap0 = df_active[(df_active['Số lượng nhận'] == 0) & (df_active['Chênh lệch'].abs() > 0)].groupby('Ngày_str').size().rename('SL line nhập=0')

pivot_ngay = pivot_ngay_sum.join(pivot_ngay_count).join(pivot_ngay_nhap0).fillna(0).reset_index()
pivot_ngay['Ngày_dt'] = pd.to_datetime(pivot_ngay['Ngày_str'], format='%d/%m/%Y', errors='coerce')
pivot_ngay = pivot_ngay.sort_values(by='Ngày_dt').drop(columns=['Ngày_dt'])

tong_row_ngay = pivot_ngay.sum(numeric_only=True).to_frame().T
tong_row_ngay['Ngày_str'] = 'Tổng'

pivot_ngay = pivot_ngay.drop(columns=['SL line nhập=0', 'SL line chênh lệch'])

pivot_ngay.rename(columns={
    'Tổng GT': 'Giá trị chênh lệch (VNĐ)',
    'BS_ST': 'SL đã tạo bs cho ST',
    'Kho_Rau': 'SL đã xác nhận được trả kho rau',
    'Hao hụt': 'Số lượng hao hụt',
    'CXD': 'Số lượng chưa xác định'
}, inplace=True)
tong_row_ngay.rename(columns={
    'Tổng GT': 'Giá trị chênh lệch (VNĐ)',
    'BS_ST': 'SL đã tạo bs cho ST',
    'Kho_Rau': 'SL đã xác nhận được trả kho rau',
    'Hao hụt': 'Số lượng hao hụt',
    'CXD': 'Số lượng chưa xác định'
}, inplace=True)

# 2. Theo CLV2
pivot_clv2_sum = df_active.groupby('CLV2')[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch']].sum()
pivot_clv2_count = df_active[df_active['Chênh lệch'].abs() > 0].groupby('CLV2').size().rename('Số lượng line')
pivot_clv2 = pivot_clv2_sum.join(pivot_clv2_count).fillna(0).reset_index()
pivot_clv2['Số lượng line'] = pivot_clv2['Số lượng line'].astype(int)
pivot_clv2 = pivot_clv2[['CLV2', 'Số lượng line', 'Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch']]
pivot_clv2 = pivot_clv2.sort_values(by='Chênh lệch', ascending=False) # Sắp xếp giảm dần vì số chênh lệch lớn nhất lên đầu
tong_row_clv2 = pivot_clv2.sum(numeric_only=True).to_frame().T
tong_row_clv2['CLV2'] = 'Tổng'

# 3. Top 5 CLV4 (Chênh lệch lớn nhất - tính theo trị tuyệt đối)
clv4_sum = df_active.groupby('CLV4')[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch']].sum().reset_index()
clv4_sum['Abs_ChenhLech'] = clv4_sum['Chênh lệch'].abs()
pivot_clv4 = clv4_sum.sort_values(by='Abs_ChenhLech', ascending=False).drop(columns=['Abs_ChenhLech']).head(5)

# 4A. Bảng SỐ LƯỢNG Chi tiết Từng Ngày - Siêu Thị
pivot_qty_sum = df_active.groupby(['Ngày_str', 'ID ST', 'Chi nhánh nhận'])[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Hao hụt', 'BS_ST', 'Kho_Rau', 'CXD']].sum()
pivot_qty_count = df_active[df_active['Chênh lệch'].abs() > 0].groupby(['Ngày_str', 'ID ST', 'Chi nhánh nhận']).size().rename('SL line chênh lệch')
pivot_qty_nhap0 = df_active[(df_active['Số lượng nhận'] == 0) & (df_active['Chênh lệch'].abs() > 0)].groupby(['Ngày_str', 'ID ST', 'Chi nhánh nhận']).size().rename('SL line nhập=0')

pivot_qty = pivot_qty_sum.join(pivot_qty_count).join(pivot_qty_nhap0).fillna(0).reset_index()

if 'SL line chênh lệch' not in pivot_qty.columns:
    pivot_qty['SL line chênh lệch'] = 0
if 'SL line nhập=0' not in pivot_qty.columns:
    pivot_qty['SL line nhập=0'] = 0

pivot_qty['SL line chênh lệch'] = pivot_qty['SL line chênh lệch'].astype(int)
pivot_qty['SL line nhập=0'] = pivot_qty['SL line nhập=0'].astype(int)
pivot_qty.insert(3, 'SL SKU NHẬP = 0/SL SKU CHÊNH LỆCH', pivot_qty['SL line nhập=0'].astype(str) + " / " + pivot_qty['SL line chênh lệch'].astype(str))

pivot_qty.rename(columns={
    'BS_ST': 'SL đã tạo bs cho ST',
    'Kho_Rau': 'SL đã xác nhận được trả kho rau',
    'Hao hụt': 'Số lượng hao hụt',
    'CXD': 'Số lượng chưa xác định'
}, inplace=True)
pivot_qty['Tỷ lệ (%)'] = np.where(pivot_qty['Số lượng chuyển'] > 0, (pivot_qty['Chênh lệch'] / pivot_qty['Số lượng chuyển']) * 100, 0)
pivot_qty['Abs_ChenhLech'] = pivot_qty['Chênh lệch'].abs()
pivot_qty = pivot_qty.sort_values(by='Abs_ChenhLech', ascending=False).drop(columns=['Abs_ChenhLech'])
pivot_qty = pivot_qty[['Ngày_str', 'ID ST', 'Chi nhánh nhận', 'SL SKU NHẬP = 0/SL SKU CHÊNH LỆCH', 'Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Tỷ lệ (%)', 'SL đã tạo bs cho ST', 'SL đã xác nhận được trả kho rau', 'Số lượng hao hụt', 'Số lượng chưa xác định']]

# 4B. Bảng GIÁ TRỊ Chi tiết Từng Ngày - Siêu Thị
pivot_val_sum = df_active.groupby(['Ngày_str', 'ID ST', 'Chi nhánh nhận'])[['Tổng GT', 'Tổng ST', 'Tổng kho rau', 'Tổng hao hụt', 'Tổng chưa xác định']].sum().reset_index()
pivot_val_sum.rename(columns={'Tổng GT': 'Giá trị chênh lệch (VNĐ)'}, inplace=True)


# Nút Tải lại dữ liệu
if st.button('🔄 Cập nhật dữ liệu mới nhất'):
    st.cache_data.clear()
    st.rerun()

# Thẻ thông tin (Metrics)
st.write("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Tổng số lượng chuyển", f"{tong_row_clv2.iloc[0]['Số lượng chuyển']:,.1f}")
with col2:
    st.metric("Tổng số lượng nhận", f"{tong_row_clv2.iloc[0]['Số lượng nhận']:,.1f}")
with col3:
    st.metric("TỔNG CHÊNH LỆCH", f"{tong_row_clv2.iloc[0]['Chênh lệch']:,.1f}")

# Hàm format màu đỏ cho số chênh lệch
def color_red_for_chenhlech(val):
    color = 'red' if isinstance(val, (int, float)) and val > 0 else ''
    return f'color: {color}'

# Hàm format số theo chuẩn Việt Nam (1.000.000,00)
def format_vn(val):
    if isinstance(val, (int, float)):
        # Format chuẩn tiếng anh 1,234.56 -> đổi chéo phẩy và chấm
        return f"{val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    return val

def create_multiindex_headers(df, tong_df):
    if df.empty or tong_df.empty: return df
    
    tuples = []
    for i, col in enumerate(df.columns):
        if col in tong_df.columns:
            val = tong_df.iloc[0][col]
            if val not in [None, 'Tổng', '', 0] and pd.notna(val):
                if pd.api.types.is_numeric_dtype(type(val)) or isinstance(val, (int, float)):
                    tuples.append((f"🟡 {format_vn(val)}", col))
                else:
                    tuples.append((f"🟡 {str(val)}", col))
            else:
                if i == 0:
                    tuples.append(('⭐ TỔNG', col))
                else:
                    tuples.append(('', col))
        else:
            if i == 0:
                tuples.append(('⭐ TỔNG', col))
            else:
                tuples.append(('', col))
                
    df_new = df.copy()
    df_new.columns = pd.MultiIndex.from_tuples(tuples)
    return df_new

pivot_ngay_renamed = create_multiindex_headers(pivot_ngay, tong_row_ngay)
pivot_clv2_renamed = create_multiindex_headers(pivot_clv2, tong_row_clv2)


# Layout cho các bảng
st.write("---")
st.subheader("📅 1. TỔNG HỢP THEO TỪNG NGÀY")
st.write("### 📌 Đánh giá nhanh tình hình")
if not pivot_ngay.empty:
    top_day = pivot_ngay.sort_values(by='Chênh lệch', ascending=False).iloc[0]
    st.info(f"🔹 **Ngày biến động nhất**: **{top_day['Ngày_str']}** ghi nhận mức chênh lệch cao nhất ({top_day['Chênh lệch']:,.2f} item / {top_day['Giá trị chênh lệch (VNĐ)']:,.0f} VNĐ).")

display_df_with_download(pivot_ngay_renamed.style.format(format_vn).map(color_red_for_chenhlech, subset=[c for c in pivot_ngay_renamed.columns if 'Chênh lệch' in c[1] and 'Giá trị' not in c[1] and 'SKU' not in c[1]]), "Tong_Hop_Theo_Ngay")

st.write("---")
col4, col5 = st.columns(2)
with col4:
    st.subheader("🔥 2. TOP 5 CATE CHÊNH LỆCH LỚN NHẤT")
    st.write("### 📌 Đánh giá nhanh tình hình")
    if not pivot_clv4.empty:
        top_clv4 = pivot_clv4.iloc[0]
        st.info(f"🔹 **Mã hàng (CLV4) cảnh báo đỏ**: **{top_clv4['CLV4']}** đang dẫn đầu với mức chênh lệch {top_clv4['Chênh lệch']:,.2f}.")
    display_df_with_download(pivot_clv4.style.format(format_vn).map(color_red_for_chenhlech, subset=['Chênh lệch']), "Top_5_CLV4")
with col5:
    st.subheader("📦 3. TỔNG HỢP THEO NGÀNH HÀNG (CLV2)")
    st.write("### 📌 Đánh giá nhanh tình hình")
    if not pivot_clv2.empty:
        top_clv2 = pivot_clv2.iloc[0]
        st.info(f"🔹 **Ngành hàng (CLV2) trọng điểm**: **{top_clv2['CLV2']}** chiếm số lượng chênh lệch cao nhất ({top_clv2['Chênh lệch']:,.2f}).")
    display_df_with_download(pivot_clv2_renamed.style.format(format_vn).map(color_red_for_chenhlech, subset=[c for c in pivot_clv2_renamed.columns if 'Chênh lệch' in c[1] and 'SL' not in c[1]]), "Tong_Hop_CLV2")

st.write("---")

# Bộ lọc theo ngày dùng chung cho các bảng chi tiết
sorted_dates = [d for d in pivot_ngay['Ngày_str'] if d != 'Tổng']
dates = ["Tất cả các ngày"] + sorted_dates

st.write("---")
st.subheader("🛒 4. CHI TIẾT SỐ LƯỢNG & GIÁ TRỊ THEO NHÓM HÀNG (CLV4)")

item_qty_sum = df_active.groupby(['Ngày_str', 'CLV4'])[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Hao hụt', 'BS_ST', 'Kho_Rau', 'CXD']].sum()
item_qty_count = df_active[df_active['Chênh lệch'].abs() > 0].groupby(['Ngày_str', 'CLV4']).size().rename('SL ST chênh lệch')
item_qty_nhap0 = df_active[(df_active['Số lượng nhận'] == 0) & (df_active['Chênh lệch'].abs() > 0)].groupby(['Ngày_str', 'CLV4']).size().rename('SL ST nhập=0')

pivot_qty_item = item_qty_sum.join(item_qty_count).join(item_qty_nhap0).fillna(0).reset_index()

if 'SL ST chênh lệch' not in pivot_qty_item.columns:
    pivot_qty_item['SL ST chênh lệch'] = 0
if 'SL ST nhập=0' not in pivot_qty_item.columns:
    pivot_qty_item['SL ST nhập=0'] = 0

pivot_qty_item['SL ST chênh lệch'] = pivot_qty_item['SL ST chênh lệch'].astype(int)
pivot_qty_item['SL ST nhập=0'] = pivot_qty_item['SL ST nhập=0'].astype(int)
pivot_qty_item.insert(2, 'SL ST NHẬP = 0/SL ST CHÊNH LỆCH', pivot_qty_item['SL ST nhập=0'].astype(str) + " / " + pivot_qty_item['SL ST chênh lệch'].astype(str))

pivot_qty_item.rename(columns={
    'CLV4': 'Mã hàng (CLV4)',
    'BS_ST': 'SL đã tạo bs cho ST',
    'Kho_Rau': 'SL đã xác nhận được trả kho rau',
    'Hao hụt': 'Số lượng hao hụt',
    'CXD': 'Số lượng chưa xác định'
}, inplace=True)
pivot_qty_item['Tỷ lệ (%)'] = np.where(pivot_qty_item['Số lượng chuyển'] > 0, (pivot_qty_item['Chênh lệch'] / pivot_qty_item['Số lượng chuyển']) * 100, 0)
pivot_qty_item['Abs_ChenhLech'] = pivot_qty_item['Chênh lệch'].abs()
pivot_qty_item = pivot_qty_item.sort_values(by='Abs_ChenhLech', ascending=False).drop(columns=['Abs_ChenhLech'])
pivot_qty_item = pivot_qty_item[['Ngày_str', 'Mã hàng (CLV4)', 'SL ST NHẬP = 0/SL ST CHÊNH LỆCH', 'Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Tỷ lệ (%)', 'SL đã tạo bs cho ST', 'SL đã xác nhận được trả kho rau', 'Số lượng hao hụt', 'Số lượng chưa xác định']]

pivot_val_item = df_active.groupby(['Ngày_str', 'CLV4'])[['Tổng GT', 'Tổng ST', 'Tổng kho rau', 'Tổng hao hụt', 'Tổng chưa xác định']].sum().reset_index()
pivot_val_item.rename(columns={'Tổng GT': 'Giá trị chênh lệch (VNĐ)', 'CLV4': 'Mã hàng (CLV4)'}, inplace=True)

selected_date_item = st.selectbox("🔍 Lọc theo Ngày (Mã hàng):", dates)

st.write("### 📌 Đánh giá nhanh tình hình")
if not pivot_qty_item.empty and not pivot_val_item.empty:
    top_item_qty = pivot_qty_item.sort_values(by='Chênh lệch', ascending=False).iloc[0] if selected_date_item == "Tất cả các ngày" else pivot_qty_item[pivot_qty_item['Ngày_str'] == selected_date_item].sort_values(by='Chênh lệch', ascending=False).iloc[0] if not pivot_qty_item[pivot_qty_item['Ngày_str'] == selected_date_item].empty else None
    top_item_val = pivot_val_item.sort_values(by='Giá trị chênh lệch (VNĐ)', ascending=False).iloc[0] if selected_date_item == "Tất cả các ngày" else pivot_val_item[pivot_val_item['Ngày_str'] == selected_date_item].sort_values(by='Giá trị chênh lệch (VNĐ)', ascending=False).iloc[0] if not pivot_val_item[pivot_val_item['Ngày_str'] == selected_date_item].empty else None
    
    if top_item_qty is not None and top_item_val is not None:
        st.info(
            f"🔹 **Mã hàng chênh lệch số lượng lớn nhất**: **{top_item_qty['Mã hàng (CLV4)']}** (Chênh lệch {top_item_qty['Chênh lệch']:,.2f} item).\n\n"
            f"🔹 **Mã hàng chênh lệch giá trị lớn nhất**: **{top_item_val['Mã hàng (CLV4)']}** (Giá trị chênh lệch {top_item_val['Giá trị chênh lệch (VNĐ)']:,.0f} VNĐ)."
        )

if selected_date_item != "Tất cả các ngày":
    filtered_qty_item = pivot_qty_item[pivot_qty_item['Ngày_str'] == selected_date_item]
    filtered_val_item = pivot_val_item[pivot_val_item['Ngày_str'] == selected_date_item]
else:
    filtered_qty_item = pivot_qty_item
    filtered_val_item = pivot_val_item

tong_qty_item = pd.DataFrame() if filtered_qty_item.empty else filtered_qty_item.sum(numeric_only=True).to_frame().T
if not tong_qty_item.empty: tong_qty_item['Ngày_str'] = 'Tổng'
filtered_qty_item_renamed = create_multiindex_headers(filtered_qty_item, tong_qty_item)

tong_val_item = pd.DataFrame() if filtered_val_item.empty else filtered_val_item.sum(numeric_only=True).to_frame().T
if not tong_val_item.empty: tong_val_item['Ngày_str'] = 'Tổng'
filtered_val_item_renamed = create_multiindex_headers(filtered_val_item, tong_val_item)

tab3, tab4 = st.tabs(["📊 Chi Tiết SỐ LƯỢNG (Mã Hàng)", "💰 Chi Tiết GIÁ TRỊ (Mã Hàng)"])

with tab3:
    display_df_with_download(filtered_qty_item_renamed.style.format(format_vn).map(color_red_for_chenhlech, subset=[c for c in filtered_qty_item_renamed.columns if 'Chênh lệch' in c[1] or 'Tỷ lệ (%)' in c[1]]), "Chi_Tiet_SL_CLV4", height=600)
    
with tab4:
    display_df_with_download(filtered_val_item_renamed.style.format(format_vn), "Chi_Tiet_GT_CLV4", height=600)

# --- 6. CHI TIẾT MÃ HÀNG (SKU) ---
st.write("---")
st.subheader("🏷️ 5. CHI TIẾT SỐ LƯỢNG & GIÁ TRỊ THEO MÃ HÀNG (SKU)")

sku_qty_sum = df_active.groupby(['Ngày_str', 'SKU_Full'])[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Hao hụt', 'BS_ST', 'Kho_Rau', 'CXD']].sum()
sku_qty_count = df_active[df_active['Chênh lệch'].abs() > 0].groupby(['Ngày_str', 'SKU_Full']).size().rename('SL ST chênh lệch')
sku_qty_nhap0 = df_active[(df_active['Số lượng nhận'] == 0) & (df_active['Chênh lệch'].abs() > 0)].groupby(['Ngày_str', 'SKU_Full']).size().rename('SL ST nhập=0')

pivot_qty_sku = sku_qty_sum.join(sku_qty_count).join(sku_qty_nhap0).fillna(0).reset_index()

if 'SL ST chênh lệch' not in pivot_qty_sku.columns:
    pivot_qty_sku['SL ST chênh lệch'] = 0
if 'SL ST nhập=0' not in pivot_qty_sku.columns:
    pivot_qty_sku['SL ST nhập=0'] = 0

pivot_qty_sku['SL ST chênh lệch'] = pivot_qty_sku['SL ST chênh lệch'].astype(int)
pivot_qty_sku['SL ST nhập=0'] = pivot_qty_sku['SL ST nhập=0'].astype(int)
pivot_qty_sku.insert(2, 'SL ST NHẬP = 0/SL ST CHÊNH LỆCH', pivot_qty_sku['SL ST nhập=0'].astype(str) + " / " + pivot_qty_sku['SL ST chênh lệch'].astype(str))

pivot_qty_sku.rename(columns={
    'SKU_Full': 'Mã hàng (SKU)',
    'BS_ST': 'SL đã tạo bs cho ST',
    'Kho_Rau': 'SL đã xác nhận được trả kho rau',
    'Hao hụt': 'Số lượng hao hụt',
    'CXD': 'Số lượng chưa xác định'
}, inplace=True)
pivot_qty_sku['Tỷ lệ (%)'] = np.where(pivot_qty_sku['Số lượng chuyển'] > 0, (pivot_qty_sku['Chênh lệch'] / pivot_qty_sku['Số lượng chuyển']) * 100, 0)
pivot_qty_sku['Abs_ChenhLech'] = pivot_qty_sku['Chênh lệch'].abs()
pivot_qty_sku = pivot_qty_sku.sort_values(by='Abs_ChenhLech', ascending=False).drop(columns=['Abs_ChenhLech'])
pivot_qty_sku = pivot_qty_sku[['Ngày_str', 'Mã hàng (SKU)', 'SL ST NHẬP = 0/SL ST CHÊNH LỆCH', 'Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Tỷ lệ (%)', 'SL đã tạo bs cho ST', 'SL đã xác nhận được trả kho rau', 'Số lượng hao hụt', 'Số lượng chưa xác định']]

pivot_val_sku = df_active.groupby(['Ngày_str', 'SKU_Full'])[['Tổng GT', 'Tổng ST', 'Tổng kho rau', 'Tổng hao hụt', 'Tổng chưa xác định']].sum().reset_index()
pivot_val_sku.rename(columns={'Tổng GT': 'Giá trị chênh lệch (VNĐ)', 'SKU_Full': 'Mã hàng (SKU)'}, inplace=True)

selected_date_sku = st.selectbox("🔍 Lọc theo Ngày (SKU):", dates)

st.write("### 📌 Đánh giá nhanh tình hình")
if not pivot_qty_sku.empty and not pivot_val_sku.empty:
    top_sku_qty = pivot_qty_sku.sort_values(by='Chênh lệch', ascending=False).iloc[0] if selected_date_sku == "Tất cả các ngày" else pivot_qty_sku[pivot_qty_sku['Ngày_str'] == selected_date_sku].sort_values(by='Chênh lệch', ascending=False).iloc[0] if not pivot_qty_sku[pivot_qty_sku['Ngày_str'] == selected_date_sku].empty else None
    top_sku_val = pivot_val_sku.sort_values(by='Giá trị chênh lệch (VNĐ)', ascending=False).iloc[0] if selected_date_sku == "Tất cả các ngày" else pivot_val_sku[pivot_val_sku['Ngày_str'] == selected_date_sku].sort_values(by='Giá trị chênh lệch (VNĐ)', ascending=False).iloc[0] if not pivot_val_sku[pivot_val_sku['Ngày_str'] == selected_date_sku].empty else None
    
    if top_sku_qty is not None and top_sku_val is not None:
        st.info(
            f"🔹 **Mã hàng chênh lệch số lượng lớn nhất**: **{top_sku_qty['Mã hàng (SKU)']}** (Chênh lệch {top_sku_qty['Chênh lệch']:,.2f} item).\n\n"
            f"🔹 **Mã hàng chênh lệch giá trị lớn nhất**: **{top_sku_val['Mã hàng (SKU)']}** (Giá trị chênh lệch {top_sku_val['Giá trị chênh lệch (VNĐ)']:,.0f} VNĐ)."
        )

if selected_date_sku != "Tất cả các ngày":
    filtered_qty_sku = pivot_qty_sku[pivot_qty_sku['Ngày_str'] == selected_date_sku]
    filtered_val_sku = pivot_val_sku[pivot_val_sku['Ngày_str'] == selected_date_sku]
else:
    filtered_qty_sku = pivot_qty_sku
    filtered_val_sku = pivot_val_sku

tong_qty_sku = pd.DataFrame() if filtered_qty_sku.empty else filtered_qty_sku.sum(numeric_only=True).to_frame().T
if not tong_qty_sku.empty: tong_qty_sku['Ngày_str'] = 'Tổng'
filtered_qty_sku_renamed = create_multiindex_headers(filtered_qty_sku, tong_qty_sku)

tong_val_sku = pd.DataFrame() if filtered_val_sku.empty else filtered_val_sku.sum(numeric_only=True).to_frame().T
if not tong_val_sku.empty: tong_val_sku['Ngày_str'] = 'Tổng'
filtered_val_sku_renamed = create_multiindex_headers(filtered_val_sku, tong_val_sku)

tab5, tab6 = st.tabs(["📊 Chi Tiết SỐ LƯỢNG (SKU)", "💰 Chi Tiết GIÁ TRỊ (SKU)"])

with tab5:
    display_df_with_download(filtered_qty_sku_renamed.style.format(format_vn).map(color_red_for_chenhlech, subset=[c for c in filtered_qty_sku_renamed.columns if 'Chênh lệch' in c[1] or 'Tỷ lệ (%)' in c[1]]), "Chi_Tiet_SL_SKU", height=600)
    
with tab6:
    display_df_with_download(filtered_val_sku_renamed.style.format(format_vn), "Chi_Tiet_GT_SKU", height=600)

st.write("---")
st.subheader("🏬 6. CHI TIẾT SỐ LƯỢNG & GIÁ TRỊ THEO SIÊU THỊ")

selected_date = st.selectbox("🔍 Lọc theo Ngày:", dates)

st.write("### 📌 Đánh giá nhanh tình hình")
if not pivot_qty.empty and not pivot_val_sum.empty:
    top_st_qty = pivot_qty.sort_values(by='Chênh lệch', ascending=False).iloc[0] if selected_date == "Tất cả các ngày" else pivot_qty[pivot_qty['Ngày_str'] == selected_date].sort_values(by='Chênh lệch', ascending=False).iloc[0] if not pivot_qty[pivot_qty['Ngày_str'] == selected_date].empty else None
    top_st_val = pivot_val_sum.sort_values(by='Giá trị chênh lệch (VNĐ)', ascending=False).iloc[0] if selected_date == "Tất cả các ngày" else pivot_val_sum[pivot_val_sum['Ngày_str'] == selected_date].sort_values(by='Giá trị chênh lệch (VNĐ)', ascending=False).iloc[0] if not pivot_val_sum[pivot_val_sum['Ngày_str'] == selected_date].empty else None
    
    if top_st_qty is not None and top_st_val is not None:
        st.info(
            f"🔹 **ST chênh lệch số lượng lớn nhất**: **{top_st_qty['Chi nhánh nhận']}** (Chênh lệch {top_st_qty['Chênh lệch']:,.2f} item).\n\n"
            f"🔹 **ST chênh lệch giá trị lớn nhất**: **{top_st_val['Chi nhánh nhận']}** (Giá trị chênh lệch {top_st_val['Giá trị chênh lệch (VNĐ)']:,.0f} VNĐ)."
        )

if selected_date != "Tất cả các ngày":
    filtered_qty = pivot_qty[pivot_qty['Ngày_str'] == selected_date]
    filtered_val = pivot_val_sum[pivot_val_sum['Ngày_str'] == selected_date]
else:
    filtered_qty = pivot_qty
    filtered_val = pivot_val_sum

tong_qty = pd.DataFrame() if filtered_qty.empty else filtered_qty.sum(numeric_only=True).to_frame().T
if not tong_qty.empty: tong_qty['Ngày_str'] = 'Tổng'
filtered_qty_renamed = create_multiindex_headers(filtered_qty, tong_qty)

tong_val = pd.DataFrame() if filtered_val.empty else filtered_val.sum(numeric_only=True).to_frame().T
if not tong_val.empty: tong_val['Ngày_str'] = 'Tổng'
filtered_val_renamed = create_multiindex_headers(filtered_val, tong_val)

tab1, tab2 = st.tabs(["📊 Chi Tiết SỐ LƯỢNG", "💰 Chi Tiết GIÁ TRỊ (VNĐ)"])

with tab1:
    display_df_with_download(filtered_qty_renamed.style.format(format_vn).map(color_red_for_chenhlech, subset=[c for c in filtered_qty_renamed.columns if 'Chênh lệch' in c[1] or 'Tỷ lệ (%)' in c[1]]), "Chi_Tiet_SL_Sieu_Thi", height=600)

with tab2:
    display_df_with_download(filtered_val_renamed.style.format(format_vn), "Chi_Tiet_GT_Sieu_Thi", height=600)

# --- 5. CHI TIẾT NHÓM HÀNG (CLV4) ---
st.subheader("🚨 7. BÁO CÁO LỖI: ST NHẬP THIẾU")

week_options = [
    "Tất cả các tuần",
    "Nguyên Tháng 4",
    "Nguyên Tháng 5",
    "Tuần 14 (30.03 - 05.04)",
    "Tuần 15 (06.04 - 12.04)",
    "Tuần 16 (13.04 - 19.04)",
    "Tuần 17 (20.04 - 26.04)",
    "Tuần 18 (27.04 - 03.05)",
    "Tuần 19 (04.05 - 10.05)",
    "Tuần 20 (11.05 - 17.05)",
    "Tuần 21 (18.05 - 24.05)",
    "Tuần 22 (25.05 - 31.05)"
]

week_filter = st.selectbox("📅 Chọn Tuần:", week_options)

start_date = pd.to_datetime('2026-03-30')
end_date = pd.to_datetime('2026-05-31')

if week_filter == "Nguyên Tháng 4":
    start_date = pd.to_datetime('2026-03-30')
    end_date = pd.to_datetime('2026-05-03')
elif week_filter == "Nguyên Tháng 5":
    start_date = pd.to_datetime('2026-05-04')
    end_date = pd.to_datetime('2026-05-31')
elif week_filter != "Tất cả các tuần":
    date_str = week_filter.split('(')[1].split(')')[0]
    start_str, end_str = date_str.split(' - ')
    start_date = pd.to_datetime(start_str + '.2026', format='%d.%m.%Y')
    end_date = pd.to_datetime(end_str + '.2026', format='%d.%m.%Y')

df_tuan = df_all[(df_all['Ngày'] >= start_date) & (df_all['Ngày'] <= end_date)].copy()
df_loi = df_tuan[df_tuan['Lỗi'].fillna('').str.contains('ST nhập thiếu', case=False)].copy()

if not df_loi.empty:
    if 'GSM phụ trách' in df_loi.columns:
        df_loi['GSM phụ trách'] = df_loi['GSM phụ trách'].astype(str).str.split('-').str[-1].str.strip()
    else:
        df_loi['GSM phụ trách'] = 'N/A'
        
    if 'RSM phụ trách' not in df_loi.columns:
        df_loi['RSM phụ trách'] = 'N/A'
        
    t1_loi = df_loi.groupby(['ID ST', 'Chi nhánh nhận', 'GSM phụ trách', 'RSM phụ trách']).agg(
        So_ngay_tao_bo_sung=('Ngày', 'nunique'),
        Tong_SL_da_tao=('Qty_O', 'sum'),
        Tong_gia_tri=('Tổng ST', 'sum')
    ).reset_index()
    t1_loi.columns = ['ID ST', 'Name Mart', 'GSM phụ trách', 'RSM phụ trách', 'Số ngày tạo bổ sung', 'Tổng SL đã tạo', 'Tổng giá trị']
    
    t2_loi = df_loi.groupby('RSM phụ trách').agg(
        SL_ST_phat_sinh=('ID ST', 'nunique'),
        SL_tao_bo_sung=('Qty_O', 'sum'),
        Gia_tri_tao_bo_sung=('Tổng ST', 'sum')
    ).reset_index()
    
    if 'RSM phụ trách' in df_tuan.columns and 'GSM phụ trách' in df_tuan.columns:
        df_tuan['GSM_tmp'] = df_tuan['GSM phụ trách'].astype(str).str.split('-').str[-1].str.strip()
        gsm_per_rsm = df_tuan.groupby('RSM phụ trách')['GSM_tmp'].nunique().reset_index()
        gsm_per_rsm.columns = ['RSM phụ trách', 'SL GSM quản lý']
        t2_loi = pd.merge(t2_loi, gsm_per_rsm, on='RSM phụ trách', how='left')
    else:
        t2_loi['SL GSM quản lý'] = 0
        
    t2_loi = t2_loi[['RSM phụ trách', 'SL GSM quản lý', 'SL_ST_phat_sinh', 'SL_tao_bo_sung', 'Gia_tri_tao_bo_sung']]
    t2_loi.columns = ['RSM phụ trách', 'SL GSM quản lý', 'SL ST phát sinh', 'SL tạo bổ sung', 'Giá trị tạo bổ sung']
    
    t3_loi = df_loi.groupby('GSM phụ trách').agg(
        SL_ST_phat_sinh=('ID ST', 'nunique'),
        SL_tao_bo_sung=('Qty_O', 'sum'),
        Gia_tri_tao_bo_sung=('Tổng ST', 'sum')
    ).reset_index()
    t3_loi.columns = ['GSM phụ trách', 'SL ST phát sinh', 'SL tạo bổ sung', 'Giá trị tạo bổ sung']

    def create_tong_row(df_to_append, label_col):
        if df_to_append.empty: return pd.DataFrame()
        tong_row = df_to_append.sum(numeric_only=True).to_frame().T
        tong_row[label_col] = 'Tổng'
        return tong_row
        
    t1_tong = create_tong_row(t1_loi, 'ID ST')
    t2_tong = create_tong_row(t2_loi, 'RSM phụ trách')
    t3_tong = create_tong_row(t3_loi, 'GSM phụ trách')

    t1_renamed = create_multiindex_headers(t1_loi, t1_tong)
    t2_renamed = create_multiindex_headers(t2_loi, t2_tong)
    t3_renamed = create_multiindex_headers(t3_loi, t3_tong)

    st.write(f"**Bảng tổng hợp theo Siêu thị ({week_filter})**")
    display_df_with_download(t1_renamed.style.format(format_vn), "Bang_Loi_Sieu_Thi")
    
    col6, col7 = st.columns(2)
    with col6:
        st.write(f"**Bảng tổng hợp theo RSM ({week_filter})**")
        display_df_with_download(t2_renamed.style.format(format_vn), "Bang_Loi_RSM")
    with col7:
        st.write(f"**Bảng tổng hợp theo GSM ({week_filter})**")
        display_df_with_download(t3_renamed.style.format(format_vn), "Bang_Loi_GSM")

    # Đánh giá chi tiết (Analytical Insights)
    st.write("### 📌 Đánh giá nhanh tình hình")
    total_val = df_loi['Tổng ST'].sum()
    total_st = df_loi['ID ST'].nunique()
    if not df_loi.empty:
        top_rsm = t2_loi.sort_values(by='Giá trị tạo bổ sung', ascending=False).iloc[0]
        top_gsm = t3_loi.sort_values(by='Giá trị tạo bổ sung', ascending=False).iloc[0]
        top_freq_st = t1_loi.sort_values(by=['Số ngày tạo bổ sung', 'Tổng giá trị'], ascending=[False, False]).iloc[0]
        
        st.info(
            f"🔹 **Tổng quan toàn hệ thống**: Trong kỳ báo cáo, ghi nhận **{total_st} siêu thị** phát sinh chênh lệch giao nhận với tổng giá trị là **{total_val:,.0f} VNĐ**.\n\n"
            f"🔹 **Cảnh báo tần suất Siêu thị**: **{top_freq_st['Name Mart']}** là điểm bán có tần suất sai lệch cao nhất, phát sinh nghiệp vụ tạo phiếu bổ sung trong **{top_freq_st['Số ngày tạo bổ sung']:.0f} ngày** (Khu vực GSM {top_freq_st['GSM phụ trách']}).\n\n"
            f"🔹 **Giám sát trọng điểm (Cấp RSM)**: Vùng quản lý của RSM **{top_rsm['RSM phụ trách']}** đang ghi nhận tổng giá trị chênh lệch lớn nhất toàn chuỗi ({top_rsm['Giá trị tạo bổ sung']:,.0f} VNĐ, phân bổ trên {top_rsm['SL ST phát sinh']} siêu thị).\n\n"
            f"🔹 **Giám sát trọng điểm (Cấp GSM)**: Khu vực của GSM **{top_gsm['GSM phụ trách']}** có giá trị phát sinh chênh lệch cao nhất ({top_gsm['Giá trị tạo bổ sung']:,.0f} VNĐ)."
        )

    # Bảng so sánh từng tuần
    def assign_week(date):
        if pd.isna(date): return None
        for opt in week_options[3:]: # Start from Tuần 14
            date_str = opt.split('(')[1].split(')')[0]
            start_str, end_str = date_str.split(' - ')
            s_date = pd.to_datetime(start_str + '.2026', format='%d.%m.%Y')
            e_date = pd.to_datetime(end_str + '.2026', format='%d.%m.%Y')
            if s_date <= date <= e_date:
                return opt
        return None

    df_loi_week = df_loi.copy()
    df_loi_week['Tuần'] = df_loi_week['Ngày'].apply(assign_week)
    
    if not df_loi_week['Tuần'].isna().all():
        def create_weekly_comparison(df, group_cols, index_name):
            res = {}
            metrics = {
                '📅 Số ngày tạo BS': ('Ngày', 'nunique'),
                '📦 SL tạo BS': ('Qty_O', 'sum'),
                '💰 Giá trị tạo BS (VNĐ)': ('Tổng ST', 'sum')
            }
            for title, (col, agg) in metrics.items():
                pivot = df.pivot_table(index=group_cols, columns='Tuần', values=col, aggfunc=agg, fill_value=0)
                weeks = sorted(list(pivot.columns))
                pivot = pivot[weeks]
                
                tong_row = pivot.sum(numeric_only=True).to_frame().T
                t_renamed = create_multiindex_headers(pivot, tong_row)
                res[title] = t_renamed
            return res

        st.write("---")
        st.write("### 📈 7. SO SÁNH TỪNG TUẦN (SỐ NGÀY, SỐ LƯỢNG, GIÁ TRỊ)")
        
        st.write("### 📌 Đánh giá nhanh tình hình")
        week_val_sum = df_loi_week.groupby('Tuần')['Tổng ST'].sum()
        if not week_val_sum.empty:
            max_week = week_val_sum.idxmax()
            max_week_val = week_val_sum.max()
            st.info(
                f"🔹 **Đỉnh điểm chênh lệch (Cảnh báo Tuần)**: **{max_week}** đang là tuần ghi nhận thiệt hại chênh lệch lớn nhất toàn hệ thống với tổng giá trị lên đến **{max_week_val:,.0f} VNĐ**."
            )
        
        def render_comparison(df_loi_week, group_cols, index_name, section_title):
            st.write(f"**{section_title}**")
            comp_dict = create_weekly_comparison(df_loi_week, group_cols, index_name)
            tabs = st.tabs(list(comp_dict.keys()))
            for tab, (title, df_comp) in zip(tabs, comp_dict.items()):
                with tab:
                    display_df_with_download(df_comp.style.format(format_vn), f"So_Sanh_{index_name}_{title}")

        render_comparison(df_loi_week, ['RSM phụ trách'], 'RSM phụ trách', f"7.1 So sánh từng tuần theo RSM ({week_filter})")
        render_comparison(df_loi_week, ['GSM phụ trách'], 'GSM phụ trách', f"7.2 So sánh từng tuần theo GSM ({week_filter})")
        render_comparison(df_loi_week, ['ID ST', 'Chi nhánh nhận'], 'ID ST', f"7.3 So sánh từng tuần theo Siêu Thị ({week_filter})")

else:
    st.info(f"Không có dữ liệu lỗi 'ST nhập thiếu' trong {week_filter}.")
