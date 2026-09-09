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

# 頂部選擇區（目前編輯的表單）
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

# 確保欄位完整
for col in ["姓名"] + exam_cols:
  if col not in current_df.columns:
    current_df[col] = ""

# 編輯區
editable_df = current_df[["姓名"] + exam_cols].copy()

st.markdown("### ✍️ 成績登記表（直接在此輸入或修改成績）")
updated_editor_df = st.data_editor(
    editable_df,
    num_rows="dynamic",
    hide_index=True,
    use_container_width=True,
    key=f"editor_{sheet_name}",
)

# 背景即時計算總分、平均與排名
display_df = updated_editor_df.copy()
for col in exam_cols:
  display_df[col] = pd.to_numeric(display_df[col], errors="coerce")

display_df["總分"] = display_df[exam_cols].sum(axis=1, min_count=1)
display_df["平均"] = display_df[exam_cols].mean(axis=1).round(2)
display_df["排名"] = display_df["總分"].rank(
    ascending=False, method="min", na_option="bottom"
)
display_df["排名"] = display_df["排名"].fillna(0).astype(int)

cols_order = ["排名", "姓名"] + exam_cols + ["總分", "平均"]
display_df = display_df[cols_order].sort_values(by="排名", ascending=True)

st.markdown("### 📋 即時成績總表與排名預覽")
st.dataframe(display_df, hide_index=True, use_container_width=True)

# 儲存按鈕
if cloud_connected:
  if st.button("☁️ 儲存並同步至 Google 試算表", type="primary"):
    try:
      save_df = updated_editor_df[["姓名"] + exam_cols].copy()
      save_df = save_df.fillna("")
      worksheet.clear()
      worksheet.update([save_df.columns.values.tolist()] + save_df.values.tolist())
      st.success("✅ 成功同步至 Google 試算表！資料已永久保存。")
    except Exception as e:
      st.error(f"❌ 同步失敗：{e}")
else:
  st.session_state[sheet_name] = updated_editor_df[["姓名"] + exam_cols].copy()

# --- 恢復：多檔案選擇與 A3 專業報表匯出功能 ---
st.markdown("---")
st.subheader("🖨️ 多檔案選取與 A3 PDF 報表大量匯出")

# 取得目前 Google 試算表裡面所有的工作表清單（如果沒連線就抓本機 session_state）
if cloud_connected:
  try:
    all_worksheets = [ws.title for ws in sh.worksheets()]
  except:
    all_worksheets = [sheet_name]
else:
  all_worksheets = [
      k for k in st.session_state.keys() if not k.startswith("editor_")
  ]
  if not all_worksheets:
    all_worksheets = [sheet_name]

selected_sheets_to_print = st.multiselect(
    "勾選想要列印成 A3 報表的科目/月份清單",
    options=all_worksheets,
    default=[sheet_name],
)

if st.button("📥 產生並下載勾選項目的 A3 PDF 報表"):
  if not selected_sheets_to_print:
    st.warning("⚠️ 請至少勾選一個檔案！")
  else:
    pdf_buffer = io.BytesIO()
    with PdfPages(pdf_buffer) as pdf:
      for s_name in selected_sheets_to_print:
        # 讀取該工作表的資料
        if cloud_connected:
          try:
            ws_target = sh.worksheet(s_name)
            target_data = ws_target.get_all_records()
            t_df = pd.DataFrame(target_data)
          except:
            continue
        else:
          t_df = st.session_state.get(
              s_name,
              pd.DataFrame(
                  columns=["姓名"] + exam_cols,
                  data=[["範例學生1", "", "", "", "", "", "", "", ""]],
              ),
          )

        if t_df.empty:
          continue

        for col in exam_cols:
          if col not in t_df.columns:
            t_df[col] = ""
          t_df[col] = pd.to_numeric(t_df[col], errors="coerce")

        t_df["總分"] = t_df[exam_cols].sum(axis=1, min_count=1)
        t_df["平均"] = t_df[exam_cols].mean(axis=1).round(2)
        t_df["排名"] = t_df["總分"].rank(
            ascending=False, method="min", na_option="bottom"
        )
        t_df["排名"] = t_df["排名"].fillna(0).astype(int)
        t_df = t_df[["排名", "姓名"] + exam_cols + ["總分", "平均"]].sort_values(
            by="排名", ascending=True
        )

        # 繪製 A3 橫向頁面
        fig, ax = plt.subplots(figsize=(16.53, 11.69))
        ax.axis("off")

        ax.text(
            0.05,
            0.92,
            f"【A3 專業成績總表】 {s_name}",
            fontsize=22,
            fontweight="bold",
            color="#2C3E50",
        )

        cell_text = []
        for _, row in t_df.iterrows():
          cell_text.append([str(val) if pd.notna(val) else "" for val in row])

        table = ax.table(
            cellText=cell_text,
            colLabels=t_df.columns,
            loc="center",
            cellLoc="center",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(11)
        table.scale(1, 1.8)

        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

    pdf_buffer.seek(0)
    st.download_button(
        label="💾 點擊下載多檔案合併 A3 PDF 檔案",
        data=pdf_buffer,
        file_name="多檔案合併_A3成績報表.pdf",
        mime="application/pdf",
    )