# ==========================================
# 🚀 App級 UI 重構版（不動資料邏輯）
# ==========================================
if df is not None:

    # 🔷 側邊欄（像App）
    with st.sidebar:
        st.markdown("## 🐶 巴卡洛系統")
        st.caption("營運分析平台")

        menu_options = [
            "🏆 Dashboard", 
            "🔎 店家查帳", 
            "📋 全店家總表", 
            "🎯 系列分析", 
            "🕵️ 業務績效"
        ]
        analysis_mode = st.radio("功能選單", menu_options)

        st.markdown("---")

        # 📅 時間控制（放側邊）
        min_date = df['OUTDATE'].min().date()
        max_date = df['OUTDATE'].max().date()

        date_preset = st.selectbox("時間區間", [
            "最近 7 天","最近 30 天","最近 3 個月",
            "最近 6 個月","今年","去年","全部"
        ], index=3)

        if date_preset == "最近 7 天":
            start_d, end_d = max_date - pd.Timedelta(days=7), max_date
        elif date_preset == "最近 30 天":
            start_d, end_d = max_date - pd.Timedelta(days=30), max_date
        elif date_preset == "最近 3 個月":
            start_d, end_d = (pd.to_datetime(max_date) - pd.DateOffset(months=3)).date(), max_date
        elif date_preset == "最近 6 個月":
            start_d, end_d = (pd.to_datetime(max_date) - pd.DateOffset(months=6)).date(), max_date
        elif date_preset == "今年":
            start_d, end_d = pd.Timestamp(f"{max_date.year}-01-01").date(), max_date
        elif date_preset == "去年":
            start_d, end_d = pd.Timestamp(f"{max_date.year-1}-01-01").date(), pd.Timestamp(f"{max_date.year-1}-12-31").date()
        else:
            start_d, end_d = min_date, max_date

        selected_start = st.date_input("起日", value=start_d)
        selected_end = st.date_input("迄日", value=end_d)

    # 🔷 主畫面 Header
    st.markdown("## 📊 營運儀表板")
    st.caption(f"{selected_start} ～ {selected_end}")

    # 🔥 時間篩選（完全保留你的邏輯）
    time_mask = (df['OUTDATE'].dt.date >= selected_start) & (df['OUTDATE'].dt.date <= selected_end)
    v_df = df[time_mask]

    st.markdown("---")

    # ==========================================
    # 🏆 Dashboard
    # ==========================================
    if "Dashboard" in analysis_mode:

        # KPI（改成一排）
        col1, col2, col3, col4 = st.columns(4)

        col1.metric("營收", f"${v_df['金額'].sum():,.0f}")
        col2.metric("出貨", f"{v_df['數量'].sum():,.0f}")
        col3.metric("店家", f"{v_df['店家名稱'].nunique()}")
        col4.metric("訂單", f"{v_df['SOURNO'].nunique()}")

        st.markdown("### 📈 營收趨勢")

        trend = v_df.groupby('OUTDATE')['金額'].sum().reset_index()
        fig = px.line(trend, x='OUTDATE', y='金額')

        fig.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(l=10, r=10, t=30, b=10)
        )

        st.plotly_chart(fig, use_container_width=True)

    # ==========================================
    # 🔎 店家查帳（UI微調）
    # ==========================================
    elif "店家查帳" in analysis_mode:

        kw = st.text_input("搜尋店家")

        if kw:
            filter_df = v_df[v_df['店家名稱'].str.contains(kw, na=False)]
        else:
            filter_df = v_df

        cust_group = filter_df.groupby('店家名稱')['金額'].sum().sort_values(ascending=False).reset_index()

        if not cust_group.empty:
            sel = st.selectbox("選擇店家", cust_group['店家名稱'])
        else:
            st.warning("無資料")
            sel = None

        if sel:
            st.success(f"目前店家：{sel}")

            sub = df[df['店家名稱'] == sel]

            tab1, tab2 = st.tabs(["歷史紀錄", "一年報價"])

            with tab1:
                sub_time_filtered = filter_df[filter_df['店家名稱'] == sel]
                og = sub_time_filtered.groupby(['日期_CN', 'SOURNO'])['金額'].sum().reset_index()

                st.dataframe(og, use_container_width=True)

            with tab2:
                one_year_ago = df['OUTDATE'].max() - pd.DateOffset(years=1)
                sub_1yr = sub[sub['OUTDATE'] >= one_year_ago]

                s_agg = sub_1yr.groupby('產品全名')[['數量', '金額']].sum().reset_index()

                st.dataframe(s_agg, use_container_width=True)

    # ==========================================
    # 📋 全店家
    # ==========================================
    elif "全店家總表" in analysis_mode:

        st.dataframe(v_df.head(500), use_container_width=True)

    # ==========================================
    # 🎯 系列分析
    # ==========================================
    elif "系列分析" in analysis_mode:

        pre = st.text_input("代碼")
        if pre:
            sub = v_df[v_df['Prefix'] == pre]

            fig = px.bar(sub.groupby('產品全名')['金額'].sum().reset_index(),
                         x='金額', y='產品全名', orientation='h')

            st.plotly_chart(fig, use_container_width=True)

    # ==========================================
    # 🕵️ 業務績效
    # ==========================================
    elif "業務績效" in analysis_mode:

        sales = st.selectbox("選業務", v_df['業務員'].unique())

        s_df = v_df[v_df['業務員'] == sales]

        col1, col2 = st.columns(2)
        col1.metric("業績", f"${s_df['金額'].sum():,.0f}")
        col2.metric("店家數", f"{s_df['店家名稱'].nunique()}")

        st.dataframe(s_df.head(300), use_container_width=True)
