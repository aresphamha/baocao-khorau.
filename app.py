import streamlit as st
import pandas as pd
import numpy as np

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
    
    df_may = pd.read_csv(url_may, skiprows=2)
    df_apr = pd.read_csv(url_apr, skiprows=2)
    
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

pivot_ngay['SL line chênh lệch'] = pivot_ngay['SL line chênh lệch'].astype(int)
pivot_ngay['SL line nhập=0'] = pivot_ngay['SL line nhập=0'].astype(int)
pivot_ngay.insert(1, 'SL line nhập=0 / chênh lệch', pivot_ngay['SL line nhập=0'].astype(str) + " / " + pivot_ngay['SL line chênh lệch'].astype(str))
pivot_ngay = pivot_ngay.drop(columns=['SL line nhập=0', 'SL line chênh lệch'])

tong_row_ngay.insert(1, 'SL line nhập=0 / chênh lệch', '')
pivot_ngay = pd.concat([tong_row_ngay, pivot_ngay], ignore_index=True)

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
pivot_clv2 = pd.concat([tong_row_clv2, pivot_clv2], ignore_index=True)
# 3. Top 5 CLV4 (Chênh lệch lớn nhất - tính theo trị tuyệt đối)
clv4_sum = df_active.groupby('CLV4')[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch']].sum().reset_index()
clv4_sum['Abs_ChenhLech'] = clv4_sum['Chênh lệch'].abs()
pivot_clv4 = clv4_sum.sort_values(by='Abs_ChenhLech', ascending=False).drop(columns=['Abs_ChenhLech']).head(5)

# 4A. Bảng SỐ LƯỢNG Chi tiết Từng Ngày - Siêu Thị
pivot_qty_sum = df_active.groupby(['Ngày_str', 'ID ST', 'Chi nhánh nhận'])[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Hao hụt', 'BS_ST', 'Kho_Rau', 'CXD']].sum()
pivot_qty_count = df_active[df_active['Chênh lệch'].abs() > 0].groupby(['Ngày_str', 'ID ST', 'Chi nhánh nhận']).size().rename('SL line chênh lệch')
pivot_qty_nhap0 = df_active[(df_active['Số lượng nhận'] == 0) & (df_active['Chênh lệch'].abs() > 0)].groupby(['Ngày_str', 'ID ST', 'Chi nhánh nhận']).size().rename('SL line nhập=0')

pivot_qty = pivot_qty_sum.join(pivot_qty_count).join(pivot_qty_nhap0).fillna(0).reset_index()
pivot_qty['SL line chênh lệch'] = pivot_qty['SL line chênh lệch'].astype(int)
pivot_qty['SL line nhập=0'] = pivot_qty['SL line nhập=0'].astype(int)
pivot_qty.insert(3, 'SL line nhập=0 / chênh lệch', pivot_qty['SL line nhập=0'].astype(str) + " / " + pivot_qty['SL line chênh lệch'].astype(str))

pivot_qty.rename(columns={
    'BS_ST': 'SL đã tạo bs cho ST',
    'Kho_Rau': 'SL đã xác nhận được trả kho rau',
    'Hao hụt': 'Số lượng hao hụt',
    'CXD': 'Số lượng chưa xác định'
}, inplace=True)
pivot_qty['Tỷ lệ (%)'] = np.where(pivot_qty['Số lượng chuyển'] > 0, (pivot_qty['Chênh lệch'] / pivot_qty['Số lượng chuyển']) * 100, 0)
pivot_qty['% CXD'] = np.where(pivot_qty['Chênh lệch'].abs() > 0, (pivot_qty['Số lượng chưa xác định'] / pivot_qty['Chênh lệch'].abs()) * 100, 0)
pivot_qty['Abs_ChenhLech'] = pivot_qty['Chênh lệch'].abs()
pivot_qty = pivot_qty.sort_values(by='Abs_ChenhLech', ascending=False).drop(columns=['Abs_ChenhLech'])
pivot_qty = pivot_qty[['Ngày_str', 'ID ST', 'Chi nhánh nhận', 'SL line nhập=0 / chênh lệch', 'Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Tỷ lệ (%)', 'SL đã tạo bs cho ST', 'SL đã xác nhận được trả kho rau', 'Số lượng hao hụt', 'Số lượng chưa xác định', '% CXD']]

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

# Hàm format dòng tổng (vàng, in đậm)
def highlight_tong_row(row):
    if any(str(val) == 'Tổng' for val in row.values):
        return ['font-weight: bold; color: #ffeb3b; background-color: #424242'] * len(row)
    return [''] * len(row)

# Hàm format số theo chuẩn Việt Nam (1.000.000,00)
def format_vn(val):
    if isinstance(val, (int, float)):
        # Format chuẩn tiếng anh 1,234.56 -> đổi chéo phẩy và chấm
        return f"{val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    return val

# Layout cho các bảng
st.write("---")
st.subheader("📅 1. TỔNG HỢP THEO TỪNG NGÀY")
st.dataframe(pivot_ngay.style.format(format_vn).map(color_red_for_chenhlech, subset=['Chênh lệch']).apply(highlight_tong_row, axis=1), use_container_width=True)

st.write("---")
col4, col5 = st.columns(2)
with col4:
    st.subheader("🔥 2. TOP 5 CATE CHÊNH LỆCH LỚN NHẤT")
    st.dataframe(pivot_clv4.style.format(format_vn).map(color_red_for_chenhlech, subset=['Chênh lệch']), use_container_width=True)
with col5:
    st.subheader("📦 3. TỔNG HỢP THEO NGÀNH HÀNG (CLV2)")
    st.dataframe(pivot_clv2.style.format(format_vn).map(color_red_for_chenhlech, subset=['Chênh lệch']).apply(highlight_tong_row, axis=1), use_container_width=True)

st.write("---")
st.subheader("🏬 4. CHI TIẾT SỐ LƯỢNG & GIÁ TRỊ THEO SIÊU THỊ")

# Bộ lọc theo ngày dùng chung cho cả 2 bảng
sorted_dates = [d for d in pivot_ngay['Ngày_str'] if d != 'Tổng']
dates = ["Tất cả các ngày"] + sorted_dates
selected_date = st.selectbox("🔍 Lọc theo Ngày:", dates)

if selected_date != "Tất cả các ngày":
    filtered_qty = pivot_qty[pivot_qty['Ngày_str'] == selected_date]
    filtered_val = pivot_val_sum[pivot_val_sum['Ngày_str'] == selected_date]
else:
    filtered_qty = pivot_qty
    filtered_val = pivot_val_sum

tab1, tab2 = st.tabs(["📊 Chi Tiết SỐ LƯỢNG", "💰 Chi Tiết GIÁ TRỊ (VNĐ)"])

with tab1:
    st.dataframe(filtered_qty.style.format(format_vn).map(color_red_for_chenhlech, subset=['Chênh lệch', 'Tỷ lệ (%)']), use_container_width=True, height=600)
    
with tab2:
    st.dataframe(filtered_val.style.format(format_vn), use_container_width=True, height=600)

st.write("---")
st.subheader("🚨 5. BÁO CÁO LỖI: ST NHẬP THIẾU")

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

    def append_tong_row(df_to_append, label_col):
        if df_to_append.empty: return df_to_append
        tong_row = df_to_append.sum(numeric_only=True).to_frame().T
        tong_row[label_col] = 'Tổng'
        return pd.concat([tong_row, df_to_append], ignore_index=True)
        
    t1_loi = append_tong_row(t1_loi, 'ID ST')
    t2_loi = append_tong_row(t2_loi, 'RSM phụ trách')
    t3_loi = append_tong_row(t3_loi, 'GSM phụ trách')

    st.write(f"**Bảng tổng hợp theo Siêu thị ({week_filter})**")
    st.dataframe(t1_loi.style.format(format_vn).apply(highlight_tong_row, axis=1), use_container_width=True)
    
    col6, col7 = st.columns(2)
    with col6:
        st.write(f"**Bảng tổng hợp theo RSM ({week_filter})**")
        st.dataframe(t2_loi.style.format(format_vn).apply(highlight_tong_row, axis=1), use_container_width=True)
    with col7:
        st.write(f"**Bảng tổng hợp theo GSM ({week_filter})**")
        st.dataframe(t3_loi.style.format(format_vn).apply(highlight_tong_row, axis=1), use_container_width=True)
else:
    st.info(f"Không có dữ liệu lỗi 'ST nhập thiếu' trong {week_filter}.")
