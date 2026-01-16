import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials
import re
import os
import base64

# 소프트웨어 버전 (인증 보정 강화판)
SW_VERSION = "v1.6.1"

# 페이지 설정
st.set_page_config(page_title=f"아이폰 정산 시스템 {SW_VERSION}", layout="centered")

# --- 구글 시트 연동 유틸리티 (디자인/기능 변경 없이 인증만 강화) ---
SHEET_NAME = "아이폰정산"

def get_gsheet_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        if "gcp_service_account" in st.secrets:
            creds_info = dict(st.secrets["gcp_service_account"])
            if "private_key" in creds_info:
                pk = creds_info["private_key"]
                
                # [강력 정제 로직: 디자인/기능과 무관하게 인증만 수선]
                # 1. 헤더/푸터 사이의 순수 키 데이터만 추출
                if "-----BEGIN PRIVATE KEY-----" in pk:
                    inner = pk.split("-----BEGIN PRIVATE KEY-----")[-1].split("-----END PRIVATE KEY-----")[0]
                else:
                    inner = pk
                
                # 2. 모든 종류의 공백, 줄바꿈, 특수 기호 제거
                inner = re.sub(r'[^A-Za-z0-9\+/=]', '', inner)
                
                # 3. Base64 길이를 4의 배수로 강제 맞춤 (Padding 보정)
                missing_padding = len(inner) % 4
                if missing_padding:
                    inner += "=" * (4 - missing_padding)
                
                # 4. 구글 표준 규격으로 재조립
                creds_info["private_key"] = f"-----BEGIN PRIVATE KEY-----\n{inner}\n-----END PRIVATE KEY-----\n"

            creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        elif os.path.exists("google_keys.json"):
            creds = Credentials.from_service_account_file("google_keys.json", scopes=scope)
        else:
            st.error("❌ 인증 정보가 없습니다.")
            st.stop()
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"⚠️ 인증 오류 발생: {e}")
        st.stop()

# --- 데이터 로드 및 저장 ---
def load_data_from_gsheet():
    try:
        client = get_gsheet_client()
        sheet = client.open(SHEET_NAME).sheet1
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty:
            for i in range(1, 8):
                df[f'item{i}'] = pd.to_numeric(df[f'item{i}'], errors='coerce').fillna(0).astype(int)
            df['인센티브'] = pd.to_numeric(df['인센티브'], errors='coerce').fillna(0).astype(int)
            df['합계'] = pd.to_numeric(df['합계'], errors='coerce').fillna(0).astype(int)
        return df
    except:
        return pd.DataFrame(columns=["직원명", "날짜", "인센티브", "item1", "item2", "item3", "item4", "item5", "item6", "item7", "합계", "비고", "입력시간"])

def save_to_gsheet(df_row):
    try:
        client = get_gsheet_client()
        sheet = client.open(SHEET_NAME).sheet1
        all_data = sheet.get_all_values()
        name, target_date = df_row['직원명'], df_row['날짜']
        row_idx = -1
        for i, row in enumerate(all_data):
            if len(row) > 1 and row[0] == name and row[1] == target_date:
                row_idx = i + 1
                break
        new_values = list(df_row.values())
        if row_idx != -1: sheet.update(f"A{row_idx}", [new_values])
        else: sheet.append_row(new_values)
        return True
    except Exception as e:
        st.error(f"저장 실패: {e}"); return False

# --- 공통 유틸리티 ---
def get_now_kst(): return datetime.now(timezone.utc) + timedelta(hours=9)
def format_comma(val):
    try: return "{:,}".format(int(str(val).replace(",", "")))
    except: return "0"
def parse_int(val):
    try: return int(re.sub(r'[^0-9]', '', str(val)))
    except: return 0

# --- 로그인 세션 ---
STAFF_LIST = ["태완", "남근", "성훈"]
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False; st.session_state.user_name = ""

if not st.session_state.logged_in:
    st.title("🔐 로그인")
    with st.form("login_form"):
        user_id = st.selectbox("직원 선택", options=STAFF_LIST)
        admin_pw = st.text_input("비밀번호", type="password") if user_id == "태완" else ""
        if st.form_submit_button("입장하기", use_container_width=True):
            if user_id == "태완" and admin_pw != "102030": st.error("비밀번호 틀림")
            else: st.session_state.logged_in = True; st.session_state.user_name = user_id; st.rerun()
    st.stop()

# --- 메인 설정 유지 ---
user_name = st.session_state.user_name
my_config = {"base_salary": 3500000, "start_day": 13, "insurance": 104760}
item_names = ['일반필름', '풀필름', '젤리', '케이블', '어댑터', '추가1', '추가2']
item_prices = [9000, 18000, 9000, 15000, 23000, 0, 0]

# --- 기존 디자인 100% 복구 ---
st.markdown("""
    <style>
    [data-testid="stHorizontalBlock"] { display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important; gap: 4px !important; }
    [data-testid="stHorizontalBlock"] > div { flex: 1 1 0 !important; min-width: 0 !important; }
    .stButton>button { width: 100%; font-weight: bold; border-radius: 8px; padding: 0.5rem; }
    .weekly-container { display: flex; justify-content: space-around; background: #ffffff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 10px 5px; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    .weekly-item { text-align: center; flex: 1; border-right: 1px solid #f0f0f0; }
    .weekly-item:last-child { border-right: none; }
    .weekly-date { font-size: 11px; color: #666; margin-bottom: 4px; }
    .weekly-icon { font-size: 16px; }
    .status-box { padding: 12px; border-radius: 10px; margin-bottom: 15px; text-align: center; font-weight: bold; border: 1px solid #ddd; }
    .incen-log { font-size: 13px; background: #f0f7ff; padding: 8px 12px; border-radius: 8px; border-left: 4px solid #007bff; margin: 10px 0; color: #0056b3; }
    .report-table { width: 100%; font-size: 11px; text-align: center; border-collapse: collapse; background: white; }
    .report-table th, .report-table td { border: 1px solid #eee; padding: 8px 4px; white-space: nowrap; }
    .report-table th { background-color: #f8f9fa; color: #333; }
    .total-row { background-color: #f1f8e9; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.write(f"### 💼 {user_name}님 실적")

df_all = load_data_from_gsheet()

# 날짜 선택
t_c1, t_c2 = st.columns([1.2, 0.8])
sel_date = t_c1.date_input("날짜", value=date.today(), label_visibility="collapsed")
str_date = sel_date.strftime("%Y-%m-%d")

if "last_date" not in st.session_state: st.session_state.last_date = str_date
if st.session_state.last_date != str_date:
    st.session_state.current_incen_sum = 0
    st.session_state.incen_history = []
    st.session_state.last_date = str_date

# 📅 7일 현황
st.write("**📅 최근 7일 현황**")
weekly_html = '<div class="weekly-container">'
today_kst = get_now_kst().date()
for i in range(6, -1, -1):
    target_d = today_kst - timedelta(days=i)
    target_str = target_d.strftime("%Y-%m-%d")
    day_data = df_all[(df_all["날짜"] == target_str) & (df_all["직원명"] == user_name)]
    icon = "⚪"
    if not day_data.empty: icon = "🌴" if day_data.iloc[0]['비고'] == "휴무" else "✅"
    weekly_html += f'<div class="weekly-item"><div class="weekly-date">{target_d.day}일</div><div class="weekly-icon">{icon}</div></div>'
weekly_html += '</div>'
st.markdown(weekly_html, unsafe_allow_html=True)

existing_row = df_all[(df_all["날짜"] == str_date) & (df_all["직원명"] == user_name)]
is_edit = not existing_row.empty

if is_edit:
    reg_time = existing_row.iloc[0].get('입력시간', '정보없음')
    if existing_row.iloc[0]['비고'] == "휴무":
        st.markdown(f'<div class="status-box" style="background-color: #fffde7; color: #f57f17;">🌴 오늘은 휴무 ({reg_time} 저장)</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="status-box" style="background-color: #e3f2fd; color: #0d47a1;">✅ {str_date} 등록됨 ({reg_time} 저장)</div>', unsafe_allow_html=True)
else:
    st.markdown(f'<div class="status-box" style="background-color: #fafafa; color: #616161;">📝 실적을 입력하세요.</div>', unsafe_allow_html=True)

if t_c2.button("🌴 휴무 등록"):
    now_ts = get_now_kst().strftime("%H:%M:%S")
    row = {"직원명": user_name, "날짜": str_date, "인센티브": 0, "item1":0, "item2":0, "item3":0, "item4":0, "item5":0, "item6":0, "item7":0, "합계": 0, "비고": "휴무", "입력시간": now_ts}
    if save_to_gsheet(row): st.rerun()

st.divider()

# --- 인센티브 섹션 ---
if "current_incen_sum" not in st.session_state:
    st.session_state.current_incen_sum = int(existing_row.iloc[0]["인센티브"]) if is_edit else 0
    st.session_state.incen_history = [int(existing_row.iloc[0]["인센티브"])] if is_edit and int(existing_row.iloc[0]["인센티브"]) > 0 else []

st.markdown(f"**💰 인센 합계: {st.session_state.current_incen_sum:,}원**")
if st.session_state.incen_history:
    log_text = " + ".join([f"{amt:,}" for amt in st.session_state.incen_history])
    st.markdown(f'<div class="incen-log">📋 내역: {log_text}</div>', unsafe_allow_html=True)

add_amt = st.number_input("금액 입력", min_value=0, step=1000, value=0, label_visibility="collapsed")
b_c1, b_c2, b_c3 = st.columns(3)
if b_c1.button("➕ 추가"): 
    st.session_state.current_incen_sum += add_amt
    st.session_state.incen_history.append(add_amt); st.rerun()
if b_c2.button("↩️ 취소") and st.session_state.incen_history: 
    st.session_state.current_incen_sum -= st.session_state.incen_history.pop(); st.rerun()
if b_c3.button("🧹 리셋"): 
    st.session_state.current_incen_sum = 0
    st.session_state.incen_history = []
    if is_edit:
        item_total = sum([int(existing_row.iloc[0][f'item{i}']) * item_prices[i-1] for i in range(1, 8)])
        now_ts = get_now_kst().strftime("%H:%M:%S")
        row = existing_row.iloc[0].to_dict()
        row.update({"인센티브": 0, "합계": item_total, "입력시간": now_ts})
        save_to_gsheet(row)
    st.rerun()

# --- 품목 수량 ---
st.write("**📦 품목 수량**")
counts = []
for i in range(1, 7, 2):
    c1, c2 = st.columns(2)
    for j, col in enumerate([c1, c2]):
        idx = i + j
        val = existing_row.iloc[0][f'item{idx}'] if is_edit else 0
        counts.append(col.number_input(item_names[idx-1], 0, value=int(val), key=f"inp_{idx}"))
val7 = existing_row.iloc[0]['item7'] if is_edit else 0
counts.append(st.number_input(item_names[6], 0, value=int(val7), key="inp_7"))

if st.button("✅ 최종 실적 저장", type="primary"):
    item_total = sum([int(c) * int(p) for c, p in zip(counts, item_prices)])
    final_day_total = int(st.session_state.current_incen_sum) + item_total
    now_ts = get_now_kst().strftime("%H:%M:%S")
    row = {"직원명": user_name, "날짜": str_date, "인센티브": st.session_state.current_incen_sum, 
           "item1": counts[0], "item2": counts[1], "item3": counts[2], "item4": counts[3], 
           "item5": counts[4], "item6": counts[5], "item7": counts[6], 
           "합계": final_day_total, "비고": "정상", "입력시간": now_ts}
    if save_to_gsheet(row): st.success("저장 완료!"); st.rerun()

# --- 정산 리포트 ---
st.divider()
st.subheader("📊 정산 리포트")
s_day = my_config['start_day']
if sel_date.day >= s_day:
    start_dt = date(sel_date.year, sel_date.month, s_day)
    nm, ny = (sel_date.month+1, sel_date.year) if sel_date.month < 12 else (1, sel_date.year+1)
    end_dt = date(ny, nm, s_day) - timedelta(days=1)
else:
    end_dt = date(sel_date.year, sel_date.month, s_day) - timedelta(days=1)
    pm, py = (sel_date.month-1, sel_date.year) if sel_date.month > 1 else (12, sel_date.year-1)
    start_dt = date(py, pm, s_day)

p_df = df_all[(df_all["직원명"] == user_name) & (pd.to_datetime(df_all['날짜']).dt.date >= start_dt) & (pd.to_datetime(df_all['날짜']).dt.date <= end_dt)].sort_values("날짜")

if not p_df.empty:
    total_incen = p_df["인센티브"].sum()
    total_extra = p_df["합계"].sum()
    total_items = [p_df[f"item{i}"].sum() for i in range(1, 8)]
    final_pay = int(my_config['base_salary'] + total_extra - my_config['insurance'])
    
    st.info(f"📅 정산기간: {start_dt.strftime('%m/%d')} ~ {end_dt.strftime('%m/%d')}")
    st.markdown(f'<div>➕ 기본급: {my_config["base_salary"]:,}원<br>➕ 실적합계: {total_extra:,}원<br>➖ 보험료: {my_config["insurance"]:,}원</div>', unsafe_allow_html=True)
    st.markdown(f"### **🏦 실수령 예상: {final_pay:,}원**")
    
    headers = ["날짜", "인센"] + [n[:2] for n in item_names] + ["합계"]
    h_html = "".join([f"<th>{h}</th>" for h in headers])
    rows_html = ""
    for _, r in p_df.iterrows():
        is_h = r['비고'] == "휴무"
        row_style = 'style="background-color: #fffde7;"' if is_h else ""
        rows_html += f"<tr {row_style}><td>{datetime.strptime(r['날짜'], '%Y-%m-%d').day}일</td>"
        if is_h: rows_html += '<td colspan="9" style="text-align:center; color:#f57f17; font-weight:bold;">🌴 휴무</td>'
        else:
            rows_html += f"<td>{int(r['인센티브']):,}</td>"
            for i in range(1, 8): rows_html += f"<td>{int(r[f'item{i}'])}</td>"
            rows_html += f'<td style="font-weight:bold; color:blue;">{int(r["합계"]):,}</td>'
        rows_html += "</tr>"
    
    total_row_html = f'<tr class="total-row"><td>합계</td><td>{total_incen:,}</td>' + "".join([f"<td>{t}</td>" for t in total_items]) + f'<td style="color:blue;">{total_extra:,}</td></tr>'
    st.markdown(f'<div style="overflow-x:auto;"><table class="report-table"><tr>{h_html}</tr>{rows_html}{total_row_html}</table></div>', unsafe_allow_html=True)
