import io
import gspread
from google.oauth2.service_account import Credentials
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib import rcParams
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="國中英數自成績登記與自動報表系統", layout="wide")

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
  # 請將這裡的 "學生成績總表" 改成你在 Google 雲端硬碟建立的試算表名稱
  sh = gc.open("學生成績總表")
  cloud_connected = True
except Exception as e:
  cloud_connected = False
  st.warning(
      f"⚠️ 尚未成功連線至 Google 試算表（若在本地測試請設定 Secrets）：{e}"
  )

st.title("📊 國中成績登記與自動報表系統（雲端同步版）")

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
          data=[["範例學生1", None, None, None, None, None, None, None, None]],
      )
  except:
    # 如果分頁不存在，自動建立一個
    worksheet = sh.add_worksheet(title=sheet_name, rows="100", cols="20")
    current_df = pd.DataFrame(
        columns=["姓名"] + exam_cols,
        data=[["範例學生1", None, None, None, None, None, None, None, None]],
    )
    worksheet.update(
        [current_df.columns.values.tolist()] + current_df.values.tolist()
    )
else:
  # 本地備用簡易記憶體
  if sheet_name not in st.session_state:
    st.session_state[sheet_name] = pd.DataFrame(
        columns=["姓名"] + exam_cols,
        data=[["範例學生1", None, None, None, None, None, None, None, None]],
    )
  current_df = st.session_state[sheet_name]

st.subheader(f"📅 目前編輯報表：{selected_year}{selected_month} {selected_grade}{selected_subject}")

# 成績編輯表格
st.markdown("### ✍️ 成績登記表")
for col in exam_cols:
  if col not in current_df.columns:
    current_df[col] = None
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

# 儲存按鈕：點擊後寫回 Google 試算表
if cloud_connected:
  if st.button("☁️ 儲存並同步至 Google 試算表", type="primary"):
    try:
      save_df = updated_df[["姓名"] + exam_cols].copy()
      worksheet.clear()
      worksheet.update([save_df.columns.values.tolist()] + save_df.values.tolist())
      st.success("✅ 成功同步至 Google 試算表！下次打開資料依然健在。")
    except Exception as e:
      st.error(f"❌ 同步失敗：{e}")
else:
  st.session_state[sheet_name] = updated_df[["姓名"] + exam_cols].copy()