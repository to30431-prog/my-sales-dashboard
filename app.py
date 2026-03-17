import streamlit as st
import pandas as pd
import plotly.express as px
import os
import re
import zipfile

# --- 🎨 頁面設定 ---
st.set_page_config(page_title="峰揚行動查價系統", page_icon="📱", layout="centered", initial_sidebar_state="collapsed")

# --- 💅 CSS 終極大改造 (完全針對手機平板設計) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;700;900&family=Noto+Sans+TC:wght@400;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Nunito', 'Noto Sans TC', sans-serif !important; }
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="collapsedControl"] {display: none;}
    .stApp { background-color: #F8F9FA; color: #333333 !important; }
    .block-container { padding-top: 1rem !important; padding-bottom: 5rem !important; max-width: 800px; }
    
    /* 🌟 APP 化導航列 (橫向果凍按鈕) */
    div.row-widget.stRadio > div { flex-direction: row; flex-wrap: wrap; gap: 6px; justify-content: center; }
    div.row-widget.stRadio > div > label {
        background: #FFFFFF; padding: 8px 12px; border-radius: 18px; border: 1px solid #E0E0E0; cursor: pointer;
        transition: all 0.2s ease; box-shadow: 0 2px 5px rgba(0,0,0,0.02); margin: 0; font-size: 14px;
    }
    div.row-widget.stRadio > div > label[data-checked="true"] {
        background: linear-gradient(135deg, #1ABC9C 0%, #16A085 100%); border: none; color: white !important; box-shadow: 0 4px 10px rgba(26, 188, 156, 0.3);
    }
    div.row-widget.stRadio > div > label[data-checked="true"] * { color: white !important; font-weight: 900 !important; }
    div.row-widget.stRadio > div > label > div:first-child { display: none; }
    
    /* 🌟 數據卡片 (iOS Widget 風格) */
    div[data-testid="stMetric"], div[data-testid="metric-container"] {
        background: #FFFFFF !important; border: none; padding: 15px 10px; border-radius: 16px; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.04); text-align: center;
    }
    div[data-testid="stMetricValue"] div { color: #2C3E50 !important; font-size: 1.5rem !important; font-weight: 900; }
    .streamlit-expanderHeader { background-color: #FFFFFF; border-radius: 12px; font-weight: 700; box-shadow: 0 2px 5px rgba(0,0,0,0.03); }
    .stDataFrame div { font-size: 14px !important; }
    </style>
""", unsafe_allow_html=True)

# --- 🔍 檔案搜尋器 ---
def find_file_recursive(target_names):
    targets_lower = [t.lower() for t in target_names]
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.lower() in targets_lower: return os.path.join(root, file)
    return None

# --- 🔥 數據載入引擎 (修正名片連結邏輯) ---
@st.cache_data(show_spinner="🚀 正在同步進銷存數據...", max_entries=1)
def load_data_final():
    try:
        zip_path = find_file_recursive(['All_Sales_5Years.zip', 'All_Sales_5years.zip'])
        csv_path = find_file_recursive(['All_Sales_5Years.csv', 'All_Sales_2025_2026.csv'])
        
        df = None
        if zip_path:
            with zipfile.ZipFile(zip_path, 'r') as z:
                valid_files = [f for f in z.namelist() if f.lower().endswith('.csv') and not f.startswith('__')]
                if valid_files:
                    with z.open(valid_files[0]) as f:
                        try: df = pd.read_csv(f, encoding='utf-8', low_memory=False)
                        except: df = pd.read_csv(f, encoding='cp950', low_memory=False)
        elif csv_path:
            try: df = pd.read_csv(csv_path, encoding='utf-8', low_memory=False)
            except: df = pd.read_csv(csv_path, encoding='cp950', low_memory=False)
        
        if df is None: return None, "找不到銷貨資料檔"

        df['OUTDATE'] = pd.to_datetime(df['OUTDATE'], format='%Y%m%d', errors='coerce')
        df = df.sort_values('OUTDATE')
        df['日期_CN'] = df['OUTDATE'].dt.strftime('%Y年%m月%d日')
        df['金額'] = pd.to_numeric(df['SUBTOT'], errors='coerce').fillna(0)
        df['數量'] = pd.to_numeric(df['OUTQTY'], errors='coerce').fillna(0)
        
        # 產品解析
        code_col = next((c for c in df.columns if c.upper() in ['IT_NO', 'ITEM_NO', 'CODE']), df.columns[0])
        name_col = next((c for c in df.columns if c.upper() in ['TITLE', 'NAME', 'C_NAME', 'PROD_NAME']), code_col)
        df['產品編號'] = df[code_col].astype(str).str.strip()
        df['產品名稱'] = df[name_col].astype(str).str.strip()
        df['產品全名'] = "[" + df['產品編號'] + "] " + df['產品名稱']

        # 系列解析
        def split_prod_code(code):
            match = re.search(r"([a-zA-Z]+)[\s-]*(\d+)", str(code))
            return (match.group(1).upper(), int(match.group(2))) if match else ("N/A", 0)
        df['Prefix'], df['ProdNum'] = zip(*df['產品編號'].apply(split_prod_code))

        # 客戶代號清洗
        def super_clean(x): return str(x).strip()[:-2] if str(x).strip().endswith('.0') else str(x).strip()
        df['CUST_KEY'] = df['CUST_NO'].apply(super_clean)
        df['SALES_KEY'] = df['SUBNO'].apply(super_clean)
        
        name_map, cust_info_map, cust_id_to_name = {}, {}, {}
        
        # 1. 業務員清單
        lab_path = find_file_recursive(['LABORER.DBF', 'laborer.dbf'])
        if lab_path:
            try:
                from dbfread import DBF
                l_df = pd.DataFrame(iter(DBF(lab_path, encoding='cp950', ignore_missing_memofile=True)))
                id_c = next((c for c in l_df.columns if c.upper() in ['SUBNO', 'S_NO', 'ID']), l_df.columns[0])
                na_c = next((c for c in l_df.columns if c.upper() in ['NAME', 'NAME_C', 'SNAME']), l_df.columns[1])
                l_df['k'] = l_df[id_c].apply(super_clean)
                name_map = l_df.set_index('k')[na_c].to_dict()
            except: pass

        # 2. 客戶名片清單 (修正點：使用 COMPANY 作為主要對應)
        cust_path = find_file_recursive(['CUST.DBF', 'cust.dbf'])
        if cust_path:
            try:
                from dbfread import DBF
                c_df = pd.DataFrame(iter(DBF(cust_path, encoding='cp950', ignore_missing_memofile=True)))
                c_id = next((c for c in c_df.columns if c.upper() in ['CUST_NO', 'CNO', 'ID']), c_df.columns[0])
                # 這裡強制鎖定你截圖中看到的 COMPANY 欄位
                c_na = next((c for c in c_df.columns if c.upper() in ['COMPANY', 'C_NA', 'NAME']), c_df.columns[1])
                
                c_df['clean_k'] = c_df[c_id].apply(super_clean)
                c_df['clean_n'] = c_df[c_na].astype(str).str.strip()
                
                # 建立 ID -> 名稱 的對照表
                cust_id_to_name = c_df.set_index('clean_k')['clean_n'].to_dict()
                
                # 建立 名稱 -> 名片資訊 的對照表
                for _, row in c_df.iterrows():
                    c_name = str(row['clean_n'])
                    tel = next((str(row[c]).strip() for c in c_df.columns if c.upper() in ['TELE1', 'COMP_TEL', 'TEL1'] and str(row[c]).strip() not in ["", "nan"]), "系統無紀錄")
                    add = next((str(row[c]).strip() for c in c_df.columns if c.upper() in ['CARADD', 'SEND_ADDR', 'INVOADD'] and str(row[c]).strip() not in ["", "nan"]), "系統無紀錄")
                    cust_info_map[c_name] = {"電話": tel, "地址": add}
            except: pass

        df['店家名稱'] = df['CUST_KEY'].map(cust_id_to_name).fillna(df['CUST_KEY'])
        df['業務員'] = df['SALES_KEY'].map(name_map).fillna(df['SALES_KEY'])
        return df, cust_info_map

    except Exception as e: return None, str(e)

# --- 啟動解析 ---
res_df, res_info = load_data_final()
if res_df is None: st.error(res_info); st.stop()

# 📱 頂部標題
st.markdown("<h2 style='text-align: center;'>⚡ 峰揚行動查價站</h2>", unsafe_allow_html=True)

# 🚀 導航列
menu_options = ["🏆 營覽", "🔎 查店", "📋 底價", "🎯 系列", "🕵️ 業務"]
analysis_mode = st.radio("選單", menu_options, horizontal=True, label_visibility="collapsed")

# 🚀 時間濾鏡
min_d, max_d = res_df['OUTDATE'].min().date(), res_df['OUTDATE'].max().date()
with st.expander("📅 時間範圍", expanded=False):
    preset = st.selectbox("⏳ 跳轉", ["最近 30 天", "最近 7 天", "本月", "最近 3 個月", "今年 (YTD)", "全部"])
    if preset == "最近 7 天": s_d, e_d = max_d - pd.Timedelta(days=7), max_date = max_d
    elif preset == "最近 30 天": s_d, e_d = max_d - pd.Timedelta(days=30), max_d
    elif preset == "本月": s_d, e_d = max_d.replace(day=1), max_d
    elif preset == "最近 3 個月": s_d, e_d = (pd.to_datetime(max_d) - pd.DateOffset(months=3)).date(), max_d
    elif preset == "今年 (YTD)": s_d, e_d = pd.Timestamp(f"{max_d.year}-01-01").date(), max_d
    else: s_d, e_d = min_d, max_d
    c_s, c_e = st.columns(2)
    sel_s = c_s.date_input("起", value=s_d, min_value=min_d, max_value=max_d)
    sel_e = c_e.date_input("迄", value=e_d, min_value=min_d, max_value=max_d)

v_df = res_df[(res_df['OUTDATE'].dt.date >= sel_s) & (res_df['OUTDATE'].dt.date <= sel_e)]
st.markdown("---")

# --- 功能模組 ---
if "營覽" in analysis_mode:
    c1, c2 = st.columns(2)
    c1.metric("💰 總營收", f"${v_df['金額'].sum():,.0f}")
    c2.metric("📦 出貨(包)", f"{v_df['數量'].sum():,.0f}")
    t_s, t_c = st.tabs(["👑 業務榜", "🏪 店家榜"])
    with t_s:
        sr = v_df.groupby('業務員')['金額'].sum().reset_index().sort_values('金額', ascending=False).head(10)
        fig = px.bar(sr, x='金額', y='業務員', orientation='h', color='金額', text_auto='.2s')
        fig.update_layout(yaxis=dict(autorange="reversed", fixedrange=True), xaxis=dict(fixedrange=True), dragmode=False, height=350, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    with t_c:
        cr = v_df.groupby('店家名稱')['金額'].sum().reset_index().sort_values('金額', ascending=False).head(10)
        fig = px.bar(cr, x='金額', y='店家名稱', orientation='h', color='金額', color_continuous_scale='Oranges', text_auto='.2s')
        fig.update_layout(yaxis=dict(autorange="reversed", fixedrange=True), xaxis=dict(fixedrange=True), dragmode=False, height=350, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

elif "查店" in analysis_mode:
    kw = st.text_input("🔍 店家關鍵字搜尋", "", placeholder="例如：凱爾...")
    f_df = v_df[v_df['店家名稱'].str.contains(kw, na=False)] if kw else v_df
    cust_g = f_df.groupby('店家名稱')['金額'].sum().sort_values(ascending=False).reset_index()
    if cust_g.empty: st.warning("無交易紀錄"); sel = "--"
    else:
        sel_l = st.selectbox("🎯 請確認選擇店家", ["--- 請選擇 ---"] + [f"{x['店家名稱']} (${x['金額']:,.0f})" for _, x in cust_g.iterrows()])
        sel = sel_l.split(' ($')[0] if sel_l != "--- 請選擇 ---" else "--"
    if sel != "--":
        info = res_info.get(sel.strip(), {"電話": "系統無紀錄", "地址": "系統無紀錄"})
        st.markdown(f"""<div style='background: linear-gradient(to right, #ffffff, #f0f9ff); padding:20px; border-radius:15px; border: 1px solid #e1f0fa; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.03);'>
            <h3 style='color:#2980B9; margin-top:0; font-weight:900;'>🏪 {sel}</h3>
            <div style='font-size:1.1rem; line-height:1.8;'>📞 <b>{info['電話']}</b><br>📍 <span style='font-size:0.95rem;'>{info['地址']}</span></div></div>""", unsafe_allow_html=True)
        t1, t2 = st.tabs(["📦 一年底價單", "🧾 歷史明細"])
        with t1:
            sub_1y = res_df[(res_df['店家名稱'] == sel) & (res_df['OUTDATE'] >= (res_df['OUTDATE'].max() - pd.DateOffset(years=1)))]
            if sub_1y.empty: st.info("無紀錄")
            else:
                lat = sub_1y.sort_values('OUTDATE', ascending=False).drop_duplicates('產品全名')
                lat['p'] = (lat['金額'] / lat['數量']).fillna(0).round(0).astype(int)
                lat_m = lat.set_index('產品全名')['p'].to_dict()
                agg = sub_1y.groupby('產品全名')[['數量', '金額']].sum().reset_index().sort_values('金額', ascending=False)
                agg['參考單價'] = agg['產品全名'].map(lat_m)
                st.dataframe(agg[['產品全名', '數量', '參考單價', '金額']], use_container_width=True, hide_index=True)
        with t2:
            og = f_df[f_df['店家名稱'] == sel].groupby(['日期_CN', 'SOURNO'])['金額'].sum().reset_index().sort_values('日期_CN', ascending=False)
            d_sel = st.selectbox("點選看單筆內容", ["--- 請選擇 ---"] + [f"{x['日期_CN']} (單:{x['SOURNO']} / ${x['金額']:,.0f})" for _, x in og.iterrows()])
            if " (單:" in d_sel:
                t_no = d_sel.split('單:')[1].split(' /')[0]
                st.dataframe(f_df[(f_df['SOURNO'].astype(str) == t_no)][['產品全名', '數量', '金額']], use_container_width=True, hide_index=True)

elif "底價" in analysis_mode:
    st.markdown("### 📋 歷史底價總表")
    df_1y = res_df[res_df['OUTDATE'] >= (res_df['OUTDATE'].max() - pd.DateOffset(years=1))]
    c_f1, c_f2 = st.columns(2)
    s_s = c_f1.selectbox("👤 業務", ["-- 全部 --"] + sorted(df_1y['業務員'].unique()))
    df_1y = df_1y[df_1y['業務員'] == s_s] if s_s != "-- 全部 --" else df_1y
    s_c = c_f2.selectbox("🏪 店家", ["-- 全部 --"] + sorted(df_1y['店家名稱'].unique()))
    df_1y = df_1y[df_1y['店家名稱'] == s_c] if s_c != "-- 全部 --" else df_1y
    agg = df_1y.groupby(['業務員', '店家名稱', '產品全名'])[['數量', '金額']].sum().reset_index()
    lat = df_1y.sort_values('OUTDATE', ascending=False).drop_duplicates(['店家名稱', '產品全名'])
    lat['p'] = (lat['金額'] / lat['數量']).fillna(0).round(0)
    lat_m = lat.set_index(['店家名稱', '產品全名'])['p'].to_dict()
    agg['參考單價'] = agg.apply(lambda r: lat_m.get((r['店家名稱'], r['產品全名']), 0), axis=1)
    if len(agg) > 800:
        st.warning("僅顯前 800 筆"); st.dataframe(agg[['業務員', '店家名稱', '產品全名', '數量', '參考單價', '金額']].head(800), use_container_width=True, hide_index=True)
    else: st.dataframe(agg[['業務員', '店家名稱', '產品全名', '數量', '參考單價', '金額']], use_container_width=True, hide_index=True)

elif "系列" in analysis_mode:
    st.markdown("### 🎯 系列產品分析")
    c1, c2 = st.columns(2)
    pre = c1.text_input("代碼", "").upper().strip()
    ran = c2.text_input("範圍", "").strip()
    if pre:
        mask = (v_df['Prefix'] == pre)
        if '-' in ran:
            try: s, e = map(int, ran.split('-')); mask &= (v_df['ProdNum'] >= s) & (v_df['ProdNum'] <= e)
            except: pass
        sub = v_df[mask]
        if sub.empty: st.warning("無資料")
        else:
            pr_agg = sub.groupby('產品全名')['金額'].sum().reset_index().sort_values('金額', ascending=False)
            fig = px.bar(pr_agg, x='金額', y='產品全名', orientation='h', color='金額', text_auto='.2s')
            fig.update_layout(yaxis=dict(autorange="reversed", fixedrange=True), xaxis=dict(fixedrange=True), dragmode=False, height=300, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            sel_p = st.selectbox("🛍️ 選產品追蹤買家", ["--- 請選擇 ---"] + pr_agg['產品全名'].tolist())
            if sel_p != "--- 請選擇 ---":
                st.dataframe(sub[sub['產品全名'] == sel_p].groupby('店家名稱')[['數量', '金額']].sum().sort_values('數量', ascending=False), use_container_width=True, hide_index=True)

elif "業務" in analysis_mode:
    st.markdown("### 🕵️ 業務績效深鑽")
    sel_s = st.selectbox("👤 選擇業務員", ["--- 請選擇 ---"] + sorted(v_df['業務員'].unique()))
    if sel_s != "--- 請選擇 ---":
        s_df = v_df[v_df['業務員'] == sel_s]
        c1, c2 = st.columns(2)
        c1.metric("業績", f"${s_df['金額'].sum():,.0f}")
        c2.metric("店數", f"{s_df['店家名稱'].nunique()}")
        sel_c = st.selectbox("🔍 查看該員成交店家", ["--- 請選擇 ---"] + s_df.groupby('店家名稱')['金額'].sum().sort_values(ascending=False).index.tolist())
        if sel_c != "--- 請選擇 ---":
            t1, t2 = st.tabs(["📦 產品總計", "🧾 單筆歷史"])
            with t1: st.dataframe(s_df[s_df['店家名稱'] == sel_c].groupby('產品全名')[['數量', '金額']].sum().sort_values('金額', ascending=False), use_container_width=True, hide_index=True)
            with t2: st.dataframe(s_df[s_df['店家名稱'] == sel_c][['日期_CN', '產品全名', '數量', '金額']].sort_values('日期_CN', ascending=False), use_container_width=True, hide_index=True)