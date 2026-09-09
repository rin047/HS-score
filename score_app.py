import io
import gspread
from google.oauth2.service_account import Credentials
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib import rcParams
import numpy as np
import pandas as pd
import streamlit as st

# 設定字型避免中文亂碼
rcParams["font.sans-serif"] = ["Microsoft JhengHei", "Arial", "sans-serif"]
rcParams["axes.unicode_minus"] = False

st.set_page_config(page_title="國中英數自成績登記與 A3 報表系統", layout="wide")

# 連線 Google 試算表設定
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


@st.cache_resource
def init_gspread_client():
  credentials = Credentials.from_service_account_info(
      st.secrets["gcp_service_account"], scopes=SCOPES
  )
  return gspread.authorize(credentials)


try:
  gc = init_gspread_client()
  sh = gc.open("學生成績總表")
  cloud_connected = True
except Exception as e:
  cloud_connected = False
  st.warning(f"⚠️ 連線至 Google 試算表失敗：{e}")

st.title("📊 國中成績登記與 A3 PDF 報表雲端系統")

# 頂部選擇區
col_year, col_month, col_grade, col_subject = st.columns(4)
with col_year:
  selected_year = st.selectbox(
      "選擇年份", ["2024年", "2025年", "2026年", "2027年"], index=2
  )
with col_month:
  selected_month = st.selectbox(
      "選擇月份", [f"{i}月" for i in range(1, 13)], index=7
  )
with col_grade:
  selected_grade = st.selectbox("選擇年級", ["國一", "國二", "國三"], index=1)
with col_subject:
  selected_subject = st.selectbox("選擇科目", ["英文", "數學", "自然"], index=2)

exam_cols = [f"第{i}次測驗" for i in range(1, 9)]
sheet_name = f"{selected_year}_{selected_month}_{selected_grade}_{selected_subject}"

# 從 Google 試算表讀取資料或初始化
if cloud_connected:
  try:
    worksheet = sh.worksheet(sheet_name)
    data_list = worksheet.get_all_records()
    if data_list:
      current_df = pd.DataFrame(data_list)
    else:
      current_df = pd.DataFrame(
          columns=["姓名"] + exam_cols,
          data=[["範例學生1", "", "", "", "", "", "", "", ""]],
      )
  except:
    worksheet = sh.add_worksheet(title=sheet_name, rows="100", cols="20")
    current_df = pd.DataFrame(
        columns=["姓名"] + exam_cols,
        data=[["範例學生1", "", "", "", "", "", "", "", ""]],
    )
    worksheet.update(
        [current_df.columns.values.tolist()] + current_df.values.tolist()
    )
else:
  if sheet_name not in st.session_state:
    st.session_state[sheet_name] = pd.DataFrame(
        columns=["姓名"] + exam_cols,
        data=[["範例學生1", "", "", "", "", "", "", "", ""]],
    )
  current_df = st.session_state[sheet_name]

st.subheader(f"📅 目前編輯報表：{selected_year}{selected_month} {selected_grade}{selected_subject}")

# 確保成績欄位為數字或空值
for col in exam_cols:
  if col not in current_df.columns:
    current_df[col] = ""
  else:
    current_df[col] = pd.to_numeric(current_df[col], errors="coerce")

if not current_df.empty:
  current_df["總分"] = current_df[exam_cols].sum(axis=1, min_count=1)
  current_df["平均"] = current_df[exam_cols].mean(axis=1).round(2)
  current_df["排名"] = current_df["總分"].rank(
      ascending=False, method="min", na_option="bottom"
  )
  current_df["排名"] = current_df["排名"].fillna(0).astype(int)
  cols_order = ["排名", "姓名"] + exam_cols + ["總分", "平均"]
  current_df = current_df[cols_order].sort_values(by="排名", ascending=True)

updated_df = st.data_editor(
    current_df,
    num_rows="dynamic",
    hide_index=True,
    use_container_width=True,
    key=f"editor_{sheet_name}",
)

# 儲存按鈕：點擊後寫回 Google 試算表（自動把 NaN 轉成空字串避免崩潰）
if cloud_connected:
  if st.button("☁️ 儲存並同步至 Google 試算表", type="primary"):
    try:
      save_df = updated_df[["姓名"] + exam_cols].copy()
      save_df = save_df.fillna("")  # 關鍵：將 NaN 轉為空字串
      worksheet.clear()
      worksheet.update([save_df.columns.values.tolist()] + save_df.values.tolist())
      st.success("✅ 成功同步至 Google 試算表！資料已永久保存。")
    except Exception as e:
      st.error(f"❌ 同步失敗：{e}")
else:
  st.session_state[sheet_name] = updated_df[["姓名"] + exam_cols].copy()

# --- A3 PDF 報表產生區 ---
st.markdown("---")
st.subheader("🖨️ A3 專業報表匯出功能")

if st.button("📥 產生並下載 A3 PDF 報表"):
  pdf_buffer = io.BytesIO()
  # 設定 A3 橫向尺寸 (寬 420mm, 高 297mm)
  fig, ax = plt.subplots(figsize=(16.53, 11.69))
  ax.axis("off")

  # 標題設計
  ax.text(
      0.05,
      0.90,
      f"{selected_year} {selected_month} - {selected_grade} {selected_subject} 成績總表",
      fontsize=22,
      fontweight="bold",
      color="#2C3E50",
  )

  # 繪製表格內容
  cell_text = []
  for _, row in updated_df.iterrows():
    cell_text.append([str(val) if pd.notna(val) else "" for val in row])

  table = ax.table(
      cellText=cell_text,
      colLabels=updated_df.columns,
      loc="center",
      cellLoc="center",
  )
  table.auto_set_font_size(False)
  table.set_fontsize(12)
  table.scale(1, 1.8)

  plt.tight_layout()
  plt.savefig(pdf_buffer, format="pdf", bbox_inches="tight")
  plt.close()
  pdf_buffer.seek(0)

  st.download_button(
      label="💾 點擊下載 PDF 檔案",
      data=pdf_buffer,
      file_name=f"{selected_year}_{selected_month}_{selected_grade}_{selected_subject}_A3報表.pdf",
      mime="application/pdf",
  )