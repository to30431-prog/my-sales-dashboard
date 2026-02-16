import streamlit as st
import pandas as pd
import plotly.express as px
import os
import re
import zipfile
import streamlit.components.v1 as components

# --- 🎨 頁面設定 ---
st.set_page_config(page_title="企業數位戰情室 (雲端旗艦版)", page_icon="📈", layout="wide")

# --- 💅 CSS 美學核心 ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Microsoft JhengHei', 'Noto Sans TC', sans-serif; }
    
    /* KPI 卡片優化 */
    div[data-testid="stMetric"], div[data-testid="metric-container"] {
        background-color: #FFFFFF; border: 1px solid #E0E0E0; padding: 15px; border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); color: #333; transition: transform 0.2s;
    }
    div[data-testid="stMetric"]:hover { transform: translateY(-3px); box-shadow: 0 8px 15px rgba(0,0,0,0.1); border-color: #B0B0B0; }
    
    /* 側邊欄 */
    [data-testid="stSidebar"] { background-color: #F8F9FA; border-right: 1px solid #E0E0E0; }
    
    /* 列印設定 */
    @media print {
        [data-testid="stSidebar"], header, footer, .stButton, .print-btn { display: none !important; }
        .main .block-container { max-width: 100% !important; padding: 0 !important; margin: 0 !important; }
        .stPlotlyChart { display: block !important; break-inside: avoid !important; width: 100% !important; }
        div[data-testid="stMetric"] { border: 1px solid #000 !important; box-shadow: none !important; }
        * { -webkit-print-color-adjust: exact !important; }
    }
    </style>
""", unsafe_allow_html=True)

# --- 🔍 核彈級檔案搜尋器 (不管檔案藏在哪一層資料夾，都能找到) ---
def find_file_recursive(target_names):
    # 轉成小寫方便比對
    targets_lower = [t.lower() for t in target_names]
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.lower() in targets_lower:
                return os.path.join(root, file)
    return None

# --- 🔥 AI 數據載入引擎 ---
@st.cache_data(show_spinner="🚀 正在全機掃描並載入數據，請稍候...")
def load_data_final():
    try:
        # 1. 搜尋主資料檔 (ZIP 或 CSV)
        zip_path = find_file_recursive(['All_Sales_5Years.zip', 'All_Sales_5years.zip', 'all_sales_5years.zip'])
        csv_path = find_file_recursive(['All_Sales_5Years.csv'])
        
        df = None
        
        # A. 優先讀取 ZIP
        if zip_path:
            try:
                with zipfile.ZipFile(zip_path, 'r') as z:
                    # 找出 ZIP 裡唯一的 CSV (忽略 macOS 隱藏檔)
                    valid_files = [f for f in z.namelist() if f.lower().endswith('.csv') and not f.startswith('__')]
                    if valid_files:
                        target_csv = valid_files[0]
                        with z.open(target_csv) as f:
                            try: df = pd.read_csv(f, encoding='utf-8', low_memory=False)
                            except: df = pd.read_csv(f, encoding='cp950', low_memory=False)
            except Exception as e:
                return None, f"Zip 讀取失敗: {str(e)}", {}
        
        # B. 備案：讀取 CSV
        elif csv_path:
            try: df = pd.read_csv(csv_path, encoding='utf-8', low_memory=False)
            except: df = pd.read_csv(csv_path, encoding='cp950', low_memory=False)
            
        else:
            return None, "❌ 找不到資料檔 (請確認 GitHub 上有 All_Sales_5Years.zip)", {}

        # --- 數據清洗 ---
        if df is None: return None, "讀取後資料為空", {}

        df['OUTDATE'] = pd.to_datetime(df['OUTDATE'], format='%Y%m%d', errors='coerce')
        df = df.sort_values('OUTDATE')
        df['日期_CN'] = df['OUTDATE'].dt.strftime('%Y年%m月%d日')
        df['金額'] = pd.to_numeric(df['SUBTOT'], errors='coerce').fillna(0)
        df['數量'] = pd.to_numeric(df['OUTQTY'], errors='coerce').fillna(0)
        
        # 產品編號偵測
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

        # 品名偵測
        title_candidates = [c for c in df.columns if c.upper() in ['TITLE', 'NAME', 'PROD_NAME', 'DESCRIPTION', 'C_NAME']]
        best_name_col = title_candidates[0] if title_candidates else best_code_col
        if best_name_col: df['產品名稱'] = df[best_name_col].astype(str)
        else: df['產品名稱'] = df['產品編號']
        df['產品全名'] = "[" + df['產品編號'] + "] " + df['產品名稱']

        # 系列拆解
        def split_prod_code(code):
            match = re.search(r"([a-zA-Z]+)[\s-]*(\d+)", str(code))
            return (match.group(1).upper(), int(match.group(2))) if match else ("N/A", 0)
        df['Prefix'], df['ProdNum'] = zip(*df['產品編號'].apply(split_prod_code))

        # ID 清洗
        def super_clean(x):
            if pd.isna(x): return "None"
            s = str(x).strip()
            if s.endswith('.0'): s = s[:-2]
            return s
        df['CUST_KEY'] = df['CUST_NO'].apply(super_clean)
        df['SALES_KEY'] = df['SUBNO'].apply(super_clean)

        # ==========================================
        # 2. 智慧讀取 DBF (搜尋所有可能的檔名)
        # ==========================================
        
        # --- 成本檔 (STOCK) ---
        cost_map = {}
        stock_path = find_file_recursive(['STOCK.DBF', 'stock.dbf', '股票代號 : DBF', '股票代號.DBF'])
        
        if stock_path:
            try:
                from dbfread import DBF
                s_table = DBF(stock_path, encoding='cp950', char_decode_errors='ignore', ignore_missing_memofile=True)
                s_df = pd.DataFrame(iter(s_table))
                p_col = next((c for c in s_df.columns if c.upper() in ['PART_NO', 'ITEM_NO', 'P_NO']), None)
                c_col = next((c for c in s_df.columns if c.upper() in ['VECOST', 'LSCOST', 'OLDCOST', 'STD_COST', 'COST']), None)
                if p_col and c_col:
                    s_df['key'] = s_df[p_col].astype(str).str.strip()
                    s_df['cost'] = pd.to_numeric(s_df[c_col], errors='coerce').fillna(0)
                    cost_map = s_df.set_index('key')['cost'].to_dict()
            except: pass
        
        df['單一成本'] = df['產品編號'].map(cost_map).fillna(0)
        df['總成本'] = df['單一成本'] * df['數量']
        df['毛利'] = df['金額'] - df['總成本']
        
        # --- 業務檔 (LABORER) ---
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

        # --- 客戶檔 (CUST) ---
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

        # 應用對照表
        df['業務員'] = df['SALES_KEY'].map(name_map).fillna(df['SALES_KEY'])
        mask_sales_fail = df['業務員'] == df['SALES_KEY']
        if mask_sales_fail.any():
             df.loc[mask_sales_fail, '業務員'] = df.loc[mask_sales_fail, 'SALES_KEY'].str.zfill(4).map(name_map).fillna(df.loc[mask_sales_fail, 'SALES_KEY'])
        df['店家名稱'] = df['CUST_KEY'].map(cust_map).fillna(df['CUST_KEY'])
        
        return df, cost_map

    except Exception as e:
        return None, str(e), {}

# 載入
result = load_data_final()
if result[0] is not None: df, cost_map = result
else: st.error(f"⚠️ 系統錯誤: {result[1]}"); st.stop()

if df is not None:
    # --- 側邊欄 ---
    with st.sidebar:
        st.title("🎛️ 戰情室中控台")
        st.image("https://cdn-icons-png.flaticon.com/512/3094/3094851.png", width=50) 
        st.write(f"📊 總資料筆數: {len(df):,}")
        
        analysis_mode = st.radio("請選擇視角：", [
            "🏆 營運總覽 Dashboard", 
            "🔎 店家查帳 (查進貨)", 
            "🎯 精準系列分析 (查產品)", 
            "🕵️‍♀️ 業務績效深鑽 (查人)", 
            "💰 毛利與淨利精算 (查錢)"
        ])
        
        st.markdown("---")
        st.header("📅 日期時間軸")
        min_date = df['OUTDATE'].min().date()
        max_date = df['OUTDATE'].max().date()
        
        date_preset = st.selectbox("⏳ 快速時間跳轉", ["最近 30 天", "今年以來 (YTD)", "去年全年度", "近 3 年", "全部 5 年"])
        if date_preset == "最近 30 天": start_d, end_d = max_date - pd.Timedelta(days=30), max_date
        elif date_preset == "今年以來 (YTD)": start_d, end_d = pd.Timestamp(f"{max_date.year}-01-01").date(), max_date
        elif date_preset == "去年全年度": start_d, end_d = pd.Timestamp(f"{max_date.year-1}-01-01").date(), pd.Timestamp(f"{max_date.year-1}-12-31").date()
        elif date_preset == "近 3 年": start_d, end_d = max_date - pd.Timedelta(days=365*3), max_date
        else: start_d, end_d = min_date, max_date
        
        date_range = st.date_input("🗓️ 自訂精確範圍", [start_d, end_d], min_value=min_date, max_value=max_date)

    v_df = df.copy()
    if len(date_range) == 2:
        v_df = v_df[(v_df['OUTDATE'].dt.date >= date_range[0]) & (v_df['OUTDATE'].dt.date <= date_range[1])]

    # 頂部標題
    col_t, col_p = st.columns([8,1])
    with col_t: 
        st.markdown(f"## {analysis_mode}")
        st.caption(f"數據範圍：{date_range[0]} 至 {date_range[1]}")
    with col_p: 
        components.html("""<button class="print-btn" onclick="window.print()" style="background:#2C3E50;color:white;border:none;padding:10px 15px;border-radius:8px;cursor:pointer;font-weight:bold;">🖨️ 列印報表</button>""", height=60)

    # ==========================================
    # 🏆 營運總覽 Dashboard
    # ==========================================
    if "營運總覽" in analysis_mode:
        st.markdown("### 📊 關鍵績效指標 (KPI)")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💰 區間總營收", f"${v_df['金額'].sum():,.0f}", delta="營收總額", delta_color="normal")
        c2.metric("📦 總出貨包數", f"{v_df['數量'].sum():,.0f}", delta="銷售力度", delta_color="off")
        c3.metric("🏪 成交店數", f"{v_df['店家名稱'].nunique()}", delta="活躍客戶")
        c4.metric("🧾 成交單數", f"{v_df['SOURNO'].nunique()}", delta="交易熱度")
        st.markdown("---")
        
        days_diff = (date_range[1] - date_range[0]).days if len(date_range) == 2 else 0
        if days_diff > 365:
            v_df['年月'] = v_df['OUTDATE'].dt.strftime('%Y-%m')
            fig_trend = px.bar(v_df.groupby('年月')['金額'].sum().reset_index(), x='年月', y='金額', title="📈 月營收趨勢 (長期)", color_discrete_sequence=['#F39C12'])
        else:
            daily = v_df.groupby('日期_CN')['金額'].sum().reset_index()
            daily['SD'] = pd.to_datetime(daily['日期_CN'], format='%Y年%m月%d日')
            fig_trend = px.area(daily.sort_values('SD'), x='日期_CN', y='金額', title="📈 日營收趨勢 (短期)", color_discrete_sequence=['#F39C12'])
        st.plotly_chart(fig_trend, use_container_width=True)
        
        c_L, c_R = st.columns(2)
        with c_L:
            st.subheader("👑 業務戰神榜")
            sr = v_df.groupby('業務員')['金額'].sum().reset_index().sort_values('金額', ascending=False).head(10)
            fig = px.bar(sr, x='金額', y='業務員', orientation='h', text_auto='.2s', color='金額', color_continuous_scale='Blues')
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)
        with c_R:
            st.subheader("🏪 店家貢獻榜")
            cr = v_df.groupby('店家名稱')['金額'].sum().reset_index().sort_values('金額', ascending=False).head(10)
            fig = px.bar(cr, x='金額', y='店家名稱', orientation='h', text_auto='.2s', color='金額', color_continuous_scale='Oranges')
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("🔥 熱銷產品 Top 15")
        pr = v_df.groupby('產品全名')[['金額', '數量']].sum().reset_index().sort_values('金額', ascending=False).head(15)
        fig_p = px.bar(pr, x='金額', y='產品全名', orientation='h', text_auto='.2s', color='金額', color_continuous_scale='Greens')
        fig_p.update_layout(yaxis=dict(autorange="reversed"), height=600)
        st.plotly_chart(fig_p, use_container_width=True)

    # ==========================================
    # 1. 店家查帳
    # ==========================================
    elif "店家查帳" in analysis_mode:
        st.info("💡 輸入店家名稱關鍵字，快速調閱進貨歷史")
        kw = st.sidebar.text_input("🔍 搜尋店家", "")
        if kw: v_df = v_df[v_df['店家名稱'].str.contains(kw, na=False)]
        cL, cR = st.columns([1,2])
        with cL:
            st.markdown("### 📋 店家列表")
            cust_group = v_df.groupby('店家名稱')['金額'].sum().sort_values(ascending=False).reset_index()
            cust_group['Label'] = cust_group.apply(lambda x: f"{x['店家名稱']} (${x['金額']:,.0f})", axis=1)
            opts = cust_group['Label'].tolist()
            sel_label = st.selectbox("請選擇店家", ["--- 請選擇 ---"] + opts)
            sel = sel_label.split(' ($')[0] if sel_label != "--- 請選擇 ---" else "--"
            if sel != "--":
                amt = v_df[v_df['店家名稱'] == sel]['金額'].sum()
                st.success(f"已選擇：**{sel}**")
                st.metric("該店區間總額", f"${amt:,.0f}")
        with cR:
            if sel != "--":
                st.markdown(f"### 🧾 {sel} 進貨紀錄")
                sub = v_df[v_df['店家名稱'] == sel]
                og = sub.groupby(['日期_CN', 'SOURNO'])['金額'].sum().reset_index().sort_values('日期_CN', ascending=False)
                og['L'] = og.apply(lambda x: f"{x['日期_CN']} (金額: ${x['金額']:,.0f})", axis=1)
                d_sel = st.selectbox("選擇進貨單", og['L'].tolist())
                if d_sel:
                    target_date = d_sel.split(' (')[0]
                    detail_df = sub[sub['日期_CN'] == target_date][['產品全名', '數量', '金額']]
                    st.dataframe(detail_df, use_container_width=True)

    # ==========================================
    # 2. 系列分析
    # ==========================================
    elif "系列分析" in analysis_mode:
        st.info("💡 輸入產品代碼前綴 (例如: BN)，分析整個系列的表現")
        c1, c2, c3 = st.columns(3)
        with c1: pre = st.text_input("1. 代碼 (如 BN)", "").upper().strip()
        with c2: s = st.number_input("2. 起始號", 1, value=1)
        with c3: e = st.number_input("3. 結束號", 1, value=99)
        if pre:
            mask = (v_df['Prefix'] == pre) & (v_df['ProdNum'] >= s) & (v_df['ProdNum'] <= e)
            sub = v_df[mask]
            if sub.empty: st.warning("❌ 查無資料，請確認代碼是否正確。")
            else:
                st.success(f"✅ 成功鎖定 **{pre} 系列** (共 {len(sub)} 筆交易)")
                t1, t2 = st.tabs(["💰 銷售金額 ($)", "📦 銷售數量 (包)"])
                pr_amt = sub.groupby('產品全名')['金額'].sum().reset_index().sort_values('金額', ascending=False)
                pr_qty = sub.groupby('產品全名')['數量'].sum().reset_index().sort_values('數量', ascending=False)
                with t1:
                    fig = px.bar(pr_amt, x='金額', y='產品全名', orientation='h', text_auto='.2s', color='金額', color_continuous_scale='Blues')
                    fig.update_layout(yaxis=dict(autorange="reversed"))
                    st.plotly_chart(fig, use_container_width=True)
                with t2:
                    fig2 = px.bar(pr_qty, x='數量', y='產品全名', orientation='h', text_auto='.0f', color='數量', color_continuous_scale='Greens')
                    fig2.update_layout(yaxis=dict(autorange="reversed"))
                    st.plotly_chart(fig2, use_container_width=True)

    # ==========================================
    # 3. 業務績效深鑽
    # ==========================================
    elif "業務績效" in analysis_mode:
        sales_list = sorted(v_df['業務員'].astype(str).unique())
        c_search, c_sel = st.columns([1, 2])
        with c_search:
            search_sales = st.text_input("🔍 搜尋姓名", "")
            if search_sales: sales_list = [s for s in sales_list if search_sales in s]
        with c_sel:
            selected_sales = st.selectbox("選擇業務員", ["--- 請選擇 ---"] + sales_list)
        if selected_sales != "--- 請選擇 ---":
            s_df = v_df[v_df['業務員'] == selected_sales]
            st.markdown(f"### 👤 {selected_sales} 個人戰情板")
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("💰 個人業績", f"${s_df['金額'].sum():,.0f}")
            k2.metric("📦 銷售包數", f"{s_df['數量'].sum():,.0f}")
            k3.metric("🏪 成交家數", f"{s_df['店家名稱'].nunique()}")
            k4.metric("🛍️ 產品款數", f"{s_df['產品全名'].nunique()}")
            st.markdown("---")
            col_cust, col_prod = st.columns(2)
            with col_cust:
                st.markdown("#### 🏪 他的主力客戶")
                cust_rank = s_df.groupby('店家名稱')['金額'].sum().reset_index().sort_values('金額', ascending=False).head(20)
                fig_c = px.bar(cust_rank, x='金額', y='店家名稱', orientation='h', text_auto='.2s', color='金額', color_continuous_scale='Oranges')
                fig_c.update_layout(yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig_c, use_container_width=True)
            with col_prod:
                st.markdown("#### 🛍️ 他的主力產品")
                prod_rank = s_df.groupby('產品全名')['金額'].sum().reset_index().sort_values('金額', ascending=False).head(20)
                fig_p = px.bar(prod_rank, x='金額', y='產品全名', orientation='h', text_auto='.2s', color='金額', color_continuous_scale='Greens')
                fig_p.update_layout(yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig_p, use_container_width=True)

    # ==========================================
    # 4. 毛利與淨利精算
    # ==========================================
    elif "毛利與淨利" in analysis_mode:
        total_rev = v_df['金額'].sum()
        total_qty = v_df['數量'].sum()
        total_product_cost = v_df['總成本'].sum()
        gross_profit = total_rev - total_product_cost
        gp_margin = (gross_profit / total_rev * 100) if total_rev > 0 else 0
        
        st.markdown("### 💰 獲利結構精算表")
        if total_product_cost == 0:
            st.warning("⚠️ 成本資料為 0！請確認 GitHub 上是否有上傳 `STOCK.DBF` (或 `股票代號 : DBF`)。")
            
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("1️⃣ 總營收 (Revenue)", f"${total_rev:,.0f}", delta="收入來源")
        col_m2.metric("2️⃣ 商品成本 (COGS)", f"${total_product_cost:,.0f}", delta="銷貨成本", delta_color="inverse")
        col_m3.metric("3️⃣ 商品毛利 (Gross Profit)", f"${gross_profit:,.0f}", f"毛利率 {gp_margin:.1f}%")
        st.markdown("---")
        
        with st.container():
            st.markdown("""<div style="background-color:#F8F9FA; padding:20px; border-radius:10px; border-left: 5px solid #2ECC71;"><h3 style="margin:0; color:#2C3E50;">🧮 淨利試算機 (Net Profit Calculator)</h3><p style="color:#7F8C8D;">請輸入您的營業費用，系統將自動計算最終獲利。</p></div>""", unsafe_allow_html=True)
            st.write("")
            num_months = (v_df['OUTDATE'].max().year - v_df['OUTDATE'].min().year) * 12 + v_df['OUTDATE'].max().month - v_df['OUTDATE'].min().month + 1
            if num_months < 1: num_months = 1
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("#### 🔻 變動支出 (包裝耗材)")
                pack_unit_cost = st.number_input("平均每包耗材成本 (元)", value=2.5, step=0.1)
                total_pack_cost = total_qty * pack_unit_cost
                st.caption(f"計算：{total_qty:,.0f} 包 x ${pack_unit_cost} = **${total_pack_cost:,.0f}**")
            with c2:
                st.markdown("#### 🔻 固定支出 (房租人事)")
                monthly_fixed = st.number_input("每月固定開銷 (元)", value=500000, step=10000)
                total_fixed_cost = monthly_fixed * num_months
                st.caption(f"計算：${monthly_fixed:,.0f} x {num_months} 個月 = **${total_fixed_cost:,.0f}**")
            
            net_profit = gross_profit - total_pack_cost - total_fixed_cost
            net_margin = (net_profit / total_rev * 100) if total_rev > 0 else 0
            
            if net_profit > 0:
                res_color = "#27AE60"; res_bg = "#E8F8F5"; res_emoji = "🎉 恭喜獲利！"
            else:
                res_color = "#C0392B"; res_bg = "#FDEDEC"; res_emoji = "⚠️ 注意虧損！"
                
            st.markdown(f"""<div style="margin-top:20px; background-color: {res_bg}; border: 2px solid {res_color}; padding: 25px; border-radius: 15px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.1);"><h4 style="color: {res_color}; margin:0;">{res_emoji} 稅前淨利</h4><h1 style="color: {res_color}; margin:10px 0; font-size: 3em;">${net_profit:,.0f}</h1><h3 style="color: #555;">淨利率：{net_margin:.1f}%</h3><div style="display: flex; justify-content: center; gap: 15px; margin-top: 15px; color: #7F8C8D; font-size: 0.9em;"><span>商品毛利: ${gross_profit:,.0f}</span> • <span>包材費: -${total_pack_cost:,.0f}</span> • <span>固定開銷: -${total_fixed_cost:,.0f}</span></div></div>""", unsafe_allow_html=True)
            
        st.markdown("---")
        tab1, tab2 = st.tabs(["💎 賺錢金雞母 (高毛利)", "💣 賠錢貨警示 (低毛利)"])
        prod_gp = v_df.groupby('產品全名')[['金額', '毛利']].sum().reset_index()
        prod_gp['毛利率'] = (prod_gp['毛利'] / prod_gp['金額'] * 100).fillna(0)
        with tab1:
            top_gp = prod_gp.sort_values('毛利', ascending=False).head(20)
            fig_tg = px.bar(top_gp, x='毛利', y='產品全名', orientation='h', title="高毛利產品 Top 20", text_auto='.2s', color='毛利', color_continuous_scale='Greens')
            fig_tg.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig_tg, use_container_width=True)
        with tab2:
            low_gp = prod_gp[prod_gp['金額'] > 5000].sort_values('毛利率', ascending=True).head(20)
            fig_lg = px.bar(low_gp, x='毛利率', y='產品全名', orientation='h', title="低毛利/虧損產品 Top 20", text_auto='.1f', color='毛利率', color_continuous_scale='RdYlGn')
            st.plotly_chart(fig_lg, use_container_width=True)