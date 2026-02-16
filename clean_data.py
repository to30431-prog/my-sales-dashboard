import pandas as pd
from dbfread import DBF, FieldParser
import os
import sys

# 定義防彈解析器 (防止舊資料格式錯誤導致當機)
class SafeParser(FieldParser):
    def parse(self, field, data):
        try:
            return super().parse(field, data)
        except ValueError:
            return 0
        except Exception:
            return None

FILE_NAME = 'SALER2.DBF'
OUTPUT_NAME = 'All_Sales_5Years.csv'  # <--- 檔名改成這個，對應剛才的戰情室程式

print("🚀 正在啟動「全公司 5 年數據」濾網...")
print("👉 目標：抓取 2020/01/01 至今，所有業務員的業績")
print("⚠️ 注意：因為資料量變大，這次掃描會比較久，請耐心等待...")

if not os.path.exists(FILE_NAME):
    print(f"❌ 錯誤：找不到 {FILE_NAME}")
    sys.exit()

try:
    table = DBF(
        FILE_NAME, 
        encoding='cp950', 
        char_decode_errors='ignore', 
        ignore_missing_memofile=True,
        parserclass=SafeParser
    )
    
    data = []
    print(f"📂 正在掃描 {FILE_NAME} (這可能會花幾分鐘)...")
    
    count = 0
    match_count = 0
    
    for i, record in enumerate(table):
        if i % 100000 == 0 and i > 0:
            print(f"   已掃描 {i} 筆原始資料... (目前找到 {match_count} 筆符合條件)")
            
        try:
            # 抓取日期欄位
            outdate = str(record.get('OUTDATE', ''))
            
            # --- 關鍵修改 ---
            # 只要是 2020 年 1 月 1 日以後的單，全部都要！
            if outdate >= '20200101':
                data.append(record)
                match_count += 1
                
        except Exception:
            continue

    if data:
        print(f"📊 正在轉存 CSV (這步最吃記憶體，請稍候)...")
        df = pd.DataFrame(data)
        df.to_csv(OUTPUT_NAME, index=False, encoding='utf-8-sig')
        print(f"\n✅ 大功告成！已抓出 2020-2026 共 {len(df)} 筆資料")
        print(f"📁 檔案名稱：{OUTPUT_NAME}")
        print("👉 請把這個 CSV 檔案丟進您的「公司戰情室」資料夾，取代舊檔！")
    else:
        print("\n⚠️ 奇怪，沒有找到 2020 年後的資料。")

except Exception as e:
    print(f"\n❌ 發生錯誤：{e}")

os.system("pause")