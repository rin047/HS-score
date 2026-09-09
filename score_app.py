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

st.set_page_config(
    page_title="國中英數自成績登記與 A3 報表系統", layout="wide"
)

# --- 文青風 (Morandi) 色彩配置 ---
MORANDI_BG = "#F7F6F3"
MORANDI_PRIMARY = "#4A5568"
MORANDI_ACCENT = "#718096"
MORANDI_HEADER_BG = "#E2E8F0"

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
  st.warning(f"⚠️ 連線至 Google 試算表失敗：{e}（目前使用本機暫存模式）")

st.title("🌿 國中成績登記與 A3 雲端管理系統")
st.markdown(
    "<span style='color: #718096; font-size: 1.1em;'>極簡文青風介面 · 資料雲端長久保存 · 專業 A3 報表輸出</span>",
    unsafe_allow_html=True,
)
st.markdown("---")

# --- 側邊欄：設定與自訂考試名稱 ---
with st.sidebar:
  st.header("⚙️ 報表與考試設定")

  selected_year = st.selectbox(
      "選擇年份", ["2024年", "2025年", "2026年", "2027年"], index=2
  )
  selected_month = st.selectbox(
      "選擇月份", [f"{i}月" for i in range(1, 13)], index=7
  )
  selected_grade = st.selectbox("選擇年級", ["國一", "國二", "國三"], index=1)
  selected_subject = st.selectbox("選擇科目", ["英文", "數學", "自然"], index=2)

  st.markdown("---")
  st.subheader("✏️ 自訂考試欄位名稱")
  st.markdown("你可以隨時修改下方各欄位的考試名稱：")

  # 預設 8 個考試欄位名稱，使用者可自由改名
  default_exam_names = [f"第{i}次測驗" for i in range(1, 9)]
  custom_exam_cols = []
  for i in range(8):
    c_name = st.text_input(
        f"欄位 {i+1}", default_exam_names[i], key=f"exam_name_{i}"
    )
    custom_exam_cols.append(c_name)

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
          columns=["姓名"] + custom_exam_cols,
          data=[["範例學生1"] + [""] * len(custom_exam_cols)],
      )
  except:
    worksheet = sh.add_worksheet(title=sheet_name, rows="100", cols="20")
    current_df = pd.DataFrame(
        columns=["姓名"] + custom_exam_cols,
        data=[["範例學生1"] + [""] * len(custom_exam_cols)],
    )
    worksheet.update(
        [current_df.columns.values.tolist()] + current_df.values.tolist()
    )
else:
  if sheet_name not in st.session_state:
    st.session_state[sheet_name] = pd.DataFrame(
        columns=["姓名"] + custom_exam_cols,
        data=[["範例學生1"] + [""] * len(custom_exam_cols)],
    )
  current_df = st.session_state[sheet_name]

st.subheader(
    f"📖 目前編輯中：{selected_year} {selected_month} ｜"
    f" {selected_grade}{selected_subject}"
)

# 確保欄位與自訂考試名稱一致
for col in ["姓名"] + custom_exam_cols:
  if col not in current_df.columns:
    current_df[col] = ""

editable_df = current_df[["姓名"] + custom_exam_cols].copy()

# 介面編輯表格
updated_editor_df = st.data_editor(
    editable_df,
    num_rows="dynamic",
    hide_index=True,
    use_container_width=True,
    key=f"editor_{sheet_name}",
)

# 在背景即時計算總分、平均與排名
display_df = updated_editor_df.copy()
for col in custom_exam_cols:
  display_df[col] = pd.to_numeric(display_df[col], errors="coerce")

display_df["總分"] = display_df[custom_exam_cols].sum(axis=1, min_count=1)
display_df["平均"] = display_df[custom_exam_cols].mean(axis=1).round(2)
display_df["排名"] = display_df["總分"].rank(
    ascending=False, method="min", na_option="bottom"
)
display_df["排名"] = display_df["排名"].fillna(0).astype(int)

cols_order = ["排名", "姓名"] + custom_exam_cols + ["總分", "平均"]
display_df = display_df[cols_order].sort_values(by="排名", ascending=True)

st.markdown("### 📊 即時成績排名預覽")
st.dataframe(display_df, hide_index=True, use_container_width=True)

# 儲存按鈕
col_save, col_info = st.columns([1, 3])
with col_save:
  if cloud_connected:
    if st.button("☁️ 儲存並同步至 Google 試算表", type="primary"):
      try:
        save_df = updated_editor_df[["姓名"] + custom_exam_cols].copy()
        save_df = save_df.fillna("")
        worksheet.clear()
        worksheet.update(
            [save_df.columns.values.tolist()] + save_df.values.tolist()
        )
        st.success("✅ 同步成功！")
      except Exception as e:
        st.error(f"❌ 同步失敗：{e}")
  else:
    if st.button("💾 儲存至本機快取", type="primary"):
      st.session_state[sheet_name] = updated_editor_df[
          ["姓名"] + custom_exam_cols
      ].copy()
      st.success("✅ 已儲存至本機！")

# --- 文青風 A3 PDF 報表匯出區 ---
st.markdown("---")
st.subheader("🖨️ 文青風 A3 專業報表大量匯出")

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
    "勾選想要列印成 A3 報表的項目清單",
    options=all_worksheets,
    default=[sheet_name],
)

if st.button("📥 產生並下載文青風 A3 PDF 報表"):
  if not selected_sheets_to_print:
    st.warning("⚠️ 請至少勾選一個檔案！")
  else:
    pdf_buffer = io.BytesIO()
    with PdfPages(pdf_buffer) as pdf:
      for s_name in selected_sheets_to_print:
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
                  columns=["姓名"] + custom_exam_cols,
                  data=[["範例學生1"] + [""] * len(custom_exam_cols)],
              ),
          )

        if t_df.empty:
          continue

        # 自動抓取該表格內含的成績欄位
        t_exam_cols = [c for c in t_df.columns if c != "姓名"]
        for col in t_exam_cols:
          t_df[col] = pd.to_numeric(t_df[col], errors="coerce")

        t_df["總分"] = t_df[t_exam_cols].sum(axis=1, min_count=1)
        t_df["平均"] = t_df[t_exam_cols].mean(axis=1).round(2)
        t_df["排名"] = t_df["總分"].rank(
            ascending=False, method="min", na_option="bottom"
        )
        t_df["排名"] = t_df["排名"].fillna(0).astype(int)
        t_df = t_df[["排名", "姓名"] + t_exam_cols + ["總分", "平均"]].sort_values(
            by="排名", ascending=True
        )

        # 繪製 A3 橫向文青風頁面
        fig, ax = plt.subplots(figsize=(16.53, 11.69))
        fig.patch.set_facecolor("#FAFAFA")
        ax.set_facecolor("#FAFAFA")
        ax.axis("off")

        # 頂部文青風標題裝飾
        ax.text(
            0.05,
            0.93,
            "A C A D E M I C   R E P O R T",
            fontsize=12,
            fontweight="light",
            color="#A0AEC0",
            letterspacing=2,
        )
        ax.text(
            0.05,
            0.88,
            f"成績總表 ── {s_name.replace('_', ' ')}",
            fontsize=24,
            fontweight="bold",
            color="#2D3748",
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

        # 套用文青風格表格外觀 (柔和色調、深灰框線)
        for key, cell in table.get_celld().items():
          cell.set_edgecolor("#CBD5E0")
          cell.set_linewidth(0.8)
          if key[0] == 0:
            cell.set_facecolor("#EDF2F7")
            cell.set_text_props(
                weight="bold", color="#2D3748", fontsize=11
            )
          else:
            if key[0] % 2 == 0:
              cell.set_facecolor("#F7FAFC")
            else:
              cell.set_facecolor("#FFFFFF")
            cell.set_text_props(color="#4A5568", fontsize=11)

        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

    pdf_buffer.seek(0)
    st.download_button(
        label="💾 點擊下載文青風 A3 成績總表 PDF",
        data=pdf_buffer,
        file_name="Morandi_A3_Score_Report.pdf",
        mime="application/pdf",
    )