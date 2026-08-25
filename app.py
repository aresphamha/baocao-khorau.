import streamlit as st
import pandas as pd
import numpy as np
import io
import pymysql

# DB connection helper for StarRocks database
def get_connection():
    return pymysql.connect(
        host='103.147.122.103',
        port=9030,
        user='kfm_scm_tho_nguyen',
        password='oh1dtJwR4ihLGrX4E7bs',
        database='kfm_scm',
    )

def fetch_data_to_df(sql_query):
    conn = get_connection()
    try:
        df = pd.read_sql(sql_query, conn)
        return df
    finally:
        conn.close()

def get_excel_bytes(df):
    output = io.BytesIO()
    df_to_export = df.copy()
    if isinstance(df_to_export.columns, pd.MultiIndex):
        df_to_export.columns = [' - '.join(str(c) for c in col if c).strip() for col in df_to_export.columns.values]
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
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

# Hàm làm sạch số liệu thông minh (Xử lý lẫn lộn định dạng Anh/Việt)
def clean_number(x):
    if pd.isna(x) or x == '':
        return 0.0
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        x = x.strip()
        if x == '':
            return 0.0
        num_dots = x.count('.')
        num_commas = x.count(',')
        
        if num_dots > 0 and num_commas > 0:
            last_dot = x.rfind('.')
            last_comma = x.rfind(',')
            if last_comma > last_dot: # Format VN: 1.234,50
                x = x.replace('.', '').replace(',', '.')
            else: # Format EN: 1,234.50
                x = x.replace(',', '')
        elif num_commas > 0:
            parts = x.split(',')
            if num_commas > 1:
                x = x.replace(',', '')
            else:
                x = x.replace(',', '.') # VN format: comma is decimal
        elif num_dots > 0:
            parts = x.split('.')
            if num_dots > 1:
                x = x.replace('.', '')
            else:
                if len(parts[1]) == 3 and parts[0] not in ['0', '-0']:
                    x = x.replace('.', '') # VD: 16.000 -> 16000
                else:
                    pass # VD: 5.5 -> 5.5
    try:
        return float(x)
    except:
        return 0.0

@st.cache_data(ttl=600)  # Tự động tải lại sau mỗi 10 phút nếu có người truy cập
def load_data():
    url_apr = "https://docs.google.com/spreadsheets/d/1mYAbl4UDhjUSfr44xYdZX5YC_mG5-_9fK4tWgG8zlew/export?format=csv"
    url_may = "https://docs.google.com/spreadsheets/d/1ee53DtTCNLsr94afbuQEY_yI2EzNfrgPGCdvNDLIUZ0/export?format=csv"
    url_jun = "https://docs.google.com/spreadsheets/d/1065akVGAsBNjONniCS6ccU_mmsRFXb663_Qms8U053Q/export?format=csv"
    url_jun_new = "https://docs.google.com/spreadsheets/d/1wdbowphojL8YULVlPwDHK-hofacdt6J5K_PFZbWz-as/export?format=csv"
    url_aug = "https://docs.google.com/spreadsheets/d/1vPHHrZf5prEgE_09j_RbQQC1gNWhUmV0Q6aah6Z3mjQ/export?format=csv&gid=1422896115"
    
    def read_csv_with_retry(url, max_retries=3):
        import time
        import requests
        import io
        for i in range(max_retries):
            try:
                response = requests.get(url, timeout=30, verify=False)

                response.raise_for_status()
                return pd.read_csv(io.BytesIO(response.content), skiprows=2, dtype=str)
            except Exception as e:
                if i == max_retries - 1:
                    raise e
                time.sleep(2)
                
    df_apr = read_csv_with_retry(url_apr)
    df_may = read_csv_with_retry(url_may)
    df_jun = read_csv_with_retry(url_jun)
    df_jun_new = read_csv_with_retry(url_jun_new)
    df_aug = read_csv_with_retry(url_aug)
    
    df_apr.columns = [str(c).strip() for c in df_apr.columns]
    df_may.columns = [str(c).strip() for c in df_may.columns]
    df_jun.columns = [str(c).strip() for c in df_jun.columns]
    df_jun_new.columns = [str(c).strip() for c in df_jun_new.columns]
    df_aug.columns = [str(c).strip() for c in df_aug.columns]
    
    # Đồng bộ tên cột Tháng 4 cho giống với Tháng 5
    df_apr.rename(columns={
        'ST': 'ID ST',
        'SL chênh lệch ĐXL': 'SL chênh lệch CXD',
        'SLbổ sung cho ST': 'SL trả tồn về ST'
    }, inplace=True)
    
    df_jun.rename(columns={
        'ST': 'ID ST',
        'SL chênh lệch ĐXL': 'SL chênh lệch CXD',
        'SLbổ sung cho ST': 'SL trả tồn về ST'
    }, inplace=True)
    
    df_jun_new.rename(columns={
        'ST': 'ID ST',
        'SL chênh lệch ĐXL': 'SL chênh lệch CXD',
        'SLbổ sung cho ST': 'SL trả tồn về ST'
    }, inplace=True)
    
    df_aug.rename(columns={
        'SL chuyển': 'Số lượng chuyển',
        'SL nhận': 'Số lượng nhận',
        'ST': 'ID ST',
        'SL chênh lệch ĐXL': 'SL chênh lệch CXD',
        'SLbổ sung cho ST': 'SL trả tồn về ST'
    }, inplace=True)
    
    # Loại trừ các ngày của tháng 5 trong sheet tháng 6, và chỉ giữ các ngày trước 25/06
    df_jun['temp_date'] = pd.to_datetime(df_jun['Ngày chuyển hàng'], format='%m/%d/%Y', errors='coerce')
    df_jun = df_jun[((df_jun['temp_date'].dt.month != 5) & (df_jun['temp_date'] < '2026-06-25')) | (df_jun['Ngày chuyển hàng'].isna())].copy()
    df_jun = df_jun.drop(columns=['temp_date'])
    
    # Đối với sheet mới, chỉ giữ lại từ ngày 25/06 trở đi
    df_jun_new['temp_date'] = pd.to_datetime(df_jun_new['Ngày chuyển hàng'], format='%m/%d/%Y', errors='coerce')
    df_jun_new = df_jun_new[(df_jun_new['temp_date'] >= '2026-06-25') | (df_jun_new['Ngày chuyển hàng'].isna())].copy()
    df_jun_new = df_jun_new.drop(columns=['temp_date'])
    
    df = pd.concat([df_apr, df_may, df_jun, df_jun_new, df_aug], ignore_index=True)
    
    for col in ['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Tổng GT', 'Tổng ST', 'Tổng kho rau', 'Tổng hao hụt', 'Tổng chưa xác định']:
        if col in df.columns:
            df[col] = df[col].apply(clean_number)
            
    if 'Chi nhánh nhận' in df.columns:
        df['Chi nhánh nhận'] = df['Chi nhánh nhận'].astype(str).str.replace(',', '.', regex=False)
            
    # Lọc số lượng dựa trên cột lý do W (Hao hụt), X (Siêu thị), Y (Kho rau / Chưa xác định)
    # W tương ứng N, X tương ứng O, Y tương ứng P
    df['LyDo_W'] = df['Hao hụt'].astype(str).str.strip().str.lower()
    df['LyDo_X'] = df['Siêu thị'].astype(str).str.strip().str.lower()
    # Kết hợp cột Y giữa các tháng cũ (Kho rau\nChưa xác định) và tháng mới (Kho rau)
    col_y = df.get('Kho rau\nChưa xác định', pd.Series(np.nan, index=df.index)).fillna(df.get('Kho rau', np.nan))
    df['LyDo_Y'] = col_y.astype(str).str.strip().str.lower()
    df['LyDo_Loi'] = df['Lỗi'].astype(str).str.strip().str.lower() if 'Lỗi' in df.columns else ''
    
    df['Qty_N'] = df['Hạo hụt tự nhiên'].apply(clean_number)
    
    # Handle column name change between months
    qty_o_col = 'SL trả tồn về ST' if 'SL trả tồn về ST' in df.columns else 'SLbổ sung cho ST'
    df['Qty_O'] = df.get(qty_o_col, pd.Series(0, index=df.index)).apply(clean_number)
    
    df['Qty_P'] = df['SL chênh lệch CXD'].apply(clean_number)

    
    df['Hao hụt'] = np.where(df['LyDo_W'].str.contains('hao hụt'), df['Qty_N'], 0)
    df['BS_ST'] = np.where(df['LyDo_X'].str.contains('siêu thị'), df['Qty_O'], 0)
    df['ST_NhapThieu'] = np.where(df['LyDo_X'].str.contains('siêu thị') & df['LyDo_Loi'].str.contains('thiếu'), df['Qty_O'], 0)
    df['ST_SaiQT'] = np.where(df['LyDo_X'].str.contains('siêu thị') & ~df['LyDo_Loi'].str.contains('thiếu'), df['Qty_O'], 0)
    df['Kho_Rau'] = np.where(df['LyDo_Y'].str.contains('kho rau'), df['Qty_P'], 0)
    df['CXD'] = np.where(df['LyDo_Y'].str.contains('chưa xác định'), df['Qty_P'], 0)
            
    df['Ngày'] = pd.to_datetime(df['Ngày chuyển hàng'], format='%m/%d/%Y', errors='coerce')
    df['Ngày_str'] = df['Ngày'].dt.strftime('%d/%m/%Y').fillna(df['Ngày chuyển hàng'])
    
    df = df[df['Ngày'].notna()]
    
    # Tạo cột hiển thị SKU
    if 'Tên hàng' in df.columns and 'Tên Hàng' in df.columns:
        ten_hang = df['Tên hàng'].fillna(df['Tên Hàng'])
    elif 'Tên hàng' in df.columns:
        ten_hang = df['Tên hàng']
    elif 'Tên Hàng' in df.columns:
        ten_hang = df['Tên Hàng']
    else:
        ten_hang = pd.Series([''] * len(df))
        
    df['SKU_Full'] = df['Mã hàng'].fillna('').astype(str) + " - " + ten_hang.fillna('').astype(str)
    
    return df

@st.cache_data(ttl=3600)
def load_transfer_data_v2():
    try:
        url = 'https://docs.google.com/spreadsheets/d/1suHerEzgKzxB7g1UbrGIZPNaxK5a96xFnmxcIQywpko/export?format=xlsx'
        import requests
        import io
        response = requests.get(url, verify=False, timeout=30)
        df_clv2 = pd.read_excel(io.BytesIO(response.content), sheet_name='CLV2')

        mapping_clv2 = dict(zip(df_clv2['Mã hàng'].astype(str), df_clv2['Cate Level 2']))
        mapping_dvt = dict(zip(df_clv2['Mã hàng'].astype(str), df_clv2['ĐVT']))
        
        df_transfer = pd.read_excel(r'D:\Doi_Soat_Kho_Rau\AI\Chi tiết đi hàng 25.5.xlsx', sheet_name='transfer')
        df_transfer['Mã hàng'] = df_transfer['Mã hàng'].astype(str)
        df_transfer['Số lượng chuyển'] = pd.to_numeric(df_transfer['Số lượng chuyển'], errors='coerce').fillna(0)
        df_transfer['Số lượng nhận'] = pd.to_numeric(df_transfer['Số lượng nhận'], errors='coerce').fillna(0)
        df_transfer['CLV2'] = df_transfer['Mã hàng'].map(mapping_clv2)
        df_transfer['ĐVT'] = df_transfer['Mã hàng'].map(mapping_dvt)
        return df_transfer
    except Exception as e:
        print("Error loading transfer 25.5:", e)
        return pd.DataFrame()

# Load Data
with st.spinner('Đang tải dữ liệu từ Google Sheets và file hệ thống...'):
    df_all = load_data()
    df_transfer_25_5 = load_transfer_data_v2()

st.write("---")

# HÀM XỬ LÝ SỐ AN TOÀN CHO BÁO CÁO DAILY
def to_numeric(series):
    if series.dtype == 'object':
        return pd.to_numeric(series.str.replace(',', '.'), errors='coerce').fillna(0)
    return pd.to_numeric(series, errors='coerce').fillna(0)

def generate_insights(df_raw, table_type, df_grouped=None, df_metrics=None, date_str=None):
    if df_raw.empty and (df_grouped is None or df_grouped.empty):
        return "Không có dữ liệu trong kỳ báo cáo này."
    
    def get_hh_insight():
        if df_metrics is not None and not df_metrics.empty and 'Số lượng chuyển' in df_metrics.columns and 'Số lượng hao hụt' in df_metrics.columns:
            tong_chuyen = df_metrics['Số lượng chuyển'].sum()
            tong_hh = df_metrics['Số lượng hao hụt'].sum()
            if tong_chuyen > 0:
                return f"\n- Tỷ lệ hao hụt ghi nhận: {round((tong_hh / tong_chuyen) * 100, 2)}%."
        return ""
    
    try:
        if table_type == "Bảng 1":
            df_raw_tmp = df_raw.copy()
            df_raw_tmp['Chênh_lệch_num'] = to_numeric(df_raw_tmp['Chênh lệch'])
            df_raw_tmp['Kho_Rau_num'] = to_numeric(df_raw_tmp['Kho_Rau'])
            df_raw_tmp['BS_ST_num'] = to_numeric(df_raw_tmp['BS_ST'])
            
            total_lines = len(df_raw_tmp)
            total_chenh_lech = df_raw_tmp['Chênh_lệch_num'].sum()
            
            def fmt(val):
                try: return f"{int(val):,}".replace(',', '.') if float(val).is_integer() else f"{float(val):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                except: return str(val)
                
            msg = f"Trong kỳ có tổng cộng {total_lines} dòng phát sinh chênh lệch (Tổng chênh lệch: {fmt(total_chenh_lech)}).\n"
            msg += "\n- Phân tích 3 nhóm ngành hàng (CLV4) phát sinh chênh lệch cao nhất:\n"
            
            clv4_lines = df_raw_tmp['CLV4'].value_counts()
            top3_clv4 = clv4_lines.head(3)
            
            for clv4, lines in top3_clv4.items():
                sub_df = df_raw_tmp[df_raw_tmp['CLV4'] == clv4]
                sub_cl = sub_df['Chênh_lệch_num'].sum()
                sub_kr = sub_df['Kho_Rau_num'].sum()
                msg += f"  + [{clv4}]: {lines} dòng (Tổng chênh lệch: {fmt(sub_cl)} | Trả về Kho Rau: {fmt(sub_kr)})\n"
                
            msg += "\n- Phân bổ trả về Siêu Thị (ST):\n"
            st_by_clv4 = df_raw_tmp.groupby('CLV4')['BS_ST_num'].sum().sort_values(ascending=False)
            st_by_clv4 = st_by_clv4[st_by_clv4 > 0]
            
            if not st_by_clv4.empty:
                top_st_clv4 = st_by_clv4.index[0]
                top_st_val = st_by_clv4.iloc[0]
                total_st = st_by_clv4.sum()
                if top_st_val > (total_st * 0.3) and len(st_by_clv4) > 1:
                    msg += f"  Số lượng trả về ST tập trung nhiều nhất ở nhóm [{top_st_clv4}] ({fmt(top_st_val)}).\n"
                elif len(st_by_clv4) > 1:
                    msg += f"  Số lượng trả về ST nằm rải rác lẻ tẻ (cao nhất là [{top_st_clv4}] với {fmt(top_st_val)}).\n"
                else:
                    msg += f"  Số lượng trả về ST thuộc về nhóm [{top_st_clv4}] ({fmt(top_st_val)}).\n"
            else:
                msg += "  Không phát sinh số lượng chênh lệch trả về ST trong kỳ.\n"
                
            msg += "  -> Nguyên nhân: Do ST thao tác sai nên phải tạo lại thôi."
            msg += get_hh_insight()
            
            return msg
            
        elif table_type == "Bảng 1.1":
            if df_grouped is not None and not df_grouped.empty:
                top_nguon = df_grouped.iloc[0]['Nguồn xác nhận']
                top_sl = df_grouped.iloc[0]['Tổng (Kho Rau + ST)']
                
                def fmt(val):
                    try: return f"{int(val):,}".replace(',', '.') if float(val).is_integer() else f"{float(val):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    except: return str(val)
                
                if top_nguon == 'Check camera':
                    return f"Nguồn thông tin được dùng để xác định chênh lệch trả về các điểm nhận nhiều nhất là [{top_nguon}] (Số lượng: {fmt(top_sl)}).\n- Việc dựa phần lớn vào Check camera cho thấy tình trạng ST báo thiếu/dư hàng nhưng không cung cấp đủ hình ảnh xác thực đang khá cao. Cần nhắc nhở ST tuân thủ quy định chụp hình."
                else:
                    return f"Nguồn thông tin được dùng để xác định chênh lệch trả về các điểm nhận nhiều nhất là dựa vào [{top_nguon}] (Số lượng: {fmt(top_sl)}).\n- Điều này phản ánh cơ sở dữ liệu chính yếu mà DC dùng để đối soát và phân bổ lượng hàng chênh lệch trong kỳ."
            
        elif table_type == "Bảng 2.1_New":
            if df_metrics is not None and not df_metrics.empty:
                t_cl = df_metrics['SL chênh lệch'].sum()
                if t_cl > 0:
                    l_st_nhap = df_metrics.get('Lỗi ST (Nhập thiếu)', pd.Series([0])).sum()
                    l_st_sai = df_metrics.get('Lỗi ST (Sai QT)', pd.Series([0])).sum()
                    l_st_tong = l_st_nhap + l_st_sai
                    pct_st = (l_st_tong / t_cl) * 100
                    pct_nhap = (l_st_nhap / t_cl) * 100
                    pct_sai = (l_st_sai / t_cl) * 100
                    
                    giao_thieu_5 = df_metrics.get('<= 5%', pd.Series([0])).sum()
                    giao_thieu_10 = df_metrics.get('5-10%', pd.Series([0])).sum()
                    giao_thieu_15 = df_metrics.get('10-15%', pd.Series([0])).sum()
                    giao_thieu_15_plus = df_metrics.get('> 15%', pd.Series([0])).sum()
                    
                    pct_5 = (giao_thieu_5 / t_cl) * 100
                    pct_10 = (giao_thieu_10 / t_cl) * 100
                    pct_15 = (giao_thieu_15 / t_cl) * 100
                    pct_15_plus = (giao_thieu_15_plus / t_cl) * 100
                    
                    d_str = "kỳ báo cáo"
                    if date_str and date_str != "Tất cả các ngày":
                        try:
                            d_str = "ngày " + date_str.split('/')[0] + "." + date_str.split('/')[1]
                        except:
                            d_str = "ngày " + str(date_str)
                            
                    def get_top_clv4(col):
                        if col in df_metrics.columns and df_metrics[col].max() > 0:
                            top_row = df_metrics.loc[df_metrics[col].idxmax()]
                            return f"[{top_row['CLV4']}] - {int(top_row[col])} item"
                        return ""
                        
                    top_5_clv4 = get_top_clv4('<= 5%')
                    top_10_clv4 = get_top_clv4('5-10%')
                    top_15_clv4 = get_top_clv4('10-15%')
                    top_15_plus_clv4 = get_top_clv4('> 15%')
                            
                    msg = f"Hàng KG có số lượng nhập nhưng phát sinh chênh lệch ghi nhận {d_str}\n"
                    msg += f"- Lỗi ST chiếm {pct_st:.1f}%: trong đó nhập sót {pct_nhap:.1f}% và sai QT chiếm {pct_sai:.1f}%\n"
                    if l_st_sai > 0:
                        msg += f"  + SL ST sai QT: {int(l_st_sai)}\n"
                    msg += f"- Giao thiếu:\n"
                    msg += f"  + Nhóm <= 5%: {pct_5:.1f}%\n"
                    if top_5_clv4: msg += f"    -> Nhóm lệch nhiều nhất: {top_5_clv4}\n"
                    msg += f"  + Nhóm 5 - 10%: {pct_10:.1f}%\n"
                    if top_10_clv4: msg += f"    -> Nhóm lệch nhiều nhất: {top_10_clv4}\n"
                    msg += f"  + Nhóm 10 - 15%: {pct_15:.1f}%\n"
                    if top_15_clv4: msg += f"    -> Nhóm lệch nhiều nhất: {top_15_clv4}\n"
                    msg += f"  + Nhóm > 15%: {pct_15_plus:.1f}%"
                    if top_15_plus_clv4: msg += f"\n    -> Nhóm lệch nhiều nhất: {top_15_plus_clv4}"
                    return msg
            return "Chưa có đủ dữ liệu để đánh giá."
            
        elif table_type == "Bảng 2.1":
            clv4_counts = df_raw['CLV4'].value_counts()
            top3_clv4_str = ", ".join([f"[{k}] ({v} dòng)" for k, v in clv4_counts.head(3).items()]) if not clv4_counts.empty else 'Không xác định'
            
            sku_counts = df_raw['SKU_Full'].value_counts()
            top_sku = sku_counts.index[0] if not sku_counts.empty else 'Không xác định'
            top_sku_count = sku_counts.iloc[0] if not sku_counts.empty else 0
            
            return f"- Top 3 ngành hàng (CLV4) chiếm đa số chênh lệch: {top3_clv4_str}.\n- Đáng chú ý, mã hàng bị ảnh hưởng nhiều nhất là [{top_sku}] với {top_sku_count} dòng phát sinh." + get_hh_insight()
            
        elif table_type == "Bảng 3":
            clv4_counts = df_raw['CLV4'].value_counts()
            top3_clv4_str = ", ".join([f"[{k}] ({v} dòng)" for k, v in clv4_counts.head(3).items()]) if not clv4_counts.empty else 'Không xác định'
            
            sku_counts = df_raw['SKU_Full'].value_counts()
            top_sku = sku_counts.index[0] if not sku_counts.empty else 'Không xác định'
            top_sku_count = sku_counts.iloc[0] if not sku_counts.empty else 0
            
            base_msg = f"- Top 3 ngành hàng (CLV4) chiếm đa số chênh lệch: {top3_clv4_str}.\n- Đáng chú ý, mã hàng bị ảnh hưởng nhiều nhất là [{top_sku}] với {top_sku_count} dòng phát sinh."
            
            df_kr = df_raw.copy()
            df_kr['Kho_Rau_num'] = to_numeric(df_kr['Kho_Rau'])
            kr_by_clv4 = df_kr.groupby('CLV4')['Kho_Rau_num'].sum().sort_values(ascending=False)
            kr_by_clv4 = kr_by_clv4[kr_by_clv4 > 0]
            
            def fmt(val):
                try: return f"{int(val):,}".replace(',', '.') if float(val).is_integer() else f"{float(val):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                except: return str(val)
                
            if not kr_by_clv4.empty:
                top3 = kr_by_clv4.head(3)
                top3_msg = "\n- Top nhóm ngành hàng (CLV4) đang có lượng chênh lệch trả về Kho Rau cao nhất:\n"
                for i, (clv4, val) in enumerate(top3.items(), 1):
                    top3_msg += f"  {i}. {clv4}: {fmt(val)}\n"
            else:
                top3_msg = "\n- Không ghi nhận hàng Pack nào có chênh lệch trả về Kho Rau trong kỳ."
                
            return base_msg + top3_msg.rstrip() + get_hh_insight()
            
        elif table_type == "Bảng 2.2":
            clv4_counts = df_raw['CLV4'].value_counts()
            top3_clv4_str = ", ".join([f"[{k}] ({v} dòng)" for k, v in clv4_counts.head(3).items()]) if not clv4_counts.empty else 'Không xác định'
            
            sku_counts = df_raw['SKU_Full'].value_counts()
            top_sku = sku_counts.index[0] if not sku_counts.empty else 'Không xác định'
            top_sku_count = sku_counts.iloc[0] if not sku_counts.empty else 0
            
            sum_kr = to_numeric(df_raw['Kho_Rau']).sum()
            sum_st = to_numeric(df_raw['BS_ST']).sum()
            
            def fmt(val):
                try: return f"{int(val):,}".replace(',', '.') if float(val).is_integer() else f"{float(val):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                except: return str(val)
                
            return (f"- Top 3 ngành hàng (CLV4) chiếm đa số chênh lệch: {top3_clv4_str}.\n"
                    f"- Đáng chú ý, mã hàng bị ảnh hưởng nhiều nhất là [{top_sku}] với {top_sku_count} dòng phát sinh.\n"
                    f"- Vấn đề chênh lệch này được phân bổ xử lý như sau:\n"
                    f"  + Trả về ST (Số lượng: {fmt(sum_st)}): Lý do là DC giao bù do ban đầu giao sai điểm.\n"
                    f"  + Trả Kho Rau (Số lượng: {fmt(sum_kr)}): Do có ST khác nhận dư số này và có ST nhận thiếu."
                    f"{get_hh_insight()}")
            
        elif table_type == "Bảng 4":
            if df_grouped is not None and not df_grouped.empty:
                top_sku = df_grouped.iloc[0]['Mã & Tên hàng']
                top_hh = df_grouped.iloc[0]['Tổng số lượng hao hụt']
                
                clv4_counts = df_raw['CLV4'].value_counts()
                top3_clv4_str = ", ".join([f"[{k}] ({v} dòng)" for k, v in clv4_counts.head(3).items()]) if not clv4_counts.empty else 'Không xác định'
                
                return f"- Top 3 ngành hàng (CLV4) phát sinh hao hụt nhiều nhất: {top3_clv4_str}.\n- Mã hàng có sản lượng hao hụt nghiêm trọng nhất là [{top_sku}] (Hao hụt: {top_hh} KG).\n- Khuyến nghị: Cần ưu tiên kiểm tra chất lượng thực tế và quy trình đóng gói đối với mã hàng này."

        elif table_type == "Bảng 6":
            if df_grouped is not None and not df_grouped.empty:
                top_dc = df_grouped.iloc[0]['DC xác nhận']
                top_loi = df_grouped.iloc[0]['Lỗi']
                top_sl = df_grouped.iloc[0]['Tổng số lượng']
                
                def fmt(val):
                    try: return f"{int(val):,}".replace(',', '.') if float(val).is_integer() else f"{float(val):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    except: return str(val)
                
                return f"- Dựa trên xác nhận của DC, lỗi [{top_loi}] được ghi nhận nhiều nhất từ [{top_dc}] với tổng số lượng trả về Kho Rau là {fmt(top_sl)}.\n- Khuyến nghị: DC cần kiểm tra lại quy trình xuất hàng và kiểm đếm để giảm thiểu tình trạng này."

    except Exception as e:
        return "Chưa đủ dữ liệu để tạo nhận xét tự động."
        
    return ""

def render_dc_feedback_progress_report(df, tab_id=""):
    st.write("---")
    
    # Chỉ lấy dữ liệu từ ngày 27/05/2026 trở đi theo yêu cầu
    if 'Ngày' in df.columns:
        df = df[df['Ngày'] >= pd.to_datetime('2026-05-27')]
        
    if df.empty:
        st.info("Không có dữ liệu tiến độ DC phản hồi từ ngày 27/05 trở đi.")
        return
        
    # Tính toán daily summary (Toàn hệ thống)
    df['GT_chuyen_temp'] = to_numeric(df.get('Số lượng chuyển', pd.Series(0, index=df.index))) * to_numeric(df.get('Giá trị ĐV', pd.Series(0, index=df.index)))
    daily_summary = df.groupby('Ngày_str').agg(
        SL_chuyen=('Số lượng chuyển', lambda x: to_numeric(x).sum()),
        SL_chenh_lech=('Chênh lệch', lambda x: to_numeric(x).sum()),
        GT_chuyen=('GT_chuyen_temp', 'sum'),
        GT_chenh_lech=('Tổng GT', lambda x: to_numeric(x).sum())
    ).reset_index()

    # Lọc chỉ lấy các dòng có lý do KHO RAU ở cột Y (Bao gồm P và N)
    col_y_name = 'Kho rau\nChưa xác định' if 'Kho rau\nChưa xác định' in df.columns else ('Kho rau Chưa xác định' if 'Kho rau Chưa xác định' in df.columns else None)
    if col_y_name:
        is_kho_rau = df[col_y_name].astype(str).str.lower().str.contains('kho rau', na=False)
        qty_p = df.get('Qty_P', to_numeric(df.get('SL chênh lệch CXD', pd.Series(0, index=df.index))))
        qty_n = df.get('Qty_N', to_numeric(df.get('Hạo hụt tự nhiên', pd.Series(0, index=df.index))))
        df_dc = df[is_kho_rau & ((qty_p > 0) | (qty_n > 0))].copy()
        df_dc['SL_CXD'] = qty_p + qty_n
        df_dc['GT_CXD'] = to_numeric(df_dc.get('Tổng kho rau', pd.Series(0, index=df_dc.index))) + to_numeric(df_dc.get('Tổng hao hụt', pd.Series(0, index=df_dc.index)))
    else:
        df_dc = df[to_numeric(df.get('Kho_Rau', pd.Series(0, index=df.index))) > 0].copy()
        df_dc['SL_CXD'] = to_numeric(df_dc.get('Kho_Rau', pd.Series(0, index=df_dc.index)))
        df_dc['GT_CXD'] = to_numeric(df_dc.get('Tổng kho rau', pd.Series(0, index=df_dc.index)))
        
    if df_dc.empty:
        st.info("Không có dữ liệu tiến độ DC phản hồi trong kỳ báo cáo này.")
        return
        
    # Làm sạch dữ liệu và xử lý các ô trống/dấu cách
    df_dc['DC_Xac_Nhan'] = df_dc['DC xác nhận'].fillna('Chưa xác nhận')
    df_dc['DC_Xac_Nhan'] = df_dc['DC_Xac_Nhan'].apply(lambda x: 'Chưa xác nhận' if str(x).strip() == '' else x)
    df_dc['Nhom_Loi'] = df_dc['Lỗi'].fillna('Không phân loại').replace('', 'Không phân loại')
    
    if col_y_name:
        df_dc['Chi_Tiet_Loi'] = df_dc[col_y_name].fillna('Không ghi chú').replace('', 'Không ghi chú')
    else:
        df_dc['Chi_Tiet_Loi'] = 'Không ghi chú'
    
    # Tính toán Metrics
    df_chua_xn = df_dc[df_dc['DC_Xac_Nhan'] == 'Chưa xác nhận']
    tong_chua_xn = df_chua_xn['SL_CXD'].sum()
    tong_gt_chua_xn = df_chua_xn['GT_CXD'].sum()
    
    top_loi_name = "Không có"
    if not df_chua_xn.empty:
        loi_sum = df_chua_xn.groupby('Nhom_Loi')['SL_CXD'].sum()
        if not loi_sum.empty and loi_sum.max() > 0:
            top_loi_name = f"{loi_sum.idxmax()} ({int(loi_sum.max())} item)"
            
    def format_vn(val):
        if pd.isna(val): return ""
        if isinstance(val, (int, float)):
            if val == int(val): return f"{int(val):,}".replace(',', '.')
            else:
                formatted = f"{val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                return formatted[:-3] if formatted.endswith(',00') else formatted
        return val
    
    # Hiển thị Metrics
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="🔴 Tổng chờ DC xác nhận", value=f"{int(tong_chua_xn)} item", delta=f"{format_vn(tong_gt_chua_xn)} VNĐ", delta_color="off")
    with col2:
        st.metric(label="🔥 Top 1 Lỗi chờ phản hồi", value=top_loi_name)
    
    st.write("### 📌 Bảng chi tiết (Tiến độ DC)")
    tab_ngay, tab_loi = st.tabs(["📅 Góc nhìn 1: Theo Ngày", "⚠️ Góc nhìn 2: Theo Nhóm Lỗi"])
    
    # Góc nhìn 1
    with tab_ngay:
        st.markdown("**1. Bảng Số Lượng (Item)**")
        pivot_ngay = pd.pivot_table(df_dc, values='SL_CXD', index='Ngày_str', columns='DC_Xac_Nhan', aggfunc='sum', fill_value=0).reset_index()
        dc_cols = [c for c in pivot_ngay.columns if c != 'Ngày_str']
        pivot_ngay['SL KHO RAU'] = pivot_ngay[dc_cols].sum(axis=1)
        
        # Merge và sắp xếp cột
        final_ngay = pd.merge(daily_summary[['Ngày_str', 'SL_chuyen', 'SL_chenh_lech']], pivot_ngay, on='Ngày_str', how='right')
        sorted_dc_cols = [c for c in dc_cols if c != 'Chưa xác nhận']
        sorted_dc_cols.sort()
        if 'Chưa xác nhận' in dc_cols:
            sorted_dc_cols = ['Chưa xác nhận'] + sorted_dc_cols
            
        col_order = ['Ngày_str', 'SL_chuyen', 'SL_chenh_lech', 'SL KHO RAU'] + sorted_dc_cols
        final_ngay = final_ngay[[c for c in col_order if c in final_ngay.columns]]
        
        # Thêm cột % Tiến độ
        final_ngay['% Chưa xác nhận'] = final_ngay.apply(
            lambda r: f"{(r.get('Chưa xác nhận', 0) / r['SL KHO RAU'] * 100):.2f}%".replace('.', ',') if r.get('SL KHO RAU', 0) > 0 else "0,00%", axis=1
        )
        final_ngay['% Tiến độ phản hồi'] = final_ngay.apply(
            lambda r: f"{((r['SL KHO RAU'] - r.get('Chưa xác nhận', 0)) / r['SL KHO RAU'] * 100):.2f}%".replace('.', ',') if r.get('SL KHO RAU', 0) > 0 else "100,00%", axis=1
        )
        
        final_ngay.rename(columns={
            'Ngày_str': 'Ngày chuyển hàng',
            'SL_chuyen': 'SL chuyển',
            'SL_chenh_lech': 'SL chênh lệch'
        }, inplace=True)
        format_custom_table_with_total(final_ngay, 'Ngày chuyển hàng', f"Tien_Do_DC_Theo_Ngay_SL_{tab_id}")
        
        st.markdown("**2. Bảng Giá Trị (VNĐ)**")
        pivot_ngay_gt = pd.pivot_table(df_dc, values='GT_CXD', index='Ngày_str', columns='DC_Xac_Nhan', aggfunc='sum', fill_value=0).reset_index()
        pivot_ngay_gt['GT KHO RAU'] = pivot_ngay_gt[dc_cols].sum(axis=1)
        final_ngay_gt = pd.merge(daily_summary[['Ngày_str', 'GT_chuyen', 'GT_chenh_lech']], pivot_ngay_gt, on='Ngày_str', how='right')
        
        col_order_gt = ['Ngày_str', 'GT_chuyen', 'GT_chenh_lech', 'GT KHO RAU'] + sorted_dc_cols
        final_ngay_gt = final_ngay_gt[[c for c in col_order_gt if c in final_ngay_gt.columns]]
        
        final_ngay_gt['% Chưa xác nhận'] = final_ngay_gt.apply(
            lambda r: f"{(r.get('Chưa xác nhận', 0) / r['GT KHO RAU'] * 100):.2f}%".replace('.', ',') if r.get('GT KHO RAU', 0) > 0 else "0,00%", axis=1
        )
        final_ngay_gt['% Tiến độ phản hồi'] = final_ngay_gt.apply(
            lambda r: f"{((r['GT KHO RAU'] - r.get('Chưa xác nhận', 0)) / r['GT KHO RAU'] * 100):.2f}%".replace('.', ',') if r.get('GT KHO RAU', 0) > 0 else "100,00%", axis=1
        )
        
        final_ngay_gt.rename(columns={
            'Ngày_str': 'Ngày chuyển hàng',
            'GT_chuyen': 'GT chuyển (VNĐ)',
            'GT_chenh_lech': 'GT chênh lệch (VNĐ)'
        }, inplace=True)
        format_custom_table_with_total(final_ngay_gt, 'Ngày chuyển hàng', f"Tien_Do_DC_Theo_Ngay_GT_{tab_id}")
        
    # Góc nhìn 2
    with tab_loi:
        df_dc['Nhóm Lỗi & Chi tiết'] = df_dc['Nhom_Loi'] + " | " + df_dc['Chi_Tiet_Loi']
        
        st.markdown("**1. Bảng Số Lượng (Item)**")
        pivot_loi = pd.pivot_table(df_dc, values='SL_CXD', index='Nhóm Lỗi & Chi tiết', columns='DC_Xac_Nhan', aggfunc='sum', fill_value=0).reset_index()
        pivot_loi['SL KHO RAU'] = pivot_loi[dc_cols].sum(axis=1)
        col_order_loi = ['Nhóm Lỗi & Chi tiết', 'SL KHO RAU'] + sorted_dc_cols
        pivot_loi = pivot_loi[[c for c in col_order_loi if c in pivot_loi.columns]]
        
        pivot_loi['% Chưa xác nhận'] = pivot_loi.apply(
            lambda r: f"{(r.get('Chưa xác nhận', 0) / r['SL KHO RAU'] * 100):.2f}%".replace('.', ',') if r.get('SL KHO RAU', 0) > 0 else "0,00%", axis=1
        )
        pivot_loi['% Tiến độ phản hồi'] = pivot_loi.apply(
            lambda r: f"{((r['SL KHO RAU'] - r.get('Chưa xác nhận', 0)) / r['SL KHO RAU'] * 100):.2f}%".replace('.', ',') if r.get('SL KHO RAU', 0) > 0 else "100,00%", axis=1
        )
        
        format_custom_table_with_total(pivot_loi, 'Nhóm Lỗi & Chi tiết', f"Tien_Do_DC_Theo_Loi_SL_{tab_id}")
        
        st.markdown("**2. Bảng Giá Trị (VNĐ)**")
        pivot_loi_gt = pd.pivot_table(df_dc, values='GT_CXD', index='Nhóm Lỗi & Chi tiết', columns='DC_Xac_Nhan', aggfunc='sum', fill_value=0).reset_index()
        pivot_loi_gt['GT KHO RAU'] = pivot_loi_gt[dc_cols].sum(axis=1)
        pivot_loi_gt = pivot_loi_gt[[c for c in col_order_loi if c in pivot_loi_gt.columns]]
        pivot_loi_gt.rename(columns={'SL KHO RAU': 'GT KHO RAU'}, inplace=True) # Sửa lại tên cột vì dùng chung order list
        
        pivot_loi_gt['% Chưa xác nhận'] = pivot_loi_gt.apply(
            lambda r: f"{(r.get('Chưa xác nhận', 0) / r['GT KHO RAU'] * 100):.2f}%".replace('.', ',') if r.get('GT KHO RAU', 0) > 0 else "0,00%", axis=1
        )
        pivot_loi_gt['% Tiến độ phản hồi'] = pivot_loi_gt.apply(
            lambda r: f"{((r['GT KHO RAU'] - r.get('Chưa xác nhận', 0)) / r['GT KHO RAU'] * 100):.2f}%".replace('.', ',') if r.get('GT KHO RAU', 0) > 0 else "100,00%", axis=1
        )
        
        format_custom_table_with_total(pivot_loi_gt, 'Nhóm Lỗi & Chi tiết', f"Tien_Do_DC_Theo_Loi_GT_{tab_id}")

# ==========================================
# GIAO DIỆN CHIA TAB
# ==========================================
tab_main, tab_daily, tab_dc, tab_logic = st.tabs(["📊 Báo Cáo Tổng Quan", "📈 Báo Cáo Năng Suất Daily", "👨‍🔧 Tiến Độ DC Phản Hồi", "📑 Đặc tả Logic Đối soát"])

# ==========================================
# TRANG 1: BÁO CÁO TỔNG QUAN (CODE CŨ)
# ==========================================
with tab_main:
    month_filter_global = st.radio("🗓️ **CHỌN THÁNG BÁO CÁO:**", ["Tháng 4", "Tháng 5", "Tháng 6", "Tháng 7", "Tháng 8", "Tất cả các tháng"], index=4, horizontal=True)

    if month_filter_global == "Tháng 4":
        df_active = df_all[df_all['Ngày'].dt.month == 4].copy()
    elif month_filter_global == "Tháng 5":
        df_active = df_all[df_all['Ngày'].dt.month == 5].copy()
    elif month_filter_global == "Tháng 6":
        df_active = df_all[df_all['Ngày'].dt.month == 6].copy()
    elif month_filter_global == "Tháng 7":
        df_active = df_all[df_all['Ngày'].dt.month == 7].copy()
    elif month_filter_global == "Tháng 8":
        df_active = df_all[df_all['Ngày'].dt.month == 8].copy()
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

    # 1B. Theo ngày (Giá trị)
    pivot_ngay_val = df_active.groupby('Ngày_str')[['Tổng GT', 'Tổng ST', 'Tổng kho rau', 'Tổng hao hụt', 'Tổng chưa xác định']].sum().reset_index()
    pivot_ngay_val['Ngày_dt'] = pd.to_datetime(pivot_ngay_val['Ngày_str'], format='%d/%m/%Y', errors='coerce')
    pivot_ngay_val = pivot_ngay_val.sort_values(by='Ngày_dt').drop(columns=['Ngày_dt'])

    tong_row_ngay_val = pivot_ngay_val.sum(numeric_only=True).to_frame().T
    if not tong_row_ngay_val.empty: tong_row_ngay_val['Ngày_str'] = 'Tổng'

    pivot_ngay_val.rename(columns={
        'Tổng GT': 'Giá trị chênh lệch (VNĐ)',
        'Tổng ST': 'Giá trị đã tạo bs cho ST (VNĐ)',
        'Tổng kho rau': 'Giá trị đã xác nhận được trả kho rau (VNĐ)',
        'Tổng hao hụt': 'Giá trị hao hụt (VNĐ)',
        'Tổng chưa xác định': 'Giá trị chưa xác định (VNĐ)'
    }, inplace=True)

    if not tong_row_ngay_val.empty:
        tong_row_ngay_val.rename(columns={
            'Tổng GT': 'Giá trị chênh lệch (VNĐ)',
            'Tổng ST': 'Giá trị đã tạo bs cho ST (VNĐ)',
            'Tổng kho rau': 'Giá trị đã xác nhận được trả kho rau (VNĐ)',
            'Tổng hao hụt': 'Giá trị hao hụt (VNĐ)',
            'Tổng chưa xác định': 'Giá trị chưa xác định (VNĐ)'
        }, inplace=True)

    # 2. Theo CLV2
    pivot_clv2_sum = df_active.groupby('CLV2', dropna=False)[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch']].sum()
    pivot_clv2_count = df_active[df_active['Chênh lệch'].abs() > 0].groupby('CLV2', dropna=False).size().rename('Số lượng line')
    pivot_clv2 = pivot_clv2_sum.join(pivot_clv2_count).fillna(0).reset_index()
    pivot_clv2['Số lượng line'] = pivot_clv2['Số lượng line'].astype(int)
    pivot_clv2 = pivot_clv2[['CLV2', 'Số lượng line', 'Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch']]
    pivot_clv2 = pivot_clv2.sort_values(by='Chênh lệch', ascending=False) # Sắp xếp giảm dần vì số chênh lệch lớn nhất lên đầu
    tong_row_clv2 = pivot_clv2.sum(numeric_only=True).to_frame().T
    tong_row_clv2['CLV2'] = 'Tổng'

    # 3. Top 5 CLV4 (Chênh lệch lớn nhất - tính theo trị tuyệt đối)
    clv4_sum = df_active.groupby('CLV4', dropna=False)[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch']].sum().reset_index()
    clv4_sum['Abs_ChenhLech'] = clv4_sum['Chênh lệch'].abs()
    pivot_clv4 = clv4_sum.sort_values(by='Abs_ChenhLech', ascending=False).drop(columns=['Abs_ChenhLech']).head(5)

    # 4A. Bảng SỐ LƯỢNG Chi tiết Từng Ngày - Siêu Thị
    pivot_qty_sum = df_active.groupby(['Ngày_str', 'ID ST', 'Chi nhánh nhận'], dropna=False)[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Hao hụt', 'BS_ST', 'Kho_Rau', 'CXD']].sum()
    pivot_qty_count = df_active[df_active['Chênh lệch'].abs() > 0].groupby(['Ngày_str', 'ID ST', 'Chi nhánh nhận'], dropna=False).size().rename('SL line chênh lệch')
    pivot_qty_nhap0 = df_active[(df_active['Số lượng nhận'] == 0) & (df_active['Chênh lệch'].abs() > 0)].groupby(['Ngày_str', 'ID ST', 'Chi nhánh nhận'], dropna=False).size().rename('SL line nhập=0')

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
    pivot_val_sum = df_active.groupby(['Ngày_str', 'ID ST', 'Chi nhánh nhận'], dropna=False)[['Tổng GT', 'Tổng ST', 'Tổng kho rau', 'Tổng hao hụt', 'Tổng chưa xác định']].sum().reset_index()
    pivot_val_sum.rename(columns={'Tổng GT': 'Giá trị chênh lệch (VNĐ)'}, inplace=True)

    # Nút Tải lại dữ liệu
    if st.button('🔄 Cập nhật dữ liệu mới nhất'):
        st.cache_data.clear()
        st.rerun()

    # Hàm format màu đỏ cho số chênh lệch
    def color_red_for_chenhlech(val):
        color = 'red' if isinstance(val, (int, float)) and val > 0 else ''
        return f'color: {color}'

    # Hàm format số theo chuẩn Việt Nam (1.000.000,00)
    def format_vn(val):
        if pd.isna(val):
            return ""
        if isinstance(val, (int, float, np.integer, np.floating)):
            if val == int(val):
                return f"{int(val):,}".replace(',', '.')
            else:
                formatted = f"{val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                if formatted.endswith(',00'):
                    return formatted[:-3]
                return formatted
        return val

    def format_money(val):
        if val >= 1000000:
            return f"{val/1000000:.1f} triệu".replace('.', ',')
        elif val >= 1000:
            return f"{val/1000:.1f} ngàn".replace('.', ',')
        return format_vn(val)

    def format_custom_table_with_total(df, name_col, title_prefix):
        if df.empty: return
        
        tong_df = pd.DataFrame(index=[0])
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                tong_df[col] = df[col].sum()
            else:
                tong_df[col] = ''
                
        tuples = []
        for col in df.columns:
            val = tong_df.iloc[0][col]
            if val not in [None, 'Tổng', '', 0] and pd.notna(val):
                if pd.api.types.is_numeric_dtype(type(val)) or isinstance(val, (int, float)):
                    total_str = f"🟡 {format_vn(val)}"
                else:
                    total_str = f"🟡 {str(val)}"
            else:
                total_str = '⭐ TỔNG' if col == name_col else ''
                
            tuples.append((total_str, col))
            
        df_renamed = df.copy()
        df_renamed.columns = pd.MultiIndex.from_tuples(tuples)
        styler = df_renamed.style.format(format_vn).hide(axis="index")
        display_df_with_download(styler, f"Daily_{title_prefix}")


    def compute_daily_summary(df, date_str):
        """Calculate daily summary for given DataFrame and date string."""
        if df.empty:
            return None
        total_items = int(df['Chênh lệch'].sum())
        total_value = df['Tổng GT'].sum()
        
        df_kho_rau = pd.to_numeric(df['Kho_Rau'], errors='coerce').fillna(0)
        df_bs_st = pd.to_numeric(df['BS_ST'], errors='coerce').fillna(0)
        df_hao_hut = pd.to_numeric(df['Hao hụt'], errors='coerce').fillna(0)
        
        processed = int((df_kho_rau + df_bs_st + df_hao_hut).sum())
        returned = int(df_kho_rau.sum())
        created_bs = int(df_bs_st.sum())
        lost = int(df_hao_hut.sum())
        remaining = total_items - processed
        
        # Breakdown remaining
        df_cxd = pd.to_numeric(df['CXD'], errors='coerce').fillna(0)
        xuly_status = df['Xử lý'].astype(str).str.strip().str.lower()
        pending = int(np.where(xuly_status == 'hoàn thành', df_cxd, 0).sum())
        unprocessed = remaining - pending
        if unprocessed < 0: unprocessed = 0
        
        cat_summary = {}
        for cat in df['CLV2'].dropna().unique():
            df_cat = df[df['CLV2'] == cat]
            c_items = int(df_cat['Chênh lệch'].sum())
            c_val = df_cat['Tổng GT'].sum()
            
            c_kr = pd.to_numeric(df_cat['Kho_Rau'], errors='coerce').fillna(0)
            c_st = pd.to_numeric(df_cat['BS_ST'], errors='coerce').fillna(0)
            c_hh = pd.to_numeric(df_cat['Hao hụt'], errors='coerce').fillna(0)
            
            c_ret = int(c_kr.sum())
            c_bs = int(c_st.sum())
            c_lost = int(c_hh.sum())
            c_proc = c_ret + c_bs + c_lost
            c_rem = c_items - c_proc
            
            c_cxd = pd.to_numeric(df_cat['CXD'], errors='coerce').fillna(0)
            c_xuly = df_cat['Xử lý'].astype(str).str.strip().str.lower()
            c_pending = int(np.where(c_xuly == 'hoàn thành', c_cxd, 0).sum())
            c_unprocessed = c_rem - c_pending
            if c_unprocessed < 0: c_unprocessed = 0
            
            cause_ratio = c_ret / c_items if c_items > 0 else 0
            
            cat_summary[cat] = {
                "items": c_items,
                "value": c_val,
                "processed": c_proc,
                "return": c_ret,
                "bs": c_bs,
                "lost": c_lost,
                "remaining": c_rem,
                "pending": c_pending,
                "unprocessed": c_unprocessed,
                "cause_ratio": cause_ratio
            }
        return {
            "date": date_str,
            "total_items": total_items,
            "total_value": total_value,
            "processed": processed,
            "return": returned,
            "bs": created_bs,
            "lost": lost,
            "remaining": remaining,
            "pending": pending,
            "unprocessed": unprocessed,
            "cat_summary": cat_summary
        }
    # Thẻ thông tin (Metrics)
    st.write("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Tổng số lượng chuyển", format_vn(df_active['Số lượng chuyển'].sum()))
    with col2:
        st.metric("Tổng số lượng nhận", format_vn(df_active['Số lượng nhận'].sum()))
    with col3:
        st.metric("TỔNG CHÊNH LỆCH", format_vn(df_active['Chênh lệch'].sum()))

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
    pivot_ngay_val_renamed = create_multiindex_headers(pivot_ngay_val, tong_row_ngay_val)
    pivot_clv2_renamed = create_multiindex_headers(pivot_clv2, tong_row_clv2)

    # Layout cho các bảng
    st.write("---")
    st.subheader("📅 1. TỔNG HỢP THEO TỪNG NGÀY")
    st.write("### 📌 Đánh giá nhanh tình hình")
    if not pivot_ngay.empty:
        top_day = pivot_ngay.sort_values(by='Chênh lệch', ascending=False).iloc[0]
        st.info(f"🔹 **Ngày biến động nhất**: **{top_day['Ngày_str']}** ghi nhận mức chênh lệch cao nhất ({format_vn(top_day['Chênh lệch'])} item / {format_vn(top_day['Giá trị chênh lệch (VNĐ)'])} VNĐ).")

    tab_ngay_qty, tab_ngay_val = st.tabs(["📊 Số lượng (Từng Ngày)", "💰 Giá trị (Từng Ngày)"])

    with tab_ngay_qty:
        display_df_with_download(pivot_ngay_renamed.style.format(format_vn).map(color_red_for_chenhlech, subset=[c for c in pivot_ngay_renamed.columns if 'Chênh lệch' in c[1] and 'Giá trị' not in c[1] and 'SKU' not in c[1]]), "Tong_Hop_Theo_Ngay_So_Luong")

    with tab_ngay_val:
        display_df_with_download(pivot_ngay_val_renamed.style.format(format_vn), "Tong_Hop_Theo_Ngay_Gia_Tri")

    st.write("---")
    col4, col5 = st.columns(2)
    with col4:
        st.subheader("🔥 2. TOP 5 CATE CHÊNH LỆCH LỚN NHẤT")
        st.write("### 📌 Đánh giá nhanh tình hình")
        if not pivot_clv4.empty:
            top_clv4 = pivot_clv4.iloc[0]
            st.info(f"🔹 **Mã hàng (CLV4) cảnh báo đỏ**: **{top_clv4['CLV4']}** đang dẫn đầu với mức chênh lệch {format_vn(top_clv4['Chênh lệch'])}.")
        display_df_with_download(pivot_clv4.style.format(format_vn).map(color_red_for_chenhlech, subset=['Chênh lệch']), "Top_5_CLV4")
    with col5:
        st.subheader("📦 3. TỔNG HỢP THEO NGÀNH HÀNG (CLV2)")
        st.write("### 📌 Đánh giá nhanh tình hình")
        if not pivot_clv2.empty:
            top_clv2 = pivot_clv2.iloc[0]
            st.info(f"🔹 **Ngành hàng (CLV2) trọng điểm**: **{top_clv2['CLV2']}** chiếm số lượng chênh lệch cao nhất ({format_vn(top_clv2['Chênh lệch'])}).")
        display_df_with_download(pivot_clv2_renamed.style.format(format_vn).map(color_red_for_chenhlech, subset=[c for c in pivot_clv2_renamed.columns if 'Chênh lệch' in c[1] and 'SL' not in c[1]]), "Tong_Hop_CLV2")

    st.write("---")

    # Bộ lọc theo ngày dùng chung cho các bảng chi tiết
    sorted_dates = [d for d in pivot_ngay['Ngày_str'] if d != 'Tổng']
    dates = ["Tất cả các ngày"] + sorted_dates

    st.write("---")
    st.subheader("🛒 4. CHI TIẾT SỐ LƯỢNG & GIÁ TRỊ THEO NHÓM HÀNG (CLV4)")

    item_qty_sum = df_active.groupby(['Ngày_str', 'CLV4'], dropna=False)[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Hao hụt', 'BS_ST', 'Kho_Rau', 'CXD']].sum()
    item_qty_count = df_active[df_active['Chênh lệch'].abs() > 0].groupby(['Ngày_str', 'CLV4'], dropna=False).size().rename('SL ST chênh lệch')
    item_qty_nhap0 = df_active[(df_active['Số lượng nhận'] == 0) & (df_active['Chênh lệch'].abs() > 0)].groupby(['Ngày_str', 'CLV4'], dropna=False).size().rename('SL ST nhập=0')

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

    pivot_val_item = df_active.groupby(['Ngày_str', 'CLV4'], dropna=False)[['Tổng GT', 'Tổng ST', 'Tổng kho rau', 'Tổng hao hụt', 'Tổng chưa xác định']].sum().reset_index()
    pivot_val_item.rename(columns={'Tổng GT': 'Giá trị chênh lệch (VNĐ)', 'CLV4': 'Mã hàng (CLV4)'}, inplace=True)

    selected_date_item = st.selectbox("🔍 Lọc theo Ngày (Mã hàng):", dates)

    st.write("### 📌 Đánh giá nhanh tình hình")
    if not pivot_qty_item.empty and not pivot_val_item.empty:
        top_item_qty = pivot_qty_item.sort_values(by='Chênh lệch', ascending=False).iloc[0] if selected_date_item == "Tất cả các ngày" else pivot_qty_item[pivot_qty_item['Ngày_str'] == selected_date_item].sort_values(by='Chênh lệch', ascending=False).iloc[0] if not pivot_qty_item[pivot_qty_item['Ngày_str'] == selected_date_item].empty else None
        top_item_val = pivot_val_item.sort_values(by='Giá trị chênh lệch (VNĐ)', ascending=False).iloc[0] if selected_date_item == "Tất cả các ngày" else pivot_val_item[pivot_val_item['Ngày_str'] == selected_date_item].sort_values(by='Giá trị chênh lệch (VNĐ)', ascending=False).iloc[0] if not pivot_val_item[pivot_val_item['Ngày_str'] == selected_date_item].empty else None
        
        if top_item_qty is not None and top_item_val is not None:
            st.info(
                f"🔹 **Mã hàng chênh lệch số lượng lớn nhất**: **{top_item_qty['Mã hàng (CLV4)']}** (Chênh lệch {format_vn(top_item_qty['Chênh lệch'])} item).\n\n"
                f"🔹 **Mã hàng chênh lệch giá trị lớn nhất**: **{top_item_val['Mã hàng (CLV4)']}** (Giá trị chênh lệch {format_vn(top_item_val['Giá trị chênh lệch (VNĐ)'])} VNĐ)."
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

    sku_qty_sum = df_active.groupby(['Ngày_str', 'SKU_Full'], dropna=False)[['Số lượng chuyển', 'Số lượng nhận', 'Chênh lệch', 'Hao hụt', 'BS_ST', 'Kho_Rau', 'CXD']].sum()
    sku_qty_count = df_active[df_active['Chênh lệch'].abs() > 0].groupby(['Ngày_str', 'SKU_Full'], dropna=False).size().rename('SL ST chênh lệch')
    sku_qty_nhap0 = df_active[(df_active['Số lượng nhận'] == 0) & (df_active['Chênh lệch'].abs() > 0)].groupby(['Ngày_str', 'SKU_Full'], dropna=False).size().rename('SL ST nhập=0')

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

    pivot_val_sku = df_active.groupby(['Ngày_str', 'SKU_Full'], dropna=False)[['Tổng GT', 'Tổng ST', 'Tổng kho rau', 'Tổng hao hụt', 'Tổng chưa xác định']].sum().reset_index()
    pivot_val_sku.rename(columns={'Tổng GT': 'Giá trị chênh lệch (VNĐ)', 'SKU_Full': 'Mã hàng (SKU)'}, inplace=True)

    selected_date_sku = st.selectbox("🔍 Lọc theo Ngày (SKU):", dates)

    st.write("### 📌 Đánh giá nhanh tình hình")
    if not pivot_qty_sku.empty and not pivot_val_sku.empty:
        top_sku_qty = pivot_qty_sku.sort_values(by='Chênh lệch', ascending=False).iloc[0] if selected_date_sku == "Tất cả các ngày" else pivot_qty_sku[pivot_qty_sku['Ngày_str'] == selected_date_sku].sort_values(by='Chênh lệch', ascending=False).iloc[0] if not pivot_qty_sku[pivot_qty_sku['Ngày_str'] == selected_date_sku].empty else None
        top_sku_val = pivot_val_sku.sort_values(by='Giá trị chênh lệch (VNĐ)', ascending=False).iloc[0] if selected_date_sku == "Tất cả các ngày" else pivot_val_sku[pivot_val_sku['Ngày_str'] == selected_date_sku].sort_values(by='Giá trị chênh lệch (VNĐ)', ascending=False).iloc[0] if not pivot_val_sku[pivot_val_sku['Ngày_str'] == selected_date_sku].empty else None
        
        if top_sku_qty is not None and top_sku_val is not None:
            st.info(
                f"🔹 **Mã hàng chênh lệch số lượng lớn nhất**: **{top_sku_qty['Mã hàng (SKU)']}** (Chênh lệch {format_vn(top_sku_qty['Chênh lệch'])} item).\n\n"
                f"🔹 **Mã hàng chênh lệch giá trị lớn nhất**: **{top_sku_val['Mã hàng (SKU)']}** (Giá trị chênh lệch {format_vn(top_sku_val['Giá trị chênh lệch (VNĐ)'])} VNĐ)."
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

    tab5, tab6, tab7 = st.tabs(["📊 Chi Tiết SỐ LƯỢNG (SKU)", "💰 Chi Tiết GIÁ TRỊ (SKU)", "📝 Nhận xét"])

    with tab5:
        display_df_with_download(filtered_qty_sku_renamed.style.format(format_vn).map(color_red_for_chenhlech, subset=[c for c in filtered_qty_sku_renamed.columns if 'Chênh lệch' in c[1] or 'Tỷ lệ (%)' in c[1]]), "Chi_Tiet_SL_SKU", height=600)
        
    with tab6:
        display_df_with_download(filtered_val_sku_renamed.style.format(format_vn), "Chi_Tiet_GT_SKU", height=600)

    st.write("---")
    st.subheader("🏬 6. CHI TIẾT SỐ LƯỢNG & GIÁ TRỊ THEO SIÊU THỊ")

    selected_date = st.selectbox("🔍 Lọc theo Ngày:", dates)
    # Compute daily summary for selected date
    df_today = df_active if selected_date == "Tất cả các ngày" else df_active[df_active['Ngày_str'] == selected_date]
    summary_today = compute_daily_summary(df_today, selected_date)
    st.write("### 📌 Đánh giá nhanh tình hình")
    if not pivot_qty.empty and not pivot_val_sum.empty:
        top_st_qty = pivot_qty.sort_values(by='Chênh lệch', ascending=False).iloc[0] if selected_date == "Tất cả các ngày" else pivot_qty[pivot_qty['Ngày_str'] == selected_date].sort_values(by='Chênh lệch', ascending=False).iloc[0] if not pivot_qty[pivot_qty['Ngày_str'] == selected_date].empty else None
        top_st_val = pivot_val_sum.sort_values(by='Giá trị chênh lệch (VNĐ)', ascending=False).iloc[0] if selected_date == "Tất cả các ngày" else pivot_val_sum[pivot_val_sum['Ngày_str'] == selected_date].sort_values(by='Giá trị chênh lệch (VNĐ)', ascending=False).iloc[0] if not pivot_val_sum[pivot_val_sum['Ngày_str'] == selected_date].empty else None
        
        if top_st_qty is not None and top_st_val is not None:
            st.info(
                f"🔹 **ST chênh lệch số lượng lớn nhất**: **{top_st_qty['Chi nhánh nhận']}** (Chênh lệch {format_vn(top_st_qty['Chênh lệch'])} item).\n\n"
                f"🔹 **ST chênh lệch giá trị lớn nhất**: **{top_st_val['Chi nhánh nhận']}** (Giá trị chênh lệch {format_vn(top_st_val['Giá trị chênh lệch (VNĐ)'])} VNĐ)."
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
        start_date = pd.to_datetime('2026-04-01')
        end_date = pd.to_datetime('2026-04-30')
    elif week_filter == "Nguyên Tháng 5":
        start_date = pd.to_datetime('2026-05-01')
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
            
        t1_loi = df_loi.groupby(['ID ST', 'Chi nhánh nhận', 'GSM phụ trách', 'RSM phụ trách'], dropna=False).agg(
            So_ngay_tao_bo_sung=('Ngày', 'nunique'),
            Tong_SL_da_tao=('Qty_O', 'sum'),
            Tong_gia_tri=('Tổng ST', 'sum')
        ).reset_index()
        t1_loi.columns = ['ID ST', 'Name Mart', 'GSM phụ trách', 'RSM phụ trách', 'Số ngày tạo bổ sung', 'Tổng SL đã tạo', 'Tổng giá trị']
        
        t2_loi = df_loi.groupby('RSM phụ trách', dropna=False).agg(
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
        
        t3_loi = df_loi.groupby('GSM phụ trách', dropna=False).agg(
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
                f"🔹 **Tổng quan toàn hệ thống**: Trong kỳ báo cáo, ghi nhận **{total_st} siêu thị** phát sinh chênh lệch giao nhận với tổng giá trị là **{format_vn(total_val)} VNĐ**.\n\n"
                f"🔹 **Cảnh báo tần suất Siêu thị**: **{top_freq_st['Name Mart']}** là điểm bán có tần suất sai lệch cao nhất, phát sinh nghiệp vụ tạo phiếu bổ sung trong **{top_freq_st['Số ngày tạo bổ sung']:.0f} ngày** (Khu vực GSM {top_freq_st['GSM phụ trách']}).\n\n"
                f"🔹 **Giám sát trọng điểm (Cấp RSM)**: Vùng quản lý của RSM **{top_rsm['RSM phụ trách']}** đang ghi nhận tổng giá trị chênh lệch lớn nhất toàn chuỗi ({format_vn(top_rsm['Giá trị tạo bổ sung'])} VNĐ, phân bổ trên {top_rsm['SL ST phát sinh']} siêu thị).\n\n"
                f"🔹 **Giám sát trọng điểm (Cấp GSM)**: Khu vực của GSM **{top_gsm['GSM phụ trách']}** có giá trị phát sinh chênh lệch cao nhất ({format_vn(top_gsm['Giá trị tạo bổ sung'])} VNĐ)."
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
                    f"🔹 **Đỉnh điểm chênh lệch (Cảnh báo Tuần)**: **{max_week}** đang là tuần ghi nhận thiệt hại chênh lệch lớn nhất toàn hệ thống với tổng giá trị lên đến **{format_vn(max_week_val)} VNĐ**."
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

# ==========================================
# TRANG 2: BÁO CÁO DAILY MỚI
# ==========================================
with tab_daily:
    st.header("Báo Cáo Năng Suất Chi Tiết Mỗi Ngày")
    
    st.subheader("🥦 Đối Soát Chéo Dư - Thiếu Kho Rau")
    st.markdown("Hệ thống tự động kết nối StarRocks qua VPN để đối soát chéo lượng hàng thừa/thiếu hàng ngày.")
    
    import datetime
    # Date selection
    selected_date = st.date_input("Chọn ngày đối soát (Daily):", datetime.date(2026, 7, 22), key="veg_date_picker")
    date_str = selected_date.strftime('%Y-%m-%d')
    
    if True: # Tự động chạy khi thay đổi ngày
        with st.spinner("Đang tải dữ liệu và tính toán đối soát chéo..."):
            try:
                # 1. Fetch branch mapping
                sql_branches = """
                SELECT branch_id, branch_code, branch_name
                FROM __cdc_kfm_kf_inventories_kf_inventory_transaction_stockcard
                WHERE branch_name IS NOT NULL AND branch_name != ''
                GROUP BY branch_id, branch_code, branch_name
                """
                df_branches = fetch_data_to_df(sql_branches)
                id_to_name = dict(zip(df_branches['branch_id'], df_branches['branch_name']))
                
                # 2. Fetch shortages (KHO RAU CỦ)
                sql_mf01 = f"""
                SELECT 
                    i.to_branch_id,
                    i.code as `Mã chuyển hàng`,
                    IFNULL(NULLIF(tl.from_container_code, ''), i.double_check_code) as `Mã thùng`,
                    l.barcode as `Mã hàng`,
                    l.name as `Tên hàng`,
                    l.unit__name as `ĐVT`,
                    CAST(IFNULL(l.transfer_quantity, 0) AS DOUBLE) as `Số lượng chuyển`,
                    CAST(IFNULL(l.store_quantity, 0) AS DOUBLE) as `Số lượng nhận`
                FROM __cdc_kfm_kf_inventories_kf_transfer_items i
                INNER JOIN __cdc_kfm_ec9d24ab_33bc7bbc_L3___line_items l ON i._id = l._root_id
                LEFT JOIN (
                    SELECT 
                        transfer_code,
                        barcode,
                        group_concat(distinct from_container_code) as from_container_code
                    FROM (
                        SELECT 
                            t.from_pt_code as transfer_code,
                            tl.barcode,
                            tl.from_container_code
                        FROM __cdc_kfm_kf_transfer_tickets_kf_transfer_tickets t
                        INNER JOIN __cdc_kfm_kf_transfer_tickets_kf_transfer_ticket_lines tl ON tl.transfer_ticket_id = t._id
                        WHERE t.from_pt_code IS NOT NULL AND t.from_pt_code != ''
                          AND tl.from_container_code IS NOT NULL AND tl.from_container_code != ''
                        UNION DISTINCT
                        SELECT 
                            t.handled_pt_code as transfer_code,
                            tl.barcode,
                            tl.from_container_code
                        FROM __cdc_kfm_kf_transfer_tickets_kf_transfer_tickets t
                        INNER JOIN __cdc_kfm_kf_transfer_tickets_kf_transfer_ticket_lines tl ON tl.transfer_ticket_id = t._id
                        WHERE t.handled_pt_code IS NOT NULL AND t.handled_pt_code != ''
                          AND tl.from_container_code IS NOT NULL AND tl.from_container_code != ''
                    ) u
                    GROUP BY transfer_code, barcode
                ) tl ON tl.transfer_code = i.code AND tl.barcode = l.barcode
                WHERE i.from_branch_id = '5fdc170ebd89c10006f15b7c' -- KHO RAU CỦ
                  AND DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) = '{date_str}'
                  AND i.status = 5
                  AND (l.barcode NOT LIKE 'CC%' OR l.barcode IS NULL)
                """
                df_mf01 = fetch_data_to_df(sql_mf01)
                
                if df_mf01.empty:
                    st.warning(f"Không tìm thấy dữ liệu đi chuyển nào từ KHO RAU CỦ ngày {selected_date.strftime('%d/%m/%Y')}.")
                    df_exact = pd.DataFrame()
                    df_partial = pd.DataFrame()
                    df_cross = pd.DataFrame()
                    df_total_gte = pd.DataFrame()
                    df_only_diff = pd.DataFrame()
                    df_only_du = pd.DataFrame()
                else:
                    df_mf01['Chi nhánh nhận'] = df_mf01['to_branch_id'].map(id_to_name)
                    df_mf01 = df_mf01[df_mf01['Chi nhánh nhận'].astype(str).str.startswith('KFM_')].copy()
                    
                    df_mf01['Chênh lệch'] = df_mf01['Số lượng chuyển'] - df_mf01['Số lượng nhận']
                    df_shortage = df_mf01[df_mf01['Chênh lệch'].round(5) > 0.0].copy()
                    
                    # 3. Fetch surpluses (KHO RAU CỦ XỬ LÝ CHÊNH LỆCH CHUYỂN HÀNG)
                    sql_mf02 = f"""
                    SELECT 
                        i.to_branch_id,
                        i.code as `Mã chuyển hàng`,
                        IFNULL(NULLIF(tl.from_container_code, ''), i.double_check_code) as `Mã thùng`,
                        i.note as `Ghi chú chuyển (phiếu)`,
                        l.barcode as `Mã hàng`,
                        l.name as `Tên hàng`,
                        l.unit__name as `ĐVT`,
                        i.created_by as `Người tạo`,
                        CAST(IFNULL(l.store_quantity, 0) AS DOUBLE) as `SL_du`
                    FROM __cdc_kfm_kf_inventories_kf_transfer_items i
                    INNER JOIN __cdc_kfm_ec9d24ab_33bc7bbc_L3___line_items l ON i._id = l._root_id
                    LEFT JOIN (
                        SELECT 
                            transfer_code,
                            barcode,
                            group_concat(distinct from_container_code) as from_container_code
                        FROM (
                            SELECT 
                                t.from_pt_code as transfer_code,
                                tl.barcode,
                                tl.from_container_code
                            FROM __cdc_kfm_kf_transfer_tickets_kf_transfer_tickets t
                            INNER JOIN __cdc_kfm_kf_transfer_tickets_kf_transfer_ticket_lines tl ON tl.transfer_ticket_id = t._id
                            WHERE t.from_pt_code IS NOT NULL AND t.from_pt_code != ''
                              AND tl.from_container_code IS NOT NULL AND tl.from_container_code != ''
                            UNION DISTINCT
                            SELECT 
                                t.handled_pt_code as transfer_code,
                                tl.barcode,
                                tl.from_container_code
                            FROM __cdc_kfm_kf_transfer_tickets_kf_transfer_tickets t
                            INNER JOIN __cdc_kfm_kf_transfer_tickets_kf_transfer_ticket_lines tl ON tl.transfer_ticket_id = t._id
                            WHERE t.handled_pt_code IS NOT NULL AND t.handled_pt_code != ''
                              AND tl.from_container_code IS NOT NULL AND tl.from_container_code != ''
                        ) u
                        GROUP BY transfer_code, barcode
                    ) tl ON tl.transfer_code = i.code AND tl.barcode = l.barcode
                    WHERE i.from_branch_id = '6a34ed8d6607ba000703e235' -- KHO RAU CỦ XỬ LÝ CHÊNH LỆCH CHUYỂN HÀNG
                      AND DATE(DATE_ADD(i.transfer_date, INTERVAL 7 HOUR)) = '{date_str}'
                      AND i.status = 5
                      AND (l.barcode NOT LIKE 'CC%' OR l.barcode IS NULL)
                    """
                    df_mf02 = fetch_data_to_df(sql_mf02)
                    df_mf02['Chi nhánh nhận'] = df_mf02['to_branch_id'].map(id_to_name)
                    df_mf02 = df_mf02[df_mf02['Chi nhánh nhận'].astype(str).str.startswith('KFM_')].copy()
                    
                    # Creator filter logic
                    df_mf02['Người tạo'] = df_mf02['Người tạo'].apply(lambda x: 'User Hệ Thống' if str(x).strip() == '5f1152906c86b40006155d97' else 'User Khác')
                    
                    def keep_row(row):
                        creator = row['Người tạo']
                        if creator == 'User Hệ Thống':
                            return True
                        note = str(row.get('Ghi chú chuyển (phiếu)', '')).strip()
                        if not note:
                            return True
                        import re
                        matches = re.findall(r'\b(\d{1,2})[/\-.](\d{1,2})\b', note)
                        try:
                            t_year, t_month, t_day = map(int, date_str.split('-'))
                        except:
                            return True
                        for a_str, b_str in matches:
                            a, b = int(a_str), int(b_str)
                            if b == t_month and a != t_day and 1 <= a <= 31:
                                return False
                            if a == t_month and b != t_day and 1 <= b <= 31:
                                return False
                        return True
                        
                    if not df_mf02.empty:
                        df_mf02 = df_mf02[df_mf02.apply(keep_row, axis=1)].copy()
                        df_surplus = df_mf02[df_mf02['SL_du'].round(5) > 0.0].copy()
                    else:
                        df_surplus = pd.DataFrame()
                        
                    # 4. Clean surplus crate code
                    def extract_surplus_crate(row):
                        val = row.get('Ghi chú chuyển (phiếu)', None)
                        if pd.isna(val) or not val:
                            return str(row['Mã thùng']).strip()
                        val_str = str(val).strip()
                        prefixes = ["Các mã bổ sung của thùng", "Các mã bổ sung của phiếu"]
                        for prefix in prefixes:
                            if val_str.startswith(prefix):
                                return val_str[len(prefix):].strip()
                        return str(row['Mã thùng']).strip()
                        
                    if not df_surplus.empty:
                        df_surplus['Mã thùng'] = df_surplus.apply(extract_surplus_crate, axis=1)
                    else:
                        df_surplus = pd.DataFrame(columns=['Chi nhánh nhận', 'Mã chuyển hàng', 'Mã thùng', 'Ghi chú chuyển (phiếu)', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Người tạo', 'SL_du'])

                    # 5. Load layout
                    store_to_pos = {}
                    file_layout = r"d:\Doi_Soat_Kho_Rau\Layout Rau.xlsx"
                    try:
                        layout_df = pd.read_excel(file_layout, header=None)
                        layout_df.columns = ['Vị trí', 'Mã viết tắt', 'Siêu thị']
                        layout_df['Siêu thị'] = layout_df['Siêu thị'].astype(str).str.strip().str.upper()
                        for _, row in layout_df.iterrows():
                            store_to_pos[row['Siêu thị']] = int(row['Vị trí'])
                    except Exception as e_layout:
                        st.error(f"Lỗi khi đọc file layout rau: {e_layout}")

                    # Clean barcodes and exclude 'CC' prefixes
                    df_shortage['Mã hàng'] = df_shortage['Mã hàng'].astype(str).str.strip()
                    df_surplus['Mã hàng'] = df_surplus['Mã hàng'].astype(str).str.strip()
                    df_shortage = df_shortage[~df_shortage['Mã hàng'].str.upper().str.startswith('CC')].copy()
                    df_surplus = df_surplus[~df_surplus['Mã hàng'].str.upper().str.startswith('CC')].copy()

                    # 6. Group shortage & surplus
                    diff_grouped = df_shortage.groupby(['Chi nhánh nhận', 'Mã hàng']).agg({
                        'Tên hàng': lambda x: next((v for v in x if v and str(v).strip()), ''),
                        'Chênh lệch': 'sum',
                        'ĐVT': 'first',
                        'Mã thùng': lambda x: ', '.join(x.dropna().unique().astype(str))
                    }).reset_index()
                    diff_grouped.rename(columns={'Mã thùng': 'Mã thùng thiếu'}, inplace=True)
                    
                    if not df_surplus.empty:
                        du_grouped = df_surplus.groupby(['Chi nhánh nhận', 'Mã hàng']).agg({
                            'Tên hàng': lambda x: next((v for v in x if v and str(v).strip()), ''),
                            'SL_du': 'sum',
                            'ĐVT': 'first',
                            'Mã thùng': lambda x: ', '.join(x.dropna().unique().astype(str)),
                            'Mã chuyển hàng': lambda x: ', '.join(x.dropna().unique().astype(str))
                        }).reset_index()
                        du_grouped.rename(columns={'Mã thùng': 'Mã thùng thừa', 'Mã chuyển hàng': 'Mã chuyển hàng thừa'}, inplace=True)
                    else:
                        du_grouped = pd.DataFrame(columns=['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'SL_du', 'ĐVT', 'Mã thùng thừa', 'Mã chuyển hàng thừa'])

                    # Merge for internal matching
                    merged_internal = pd.merge(diff_grouped, du_grouped, on=['Chi nhánh nhận', 'Mã hàng'], how='outer')
                    merged_internal['Tên hàng'] = merged_internal['Tên hàng_x'].fillna(merged_internal['Tên hàng_y']).fillna('')
                    merged_internal['Chênh lệch'] = merged_internal['Chênh lệch'].fillna(0.0)
                    merged_internal['SL_du'] = merged_internal['SL_du'].fillna(0.0)
                    merged_internal['ĐVT'] = merged_internal['ĐVT_x'].fillna(merged_internal['ĐVT_y']).fillna('kg')
                    merged_internal['Matched_Internal'] = merged_internal[['Chênh lệch', 'SL_du']].min(axis=1)
                    merged_internal['Lệch_tuyệt_đối'] = (merged_internal['Chênh lệch'] - merged_internal['SL_du']).abs()

                    # Step 1: Khớp nội bộ 100%
                    df_exact = merged_internal[(merged_internal['Chênh lệch'] > 0) & (merged_internal['SL_du'] > 0) & (merged_internal['Lệch_tuyệt_đối'] <= 0.01)].copy()
                    df_exact['Lỗi'] = 'DC thao tác sai'
                    df_exact = df_exact[['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Mã thùng thừa', 'Mã chuyển hàng thừa', 'Chênh lệch', 'SL_du', 'Lỗi']]
                    df_exact.columns = ['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Mã thùng thừa', 'Mã chuyển hàng thừa', 'SL Thiếu (Chênh lệch)', 'SL Thừa (Nhận dư)', 'Lỗi']

                    # Step 2: Khớp nội bộ một phần
                    df_partial = merged_internal[(merged_internal['Chênh lệch'] > 0) & (merged_internal['SL_du'] > 0) & (merged_internal['Lệch_tuyệt_đối'] > 0.01)].copy()
                    df_partial['Diff'] = df_partial['Chênh lệch'] - df_partial['SL_du']
                    df_partial['Lỗi'] = 'DC thao tác sai'
                    df_partial = df_partial[['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Mã thùng thừa', 'Mã chuyển hàng thừa', 'Chênh lệch', 'SL_du', 'Diff', 'Lỗi']]
                    df_partial.columns = ['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Mã thùng thừa', 'Mã chuyển hàng thừa', 'SL Thiếu (Chênh lệch)', 'SL Thừa (Nhận dư)', 'Chênh lệch thừa - thiếu', 'Lỗi']

                    # Remainder calculation
                    merged_internal['Remaining_Shortage'] = merged_internal['Chênh lệch'] - merged_internal['Matched_Internal']
                    merged_internal['Remaining_Surplus'] = merged_internal['SL_du'] - merged_internal['Matched_Internal']
                    
                    rem_shortages = merged_internal[merged_internal['Remaining_Shortage'] > 0.01].copy()
                    rem_surpluses = merged_internal[merged_internal['Remaining_Surplus'] > 0.01].copy()

                    # Step 3: Khớp chéo liên siêu thị
                    cross_matches = []
                    skus_shortage = rem_shortages['Mã hàng'].unique()
                    skus_surplus = rem_surpluses['Mã hàng'].unique()
                    common_skus = set(skus_shortage).intersection(skus_surplus)
                    
                    matched_sho_keys = set()
                    matched_sur_keys = set()
                    
                    for sku in common_skus:
                        sku_shortages = rem_shortages[rem_shortages['Mã hàng'] == sku].copy()
                        sku_surpluses = rem_surpluses[rem_surpluses['Mã hàng'] == sku].copy()
                        
                        for idx_sur, row_sur in sku_surpluses.iterrows():
                            sur_qty = row_sur['Remaining_Surplus']
                            sur_store = row_sur['Chi nhánh nhận']
                            sur_crate = row_sur['Mã thùng thừa']
                            sur_transfer = row_sur['Mã chuyển hàng thừa']
                            sku_name = row_sur['Tên hàng']
                            dvt = row_sur['ĐVT']
                            pos_sur = store_to_pos.get(str(sur_store).upper().strip(), None)
                            
                            matching_shortages = []
                            for idx_sho, row_sho in sku_shortages.iterrows():
                                sho_qty = row_sho['Remaining_Shortage']
                                if abs(sur_qty - sho_qty) <= 0.01:
                                    matching_shortages.append(row_sho)
                            
                            if len(matching_shortages) > 0:
                                best_match = None
                                best_dist = 9999
                                for sho_row in matching_shortages:
                                    sho_store = sho_row['Chi nhánh nhận']
                                    pos_sho = store_to_pos.get(str(sho_store).upper().strip(), None)
                                    if pos_sur is not None and pos_sho is not None:
                                        dist = abs(pos_sur - pos_sho)
                                        if dist < best_dist:
                                            best_dist = dist
                                            best_match = sho_row
                                    else:
                                        if best_match is None:
                                            best_match = sho_row
                                
                                if best_match is not None:
                                    sho_store = best_match['Chi nhánh nhận']
                                    sho_qty = best_match['Remaining_Shortage']
                                    sho_crate = best_match['Mã thùng thiếu']
                                    pos_sho = store_to_pos.get(str(sho_store).upper().strip(), None)
                                    
                                    prob = "Rất cao (Vị trí kề nhau)" if best_dist <= 5 else ("Trung bình (Cùng khu)" if best_dist <= 15 else "Thấp (Trùng hợp số lượng)")
                                    cross_matches.append({
                                        'Mã hàng': sku, 'Tên hàng': sku_name, 'ĐVT': dvt, 'ST Nhận Dư (Thừa)': sur_store,
                                        'Vị trí Dư': pos_sur if pos_sur is not None else '-', 'Mã Thùng Thừa': sur_crate,
                                        'Mã Chuyển Hàng Thừa': sur_transfer, 'SL Thừa (kg)': sur_qty,
                                        'ST Nhận Thiếu (Thiếu)': sho_store, 'Vị trí Thiếu': pos_sho if pos_sho is not None else '-',
                                        'Mã Thùng Thiếu': sho_crate, 'SL Thiếu (kg)': sho_qty,
                                        'Độ lệch vị trí (Layout)': best_dist if best_dist != 9999 else '-',
                                        'Khả năng nhầm': prob, 'Lỗi': 'DC giao nhầm CH'
                                    })
                                    matched_sur_keys.add((sur_store, sku))
                                    matched_sho_keys.add((sho_store, sku))
                                    
                    df_cross = pd.DataFrame(cross_matches) if len(cross_matches) > 0 else pd.DataFrame(columns=[
                        'Mã hàng', 'Tên hàng', 'ĐVT', 'ST Nhận Dư (Thừa)', 'Vị trí Dư', 'Mã Thùng Thừa', 
                        'Mã Chuyển Hàng Thừa', 'SL Thừa (kg)', 'ST Nhận Thiếu (Thiếu)', 'Vị trí Thiếu', 
                        'Mã Thùng Thiếu', 'SL Thiếu (kg)', 'Độ lệch vị trí (Layout)', 'Khả năng nhầm', 'Lỗi'
                    ])
                    
                    # Exclude matched from remainder
                    for index, row in rem_shortages.iterrows():
                        if (row['Chi nhánh nhận'], row['Mã hàng']) in matched_sho_keys:
                            rem_shortages.at[index, 'Remaining_Shortage'] = 0.0
                    for index, row in rem_surpluses.iterrows():
                        if (row['Chi nhánh nhận'], row['Mã hàng']) in matched_sur_keys:
                            rem_surpluses.at[index, 'Remaining_Surplus'] = 0.0
                            
                    rem_shortages = rem_shortages[rem_shortages['Remaining_Shortage'] > 0.01].copy()
                    rem_surpluses = rem_surpluses[rem_surpluses['Remaining_Surplus'] > 0.01].copy()

                    # Step 4: Tổng Dư >= Tổng Thiếu
                    if not rem_shortages.empty or not rem_surpluses.empty:
                        sku_shortage_totals = rem_shortages.groupby(['Mã hàng', 'Tên hàng'])['Remaining_Shortage'].sum().reset_index() if not rem_shortages.empty else pd.DataFrame(columns=['Mã hàng', 'Tên hàng', 'Remaining_Shortage'])
                        sku_surplus_totals = rem_surpluses.groupby(['Mã hàng', 'Tên hàng'])['Remaining_Surplus'].sum().reset_index() if not rem_surpluses.empty else pd.DataFrame(columns=['Mã hàng', 'Tên hàng', 'Remaining_Surplus'])
                        sku_totals = pd.merge(sku_surplus_totals, sku_shortage_totals, on=['Mã hàng', 'Tên hàng'], how='outer')
                        sku_totals['Remaining_Surplus'] = sku_totals['Remaining_Surplus'].fillna(0.0)
                        sku_totals['Remaining_Shortage'] = sku_totals['Remaining_Shortage'].fillna(0.0)
                        sku_totals['Diff'] = sku_totals['Remaining_Surplus'] - sku_totals['Remaining_Shortage']
                        
                        df_total_gte = sku_totals[(sku_totals['Remaining_Surplus'] >= sku_totals['Remaining_Shortage']) & (sku_totals['Remaining_Surplus'] > 0)].copy()
                        
                        sur_details, sho_details = [], []
                        for idx, row in df_total_gte.iterrows():
                            sku = row['Mã hàng']
                            sku_sur = rem_surpluses[rem_surpluses['Mã hàng'] == sku]
                            sur_details.append(" | ".join([f"{r['Chi nhánh nhận']} (Vị trí: {store_to_pos.get(str(r['Chi nhánh nhận']).upper().strip(), '-')}) ({r['Remaining_Surplus']:.3f} kg)" for _, r in sku_sur.iterrows()]))
                            sku_sho = rem_shortages[rem_shortages['Mã hàng'] == sku]
                            sho_details.append(" | ".join([f"{r['Chi nhánh nhận']} (Vị trí: {store_to_pos.get(str(r['Chi nhánh nhận']).upper().strip(), '-')}) ({r['Remaining_Shortage']:.3f} kg)" for _, r in sku_sho.iterrows()]) if len(sku_sho) > 0 else "Không có")
                        
                        if not df_total_gte.empty:
                            df_total_gte['Chi tiết ST nhận Dư'] = sur_details
                            df_total_gte['Chi tiết ST nhận Thiếu'] = sho_details
                            df_total_gte = df_total_gte[['Mã hàng', 'Tên hàng', 'Remaining_Surplus', 'Chi tiết ST nhận Dư', 'Remaining_Shortage', 'Chi tiết ST nhận Thiếu', 'Diff']]
                            df_total_gte.columns = ['Mã hàng', 'Tên hàng', 'Tổng Dư Hệ Thống (kg)', 'Chi tiết ST nhận Dư', 'Tổng THIẾU Hệ Thống (kg)', 'Chi tiết ST nhận Thiếu', 'Lượng Thừa Ròng (kg)']
                        else:
                            df_total_gte = pd.DataFrame(columns=['Mã hàng', 'Tên hàng', 'Tổng Dư Hệ Thống (kg)', 'Chi tiết ST nhận Dư', 'Tổng THIẾU Hệ Thống (kg)', 'Chi tiết ST nhận Thiếu', 'Lượng Thừa Ròng (kg)'])
                    else:
                        df_total_gte = pd.DataFrame(columns=['Mã hàng', 'Tên hàng', 'Tổng Dư Hệ Thống (kg)', 'Chi tiết ST nhận Dư', 'Tổng THIẾU Hệ Thống (kg)', 'Chi tiết ST nhận Thiếu', 'Lượng Thừa Ròng (kg)'])

                    # Step 5: Chỉ có thiếu ròng
                    if not rem_shortages.empty:
                        df_only_diff = rem_shortages[['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'Remaining_Shortage']].copy()
                        df_only_diff.columns = ['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'SL Thiếu (kg)']
                    else:
                        df_only_diff = pd.DataFrame(columns=['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thiếu', 'SL Thiếu (kg)'])
                    
                    # Step 6: Chỉ có thừa ròng
                    if not rem_surpluses.empty:
                        df_only_du = rem_surpluses[['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thừa', 'Mã chuyển hàng thừa', 'Remaining_Surplus']].copy()
                        df_only_du.columns = ['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thừa', 'Mã chuyển hàng thừa', 'SL Thừa (kg)']
                    else:
                        df_only_du = pd.DataFrame(columns=['Chi nhánh nhận', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Mã thùng thừa', 'Mã chuyển hàng thừa', 'SL Thừa (kg)'])

                    # Display KPIs
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.markdown(f"""
                            <div class="metric-card" style="border-left-color: #ff4b4b; background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px;">
                                <div style="font-size: 12px; color: #a3a8b4;">KHỚP NỘI BỘ 100%</div>
                                <div style="font-size: 22px; font-weight: bold; color: #ff4b4b;">{len(df_exact)} dòng</div>
                            </div>
                        """, unsafe_allow_html=True)
                    with c2:
                        st.markdown(f"""
                            <div class="metric-card" style="border-left-color: #ffaa00; background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px;">
                                <div style="font-size: 12px; color: #a3a8b4;">KHỚP NỘI BỘ MỘT PHẦN</div>
                                <div style="font-size: 22px; font-weight: bold; color: #ffaa00;">{len(df_partial)} dòng</div>
                            </div>
                        """, unsafe_allow_html=True)
                    with c3:
                        st.markdown(f"""
                            <div class="metric-card" style="border-left-color: #00c0f2; background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px;">
                                <div style="font-size: 12px; color: #a3a8b4;">KHỚP CHÉO LIÊN ST 1-1</div>
                                <div style="font-size: 22px; font-weight: bold; color: #00c0f2;">{len(df_cross)} dòng</div>
                            </div>
                        """, unsafe_allow_html=True)
                    with c4:
                        st.markdown(f"""
                            <div class="metric-card" style="border-left-color: #2ebd59; background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px;">
                                <div style="font-size: 12px; color: #a3a8b4;">THIẾU RÒNG / THỪA RÒNG</div>
                                <div style="font-size: 22px; font-weight: bold; color: #2ebd59;">{len(df_only_diff)} / {len(df_only_du)} dòng</div>
                            </div>
                        """, unsafe_allow_html=True)

                    st.write("---")
                    # Export Excel to Memory for Download Button
                    output_excel = io.BytesIO()
                    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
                        df_exact.to_excel(writer, sheet_name='1. Khớp nội bộ 100%', index=False)
                        df_partial.to_excel(writer, sheet_name='2. Khớp nội bộ một phần', index=False)
                        df_cross.to_excel(writer, sheet_name='3. Khớp chéo liên ST 1-1', index=False)
                        df_total_gte.to_excel(writer, sheet_name='4. Tổng Dư >= Tổng Thiếu', index=False)
                        df_only_diff.to_excel(writer, sheet_name='5. Chỉ ghi nhận Thiếu ròng', index=False)
                        df_only_du.to_excel(writer, sheet_name='6. Chỉ ghi nhận Thừa ròng', index=False)
                    
                    st.download_button(
                        label="📥 Tải Xuống Báo Cáo Đối Soát Chéo Excel",
                        data=output_excel.getvalue(),
                        file_name=f"Doi_Soat_Cheo_Rau_{date_str}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                    # Tab presentation
                    sub_tab1, sub_tab2, sub_tab3, sub_tab4, sub_tab5, sub_tab6 = st.tabs([
                        "1. Khớp nội bộ 100%", 
                        "2. Khớp nội bộ một phần", 
                        "3. Khớp chéo liên ST 1-1", 
                        "4. Tổng Dư >= Tổng Thiếu", 
                        "5. Chỉ ghi nhận Thiếu ròng", 
                        "6. Chỉ ghi nhận Thừa ròng"
                    ])
                    
                    with sub_tab1:
                        st.subheader("1. Danh sách Khớp nội bộ 100% (DC thao tác sai)")
                        st.dataframe(df_exact, use_container_width=True)
                    with sub_tab2:
                        st.subheader("2. Danh sách Khớp nội bộ một phần")
                        st.dataframe(df_partial, use_container_width=True)
                    with sub_tab3:
                        st.subheader("3. Danh sách Khớp chéo liên ST 1-1 (DC giao nhầm CH)")
                        st.dataframe(df_cross, use_container_width=True)
                    with sub_tab4:
                        st.subheader("4. Danh sách Tổng Dư >= Tổng Thiếu")
                        st.dataframe(df_total_gte, use_container_width=True)
                    with sub_tab5:
                        st.subheader("5. Danh sách Chỉ ghi nhận Thiếu ròng (Siêu thị nhận thiếu)")
                        st.dataframe(df_only_diff, use_container_width=True)
                    with sub_tab6:
                        st.subheader("6. Danh sách Chỉ ghi nhận Thừa ròng (Siêu thị nhận thừa)")
                        st.dataframe(df_only_du, use_container_width=True)

            except Exception as e:
                st.error(f"Đã xảy ra lỗi khi chạy đối soát: {e}")
                st.exception(e)
    
    st.write("---")
    
    st.header("Báo Cáo Năng Suất Chi Tiết Mỗi Ngày (Google Sheets)")
    
    # Lọc dữ liệu từ ngày 01/05/2026 và tạo bộ lọc theo ngày
    df_daily_all = df_all[df_all['Ngày'] >= pd.to_datetime('2026-05-01')].copy()
    
    unique_daily_dates = df_daily_all.sort_values(by='Ngày')['Ngày_str'].dropna().unique().tolist()
    if unique_daily_dates:
        options = ["Tất cả các ngày"] + unique_daily_dates
        selected_daily_date = st.selectbox(
            "📅 Chọn ngày báo cáo (Daily):", 
            options, 
            index=len(options) - 1,
            key="selected_daily_date"
        )
        if selected_daily_date == "Tất cả các ngày":
            df_filtered = df_daily_all.copy()
        else:
            df_filtered = df_daily_all[df_daily_all['Ngày_str'] == selected_daily_date].copy()
    else:
        st.warning("Không có dữ liệu đối soát từ ngày 01/05/2026 trở đi.")
        df_filtered = pd.DataFrame()
    
    def calculate_daily_metrics(data, filter_type='all', group_by_col='CLV2'):
        if data.empty: return pd.DataFrame()
        
        data['Số lượng chuyển_clean'] = to_numeric(data['Số lượng chuyển'])
        data['Chênh lệch_clean'] = to_numeric(data['Chênh lệch'])
        
        data['Tổng_GT_num'] = to_numeric(data['Tổng GT'])
        data['Tổng_ST_num'] = to_numeric(data['Tổng ST'])
        data['Tổng_Kho_Rau_num'] = to_numeric(data['Tổng kho rau'])
        data['Tổng_Hao_Hut_num'] = to_numeric(data['Tổng hao hụt'])
        data['Tổng_CXD_num'] = to_numeric(data['Tổng chưa xác định'])
        
        # Lấy lượng chênh lệch chưa xác định (chưa có hướng xử lý)
        # Sử dụng cột Xử lý (cột Z) để phân chia Đang xử lý, Chưa xử lý, và Không xử lý (WRITE OFF)
        trang_thai = data['Xử lý'].astype(str).str.strip().str.lower()
        
        # Đang xử lý = CHƯA XÁC ĐỊNH (cột Y) + Hoàn thành (cột Z)
        data['CXD_DangXuLy'] = np.where(trang_thai == 'hoàn thành', data['CXD'], 0)
        data['GT_CXD_DangXuLy'] = np.where(trang_thai == 'hoàn thành', data['Tổng_CXD_num'], 0)
        
        # WRITE OFF = CHƯA XÁC ĐỊNH (cột Y) + Đang xử lý (cột Z)
        data['CXD_WriteOff'] = np.where(trang_thai == 'đang xử lý', data['CXD'], 0)
        data['CXD_WriteOff_Val'] = np.where(trang_thai == 'đang xử lý', data['Tổng_CXD_num'], 0)
        
        # Chưa xử lý = CHƯA XÁC ĐỊNH (cột Y) + các trường hợp còn lại
        data['CXD_ChuaXuLy'] = np.where((trang_thai != 'hoàn thành') & (trang_thai != 'đang xử lý'), data['CXD'], 0)
        data['GT_CXD_ChuaXuLy'] = np.where((trang_thai != 'hoàn thành') & (trang_thai != 'đang xử lý'), data['Tổng_CXD_num'], 0)
        
        data['GT_ST_NhapThieu'] = np.where(data['LyDo_X'].str.contains('siêu thị') & data['LyDo_Loi'].str.contains('thiếu'), data['Tổng_ST_num'], 0)
        data['GT_ST_SaiQT'] = np.where(data['LyDo_X'].str.contains('siêu thị') & ~data['LyDo_Loi'].str.contains('thiếu'), data['Tổng_ST_num'], 0)
        
        data['Is_Da_Xu_Ly'] = (data['Xử lý'].astype(str).str.strip().str.lower() == 'hoàn thành') & (data['Hao hụt'].fillna(0) <= 0)
        data['ST_Chenh_Lech'] = np.where(data['Chênh lệch_clean'].abs() > 0, data['ID ST'], np.nan)
        
        grouped = data.groupby(group_by_col, dropna=False).agg(
            Số_lượng_chuyển=('Số lượng chuyển_clean', 'sum'),
            Số_lượng_chênh_lệch=('Chênh lệch_clean', 'sum'),
            Số_lượng_ST_chênh_lệch=('ST_Chenh_Lech', 'nunique'),
            Số_lượng_line_chênh_lệch=('Mã hàng', 'count'),
            Số_lượng_line_hao_hụt=('Hao hụt', lambda x: (x > 0).sum()),
            Số_lượng_line_đã_xử_lý=('Is_Da_Xu_Ly', 'sum'),
            Số_lượng_hao_hụt=('Hao hụt', 'sum'),
            Số_lượng_bs_ST=('BS_ST', 'sum'),
            ST_nhap_thieu=('ST_NhapThieu', 'sum'),
            ST_sai_QT=('ST_SaiQT', 'sum'),
            SL_bs_kho_rau=('Kho_Rau', 'sum'),
            Số_lượng_đang_xử_lý=('CXD_DangXuLy', 'sum'),
            Số_lượng_chưa_xác_định=('CXD_ChuaXuLy', 'sum'),
            Số_lượng_write_off=('CXD_WriteOff', 'sum'),
            Giá_trị_write_off=('CXD_WriteOff_Val', 'sum'),
            Giá_trị_chênh_lệch=('Tổng_GT_num', 'sum'),
            Giá_trị_hao_hụt=('Tổng_Hao_Hut_num', 'sum'),
            Giá_trị_bs_ST=('Tổng_ST_num', 'sum'),
            GT_nhap_thieu=('GT_ST_NhapThieu', 'sum'),
            GT_sai_QT=('GT_ST_SaiQT', 'sum'),
            Giá_trị_bs_kho_rau=('Tổng_Kho_Rau_num', 'sum'),
            Giá_trị_đang_xử_lý=('GT_CXD_DangXuLy', 'sum'),
            Giá_trị_chưa_xác_định=('GT_CXD_ChuaXuLy', 'sum')
        ).reset_index()
        
        # Override SL chuyển if 25.5 and df_transfer_25_5 is loaded
        dates = data['Ngày'].dropna().dt.date.unique()
        if pd.to_datetime('2026-05-25').date() in dates and not df_transfer_25_5.empty:
            df_t = df_transfer_25_5.copy()
            if filter_type == 'kg':
                df_t = df_t[df_t['ĐVT'].astype(str).str.upper() == 'KG']
            elif filter_type == 'pack':
                df_t = df_t[df_t['ĐVT'].astype(str).str.upper() == 'PACK']
            elif filter_type == 'kg_nhan':
                df_t = df_t[(df_t['ĐVT'].astype(str).str.upper() == 'KG') & (df_t['Số lượng nhận'] > 0)]
            elif filter_type == 'kg_khongnhan':
                df_t = df_t[(df_t['ĐVT'].astype(str).str.upper() == 'KG') & (df_t['Số lượng nhận'] == 0)]
                
            if group_by_col not in df_t.columns and 'Mã hàng' in df_t.columns:
                mapping = dict(zip(data['Mã hàng'].astype(str), data[group_by_col].astype(str)))
                df_t[group_by_col] = df_t['Mã hàng'].map(mapping)
                
            transfer_grouped = df_t.groupby(group_by_col)['Số lượng chuyển'].sum().reset_index()
            grouped = grouped.drop(columns=['Số_lượng_chuyển'])
            grouped = pd.merge(grouped, transfer_grouped, on=group_by_col, how='left')
            grouped.rename(columns={'Số lượng chuyển': 'Số_lượng_chuyển'}, inplace=True)
            grouped['Số_lượng_chuyển'] = grouped['Số_lượng_chuyển'].fillna(0)
            
            cols_order = [group_by_col, 'Số_lượng_chuyển', 'Số_lượng_chênh_lệch', 'Số_lượng_ST_chênh_lệch', 'Số_lượng_line_chênh_lệch', 'Số_lượng_line_hao_hụt', 'Số_lượng_line_đã_xử_lý', 'Số_lượng_hao_hụt', 'Số_lượng_bs_ST', 'SL_bs_kho_rau', 'Số_lượng_đang_xử_lý', 'Số_lượng_chưa_xác_định', 'Số_lượng_write_off', 'Giá_trị_write_off', 'Giá_trị_chênh_lệch', 'Giá_trị_hao_hụt', 'Giá_trị_bs_ST', 'GT_nhap_thieu', 'GT_sai_QT', 'Giá_trị_bs_kho_rau', 'Giá_trị_đang_xử_lý', 'Giá_trị_chưa_xác_định']
            grouped = grouped[cols_order]
        
        grouped['Tỷ lệ line đã xử lý'] = ((grouped['Số_lượng_line_đã_xử_lý'] + grouped['Số_lượng_line_hao_hụt']) / grouped['Số_lượng_line_chênh_lệch'] * 100).round(2).astype(str) + '%'
        
        grouped['Tỷ lệ hao hụt'] = np.where(
            grouped['Số_lượng_chuyển'] > 0, 
            (grouped['Số_lượng_hao_hụt'] / grouped['Số_lượng_chuyển'] * 100).round(2).astype(str) + '%', 
            '0.0%'
        )
        
        grouped = grouped.rename(columns={
            'Số_lượng_chuyển': 'SL chuyển',
            'Số_lượng_chênh_lệch': 'SL chênh lệch',
            'Số_lượng_ST_chênh_lệch': 'SL ST chênh lệch',
            'Số_lượng_line_chênh_lệch': 'SL line chênh lệch',
            'Số_lượng_line_hao_hụt': 'SL line hao hụt',
            'Số_lượng_line_đã_xử_lý': 'SL line đã xử lý',
            'Số_lượng_hao_hụt': 'Số lượng hao hụt',
            'Số_lượng_bs_ST': 'SL bs ST',
            'ST_nhap_thieu': 'Lỗi ST (Nhập thiếu)',
            'ST_sai_QT': 'Lỗi ST (Sai QT)',
            'SL_bs_kho_rau': 'SL bs kho rau',
            'Số_lượng_đang_xử_lý': 'Đang xử lý',
            'Số_lượng_chưa_xác_định': 'Chưa xử lý',
            'Số_lượng_write_off': 'Không xử lý (WRITE OFF)',
            'Giá_trị_write_off': 'Giá trị WRITE OFF',
            'Giá_trị_chênh_lệch': 'GT chênh lệch',
            'Giá_trị_hao_hụt': 'GT hao hụt',
            'Giá_trị_bs_ST': 'GT bs ST',
            'GT_nhap_thieu': 'GT Lỗi ST (Nhập thiếu)',
            'GT_sai_QT': 'GT Lỗi ST (Sai QT)',
            'Giá_trị_bs_kho_rau': 'GT bs kho rau',
            'Giá_trị_đang_xử_lý': 'GT Đang xử lý',
            'Giá_trị_chưa_xác_định': 'GT Chưa xử lý'
        })
        
        grouped['Tổng Trả Kho Rau'] = grouped['Số lượng hao hụt'] + grouped['SL bs kho rau']
        grouped['GT Tổng Trả Kho Rau'] = grouped['GT hao hụt'] + grouped['GT bs kho rau']
        
        return grouped

    def display_daily_table(df, cols, title_prefix, group_by_col='CLV2'):
        if df.empty:
            return
        df_show = df[cols].copy()
        tong_df = pd.DataFrame(index=[0])
        for col in cols:
            if col == group_by_col:
                tong_df[col] = 'Tổng'
            elif col == 'Tỷ lệ line đã xử lý':
                sum_line_xl = df['SL line đã xử lý'].sum()
                sum_line_hh = df['SL line hao hụt'].sum()
                sum_line_cl = df['SL line chênh lệch'].sum()
                if sum_line_cl > 0:
                    tong_df[col] = str(round(((sum_line_xl + sum_line_hh) / sum_line_cl) * 100, 2)) + '%'
                else:
                    tong_df[col] = '0.0%'
            elif col == 'Tỷ lệ hao hụt':
                sum_hh = df['Số lượng hao hụt'].sum()
                sum_ch = df['SL chuyển'].sum()
                if sum_ch > 0:
                    tong_df[col] = str(round((sum_hh / sum_ch) * 100, 2)) + '%'
                else:
                    tong_df[col] = '0.0%'
            elif col == '% Lỗi ST / Chuyển':
                s_ch = df['SL chuyển'].sum()
                s_st = df['SL bs ST'].sum()
                tong_df[col] = str(round((s_st / s_ch * 100), 2)) + '%' if s_ch > 0 else '0%'
            elif col == '% Lỗi ST / Lệch':
                s_cl = df['SL chênh lệch'].sum()
                s_st = df['SL bs ST'].sum()
                tong_df[col] = str(round((s_st / s_cl * 100), 2)) + '%' if s_cl > 0 else '0%'
            elif col == '% Hao hụt / Chuyển':
                s_ch = df['SL chuyển'].sum()
                s_hh = df['Số lượng hao hụt'].sum()
                tong_df[col] = str(round((s_hh / s_ch * 100), 2)) + '%' if s_ch > 0 else '0%'
            elif col == '% Hao hụt / Lệch':
                s_cl = df['SL chênh lệch'].sum()
                s_hh = df['Số lượng hao hụt'].sum()
                tong_df[col] = str(round((s_hh / s_cl * 100), 2)) + '%' if s_cl > 0 else '0%'
            elif col == '% Trả KR (Lỗi GT) / Chuyển':
                s_ch = df['SL chuyển'].sum()
                s_kr = df['SL bs kho rau'].sum()
                tong_df[col] = str(round((s_kr / s_ch * 100), 2)) + '%' if s_ch > 0 else '0%'
            elif col == '% Trả KR (Lỗi GT) / Lệch':
                s_cl = df['SL chênh lệch'].sum()
                s_kr = df['SL bs kho rau'].sum()
                tong_df[col] = str(round((s_kr / s_cl * 100), 2)) + '%' if s_cl > 0 else '0%'
            elif pd.api.types.is_numeric_dtype(df[col]):
                tong_df[col] = df[col].sum()
            else:
                tong_df[col] = ''
                
        tuples = []
        total_cl_val = tong_df.iloc[0].get('SL chênh lệch', 0)
        total_cl = float(total_cl_val) if pd.notna(total_cl_val) and str(total_cl_val).replace('.','',1).replace('-','',1).isdigit() else 0
        
        for col in cols:
            val = tong_df.iloc[0][col]
            if val not in [None, 'Tổng', '', 0] and pd.notna(val):
                if pd.api.types.is_numeric_dtype(type(val)) or isinstance(val, (int, float)):
                    total_str = f"🟡 {format_vn(val)}"
                    if col in ['Lỗi ST (Nhập thiếu)', 'Lỗi ST (Sai QT)', 'Tổng Trả Kho Rau', 'Hao hụt (<=10%)', 'Trả KR (Lỗi giao thiếu)', '<= 5%', '5-10%', '10-15%', '> 15%'] and total_cl > 0:
                        pct = (val / total_cl) * 100
                        total_str += f" ({pct:.1f}%)"
                else:
                    total_str = f"🟡 {str(val)}"
            else:
                total_str = '⭐ TỔNG' if col == group_by_col else ''
                
            if col in ['Số lượng hao hụt', 'SL bs ST', 'Lỗi ST (Nhập thiếu)', 'Lỗi ST (Sai QT)', 'SL bs kho rau', 'Tỷ lệ hao hụt', 'Tổng Trả Kho Rau', 'Hao hụt (<=10%)', 'Trả KR (Lỗi giao thiếu)', 'GT hao hụt', 'GT bs ST', 'GT Lỗi ST (Nhập thiếu)', 'GT Lỗi ST (Sai QT)', 'GT bs kho rau', 'GT Tổng Trả Kho Rau']:
                cat = 'Đã xử lý'
                col_name = col
            elif col in ['<= 5%', '5-10%', '10-15%', '> 15%', 'GT <= 5%', 'GT 5-10%', 'GT 10-15%', 'GT > 15%']:
                cat = 'Phân bổ Chênh lệch (Số lượng)' if 'GT' not in col else 'Phân bổ Chênh lệch (Giá trị)'
                col_name = col
            else:
                cat = ''
                col_name = col
                if col == 'Không xử lý (WRITE OFF)' and 'Giá trị WRITE OFF' in df.columns:
                    val_writeoff = df['Giá trị WRITE OFF'].sum()
                    if val_writeoff > 0:
                        col_name = f"Không xử lý (WRITE OFF)\n({format_vn(val_writeoff)} đ)"
                elif col == 'Giá trị WRITE OFF':
                    col_name = 'Không xử lý (WRITE OFF)'
                
            tuples.append((total_str, cat, col_name))
            
        df_renamed = df_show.copy()
        df_renamed.columns = pd.MultiIndex.from_tuples(tuples)
        display_df_with_download(df_renamed.style.format(format_vn), f"Daily_{title_prefix}")

    st.subheader("Bảng 1: Đánh giá nhanh tình hình xử lý")
    df_b1 = calculate_daily_metrics(df_filtered, filter_type='all')
    cols = ['CLV2', 'SL chuyển', 'SL chênh lệch', 'SL ST chênh lệch', 'SL line chênh lệch', 'SL line hao hụt', 'SL line đã xử lý', 'Tỷ lệ line đã xử lý', 'Số lượng hao hụt', 'Tỷ lệ hao hụt', 'SL bs ST', 'SL bs kho rau', 'Đang xử lý', 'Chưa xử lý', 'Không xử lý (WRITE OFF)']
    cols_gt = ['CLV2', 'SL chuyển', 'GT chênh lệch', 'SL ST chênh lệch', 'SL line chênh lệch', 'SL line hao hụt', 'SL line đã xử lý', 'Tỷ lệ line đã xử lý', 'GT hao hụt', 'Tỷ lệ hao hụt', 'GT bs ST', 'GT bs kho rau', 'GT Đang xử lý', 'GT Chưa xử lý', 'Giá trị WRITE OFF']
    
    t1_sl, t1_gt = st.tabs(["📊 Số Lượng", "💰 Giá Trị"])
    with t1_sl:
        display_daily_table(df_b1, cols, "Bang_1")
    with t1_gt:
        display_daily_table(df_b1, cols_gt, "Bang_1_GT")
        
    nx_b1 = generate_insights(df_filtered, "Bảng 1", df_b1)
    st.text_area("Nhận xét Bảng 1:", value=nx_b1, key="nx_b1", height=100)
    
    # ---------------------- Đánh giá nhanh (Bảng 1) ----------------------
    summary_daily = compute_daily_summary(df_filtered, selected_daily_date)
    if summary_daily:
        st.markdown(f"**BÁO CÁO CHÊNH LỆCH ĐỐI SOÁT NGÀY {summary_daily['date'] if summary_daily['date'] != 'Tất cả các ngày' else 'TỔNG HỢP'}**")
        st.write(f"**Tổng: Lệch {summary_daily['total_items']} items (~{format_money(summary_daily['total_value'])} VNĐ).**")
        st.write("")
        st.write("**Kết quả xử lý:**")
        pct_done = round(summary_daily['processed'] / summary_daily['total_items'] * 100) if summary_daily['total_items'] else 0
        st.write(f"Đã xử lý: {summary_daily['processed']} items ({pct_done}%)")
        st.write(f"- Trả về Kho rau {summary_daily['return']} items")
        st.write(f"- Tạo bs ST {summary_daily['bs']} items")
        st.write(f"- Hao hụt {summary_daily['lost']} items (KG).")
        pct_remain = round(summary_daily['remaining'] / summary_daily['total_items'] * 100) if summary_daily['total_items'] else 0
        st.write(f"Tồn lại: {summary_daily['remaining']} items ({pct_remain}%)")
        st.write(f"(gồm {summary_daily['pending']} item đang xử lý + {summary_daily['unprocessed']} items chưa xử lý)")
        st.markdown("________________________")
        
        # Chi tiết theo nhóm
        for cat, data in summary_daily['cat_summary'].items():
            if data['items'] == 0: continue
            percent_value = (data['value'] / summary_daily['total_value'] * 100) if summary_daily['total_value'] else 0
            
            st.write(f"**{cat.upper()}**")
            st.write(f"Chênh lệch: {data['items']} items (Giá trị: ~{format_money(data['value'])} VNĐ - chiếm {round(percent_value,1)}% tổng giá trị lệch).")
            st.write(f"Đã xử lý: {data['processed']} items (Trả về Kho rau {data['return']} items, bs ST {data['bs']} items, Hao hụt {data['lost']} items).")
            
            rem_text = f"Còn tồn: "
            if data['pending'] > 0 and data['unprocessed'] > 0:
                rem_text += f"{data['pending']} items đang xử lý + {data['unprocessed']} items chưa xử lý"
            elif data['pending'] > 0:
                rem_text += f"{data['pending']} items đang xử lý"
            elif data['unprocessed'] > 0:
                rem_text += f"{data['unprocessed']} items chưa xử lý"
            else:
                rem_text += "0 items"
            st.write(rem_text)
            
            cause_pct = round(data['cause_ratio'] * 100)
            cause_val = data['value'] * data['cause_ratio']
            st.write(f"Nguyên nhân lỗi chính: DC giao thiếu thực tế chiếm đến {cause_pct}% giá trị chênh lệch (tương đương ~{format_money(cause_val)} VNĐ).")
            st.write("")
    # ----------------------------------------------------------------
    
    st.write("---")
    st.subheader("Bảng 1.1: Chi tiết đã xử lý")
    st.markdown("SL xử lý xác định qua các thông tin: Check camera, Hình ảnh ST, DC giao sai ST, DC pick sai...")
    
    # Lọc các dòng có xử lý cho Kho Rau hoặc ST
    df_note_data = df_filtered.copy()
    df_note_data['Kho_Rau_num'] = to_numeric(df_note_data['Kho_Rau'])
    df_note_data['BS_ST_num'] = to_numeric(df_note_data['BS_ST'])
    df_note_data = df_note_data[(df_note_data['Kho_Rau_num'] > 0) | (df_note_data['BS_ST_num'] > 0)].copy()
    
    if not df_note_data.empty:
        def map_note_to_category(note):
            note_str = str(note).lower().strip()
            if 'tele' in note_str or 'kdb' in note_str or 'hình' in note_str:
                return 'Hình ảnh ST'
            if 'st nhận' in note_str or 'giao sai' in note_str:
                return 'DC giao sai ST'
            if 'pick sai' in note_str or 'lấy sai' in note_str:
                return 'DC pick sai'
            return 'Check camera'
            
        df_note_data['Nguồn xác nhận'] = df_note_data['NOTE'].apply(map_note_to_category)
        
        df_note = df_note_data.groupby('Nguồn xác nhận').agg(
            SL_bs_kho_rau=('Kho_Rau_num', 'sum'),
            SL_bs_st=('BS_ST_num', 'sum'),
            So_lan=('Mã hàng', 'count')
        ).reset_index()
        
        df_note['Tổng (Kho Rau + ST)'] = df_note['SL_bs_kho_rau'] + df_note['SL_bs_st']
        df_note = df_note.sort_values(by='Tổng (Kho Rau + ST)', ascending=False)
        
        df_note.rename(columns={
            'SL_bs_kho_rau': 'SL bs kho rau',
            'SL_bs_st': 'SL bs ST',
            'So_lan': 'Số line'
        }, inplace=True)
        
        df_note = df_note[['Nguồn xác nhận', 'SL bs kho rau', 'SL bs ST', 'Tổng (Kho Rau + ST)', 'Số line']]
        
        # Bảng
        format_custom_table_with_total(df_note, 'Nguồn xác nhận', "Chi_Tiet_Ly_Do_Xu_Ly")
    else:
        st.info("Không có dữ liệu xử lý cho Kho Rau & ST trong kỳ báo cáo này.")
        df_note = pd.DataFrame()
        
    nx_b1_1 = generate_insights(df_note_data, "Bảng 1.1", df_note)
    st.text_area("Nhận xét Bảng 1.1:", value=nx_b1_1, key="nx_b1_1", height=100)
    
    st.write("---")
    st.subheader("Bảng 1.2: Đánh giá số lượng chưa xử lý (Áp dụng từ 27/05/2026)")
    st.markdown("Đề xuất hướng xử lý dựa trên Giá trị chênh lệch (Dưới 100 ngàn VNĐ -> Bỏ qua).")
    
    # Chỉ tính dữ liệu từ ngày 27/05/2026 trở đi cho Bảng 1.2
    df_cx = df_filtered[df_filtered['Ngày'] >= pd.to_datetime('2026-05-27')].copy()
    
    if df_cx.empty:
        st.info("Bảng 1.2 chỉ áp dụng cho dữ liệu từ ngày 27/05/2026 trở đi. Hãy chọn ngày phù hợp để xem.")
    else:
        # Sử dụng logic mới
        trang_thai = df_cx['Xử lý'].astype(str).str.strip().str.lower()
        df_cx['CXD_ChuaXuLy'] = np.where(trang_thai != 'hoàn thành', to_numeric(df_cx['CXD']), 0)
        
        df_cxd_only = df_cx[df_cx['CXD_ChuaXuLy'] > 0]
        
        if not df_cxd_only.empty:
            df_b12 = df_cxd_only.groupby(['CLV2', 'ID ST', 'Chi nhánh nhận']).agg(
                SL_ma=('Mã hàng', 'nunique'),
                SL_chuyen=('Số lượng chuyển', lambda x: to_numeric(x).sum()),
                SL_chenh_lech=('Chênh lệch', lambda x: to_numeric(x).sum()),
                SL_chua_xu_ly=('CXD_ChuaXuLy', 'sum'),
                Gia_tri_lech=('Tổng GT', lambda x: to_numeric(x).sum())
            ).reset_index()
            
            df_b12.rename(columns={
                'CLV2': 'Ngành hàng',
                'SL_ma': 'SL Mã',
                'SL_chuyen': 'SL Chuyển',
                'SL_chenh_lech': 'SL Chênh lệch',
                'SL_chua_xu_ly': 'Số lượng chưa xử lý',
                'Gia_tri_lech': 'Giá trị lệch (VNĐ)'
            }, inplace=True)
            
            def de_xuat_he_thong(val):
                if val < 100000:
                    return '🟢 Bỏ qua không xử lý'
                else:
                    return '🔴 Phải xử lý'
                    
            df_b12['Đề xuất hệ thống'] = df_b12['Giá trị lệch (VNĐ)'].apply(de_xuat_he_thong)
            df_b12 = df_b12.sort_values(by='Giá trị lệch (VNĐ)', ascending=False)
            
            format_custom_table_with_total(df_b12, 'Ngành hàng', "Bang_1_2")
            
            tong_tien_bo_qua = df_b12[df_b12['Giá trị lệch (VNĐ)'] < 100000]['Giá trị lệch (VNĐ)'].sum()
            sl_dong_bo_qua = len(df_b12[df_b12['Giá trị lệch (VNĐ)'] < 100000])
            sl_st_bo_qua = df_b12[df_b12['Giá trị lệch (VNĐ)'] < 100000]['ID ST'].nunique()
            
            if sl_dong_bo_qua > 0:
                nx_b12 = (f"- Đề xuất đóng/bỏ qua xử lý cho {sl_st_bo_qua} siêu thị (tương đương {sl_dong_bo_qua} PT chênh lệch) vì tổng giá trị chênh lệch ban đầu/ST < 100.000 VNĐ.\n"
                          f"  (WRITE OFF - theo Quy trình xử lý khiếu nại hậu kiểm)\n"
                          f"- Tổng giá trị tiết kiệm và bỏ qua ước tính: {format_vn(tong_tien_bo_qua)} VNĐ.\n"
                          f"- Đánh giá hiệu quả: Việc không cần xử lý với các case trên là hoàn toàn hợp lý. Đặc biệt đối với các trường hợp hàng nhận = 0 => không có hình ảnh từ siêu thị. Để đối soát, SCM phải dò camera theo thời gian nhận hàng, mất rất nhiều thời gian cắt và xem lại cam. Việc này gây tốn kém nhân lực lớn nhưng giá trị lấy lại thì không cao, không mang lại hiệu quả kinh tế.")
            else:
                nx_b12 = "- Tất cả các Siêu thị có hàng chưa xử lý đều có giá trị lớn hơn 100.000 VNĐ, cần tiếp tục đối soát và xử lý."
                
            st.text_area("Nhận xét Bảng 1.2:", value=nx_b12, key="nx_b1_2", height=150)
        else:
            st.info("Tuyệt vời! Không có hàng Chưa xử lý (Đang treo) trong ngày báo cáo này.")
        
    st.write("---")
    st.subheader("Bảng 2: Đánh giá tình hình xử lý hàng theo ĐVT: KG")
    df_kg = df_filtered[df_filtered['Loại hàng'].astype(str).str.upper() == 'KG'].copy()
    
    st.markdown("**2.1 Đánh giá mức độ nghiêm trọng chênh lệch (Hàng KG Nhận > 0 - Theo CLV4)**")
    df_kg_nhan = df_kg[to_numeric(df_kg['Số lượng nhận']) > 0].copy()
    
    # Lấy lại các cột xử lý (Hao hụt, Lỗi ST, Trả KR)
    df_b21_new = calculate_daily_metrics(df_kg_nhan, filter_type='kg_nhan', group_by_col='CLV4')
    df_b21_new['Hao hụt (<=10%)'] = df_b21_new['Số lượng hao hụt']
    df_b21_new['Trả KR (Lỗi giao thiếu)'] = df_b21_new['SL bs kho rau']
    df_b21_new['Tổng Trả Kho Rau'] = df_b21_new['Hao hụt (<=10%)'] + df_b21_new['Trả KR (Lỗi giao thiếu)']
    
    df_b21_new['GT Hao hụt (<=10%)'] = df_b21_new['GT hao hụt']
    df_b21_new['GT Trả KR (Lỗi giao thiếu)'] = df_b21_new['GT bs kho rau']
    
    # Tính tỷ lệ lệch từng dòng cho Phân bổ Chênh lệch (chỉ dựa vào phần Trả Kho Rau)
    df_kg_nhan['Số lượng chuyển_clean'] = to_numeric(df_kg_nhan['Số lượng chuyển'])
    
    # Số lượng thực sự mà Kho Rau phải chịu trách nhiệm (Hao hụt + Lỗi Giao Thiếu)
    df_kg_nhan['Row_Tong_Tra_KR'] = to_numeric(df_kg_nhan['Hao hụt']) + to_numeric(df_kg_nhan['Kho_Rau'])
    df_kg_nhan['Row_Tong_Tra_KR_GT'] = to_numeric(df_kg_nhan['Tổng hao hụt']) + to_numeric(df_kg_nhan['Tổng kho rau'])
    
    df_kg_nhan['Tỷ lệ % lệch'] = np.where(
        df_kg_nhan['Số lượng chuyển_clean'] > 0, 
        (df_kg_nhan['Row_Tong_Tra_KR'] / df_kg_nhan['Số lượng chuyển_clean']) * 100, 
        100
    )
    
    # Phân loại dòng
    conditions = [
        (df_kg_nhan['Tỷ lệ % lệch'] == 0),
        (df_kg_nhan['Tỷ lệ % lệch'] > 0) & (df_kg_nhan['Tỷ lệ % lệch'] <= 5),
        (df_kg_nhan['Tỷ lệ % lệch'] > 5) & (df_kg_nhan['Tỷ lệ % lệch'] <= 10),
        (df_kg_nhan['Tỷ lệ % lệch'] > 10) & (df_kg_nhan['Tỷ lệ % lệch'] <= 15),
        (df_kg_nhan['Tỷ lệ % lệch'] > 15)
    ]
    choices = ['0%', '<= 5%', '5-10%', '10-15%', '> 15%']
    df_kg_nhan['Nhóm lệch'] = np.select(conditions, choices, default='> 15%')
    
    # Tính TỔNG SỐ LƯỢNG LỆCH (Phần Kho Rau) rơi vào từng nhóm %
    pivot_bucket = df_kg_nhan[df_kg_nhan['Nhóm lệch'] != '0%'].pivot_table(
        index='CLV4', 
        columns='Nhóm lệch', 
        values='Row_Tong_Tra_KR', 
        aggfunc='sum', 
        fill_value=0
    ).reset_index()
    
    pivot_bucket_gt = df_kg_nhan[df_kg_nhan['Nhóm lệch'] != '0%'].pivot_table(
        index='CLV4', 
        columns='Nhóm lệch', 
        values='Row_Tong_Tra_KR_GT', 
        aggfunc='sum', 
        fill_value=0
    ).reset_index()
    rename_dict = {c: f'GT {c}' for c in ['<= 5%', '5-10%', '10-15%', '> 15%']}
    pivot_bucket_gt.rename(columns=rename_dict, inplace=True)
    
    # Merge buckets vào df_b21_new
    df_b21_new = pd.merge(df_b21_new, pivot_bucket, on='CLV4', how='left').fillna(0)
    df_b21_new = pd.merge(df_b21_new, pivot_bucket_gt, on='CLV4', how='left').fillna(0)
    
    # Đảm bảo đủ cột
    for c in ['<= 5%', '5-10%', '10-15%', '> 15%']:
        if c not in df_b21_new.columns:
            df_b21_new[c] = 0
    for c in rename_dict.values():
        if c not in df_b21_new.columns:
            df_b21_new[c] = 0
            
    cols2_1 = [
        'CLV4', 'SL chuyển', 'SL chênh lệch', 
        'Lỗi ST (Nhập thiếu)', 'Lỗi ST (Sai QT)', 
        'Tổng Trả Kho Rau', 'Hao hụt (<=10%)', 'Trả KR (Lỗi giao thiếu)',
        '<= 5%', '5-10%', '10-15%', '> 15%', 
        'Đang xử lý', 'Chưa xử lý', 'Không xử lý (WRITE OFF)'
    ]
    
    cols2_1_gt = [
        'CLV4', 'SL chuyển', 'GT chênh lệch', 
        'GT Lỗi ST (Nhập thiếu)', 'GT Lỗi ST (Sai QT)', 
        'GT Tổng Trả Kho Rau', 'GT Hao hụt (<=10%)', 'GT Trả KR (Lỗi giao thiếu)',
        'GT <= 5%', 'GT 5-10%', 'GT 10-15%', 'GT > 15%', 
        'GT Đang xử lý', 'GT Chưa xử lý', 'Giá trị WRITE OFF'
    ]
    
    t21_sl, t21_gt = st.tabs(["📊 Số Lượng", "💰 Giá Trị"])
    with t21_sl:
        display_daily_table(df_b21_new, cols2_1, "Bang_2_1_CLV4", group_by_col='CLV4')
    with t21_gt:
        display_daily_table(df_b21_new, cols2_1_gt, "Bang_2_1_CLV4_GT", group_by_col='CLV4')
    
    st.info("💡 **Gợi ý Action:** Các khoản lệch rơi vào mức `<= 5%` là hao hụt tự nhiên, có thể xem xét bỏ qua. Các mức từ `> 10%` là do lỗi chủ quan (kho nhặt thiếu, ST nhập sai), yêu cầu check lại quy trình.")

    nx_b21_new = generate_insights(df_kg_nhan, "Bảng 2.1_New", df_metrics=df_b21_new, date_str=selected_date)
    st.text_area("Nhận xét Bảng 2.1:", value=nx_b21_new, key="nx_b21_new", height=160)

    st.markdown("**2.2 Hàng có số lượng nhận > 0, phát sinh chênh lệch (Theo Ngành Hàng CLV2)**")
    df_b22_old = calculate_daily_metrics(df_kg_nhan, filter_type='kg_nhan')
    cols2 = ['CLV2', 'SL chuyển', 'SL chênh lệch', 'SL ST chênh lệch', 'SL line chênh lệch', 'SL line hao hụt', 'SL line đã xử lý', 'Tỷ lệ line đã xử lý', 'Số lượng hao hụt', 'Tỷ lệ hao hụt', 'SL bs ST', 'SL bs kho rau', 'Đang xử lý', 'Chưa xử lý', 'Không xử lý (WRITE OFF)']
    cols2_gt = ['CLV2', 'SL chuyển', 'GT chênh lệch', 'SL ST chênh lệch', 'SL line chênh lệch', 'SL line hao hụt', 'SL line đã xử lý', 'Tỷ lệ line đã xử lý', 'GT hao hụt', 'Tỷ lệ hao hụt', 'GT bs ST', 'GT bs kho rau', 'GT Đang xử lý', 'GT Chưa xử lý', 'Giá trị WRITE OFF']
    
    t22_sl, t22_gt = st.tabs(["📊 Số Lượng", "💰 Giá Trị"])
    with t22_sl:
        display_daily_table(df_b22_old, cols2, "Bang_2_2")
    with t22_gt:
        display_daily_table(df_b22_old, cols2_gt, "Bang_2_2_GT")
        
    nx_b22_old = generate_insights(df_kg_nhan, "Bảng 2.1", df_b22_old) # Use "Bảng 2.1" logic for insights since it's the old 2.1
    st.text_area("Nhận xét Bảng 2.2:", value=nx_b22_old, key="nx_b22_old", height=120)
    
    st.markdown("**2.3 Hàng có số lượng nhận = 0, phát sinh chênh lệch**")
    df_kg_khongnhan = df_kg[to_numeric(df_kg['Số lượng nhận']) == 0]
    df_b23 = calculate_daily_metrics(df_kg_khongnhan, filter_type='kg_khongnhan')
    
    t23_sl, t23_gt = st.tabs(["📊 Số Lượng", "💰 Giá Trị"])
    with t23_sl:
        display_daily_table(df_b23, cols2, "Bang_2_3")
    with t23_gt:
        display_daily_table(df_b23, cols2_gt, "Bang_2_3_GT")
        
    nx_b23 = generate_insights(df_kg_khongnhan, "Bảng 2.2", df_b23) # Use "Bảng 2.2" logic for insights since it's the old 2.2
    st.text_area("Nhận xét Bảng 2.3:", value=nx_b23, key="nx_b23", height=120)
    
    st.subheader("Bảng 3: Đánh giá theo tình hình hàng Pack")
    df_pack = df_filtered[df_filtered['Loại hàng'].astype(str).str.upper() == 'PACK'].copy()
    df_b3 = calculate_daily_metrics(df_pack, filter_type='pack')
    
    t3_sl, t3_gt = st.tabs(["📊 Số Lượng", "💰 Giá Trị"])
    with t3_sl:
        display_daily_table(df_b3, cols2, "Bang_3")
    with t3_gt:
        display_daily_table(df_b3, cols2_gt, "Bang_3_GT")
        
    nx_b3 = generate_insights(df_pack, "Bảng 3", df_b3)
    st.text_area("Nhận xét Bảng 3:", value=nx_b3, key="nx_b3", height=120)
    
    st.write("---")
    st.subheader("Bảng 4: Top sản phẩm (KG) có lượng Hao Hụt phát sinh cao nhất")
    st.markdown("Giúp theo dõi nhóm hàng KG nào thường xuyên hao hụt nhiều nhất.")
    df_kg_hao_hut = df_kg[df_kg['Hao hụt'] > 0].copy()
    if not df_kg_hao_hut.empty:
        df_top_hh = df_kg_hao_hut.groupby('SKU_Full').agg(
            Số_lượng_hao_hụt=('Hao hụt', 'sum'),
            Số_dòng_phát_sinh=('Mã hàng', 'count')
        ).reset_index()
        df_top_hh = df_top_hh.sort_values(by='Số_lượng_hao_hụt', ascending=False)
        df_top_hh.rename(columns={
            'SKU_Full': 'Mã & Tên hàng',
            'Số_lượng_hao_hụt': 'Tổng số lượng hao hụt',
            'Số_dòng_phát_sinh': 'Số line'
        }, inplace=True)
        
        # Bảng
        format_custom_table_with_total(df_top_hh, 'Mã & Tên hàng', "Top_Hao_Hut_KG")
    else:
        st.info("Không có dữ liệu hao hụt cho hàng KG trong kỳ báo cáo này.")
        df_top_hh = pd.DataFrame()
        
    nx_b4 = generate_insights(df_kg_hao_hut, "Bảng 4", df_top_hh)
    st.text_area("Nhận xét Bảng 4:", value=nx_b4, key="nx_b4", height=100)

# ==========================================
# TRANG 3: TIẾN ĐỘ DC PHẢN HỒI
# ==========================================
with tab_dc:
    st.header("👨‍🔧 Theo Dõi Tiến Độ Xử Lý & Phản Hồi Của DC")
    st.markdown("Báo cáo dành riêng để Operations theo dõi và đốc thúc DC xử lý các mã hàng chênh lệch/lỗi chưa được giải quyết.")
    render_dc_feedback_progress_report(df_active, "Tab_3")
    
    st.write("---")
    st.subheader("📋 Báo cáo bổ sung: Đánh giá LỖI TRẢ VỀ KHO RAU (Theo DC Xác Nhận)")
    st.markdown("Báo cáo số lượng trả về Kho Rau (Từ cột P) dựa trên cột DC xác nhận (AB) và cột Lỗi (V).")
    
    df_b_dc_base = df_active[to_numeric(df_active['Kho_Rau']) > 0].copy()
    if not df_b_dc_base.empty:
        if 'DC xác nhận' not in df_b_dc_base.columns:
            df_b_dc_base['DC xác nhận'] = 'N/A'
        if 'Lỗi' not in df_b_dc_base.columns:
            df_b_dc_base['Lỗi'] = 'N/A'
            
        col_kfm = 'KFM phản hồi'
        if col_kfm not in df_b_dc_base.columns:
            col_kfm = df_b_dc_base.columns[29] if len(df_b_dc_base.columns) > 29 else None
            
        df_b_dc_base['DC xác nhận'] = df_b_dc_base['DC xác nhận'].fillna('Chưa xác nhận').replace('', 'Chưa xác nhận')
        df_b_dc_base['Lỗi'] = df_b_dc_base['Lỗi'].fillna('Không có ghi chú').replace('', 'Không có ghi chú')
        
        groupby_cols = ['DC xác nhận', 'Lỗi']
        if col_kfm:
            df_b_dc_base[col_kfm] = df_b_dc_base[col_kfm].fillna('Không có phản hồi').replace('', 'Không có phản hồi')
            groupby_cols.append(col_kfm)
        
        df_b_dc = df_b_dc_base.groupby(groupby_cols).agg(
            Tổng_số_lượng=('Kho_Rau', lambda x: to_numeric(x).sum()),
            Tổng_giá_trị=('Tổng kho rau', lambda x: to_numeric(x).sum()),
            Số_line=('Mã hàng', 'count')
        ).reset_index()
        
        df_b_dc = df_b_dc.sort_values(by='Tổng_số_lượng', ascending=False)
        
        rename_dict = {
            'Tổng_số_lượng': 'Tổng số lượng',
            'Tổng_giá_trị': 'Tổng giá trị (VNĐ)',
            'Số_line': 'Số line'
        }
        if col_kfm and col_kfm != 'KFM phản hồi':
            rename_dict[col_kfm] = 'KFM phản hồi'
            
        df_b_dc.rename(columns=rename_dict, inplace=True)
        
        format_custom_table_with_total(df_b_dc, 'DC xác nhận', "Danh_Gia_Loi_Kho_Rau_Tab_3")
    else:
        st.info("Không có dữ liệu trả về Kho Rau trong kỳ báo cáo này.")
        df_b_dc = pd.DataFrame()
        
    nx_b_dc = generate_insights(df_b_dc_base, "Bảng 6", df_b_dc)
    st.text_area("Nhận xét Đánh giá Lỗi:", value=nx_b_dc, key="nx_b_dc", height=100)

with tab_logic:
    st.header("📑 Đặc tả Logic Đối soát Tự động")
    try:
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        spec_file = os.path.join(current_dir, "automation_logic_specification.md")
        with open(spec_file, "r", encoding="utf-8") as f:
            spec_content = f.read()
        st.markdown(spec_content, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Không thể đọc file đặc tả logic: {e}")




