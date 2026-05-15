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
    csv_url = "https://docs.google.com/spreadsheets/d/1suHerEzgKzxB7g1UbrGIZPNaxK5a96xFnmxcIQywpko/export?format=csv&gid=1422896115"
    df = pd.read_csv(csv_url, skiprows=2)
    df.columns = [str(c).strip() for c in df.columns]
    
    for col in ['Số lượng chuyển', 'Số lượng nhận', 'Tổng GT', 'Tổng ST', 'Tổng kho rau', 'Tổng hao hụt', 'Tổng chưa xác định']:
        if col in df.columns:
            df[col] = df[col].apply(clean_number)
            
    # Tính toán cột Chênh lệch và các cột Số lượng chi tiết
    df['Chênh lệch'] = df['Số lượng nhận'] - df['Số lượng chuyển']
    
    df['Hao hụt'] = pd.to_numeric(df['Hạo hụt tự nhiên'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    df['BS_ST'] = pd.to_numeric(df['SLbổ sung cho ST '].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    df['CXD'] = pd.to_numeric(df['SL chênh lệch CXD'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    df['Kho_Rau'] = df['Chênh lệch'].abs() - df['Hao hụt'] - df['BS_ST'] - df['CXD']
            
    df['Ngày'] = pd.to_datetime(df['Ngày chuyển hàng'], format='%m/%d/%Y', errors='coerce')
    df_may = df[df['Ngày'].dt.month == 5].copy()
    if df_may.empty:
        df_may = df.copy()
        
    df_may['Ngày_str'] = df_may['Ngày'].dt.strftime('%d/%m/%Y').fillna(df_may['Ngày chuyển hàng'])
    
    return df_may

# Load Data
with st.spinner('Đang tải dữ liệu từ Google Sheets...'):
    df_may = load_data()

# Process Dataframes
# 1. Theo ngày
pivot_ngay = df_may.groupby('Ngày_str')[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch']].sum().reset_index()
pivot_ngay['Ngày_dt'] = pd.to_datetime(pivot_ngay['Ngày_str'], format='%d/%m/%Y', errors='coerce')
pivot_ngay = pivot_ngay.sort_values(by='Ngày_dt').drop(columns=['Ngày_dt'])
tong_row_ngay = pivot_ngay.sum(numeric_only=True).to_frame().T
tong_row_ngay['Ngày_str'] = 'Tổng'
pivot_ngay = pd.concat([pivot_ngay, tong_row_ngay], ignore_index=True)

# 2. Theo CLV2
pivot_clv2_sum = df_may.groupby('CLV2')[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch']].sum()
pivot_clv2_count = df_may[df_may['Chênh lệch'].abs() > 0].groupby('CLV2').size().rename('Số lượng line')
pivot_clv2 = pivot_clv2_sum.join(pivot_clv2_count).fillna(0).reset_index()
pivot_clv2['Số lượng line'] = pivot_clv2['Số lượng line'].astype(int)
pivot_clv2 = pivot_clv2[['CLV2', 'Số lượng line', 'Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch']]
pivot_clv2 = pivot_clv2.sort_values(by='Chênh lệch', ascending=True) # Sắp xếp tăng dần vì số chênh lệch thường là âm
tong_row_clv2 = pivot_clv2.sum(numeric_only=True).to_frame().T
tong_row_clv2['CLV2'] = 'Tổng'
pivot_clv2 = pd.concat([pivot_clv2, tong_row_clv2], ignore_index=True)

# 3. Top 5 CLV4 (Chênh lệch lớn nhất - tính theo trị tuyệt đối)
clv4_sum = df_may.groupby('CLV4')[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch']].sum().reset_index()
clv4_sum['Abs_ChenhLech'] = clv4_sum['Chênh lệch'].abs()
pivot_clv4 = clv4_sum.sort_values(by='Abs_ChenhLech', ascending=False).drop(columns=['Abs_ChenhLech']).head(5)

# 4A. Bảng SỐ LƯỢNG Chi tiết Từng Ngày - Siêu Thị
pivot_qty_sum = df_may.groupby(['Ngày_str', 'ID ST', 'Chi nhánh nhận'])[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Hao hụt', 'BS_ST', 'Kho_Rau', 'CXD']].sum()
pivot_qty_count = df_may[df_may['Chênh lệch'].abs() > 0].groupby(['Ngày_str', 'ID ST', 'Chi nhánh nhận']).size().rename('Số lượng line')
pivot_qty = pivot_qty_sum.join(pivot_qty_count).fillna(0).reset_index()
pivot_qty['Số lượng line'] = pivot_qty['Số lượng line'].astype(int)
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
pivot_qty = pivot_qty[['Ngày_str', 'ID ST', 'Chi nhánh nhận', 'Số lượng line', 'Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Tỷ lệ (%)', 'SL đã tạo bs cho ST', 'SL đã xác nhận được trả kho rau', 'Số lượng hao hụt', 'Số lượng chưa xác định', '% CXD']]

# 4B. Bảng GIÁ TRỊ Chi tiết Từng Ngày - Siêu Thị
pivot_val_sum = df_may.groupby(['Ngày_str', 'ID ST', 'Chi nhánh nhận'])[['Tổng GT', 'Tổng ST', 'Tổng kho rau', 'Tổng hao hụt', 'Tổng chưa xác định']].sum().reset_index()
pivot_val_sum.rename(columns={'Tổng GT': 'Giá trị chênh lệch (VNĐ)'}, inplace=True)

# Nút Tải lại dữ liệu
if st.button('🔄 Cập nhật dữ liệu mới nhất'):
    st.cache_data.clear()
    st.rerun()

# Thẻ thông tin (Metrics)
st.write("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Tổng số lượng chuyển", f"{pivot_clv2.iloc[-1]['Số lượng chuyển']:,.1f}")
with col2:
    st.metric("Tổng số lượng nhận", f"{pivot_clv2.iloc[-1]['Số lượng nhận']:,.1f}")
with col3:
    st.metric("TỔNG CHÊNH LỆCH", f"{pivot_clv2.iloc[-1]['Chênh lệch']:,.1f}")

# Hàm format màu đỏ cho số âm
def color_negative_red(val):
    color = 'red' if isinstance(val, (int, float)) and val < 0 else ''
    return f'color: {color}'

# Layout cho các bảng
st.write("---")
st.subheader("📅 1. TỔNG HỢP THEO TỪNG NGÀY")
st.dataframe(pivot_ngay.style.format(precision=2).map(color_negative_red, subset=['Chênh lệch']), use_container_width=True)

st.write("---")
col4, col5 = st.columns(2)
with col4:
    st.subheader("🔥 2. TOP 5 CATE CHÊNH LỆCH LỚN NHẤT")
    st.dataframe(pivot_clv4.style.format(precision=2).map(color_negative_red, subset=['Chênh lệch']), use_container_width=True)
with col5:
    st.subheader("📦 3. TỔNG HỢP THEO NGÀNH HÀNG (CLV2)")
    st.dataframe(pivot_clv2.style.format(precision=2).map(color_negative_red, subset=['Chênh lệch']), use_container_width=True)

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
    st.dataframe(filtered_qty.style.format(precision=2).map(color_negative_red, subset=['Chênh lệch', 'Tỷ lệ (%)']), use_container_width=True, height=600)
    
with tab2:
    st.dataframe(filtered_val.style.format(precision=2), use_container_width=True, height=600)
