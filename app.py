# --- 💅 CSS 美學核心 (多巴胺果凍活潑版 + 平板觸控優化 + 列印修復版) ---
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
    
    /* 🌟 導航按鈕 (果凍感) - 適合平板手指點擊 */
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
    
    /* 將 Multiselect 標籤放大 */
    span[data-baseweb="tag"] {
        font-size: 16px !important; padding: 8px 12px !important; margin: 4px !important; background-color: #EBF5FB !important; color: #117A65 !important; border: 2px solid #1ABC9C !important; border-radius: 8px !important;
    }

    /* 🖨️ 列印終極修復設定 (解決空白紙問題) */
    @media print {
        /* 1. 隱藏不必要的按鈕、側邊欄與對話框 */
        [data-testid="stSidebar"], header, footer, .stButton, .print-btn, .stChatInputContainer, [data-testid="stToolbar"] { 
            display: none !important; 
        }
        
        /* 2. 暴力解除 Streamlit 的滾動條與高度限制 (印出空白的元凶) */
        html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"], .main {
            height: auto !important;
            overflow: visible !important;
            position: relative !important;
        }
        
        /* 3. 讓主畫面佔滿 100% 寬度 */
        .main .block-container { 
            max-width: 100% !important; 
            padding: 0 !important; 
            margin: 0 !important; 
        }
        
        /* 4. 防止圖表與表格被從中間切斷 */
        .stPlotlyChart, div[data-testid="stMetric"], .stDataFrame { 
            page-break-inside: avoid !important; 
            break-inside: avoid !important; 
        }
        
        /* 5. 強制印出背景顏色 */
        * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
    }
    </style>
""", unsafe_allow_html=True)