import streamlit as st
import pandas as pd
import plotly.express as px
import os
import re
import zipfile

# --- 🎨 頁面設定 (APP 沉浸模式) ---
st.set_page_config(page_title="峰揚行動查價系統", page_icon="📱", layout="centered", initial_sidebar_state="collapsed")

# --- 💅 CSS 終極大改造 (完全針對手機平板設計) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;700;900&family=Noto+Sans+TC:wght@400;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Nunito', 'Noto Sans TC', sans-serif !important; }
    
    /* 隱藏預設頂部與側邊欄，釋放最大螢幕空間 */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="collapsedControl"] {display: none;}
    
    /* 主畫面底色與間距優化 */
    .stApp { background-color: #F8F9FA; color: #333333 !important; }
    .block-container { padding-top: 1rem !important; padding-bottom: 5rem !important; max-width: 800px; }
    
    /* 🌟 APP 化導航列 (橫向果凍按鈕) */
    div.row-widget.stRadio > div { flex-direction: row; flex-wrap: wrap; gap: 8px; justify-content: center; }
    div.row-widget.stRadio > div > label {
        background: #FFFFFF; padding: 10px 16px; border-radius: 20px; border: 1px solid #E0E0E0; cursor: pointer;
        transition: all 0.2s ease; box-shadow: 0 2px 5px rgba(0,0,0,0.02); margin: 0;
    }
    div.row-widget.stRadio > div > label:hover { transform: scale(1.02); }
    div.row-widget.stRadio > div > label[data-checked="true"] {
        background: linear-gradient(135deg, #1ABC9C 0%, #16A085 100%); border: none; color: white !important; box-shadow: 0 4px 10px rgba(26, 188, 156, 0.3);
    }
    div.row-widget.stRadio > div > label[data-checked="true"] * { color: white !important; font-weight: 900 !important; }
    div.row-widget.stRadio > div > label > div:first-child { display: none; } /* 隱藏原生圓圈 */
    
    /* 🌟 數據卡片 (iOS Widget 風格) */
    div[data-testid="stMetric"], div[data-testid="metric-container"] {
        background: #FFFFFF !important; border: none; padding: 15px 10px; border-radius: 16px; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.04); text-align: center;
    }
    div[data-testid="stMetric"] label { color: #7F8C8D !important; font-size: 0.9rem !important; font-weight: 700; }
    div[data-testid="stMetricValue"] div { color: #2C3E50 !important; font-size: 1.6rem !important; font-weight: 900; }
    
    /* 抽屜 (Expander) 優化 */
    .streamlit-expanderHeader { background-color: #FFFFFF; border-radius: 12px; font-weight: 700; color: #2C3E50; box-shadow: 0 2px 5px rgba(0,0,0,0.03); }
    .streamlit-expanderContent { border: none; padding-top: 10px; }
    
    /* 輸入框變大，好點擊 */
    input, .stSelectbox > div > div { border-radius: 12px !important; padding: 4px 8px !important; }
    
    /* 標題設計 */
    h1, h2, h3 { color: #2C3E50; font-weight: 900; letter-spacing: 0.5px; margin-bottom: 0.5rem; }
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

# --- 🔥 數據載入引擎 (極致記憶體優化版) ---
@st.cache_data(show_spinner="🚀 正在全機掃描並載入數據，請稍候...", max_entries=1)
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
            except Exception as e: return None, f"Zip 讀取失敗: {str(e)}"
        elif csv_path:
            try: df = pd.read_csv(csv_path, encoding='utf-8', low_memory=False)
            except: df = pd.read_csv(csv_path, encoding='cp950', low_memory=False)
        else: return None, "❌ 找不到資料檔 (CSV或ZIP)"

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
                match = re.search(r"([a-zA-Z]{1,4})[\s-]*(\d{1,5})", str(text).strip())
                if match: return f"{match.group(1)}{match.group(2)}"
                return str(text).strip()[:5]
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
                l_df = pd.DataFrame(iter(DBF(lab_path, encoding='cp950', char_decode_errors='ignore', ignore_missing_memofile=True)))
                id_col = next((c for c in l_df.columns if c.upper() in ['SUBNO', 'SNO', 'S_NO', 'ID', 'K_NO']), None)
                name_col = next((c for c in l_df.columns if c.upper() in ['NAME', 'NAME_C', 'L_NAME', 'SNAME']), None)
                if id_col and name_col:
                    l_df['clean_key'] = l_df[id_col].apply(super_clean)
                    name_map = l_df.set_index('clean_key')[name_col].to_dict()
            except: pass

        cust_map, cust_info_map = {}, {}
        cust_path = find_file_recursive(['CUST.DBF', 'cust.dbf', '客戶.DBF'])
        if cust_path:
            try:
                from dbfread import DBF
                c_df = pd.DataFrame(iter(DBF(cust_path, encoding='cp950', char_decode_errors='replace', ignore_missing_memofile=True)))
                c_id_col = next((c for c in c_df.columns if c.upper() in ['CUST_NO', 'CNO', 'C_NO', 'K_NO', 'ID', 'CODE']), None)
                c_na_col = next((c for c in c_df.columns if c.upper() in ['C_NA', 'NAME', 'C_NAME', 'COMPANY', 'CUST_NAME', 'TITLE']), None)
                
                tel_cols = [c for c in c_df.columns if c.upper() in ['TELE1', 'TELE2', 'TEL1', 'TEL2', 'COMP_TEL', 'CON_TEL', 'TEL']]
                addr_cols = [c for c in c_df.columns if c.upper() in ['CARADD', 'INVOADD', 'SEND_ADDR', 'INVOICE_AD', 'C_ADDR1', 'C_ADDR']]
                
                if c_id_col and c_na_col:
                    c_df['clean_key'] = c_df[c_id_col].apply(super_clean)
                    c_df['clean_name'] = c_df[c_na_col].astype(str).str.strip()
                    cust_map = c_df.set_index('clean_key')['clean_name'].to_dict()
                    
                    for _, row in c_df.iterrows():
                        c_name = str(row['clean_name']) 
                        if c_name in ["nan", "None", "NaN", ""]: continue
                        
                        c_tel, c_addr = "系統無紀錄", "系統無紀錄"
                        for t_col in tel_cols:
                            val = str(row[t_col]).strip()
                            if val and val not in ["nan", "None", "NaN", ""]: c_tel = val; break
                        for a_col in addr_cols:
                            val = str(row[a_col]).strip()
                            if val and val not in ["nan", "None", "NaN", ""]: c_addr = val; break
                        cust_info_map[c_name] = {"電話": c_tel, "地址": c_addr}
            except: pass

        df['業務員'] = df['SALES_KEY'].map(name_map).fillna(df['SALES_KEY'])
        mask_sales_fail = df['業務員'] == df['SALES_KEY']
        if mask_sales_fail.any(): df.loc[mask_sales_fail, '業務員'] = df.loc[mask_sales_fail, 'SALES_KEY'].str.zfill(4).map(name_map).fillna(df.loc[mask_sales_fail, 'SALES_KEY'])
        df['店家名稱'] = df['CUST_KEY'].map(cust_map).fillna(df['CUST_KEY'])
        
        return df, cust_info_map

    except Exception as e: return None, str(e)

# --- 啟動解析 ---
result = load_data_final()
if isinstance(result, tuple) and result[0] is None: 
    st.error(f"⚠️ 系統錯誤: {result[1]}"); st.stop()
else:
    df, cust_info_map = result[0], (result[1] if len(result) > 1 else {})

if df is not None:
    
    # 📱 頂部品牌標題 (置中)
    st.markdown("<h2 style='text-align: center;'>⚡ 峰揚行動查價站</h2>", unsafe_allow_html=True)
    
    # 🚀 1. 取代側邊欄：變成頂部橫向 APP 導航列
    menu_options = [
        "🏆 營運總覽", 
        "🔎 店家查帳", 
        "📋 歷史底價表", 
        "🎯 系列分析", 
        "🕵️ 業務深鑽"
    ]
    analysis_mode = st.radio("請選擇工具：", menu_options, horizontal=True, label_visibility="collapsed")
    
    # 🚀 2. 取代側邊欄：變成抽屜式的時間濾鏡 (預設收起，不佔空間)
    min_date, max_date = df['OUTDATE'].min().date(), df['OUTDATE'].max().date()
    
    with st.expander("📅 點此修改時間範圍 (預設: 最近30天)", expanded=False):
        date_preset = st.selectbox("⏳ 快速跳轉", [
            "最近 30 天", "最近 7 天", "本月", "上個月", "最近 3 個月", "最近 6 個月", "今年以來 (YTD)", "全部 5 年"
        ])
        if date_preset == "最近 7 天": start_d, end_d = max_date - pd.Timedelta(days=7), max_date
        elif date_preset == "最近 30 天": start_d, end_d = max_date - pd.Timedelta(days=30), max_date
        elif date_preset == "本月": start_d, end_d = max_date.replace(day=1), max_date
        elif date_preset == "上個月": 
            first_day_this_month = max_date.replace(day=1)
            end_d = first_day_this_month - pd.Timedelta(days=1)
            start_d = end_d.replace(day=1)
        elif date_preset == "最近 3 個月": start_d, end_d = (pd.to_datetime(max_date) - pd.DateOffset(months=3)).date(), max_date
        elif date_preset == "最近 6 個月": start_d, end_d = (pd.to_datetime(max_date) - pd.DateOffset(months=6)).date(), max_date
        elif date_preset == "今年以來 (YTD)": start_d, end_d = pd.Timestamp(f"{max_date.year}-01-01").date(), max_date
        else: start_d, end_d = min_date, max_date
        
        c_start, c_end = st.columns(2)
        with c_start: selected_start = st.date_input("🟢 起", value=start_d, min_value=min_date, max_value=max_date)
        with c_end: selected_end = st.date_input("🔴 迄", value=end_d, min_value=min_date, max_value=max_date)
        if selected_start > selected_end: st.error("⚠️ 起算日不能晚於結尾日喔！")

    # 🔥 防當機核心：切片取資料
    v_df = df[(df['OUTDATE'].dt.date >= selected_start) & (df['OUTDATE'].dt.date <= selected_end)]

    st.markdown("---")

    # ==========================================
    # 🏆 營運總覽 Dashboard
    # ==========================================
    if "營運總覽" in analysis_mode:
        st.markdown(f"<div style='color:#7F8C8D; font-size:0.9rem; text-align:center; margin-bottom:15px;'>📊 統計區間：{selected_start} ~ {selected_end}</div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        c1.metric("💰 總營收", f"${v_df['金額'].sum():,.0f}")
        c2.metric("📦 總出貨(包)", f"{v_df['數量'].sum():,.0f}")
        c3, c4 = st.columns(2)
        c3.metric("🏪 活躍店家", f"{v_df['店家名稱'].nunique()}")
        c4.metric("🧾 訂單數", f"{v_df['SOURNO'].nunique()}")

    # ==========================================
    # 1. 店家查帳 (直覺式上下排列，手機絕佳)
    # ==========================================
    elif "店家查帳" in analysis_mode:
        st.markdown("### 🔎 單一店家查帳")
        kw = st.text_input("1️⃣ 輸入店家關鍵字 (如: 凱爾)", "", placeholder="點此輸入...")
            
        filter_df = v_df[v_df['店家名稱'].str.contains(kw, na=False)] if kw else v_df
        cust_group = filter_df.groupby('店家名稱')['金額'].sum().sort_values(ascending=False).reset_index()
        
        if cust_group.empty:
            st.warning("⚠️ 該區間內無交易紀錄！")
            sel = "--"
        else:
            cust_group['Label'] = cust_group.apply(lambda x: f"{x['店家名稱']} (${x['金額']:,.0f})", axis=1)
            sel_label = st.selectbox("2️⃣ 點選確認店家", ["--- 請選擇 ---"] + cust_group['Label'].tolist())
            sel = sel_label.split(' ($')[0] if sel_label != "--- 請選擇 ---" else "--"
            
        if sel != "--":
            clean_sel = sel.strip()
            info = cust_info_map.get(clean_sel, {"電話": "系統無紀錄", "地址": "系統無紀錄"})
            
            # 🌟 極致美化版聯絡卡片
            st.markdown(f"""
            <div style='background: linear-gradient(to right, #ffffff, #f0f9ff); padding:20px; border-radius:16px; border: 1px solid #e1f0fa; margin: 15px 0 25px 0; box-shadow: 0 8px 20px rgba(0,0,0,0.04);'>
                <h3 style='color:#2980B9; margin-top:0; font-weight:900;'>🏪 {clean_sel}</h3>
                <div style='color:#34495E; font-size:1.05rem; line-height:1.8;'>
                    <span style='display:inline-block; width:25px;'>📞</span> <b>{info['電話']}</b><br>
                    <span style='display:inline-block; width:25px;'>📍</span> <span style='font-size:0.95rem;'>{info['地址']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            sub = df[df['店家名稱'] == sel] 
            
            # 使用 Streamlit 內建的 Tabs 做子頁面切換
            tab_summary, tab_history = st.tabs(["📦 近一年專屬底價單", "🧾 單筆歷史帳單"])
            
            with tab_summary:
                st.caption("💡 自動計算該店近一年的「最新實拿單價」")
                sub_1yr = sub[sub['OUTDATE'] >= (df['OUTDATE'].max() - pd.DateOffset(years=1))]
                
                if sub_1yr.empty:
                    st.info("該店家近一年內無進貨紀錄。")
                else:
                    latest_records = sub_1yr.sort_values('OUTDATE', ascending=False).drop_duplicates('產品全名')
                    latest_records['最新單價'] = (latest_records['金額'] / latest_records['數量']).fillna(0).round(0)
                    latest_price_map = latest_records.set_index('產品全名')['最新單價'].to_dict()
                    
                    def smart_price_single(row):
                        if row['數量'] <= 0: return 0
                        avg = row['金額'] / row['數量']
                        return int(latest_price_map.get(row['產品全名'], 0)) if abs(avg - round(avg)) > 0.01 else int(round(avg))

                    s_agg = sub_1yr.groupby('產品全名')[['數量', '金額']].sum().reset_index().sort_values('金額', ascending=False)
                    s_agg['參考單價'] = s_agg.apply(smart_price_single, axis=1)
                    st.dataframe(s_agg[['產品全名', '數量', '參考單價', '金額']], use_container_width=True, hide_index=True)
                    
            with tab_history:
                sub_time_filtered = filter_df[filter_df['店家名稱'] == sel]
                og = sub_time_filtered.groupby(['日期_CN', 'SOURNO'])['金額'].sum().reset_index().sort_values('日期_CN', ascending=False)
                og['L'] = og.apply(lambda x: f"{x['日期_CN']} (單號:{x['SOURNO']} / ${x['金額']:,.0f})", axis=1)
                
                if og.empty: st.info("該區間內無單筆紀錄。")
                else:
                    d_sel = st.selectbox("點選查看單筆明細", og['L'].tolist())
                    if d_sel:
                        target_date = d_sel.split(' (')[0]
                        target_sourno = d_sel.split('單號:')[1].split(' /')[0].strip() 
                        detail_df = sub_time_filtered[(sub_time_filtered['日期_CN'] == target_date) & (sub_time_filtered['SOURNO'].astype(str).str.strip() == target_sourno)]
                        st.dataframe(detail_df[['產品全名', '數量', '金額']], use_container_width=True, hide_index=True)

    # ==========================================
    # 2. 全店家歷史底價表 (防當機)
    # ==========================================
    elif "歷史底價表" in analysis_mode:
        st.markdown("### 📋 歷史底價還原總表")
        st.caption("為確保手機順暢，請務必先選擇特定的業務或店家。")
        
        df_1yr = df[df['OUTDATE'] >= (df['OUTDATE'].max() - pd.DateOffset(years=1))]
        if df_1yr.empty: st.warning("⚠️ 近一年無資料。")
        else:
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                selected_sales = st.selectbox("1️⃣ 選擇業務", ["-- 全部 --"] + sorted(df_1yr['業務員'].astype(str).unique().tolist()))
            
            df_1yr_f = df_1yr[df_1yr['業務員'] == selected_sales] if selected_sales != "-- 全部 --" else df_1yr

            with col_f2:
                selected_cust = st.selectbox("2️⃣ 選擇店家", ["-- 全部 --"] + sorted(df_1yr_f['店家名稱'].astype(str).unique().tolist()))
            
            df_1yr_f = df_1yr_f[df_1yr_f['店家名稱'] == selected_cust] if selected_cust != "-- 全部 --" else df_1yr_f

            if df_1yr_f.empty: st.warning("⚠️ 該條件無紀錄。")
            else:
                latest_records = df_1yr_f.sort_values('OUTDATE', ascending=False).drop_duplicates(['店家名稱', '產品全名'])
                latest_records['最新單價'] = (latest_records['金額'] / latest_records['數量']).fillna(0).round(0)
                latest_price_map = latest_records.set_index(['店家名稱', '產品全名'])['最新單價'].to_dict()
                
                def smart_price_multi(row):
                    if row['數量'] <= 0: return 0
                    avg = row['金額'] / row['數量']
                    return int(latest_price_map.get((row['店家名稱'], row['產品全名']), 0)) if abs(avg - round(avg)) > 0.01 else int(round(avg))

                agg_df = df_1yr_f.groupby(['業務員', '店家名稱', '產品全名'])[['數量', '金額']].sum().reset_index()
                agg_df['參考單價'] = agg_df.apply(smart_price_multi, axis=1)
                agg_df = agg_df.sort_values(['店家名稱', '金額'], ascending=[True, False])
                
                if len(agg_df) > 800:
                    st.warning(f"⚠️ 資料共 {len(agg_df)} 筆，為防手機當機，僅顯示前 800 筆。")
                    st.dataframe(agg_df[['業務員', '店家名稱', '產品全名', '數量', '參考單價', '金額']].head(800), use_container_width=True, hide_index=True)
                else:
                    st.dataframe(agg_df[['業務員', '店家名稱', '產品全名', '數量', '參考單價', '金額']], use_container_width=True, hide_index=True)

    # ==========================================
    # 3. 系列分析
    # ==========================================
    elif "系列" in analysis_mode:
        st.markdown("### 🎯 系列產品分析")
        c1, c2 = st.columns(2)
        with c1: pre = st.text_input("輸入代碼 (如 BN)", "").upper().strip()
        with c2: s_range = st.text_input("號碼 (如 1-50 或留空)", "").strip()
        
        if pre:
            mask = (v_df['Prefix'] == pre)
            if s_range and '-' in s_range:
                try: 
                    start, end = map(int, s_range.split('-'))
                    mask &= (v_df['ProdNum'] >= start) & (v_df['ProdNum'] <= end)
                except: pass
                
            sub = v_df[mask]
            if sub.empty: st.warning("❌ 查無資料")
            else:
                st.success(f"✅ 找到 {len(sub)} 筆")
                pr_amt = sub.groupby('產品全名')['金額'].sum().reset_index().sort_values('金額', ascending=False)
                st.plotly_chart(px.bar(pr_amt, x='金額', y='產品全名', orientation='h', color='金額').update_layout(yaxis=dict(autorange="reversed"), height=300), use_container_width=True)

    # ==========================================
    # 4. 業務績效深鑽
    # ==========================================
    elif "業務績效" in analysis_mode:
        st.markdown("### 🕵️ 業務績效查核")
        selected_sales = st.selectbox("👤 選擇業務員", ["--- 請選擇 ---"] + sorted(v_df['業務員'].astype(str).unique()))
        
        if selected_sales != "--- 請選擇 ---":
            s_df = v_df[v_df['業務員'] == selected_sales]
            k1, k2 = st.columns(2)
            k1.metric("💰 業績", f"${s_df['金額'].sum():,.0f}")
            k2.metric("🏪 店家數", f"{s_df['店家名稱'].nunique()}")
            
            cust_opts = s_df.groupby('店家名稱')['金額'].sum().sort_values(ascending=False).index.tolist()
            if cust_opts:
                selected_s_cust = st.selectbox("🔍 查核單一店家交易：", ["--- 請選擇 ---"] + cust_opts)
                if selected_s_cust != "--- 請選擇 ---":
                    detail_df = s_df[s_df['店家名稱'] == selected_s_cust]
                    st.dataframe(detail_df[['日期_CN', '產品全名', '數量', '金額']].sort_values('日期_CN', ascending=False), use_container_width=True, hide_index=True)