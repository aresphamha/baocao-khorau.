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
    
    for col in ['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Tổng GT', 'Tổng ST', 'Tổng kho rau', 'Tổng hao hụt', 'Tổng chưa xác định']:
        if col in df.columns:
            df[col] = df[col].apply(clean_number)
            
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
pivot_clv2_count = df_may[df_may['Chênh lệch'] > 0].groupby('CLV2').size().rename('Số lượng line')
pivot_clv2 = pivot_clv2_sum.join(pivot_clv2_count).fillna(0).reset_index()
pivot_clv2['Số lượng line'] = pivot_clv2['Số lượng line'].astype(int)
pivot_clv2 = pivot_clv2[['CLV2', 'Số lượng line', 'Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch']]
pivot_clv2 = pivot_clv2.sort_values(by='Chênh lệch', ascending=False)
tong_row_clv2 = pivot_clv2.sum(numeric_only=True).to_frame().T
tong_row_clv2['CLV2'] = 'Tổng'
pivot_clv2 = pd.concat([pivot_clv2, tong_row_clv2], ignore_index=True)

# 3. Top 5 CLV4
pivot_clv4 = df_may.groupby('CLV4')[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch']].sum().reset_index().sort_values(by='Chênh lệch', ascending=False).head(5)

# 4. Chi tiết Từng Ngày - Siêu Thị
pivot_ngay_st_sum = df_may.groupby(['Ngày_str', 'ID ST', 'Chi nhánh nhận'])[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Tổng GT', 'Tổng ST', 'Tổng kho rau', 'Tổng hao hụt', 'Tổng chưa xác định']].sum()
pivot_ngay_st_count = df_may[df_may['Chênh lệch'] > 0].groupby(['Ngày_str', 'ID ST', 'Chi nhánh nhận']).size().rename('Số lượng line')
pivot_ngay_st = pivot_ngay_st_sum.join(pivot_ngay_st_count).fillna(0).reset_index()
pivot_ngay_st['Số lượng line'] = pivot_ngay_st['Số lượng line'].astype(int)
pivot_ngay_st.rename(columns={
    'Tổng GT': 'Giá trị chênh lệch',
    'Tổng ST': 'SL đã tạo bs cho ST',
    'Tổng kho rau': 'SL đã xác nhận được trả kho rau',
    'Tổng hao hụt': 'Số lượng hao hụt',
    'Tổng chưa xác định': 'Số lượng chưa xác định'
}, inplace=True)
pivot_ngay_st['Tỷ lệ (%)'] = np.where(pivot_ngay_st['Số lượng chuyển'] > 0, (pivot_ngay_st['Chênh lệch'] / pivot_ngay_st['Số lượng chuyển']) * 100, 0)
pivot_ngay_st['% CXD'] = np.where(pivot_ngay_st['Chênh lệch'] > 0, (pivot_ngay_st['Số lượng chưa xác định'] / pivot_ngay_st['Chênh lệch']) * 100, 0)
pivot_ngay_st = pivot_ngay_st.sort_values(by='Chênh lệch', ascending=False)
pivot_ngay_st = pivot_ngay_st[['Ngày_str', 'ID ST', 'Chi nhánh nhận', 'Số lượng line', 'Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Giá trị chênh lệch', 'Tỷ lệ (%)', 'SL đã tạo bs cho ST', 'SL đã xác nhận được trả kho rau', 'Số lượng hao hụt', 'Số lượng chưa xác định', '% CXD']]

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

# Layout cho các bảng
st.write("---")
st.subheader("📅 1. TỔNG HỢP THEO TỪNG NGÀY")
st.dataframe(pivot_ngay.style.format(precision=2), use_container_width=True)

st.write("---")
col4, col5 = st.columns(2)
with col4:
    st.subheader("🔥 2. TOP 5 CATE CHÊNH LỆCH LỚN NHẤT")
    st.dataframe(pivot_clv4.style.format(precision=2), use_container_width=True)
with col5:
    st.subheader("📦 3. TỔNG HỢP THEO NGÀNH HÀNG (CLV2)")
    st.dataframe(pivot_clv2.style.format(precision=2), use_container_width=True)

st.write("---")
st.subheader("🏬 4. CHI TIẾT TỪNG NGÀY THEO SIÊU THỊ")

# Bộ lọc theo ngày
dates = ["Tất cả các ngày"] + list(pivot_ngay_st['Ngày_str'].unique())
selected_date = st.selectbox("🔍 Lọc theo Ngày:", dates)

if selected_date != "Tất cả các ngày":
    filtered_df = pivot_ngay_st[pivot_ngay_st['Ngày_str'] == selected_date]
else:
    filtered_df = pivot_ngay_st

st.dataframe(filtered_df.style.format(precision=2), use_container_width=True, height=600)
