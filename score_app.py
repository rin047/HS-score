import streamlit as st
import pandas as pd
import numpy as np
import io
import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib.backends.backend_pdf import PdfPages

# 網頁寬螢幕設定
st.set_page_config(page_title="國中英數自成績登記與自動報表系統", layout="wide")

st.title("📊 國中成績登記與自動報表系統")

# ==========================================
# 1. 頂部多維度切換區 (年份、月份、年級、科目)
# ==========================================
st.markdown("### 🔍 選擇當前登記的學期與科目")
col_year, col_month, col_grade, col_subject = st.columns(4)

with col_year:
    selected_year = st.selectbox("選擇年份", ["2024年", "2025年", "2026年", "2027年"], index=2)
with col_month:
    selected_month = st.selectbox("選擇月份", [f"{i}月" for i in range(1, 13)], index=7)
with col_grade:
    selected_grade = st.selectbox("選擇年級", ["國一", "國二", "國三"], index=1)
with col_subject:
    selected_subject = st.selectbox("選擇科目", ["英文", "數學", "自然"], index=2)

# 定義 8 次測驗的欄位名稱
exam_cols = [f"第{i}次測驗" for i in range(1, 9)]
all_grades = ["國一", "國二", "國三"]
all_subjects = ["英文", "數學", "自然"]

# 初始化所有年級和科目的資料結構
for g in all_grades:
    for s in all_subjects:
        dk = f"data_{selected_year}_{selected_month}_{g}_{s}"
        ik = f"info_{selected_year}_{selected_month}_{g}_{s}"
        
        if ik not in st.session_state:
            if g == "國二" and s == "自然" and selected_month == "8月":
                st.session_state[ik] = {"d1": "4月6日\n3_3", "d2": "4月10日\nCH3", "d3": "4月13日\n4_1", "d4": "4月17日\nCH4", "d5": "4月20日\nCH3", "d6": "4月24日\n苓雅110", "d7": "4月27日\n苓雅109", "d8": "備用"}
            else:
                st.session_state[ik] = {f"d{i}": f"第{i}次範圍" for i in range(1, 9)}
                
        if dk not in st.session_state:
            if g == "國二" and s == "自然" and selected_month == "8月":
                st.session_state[dk] = pd.DataFrame([
                    {"姓名": "古芯瑜", "第1次測驗": 90.0, "第2次測驗": 82.0, "第3次測驗": 76.0, "第4次測驗": 70.0, "第5次測驗": 84.0, "第6次測驗": 80.0, "第7次測驗": 82.0, "第8次測驗": None},
                    {"姓名": "李晉宇", "第1次測驗": 85.0, "第2次測驗": 64.0, "第3次測驗": 88.0, "第4次測驗": 73.5, "第5次測驗": 84.0, "第6次測驗": 82.0, "第7次測驗": 79.0, "第8次測驗": None},
                    {"姓名": "楊巧薇", "第1次測驗": 70.0, "第2次測驗": 64.0, "第3次測驗": 61.0, "第4次測驗": 63.0, "第5次測驗": 96.0, "第6次測驗": 82.0, "第7次測驗": 91.0, "第8次測驗": None},
                ])
            else:
                init_data = {"姓名": [f"範例學生{g}1", f"範例學生{g}2"]}
                for col in exam_cols: init_data[col] = [None, None]
                st.session_state[dk] = pd.DataFrame(init_data)

data_key = f"data_{selected_year}_{selected_month}_{selected_grade}_{selected_subject}"
info_key = f"info_{selected_year}_{selected_month}_{selected_grade}_{selected_subject}"

main_title = f"{selected_year}{selected_month} {selected_grade}{selected_subject}成績測驗表"
st.subheader(f"📅 目前編輯報表：{main_title}")

# 編輯測驗進度
st.markdown("📝 **設定各次測驗日期與進度範圍**")
info_data = st.session_state[info_key]

r1_c1, r1_c2, r1_c3, r1_c4 = st.columns(4)
with r1_c1: val_d1 = st.text_input("第1次測驗範圍", value=info_data["d1"], key=f"input_d1_{info_key}")
with r1_c2: val_d2 = st.text_input("第2次測驗範圍", value=info_data["d2"], key=f"input_d2_{info_key}")
with r1_c3: val_d3 = st.text_input("第3次測驗範圍", value=info_data["d3"], key=f"input_d3_{info_key}")
with r1_c4: val_d4 = st.text_input("第4次測驗範圍", value=info_data["d4"], key=f"input_d4_{info_key}")

r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4)
with r2_c1: val_d5 = st.text_input("第5次測驗範圍", value=info_data["d5"], key=f"input_d5_{info_key}")
with r2_c2: val_d6 = st.text_input("第6次測驗範圍", value=info_data["d6"], key=f"input_d6_{info_key}")
with r2_c3: val_d7 = st.text_input("第7次測驗範圍", value=info_data["d7"], key=f"input_d7_{info_key}")
with r2_c4: val_d8 = st.text_input("第8次測驗範圍", value=info_data["d8"], key=f"input_d8_{info_key}")

st.session_state[info_key] = {"d1": val_d1, "d2": val_d2, "d3": val_d3, "d4": val_d4, "d5": val_d5, "d6": val_d6, "d7": val_d7, "d8": val_d8}

st.divider()

# ==========================================
# 2. 成績編輯區
# ==========================================
st.markdown("### ✍️ 成績登記表")

current_df = st.session_state[data_key].copy()
for col in exam_cols:
    if col not in current_df.columns: 
        current_df[col] = None
    else:
        current_df[col] = pd.to_numeric(current_df[col], errors='coerce')

if not current_df.empty:
    current_df["總分"] = current_df[exam_cols].sum(axis=1, min_count=1)
    current_df["平均"] = current_df[exam_cols].mean(axis=1).round(2)
    current_df["排名"] = current_df["總分"].rank(ascending=False, method="min", na_option='bottom')
    current_df["排名"] = current_df["排名"].fillna(0).astype(int)
    
    cols_order = ["排名", "姓名"] + exam_cols + ["總分", "平均"]
    current_df = current_df[cols_order].sort_values(by="排名", ascending=True)
else:
    current_df = pd.DataFrame(columns=["排名", "姓名"] + exam_cols + ["總分", "平均"])

updated_df = st.data_editor(
    current_df, num_rows="dynamic", hide_index=True, use_container_width=True, key=f"editor_{data_key}",
    column_config={
        "排名": st.column_config.NumberColumn("排名", disabled=True),
        "總分": st.column_config.NumberColumn("總分", disabled=True),
        "平均": st.column_config.NumberColumn("平均", disabled=True),
    }
)

if not updated_df.equals(current_df):
    clean_df = updated_df[["姓名"] + exam_cols].copy()
    st.session_state[data_key] = clean_df
    st.rerun()

# ==========================================
# 3. 核心：文青風自選項目 A3 橫式 PDF 生成
# ==========================================
st.divider()
st.markdown("### 🖨️ 美化版報表導出中心")
st.markdown("💡 **請勾選想要匯出到同一個 PDF 檔案中的年級與科目報表：**")

# 建立 9 個選項供使用者自由勾選
all_possible_items = []
for g in ["國一", "國二", "國三"]:
    for s in ["英文", "數學", "自然"]:
        all_possible_items.append(f"{g}{s}")

selected_items = st.multiselect(
    "選擇要匯出的項目（可多選）",
    options=all_possible_items,
    default=all_possible_items  # 預設全部勾選
)

def generate_beautiful_pdf(chosen_items):
    rcParams['font.family'] = 'sans-serif'
    rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'SimHei', 'DejaVu Sans']
    
    # 低飽和度文青風配色
    color_map = {
        "自然": {"main": "#4A6B5B", "light": "#F2F5F3"}, 
        "數學": {"main": "#A8514C", "light": "#FAF2F1"}, 
        "英文": {"main": "#8C7B43", "light": "#F8F6F0"}
    }
    
    pdf_buffer = io.BytesIO()
    
    with PdfPages(pdf_buffer) as pdf:
        for item in chosen_items:
            g = item[:2]  # 國一 / 國二 / 國三
            s = item[2:]  # 英文 / 數學 / 自然
            
            dk = f"data_{selected_year}_{selected_month}_{g}_{s}"
            ik = f"info_{selected_year}_{selected_month}_{g}_{s}"
            
            info = st.session_state[ik]
            score_df = st.session_state[dk].copy()
            theme_info = color_map.get(s, {"main": "#4A4A4A", "light": "#F9F9F9"})
            theme_color = theme_info["main"]
            row_light_bg = theme_info["light"]
            
            for col in exam_cols:
                if col not in score_df.columns: 
                    score_df[col] = np.nan
                else:
                    score_df[col] = pd.to_numeric(score_df[col], errors='coerce')
            
            if not score_df.empty:
                score_df["總分"] = score_df[exam_cols].sum(axis=1, min_count=1)
                score_df["平均"] = score_df[exam_cols].mean(axis=1).round(1)
                score_df["排名"] = score_df["總分"].rank(ascending=False, method="min", na_option='bottom')
                score_df["排名"] = score_df["排名"].fillna(0).astype(int)
                score_df = score_df[["排名", "姓名"] + exam_cols + ["總分", "平均"]].sort_values(by="排名")
            else:
                score_df = pd.DataFrame(columns=["排名", "姓名"] + exam_cols + ["總分", "平均"])
            
            fig, ax = plt.subplots(figsize=(16.5, 11.7))
            ax.axis('off')
            
            rect_title = plt.Rectangle((0.02, 0.83), 0.96, 0.12, facecolor=theme_color, alpha=0.92, transform=ax.transAxes, zorder=1)
            ax.add_patch(rect_title)
            
            full_title_text = f"{g} ｜ {s} 成績總表"
            sub_title_text = f"統計期間：{selected_year.replace('年','')} 年 {selected_month}  |  測驗日期與進度範圍記錄"
            
            plt.text(0.5, 0.91, full_title_text, fontsize=28, color='white', weight='bold', ha='center', va='center', zorder=2)
            plt.text(0.5, 0.86, sub_title_text, fontsize=15, color='#F0F0F0', weight='bold', ha='center', va='center', zorder=2)
            
            headers = ["排名", "姓名"]
            for i in range(1, 9): headers.append(info[f"d{i}"])
            headers += ["總分", "平均"]
            
            table_data = []
            for _, row in score_df.iterrows():
                rank_val = int(row["排名"]) if pd.notna(row["排名"]) and row["排名"] > 0 else "-"
                row_data = [str(rank_val), str(row["姓名"])]
                for col in exam_cols:
                    val = row[col]
                    if pd.isna(val):
                        row_data.append("")
                    else:
                        row_data.append(str(int(val)) if val % 1 == 0 else str(val))
                
                total_val = row.get("總分")
                avg_val = row["平均"]
                
                row_data.append(str(int(total_val)) if pd.notna(total_val) and total_val % 1 == 0 else (str(total_val) if pd.notna(total_val) else ""))
                row_data.append(str(avg_val) if pd.notna(avg_val) else "")
                table_data.append(row_data)
            
            if not table_data:
                table_data = [["", "暫無學生資料"] + [""] * 8 + ["", ""]]
            
            table = ax.table(cellText=table_data, colLabels=headers, loc='center', cellLoc='center', bbox=[0.02, 0.04, 0.96, 0.75])
            table.auto_set_font_size(False)
            table.set_fontsize(11)
            
            for (row_idx, col_idx), cell in table.get_celld().items():
                cell.set_linewidth(0.6)
                cell.set_edgecolor('#D1D5DB')
                
                if row_idx == 0:
                    cell.set_facecolor(theme_color)
                    cell.get_text().set_color('white')
                    cell.get_text().set_weight('bold')
                    cell.get_text().set_fontsize(15)
                else:
                    cell.set_facecolor('#FFFFFF')
                    cell.get_text().set_weight('bold')
                    cell.get_text().set_color('#2C3E50')
                    
                    if col_idx == 0:
                        cell.set_facecolor('#EAECEE')
                    elif col_idx == 1:
                        cell.set_facecolor(row_light_bg)
            
            pdf.savefig(fig, bbox_inches='tight', pad_inches=0.1)
            plt.close(fig)
                
    pdf_buffer.seek(0)
    return pdf_buffer

# 下載按鈕（若未勾選任何項目則提示）
if selected_items:
    all_pdf_data = generate_beautiful_pdf(selected_items)
    st.download_button(
        label=f"📥 下載已勾選的 {len(selected_items)} 項 A3 橫式美化報表 (PDF)",
        data=all_pdf_data,
        file_name=f"國中自選成績總報表_{selected_year}{selected_month}.pdf",
        mime="application/pdf"
    )
else:
    st.warning("⚠️ 請至少勾選一個項目以產生 PDF 報表。")