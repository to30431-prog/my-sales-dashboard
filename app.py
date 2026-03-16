import streamlit as st
import pandas as pd
import plotly.express as px
import os
import re
import zipfile
import google.generativeai as genai 

# --- 🌟 設定 Gemini API Key ---
GOOGLE_API_KEY = "AIzaSyAf_rmswAbDS87YxTAwjICVg3SPdlYZ16o" 
genai.configure(api_key=GOOGLE_API_KEY)

# --- 🎨 頁面設定 ---
st.set_page_config(page_title="峰揚行動查價系統", page_icon="📱", layout="wide")

# --- 💅 CSS 美學核心 (極簡觸控優化版) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;700;900&family=Noto+Sans+TC:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Nunito', 'Noto Sans TC', sans-serif !important; }
    
    /* 強制全局文字顏色，避免手機深色模式反白看不到 */
    .stApp { color: #333333 !important; }
    
    /* 側邊欄漸層與陰影 */
    [data-testid="stSidebar"] { 
        background: linear-gradient(135deg, #FFF6E5 0%, #F0F4FF 100%) !important; 
        border-right: none; 
        box-shadow: 4px 0 15px rgba(0,0,0,0.05); 
    }
    [data-testid="stSidebar"] * { color: #333333 !important; }
    
    /* 🌟 導航按鈕 (果凍感) - 適合手機手指點擊 */
    div.row-widget.stRadio > div { gap: 12px; }
    div.row-widget.stRadio > div > label {
        background-color: rgba(255, 255, 255, 0.7); padding: 15px 20px; border-radius: 30px; border: 2px solid transparent; cursor: pointer;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275); box-shadow: 0 4px 10px rgba(0,0,0,0.03); font-weight: bold; color: #5D6D7E !important;
    }
    div.row-widget.stRadio > div > label:hover {
        transform: translateY(-4px) scale(1.03); background: linear-gradient(120deg, #84FAB0 0%, #8FD3F4 100%); color: #0E6655 !important; border: 2px solid #FFFFFF; box-shadow: 0 10px 20px rgba(132, 250, 176, 0.4);
    }
    div.row-widget.stRadio > div > label > div:first-child { display: none; }
    
    /* 🌟 KPI 卡片果凍懸浮感 */
    div[data-testid="stMetric"], div[data-testid="metric-container"] {
        background: #FFFFFF !important; border: none; border-top: 6px solid #FF9A9E; padding: 20px; border-radius: 20px; box-shadow: 0 8px 16px rgba(0,0,0,0.06); transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }
    div[data-testid="stMetric"]:hover { transform: translateY(-8px); border-top: 6px solid #FECFEF; box-shadow: 0 15px 25px rgba(255, 154, 158, 0.25); }
    div[data-testid="stMetric"] label, div[data-testid="stMetric"] div, div[data-testid="stMetric"] p, div[data-testid="stMetricValue"] div { color: #333333 !important; }
    
    /* 標題漸層色 */
    h1, h2 { background: -webkit-linear-gradient(45deg, #f093fb 0%, #f5576c 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900; letter-spacing: 1px; }
    h3, h4 { color: #2C3E50; font-weight: 700; }
    </style>
""", unsafe_allow_html=True)

# --- 🔍 核彈級檔案搜尋器 ---
def find_file_recursive(target_names):
    targets_lower = [t.lower() for t in target_names]
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.lower() in targets_lower:
                return os.path.join(root, file)
    return None

# --- 🔥 數據載入引擎 (輕量化版) ---
@st.cache_data(show_spinner="🚀 正在全機掃描並載入數據，請稍候...")
def load_data_final():
    try:
        zip_path = find_file_recursive(['All_Sales_5Years.zip', 'All_Sales_5years.zip', 'all_sales_5years.zip'])
        csv_path = find_file_recursive(['All_Sales_5Years.csv', 'All_Sales_2025_2026.csv'])
        
        df = None
        
        if zip_path:
            try:
                with zipfile.ZipFile(zip_path, 'r') as z:
                    valid_files = [f for f in z.namelist() if f.lower().endswith('.csv') and not f.startswith('__')]
                    if valid_files:
                        target_csv = valid_files[0]
                        with z.open(target_csv) as f:
                            try: df = pd.read_csv(f, encoding='utf-8', low_memory=False)
                            except: df = pd.read_csv(f, encoding='cp950', low_memory=False)
            except Exception as e:
                return None, f"Zip 讀取失敗: {str(e)}"
        elif csv_path:
            try: df = pd.read_csv(csv_path, encoding='utf-8', low_memory=False)
            except: df = pd.read_csv(csv_path, encoding='cp950', low_memory=False)
        else:
            return None, "❌ 找不到資料檔 (CSV或ZIP)"

        if df is None: return None, "讀取後資料為空"

        df['OUTDATE'] = pd.to_datetime(df['OUTDATE'], format='%Y%m%d', errors='coerce')
        df = df.sort_values('OUTDATE')
        df['日期_CN'] = df['OUTDATE'].dt.strftime('%Y年%m月%d日')
        df['金額'] = pd.to_numeric(df['SUBTOT'], errors='coerce').fillna(0)
        df['數量'] = pd.to_numeric(df['OUTQTY'], errors='coerce').fillna(0)
        
        best_code_col = None
        priority_cols = [c for c in df.columns if c.upper() in ['IT_NO', 'ITEM_NO', 'P_NO', 'CODE', 'PROD_ID']]
        if priority_cols: best_code_col = priority_cols[0]
        else:
            max_matches = 0
            for col in df.select_dtypes(include=['object']).columns:
                matches = df[col].astype(str).str.count(r'[a-zA-Z]+[\s-]*\d+').sum()
                if matches > max_matches: max_matches = matches; best_code_col = col
        
        if best_code_col: 
            def extract_smart_code(text):
                text = str(text).strip()
                match = re.search(r"([a-zA-Z]{1,4})[\s-]*(\d{1,5})", text)
                if match: return f"{match.group(1)}{match.group(2)}"
                return text[:5]
            df['產品編號'] = df[best_code_col].apply(extract_smart_code)
        else: df['產品編號'] = "Unknown"

        title_candidates = [c for c in df.columns if c.upper() in ['TITLE', 'NAME', 'PROD_NAME', 'DESCRIPTION', 'C_NAME']]
        best_name_col = title_candidates[0] if title_candidates else best_code_col
        if best_name_col: df['產品名稱'] = df[best_name_col].astype(str)
        else: df['產品名稱'] = df['產品編號']
        df['產品全名'] = "[" + df['產品編號'] + "] " + df['產品名稱']

        def split_prod_code(code):
            match = re.search(r"([a-zA-Z]+)[\s-]*(\d+)", str(code))
            return (match.group(1).upper(), int(match.group(2))) if match else ("N/A", 0)
        df['Prefix'], df['ProdNum'] = zip(*df['產品編號'].apply(split_prod_code))

        def super_clean(x):
            if pd.isna(x): return "None"
            s = str(x).strip()
            if s.endswith('.0'): s = s[:-2]
            return s
        df['CUST_KEY'] = df['CUST_NO'].apply(super_clean)
        df['SALES_KEY'] = df['SUBNO'].apply(super_clean)
        
        name_map = {}
        lab_path = find_file_recursive(['LABORER.DBF', 'laborer.dbf', '勞工.DBF', '勞工.dbf'])
        if lab_path:
            try:
                from dbfread import DBF
                l_table = DBF(lab_path, encoding='cp950', char_decode_errors='ignore', ignore_missing_memofile=True)
                l_df = pd.DataFrame(iter(l_table))
                id_col = next((c for c in l_df.columns if c.upper() in ['SUBNO', 'SNO', 'S_NO', 'ID', 'K_NO']), None)
                name_col = next((c for c in l_df.columns if c.upper() in ['NAME', 'NAME_C', 'L_NAME', 'SNAME']), None)
                if id_col and name_col:
                    l_df['clean_key'] = l_df[id_col].apply(super_clean)
                    l_df['zfill_key'] = l_df[id_col].apply(super_clean).str.zfill(4)
                    name_map = {**l_df.set_index('clean_key')[name_col].to_dict(), **l_df.set_index('zfill_key')[name_col].to_dict()}
            except: pass

        cust_map = {}
        cust_path = find_file_recursive(['CUST.DBF', 'cust.dbf', '客戶.DBF'])
        if cust_path:
            try:
                from dbfread import DBF
                c_table = DBF(cust_path, encoding='cp950', char_decode_errors='replace', ignore_missing_memofile=True)
                c_df = pd.DataFrame(iter(c_table))
                c_id_col = next((c for c in c_df.columns if c.upper() in ['CUST_NO', 'CNO', 'C_NO', 'K_NO', 'ID', 'CODE']), None)
                c_na_col = next((c for c in c_df.columns if c.upper() in ['C_NA', 'NAME', 'C_NAME', 'COMPANY', 'CUST_NAME', 'TITLE']), None)
                if c_id_col and c_na_col:
                    c_df['clean_key'] = c_df[c_id_col].apply(super_clean)
                    cust_map = c_df.set_index('clean_key')[c_na_col].to_dict()
            except: pass

        df['業務員'] = df['SALES_KEY'].map(name_map).fillna(df['SALES_KEY'])
        mask_sales_fail = df['業務員'] == df['SALES_KEY']
        if mask_sales_fail.any():
             df.loc[mask_sales_fail, '業務員'] = df.loc[mask_sales_fail, 'SALES_KEY'].str.zfill(4).map(name_map).fillna(df.loc[mask_sales_fail, 'SALES_KEY'])
        df['店家名稱'] = df['CUST_KEY'].map(cust_map).fillna(df['CUST_KEY'])
        
        return df

    except Exception as e:
        return None, str(e)

result = load_data_final()
if isinstance(result, tuple) and result[0] is None: 
    st.error(f"⚠️ 系統錯誤: {result[1]}")
    st.stop()
else:
    df = result if not isinstance(result, tuple) else result[0]

if df is not None:
    with st.sidebar:
        st.markdown("<h2 style='text-align: center; color: #2C3E50;'>📱 行動查價站</h2>", unsafe_allow_html=True)
        st.caption(f"<div style='text-align: center; margin-bottom: 20px;'>📊 總資料筆數: {len(df):,}</div>", unsafe_allow_html=True)
        
        # 🌟 極簡選單
        menu_options = [
            "🏆 營運總覽 Dashboard", 
            "🔎 店家查帳 (單一店家查價)", 
            "📋 全店家總表 (全台查價)", 
            "🎯 系列產品分析", 
            "🕵️‍♀️ 業務績效深鑽", 
            "🚨 報價照妖鏡 (抓底價/天價)"
        ]
            
        analysis_mode = st.radio("請選擇工具：", menu_options, label_visibility="collapsed")
        
        st.markdown("---")
        st.markdown("### 📅 時間軸濾鏡")
        min_date = df['OUTDATE'].min().date()
        max_date = df['OUTDATE'].max().date()
        
        # 🚀 升級版：極致絲滑的快速時間選項
        date_preset = st.selectbox("⏳ 快速跳轉", [
            "最近 7 天", "最近 30 天", "本月", "上個月", 
            "最近 3 個月", "最近 6 個月", "最近 9 個月", 
            "今年以來 (YTD)", "去年全年度", "近 3 年", "全部 5 年"
        ])
        
        if date_preset == "最近 7 天": 
            start_d, end_d = max_date - pd.Timedelta(days=7), max_date
        elif date_preset == "最近 30 天": 
            start_d, end_d = max_date - pd.Timedelta(days=30), max_date
        elif date_preset == "本月": 
            start_d, end_d = max_date.replace(day=1), max_date
        elif date_preset == "上個月": 
            first_day_this_month = max_date.replace(day=1)
            end_d = first_day_this_month - pd.Timedelta(days=1)
            start_d = end_d.replace(day=1)
        elif date_preset == "最近 3 個月": 
            start_d, end_d = (pd.to_datetime(max_date) - pd.DateOffset(months=3)).date(), max_date
        elif date_preset == "最近 6 個月": 
            start_d, end_d = (pd.to_datetime(max_date) - pd.DateOffset(months=6)).date(), max_date
        elif date_preset == "最近 9 個月": 
            start_d, end_d = (pd.to_datetime(max_date) - pd.DateOffset(months=9)).date(), max_date
        elif date_preset == "今年以來 (YTD)": 
            start_d, end_d = pd.Timestamp(f"{max_date.year}-01-01").date(), max_date
        elif date_preset == "去年全年度": 
            start_d, end_d = pd.Timestamp(f"{max_date.year-1}-01-01").date(), pd.Timestamp(f"{max_date.year-1}-12-31").date()
        elif date_preset == "近 3 年": 
            start_d, end_d = (pd.to_datetime(max_date) - pd.DateOffset(years=3)).date(), max_date
        else: 
            start_d, end_d = min_date, max_date
        
        selected_start = st.date_input("🟢 起", value=start_d, min_value=min_date, max_value=max_date)
        selected_end = st.date_input("🔴 迄", value=end_d, min_value=min_date, max_value=max_date)
        
        if selected_start > selected_end: 
            st.error("⚠️ 起算日不能晚於結尾日喔！")

    v_df = df.copy()
    if selected_start <= selected_end:
        v_df = v_df[(v_df['OUTDATE'].dt.date >= selected_start) & (v_df['OUTDATE'].dt.date <= selected_end)]

    st.markdown(f"## {analysis_mode}")
    if "全店家總表" not in analysis_mode and "報價照妖鏡" not in analysis_mode:
        st.caption(f"🗓️ 數據範圍：**{selected_start}** 至 **{selected_end}**")

    # ==========================================
    # 🏆 營運總覽 Dashboard
    # ==========================================
    if "營運總覽" in analysis_mode:
        st.markdown("### 📊 關鍵指標")
        c1, c2 = st.columns(2)
        c1.metric("💰 區間總營收", f"${v_df['金額'].sum():,.0f}")
        c2.metric("📦 總出貨包數", f"{v_df['數量'].sum():,.0f}")
        c3, c4 = st.columns(2)
        c3.metric("🏪 成交店數", f"{v_df['店家名稱'].nunique()}")
        c4.metric("🧾 成交單數", f"{v_df['SOURNO'].nunique()}")

    # ==========================================
    # 1. 店家查帳 / 我的客戶查帳 (極簡查價版)
    # ==========================================
    elif "店家查帳" in analysis_mode:
        kw = st.sidebar.text_input("🔍 搜尋店家名稱", "")
        if kw: v_df = v_df[v_df['店家名稱'].str.contains(kw, na=False)]
        
        cust_group = v_df.groupby('店家名稱')['金額'].sum().sort_values(ascending=False).reset_index()
        if cust_group.empty:
            st.warning("⚠️ 該區間內無交易紀錄！")
            sel = "--"
        else:
            cust_group['Label'] = cust_group.apply(lambda x: f"{x['店家名稱']} (${x['金額']:,.0f})", axis=1)
            sel_label = st.selectbox("請選擇店家", ["--- 請選擇 ---"] + cust_group['Label'].tolist())
            sel = sel_label.split(' ($')[0] if sel_label != "--- 請選擇 ---" else "--"
            
        if sel != "--":
            st.success(f"已鎖定：**{sel}**")
            sub = df[df['店家名稱'] == sel] 
            
            tab_history, tab_1yr_summary = st.tabs(["🧾 單筆歷史進貨", "📦 近一年專屬報價單"])
            
            with tab_history:
                sub_time_filtered = v_df[v_df['店家名稱'] == sel]
                og = sub_time_filtered.groupby(['日期_CN', 'SOURNO'])['金額'].sum().reset_index().sort_values('日期_CN', ascending=False)
                og['L'] = og.apply(lambda x: f"{x['日期_CN']} (單號:{x['SOURNO']} / 金額: ${x['金額']:,.0f})", axis=1)
                
                if og.empty:
                    st.info("該區間內無單筆紀錄。")
                else:
                    d_sel = st.selectbox("選擇進貨單查看明細", og['L'].tolist())
                    if d_sel:
                        target_date = d_sel.split(' (')[0]
                        target_sourno = d_sel.split('單號:')[1].split(' /')[0].strip() 
                        detail_df = sub_time_filtered[(sub_time_filtered['日期_CN'] == target_date) & (sub_time_filtered['SOURNO'].astype(str).str.strip() == target_sourno)][['產品全名', '數量', '金額']]
                        st.dataframe(detail_df, use_container_width=True, hide_index=True)
                        
            with tab_1yr_summary:
                one_year_ago = df['OUTDATE'].max() - pd.DateOffset(years=1)
                sub_1yr = sub[sub['OUTDATE'] >= one_year_ago]
                
                if sub_1yr.empty:
                    st.info("該店家近一年內無進貨紀錄。")
                else:
                    latest_records = sub_1yr.sort_values('OUTDATE', ascending=False).drop_duplicates('產品全名')
                    latest_records['最新單價'] = (latest_records['金額'] / latest_records['數量']).fillna(0).round(0)
                    latest_price_map = latest_records.set_index('產品全名')['最新單價'].to_dict()
                    
                    def smart_price_single(row):
                        qty = row['數量']
                        amt = row['金額']
                        if qty <= 0: return 0
                        avg = amt / qty
                        if abs(avg - round(avg)) > 0.01:
                            return int(latest_price_map.get(row['產品全名'], 0))
                        return int(round(avg))

                    s_agg = sub_1yr.groupby('產品全名')[['數量', '金額']].sum().reset_index().sort_values('金額', ascending=False)
                    s_agg['參考單價'] = s_agg.apply(smart_price_single, axis=1)
                    
                    s_agg = s_agg[['產品全名', '數量', '參考單價', '金額']]
                    s_agg['金額'] = s_agg['金額'].round(0)
                    
                    st.dataframe(s_agg, use_container_width=True, hide_index=True, height=500)

    # ==========================================
    # 2. 全店家一年進貨總表 (全台查價)
    # ==========================================
    elif "全店家總表" in analysis_mode:
        st.info("💡 選擇特定業務與店家，系統自動還原近一年的最新拿貨底價。")
        
        one_year_ago = df['OUTDATE'].max() - pd.DateOffset(years=1)
        df_1yr = df[df['OUTDATE'] >= one_year_ago]
        
        if df_1yr.empty:
            st.warning("⚠️ 區間內無資料。")
        else:
            col_f1, col_f2 = st.columns(2)
            
            with col_f1:
                sales_list = ["--- 全部業務 ---"] + sorted(df_1yr['業務員'].astype(str).unique().tolist())
                selected_sales_filter = st.selectbox("👤 1. 請選擇業務：", sales_list)
            
            df_1yr_filtered = df_1yr[df_1yr['業務員'] == selected_sales_filter] if selected_sales_filter != "--- 全部業務 ---" else df_1yr

            with col_f2:
                cust_list = ["--- 全部店家 ---"] + sorted(df_1yr_filtered['店家名稱'].astype(str).unique().tolist())
                selected_cust_filter = st.selectbox("🏪 2. 請選擇店家：", cust_list)
            
            df_1yr_filtered = df_1yr_filtered[df_1yr_filtered['店家名稱'] == selected_cust_filter] if selected_cust_filter != "--- 全部店家 ---" else df_1yr_filtered

            if df_1yr_filtered.empty:
                st.warning("⚠️ 該條件下近一年無紀錄。")
            else:
                latest_records = df_1yr_filtered.sort_values('OUTDATE', ascending=False).drop_duplicates(['店家名稱', '產品全名'])
                latest_records['最新單價'] = (latest_records['金額'] / latest_records['數量']).fillna(0).round(0)
                latest_price_map = latest_records.set_index(['店家名稱', '產品全名'])['最新單價'].to_dict()
                
                def smart_price_multi(row):
                    qty = row['數量']
                    amt = row['金額']
                    if qty <= 0: return 0
                    avg = amt / qty
                    if abs(avg - round(avg)) > 0.01:
                        return int(latest_price_map.get((row['店家名稱'], row['產品全名']), 0))
                    return int(round(avg))

                agg_df = df_1yr_filtered.groupby(['業務員', '店家名稱', '產品全名'])[['數量', '金額']].sum().reset_index()
                agg_df['參考單價'] = agg_df.apply(smart_price_multi, axis=1)
                
                agg_df = agg_df.sort_values(['店家名稱', '金額'], ascending=[True, False])
                agg_df = agg_df[['業務員', '店家名稱', '產品全名', '數量', '參考單價', '金額']]
                agg_df['金額'] = agg_df['金額'].round(0)
                
                st.dataframe(agg_df, use_container_width=True, hide_index=True, height=600)

    # ==========================================
    # 3. 系列分析
    # ==========================================
    elif "系列" in analysis_mode:
        st.info("💡 輸入代碼前綴 (如 BN)，分析該系列總表現")
        c1, c2, c3 = st.columns(3)
        with c1: pre = st.text_input("1. 代碼", "").upper().strip()
        with c2: s = st.number_input("2. 起始號", 1, value=1)
        with c3: e = st.number_input("3. 結束號", 1, value=99)
        if pre:
            mask = (v_df['Prefix'] == pre) & (v_df['ProdNum'] >= s) & (v_df['ProdNum'] <= e)
            sub = v_df[mask]
            if sub.empty: st.warning("❌ 查無資料")
            else:
                st.success(f"✅ 找到 {len(sub)} 筆交易")
                pr_amt = sub.groupby('產品全名')['金額'].sum().reset_index().sort_values('金額', ascending=False)
                
                st.markdown("#### 💰 銷售排行榜")
                fig = px.bar(pr_amt, x='金額', y='產品全名', orientation='h', text_auto='.2s', color='金額', color_continuous_scale='Blues')
                fig.update_layout(yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig, use_container_width=True)

                st.markdown("---")
                selected_prod = st.selectbox("🎯 看單一產品賣給誰：", ["--- 請選擇 ---"] + pr_amt['產品全名'].tolist())
                if selected_prod != "--- 請選擇 ---":
                    prod_df = sub[sub['產品全名'] == selected_prod]
                    buyer_rank = prod_df.groupby('店家名稱')[['數量', '金額']].sum().reset_index().sort_values('數量', ascending=False)
                    st.dataframe(buyer_rank, use_container_width=True, hide_index=True)

    # ==========================================
    # 4. 業務績效深鑽
    # ==========================================
    elif "業務績效" in analysis_mode:
        sales_list = sorted(v_df['業務員'].astype(str).unique())
        selected_sales = st.selectbox("👤 選擇業務員", ["--- 請選擇 ---"] + sales_list)
        
        if selected_sales != "--- 請選擇 ---":
            s_df = v_df[v_df['業務員'] == selected_sales]
            k1, k2 = st.columns(2)
            k1.metric("💰 總結業績", f"${s_df['金額'].sum():,.0f}")
            k2.metric("🏪 成交家數", f"{s_df['店家名稱'].nunique()}")
            
            st.markdown("---")
            cust_opts = s_df.groupby('店家名稱')['金額'].sum().sort_values(ascending=False).index.tolist()
            if cust_opts:
                selected_s_cust = st.selectbox("🔍 深度查帳 (看他賣了什麼給店家)：", ["--- 請選擇 ---"] + cust_opts)
                
                if selected_s_cust != "--- 請選擇 ---":
                    detail_df = s_df[s_df['店家名稱'] == selected_s_cust]
                    
                    t_prod, t_detail = st.tabs(["📦 賣出產品總計", "🧾 單筆歷史紀錄"])
                    with t_prod:
                        prod_summary = detail_df.groupby('產品全名')[['數量', '金額']].sum().reset_index().sort_values('金額', ascending=False)
                        st.dataframe(prod_summary, use_container_width=True, hide_index=True)
                    with t_detail:
                        show_cols = ['日期_CN', 'SOURNO', '產品全名', '數量', '金額']
                        st.dataframe(detail_df[show_cols].sort_values('日期_CN', ascending=False), use_container_width=True, hide_index=True)
            else:
                st.warning("該區間內無成交紀錄。")

    # ==========================================
    # 🌟 5. 業務報價照妖鏡 (精準攤薄算法)
    # ==========================================
    elif "報價照妖鏡" in analysis_mode:
        st.info("💡 系統已自動將「0元搭贈」合併計算真實底價，並排除退貨。一眼看穿誰賣最便宜！")

        agg_quotes = v_df.groupby(['產品全名', '業務員', '店家名稱'])[['金額', '數量']].sum().reset_index()
        valid_quotes = agg_quotes[(agg_quotes['數量'] > 0) & (agg_quotes['金額'] > 0)].copy()

        if valid_quotes.empty:
            st.warning("⚠️ 該區間內無有效交易紀錄。")
        else:
            valid_quotes['真實單價'] = (valid_quotes['金額'] / valid_quotes['數量']).round(1)
            sorted_quotes = valid_quotes.sort_values(['產品全名', '真實單價'], ascending=[True, True])

            min_df = sorted_quotes.drop_duplicates('產品全名', keep='first').rename(
                columns={'真實單價': '最低單價', '業務員': '最低價業務', '店家名稱': '最低價店家'}
            )
            max_df = sorted_quotes.drop_duplicates('產品全名', keep='last').rename(
                columns={'真實單價': '最高單價', '業務員': '最高價業務', '店家名稱': '最高價店家'}
            )

            compare_df = pd.merge(
                min_df[['產品全名', '最低單價', '最低價業務', '最低價店家']],
                max_df[['產品全名', '最高單價', '最高價業務', '最高價店家']],
                on='產品全名'
            )

            compare_df['價差'] = (compare_df['最高單價'] - compare_df['最低單價']).round(1)
            compare_df = compare_df.sort_values('價差', ascending=False)

            search_prod = st.text_input("🔍 搜尋特定產品：", "")
            only_diff = st.checkbox("⚠️ 只顯示有「價差」的產品", value=True)

            if search_prod:
                compare_df = compare_df[compare_df['產品全名'].str.contains(search_prod, case=False, na=False)]
            if only_diff:
                compare_df = compare_df[compare_df['價差'] > 0]

            st.dataframe(compare_df, use_container_width=True, hide_index=True, height=600)