import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials
import os

# 소프트웨어 버전
SW_VERSION = "v2.1.8"

# 페이지 설정
st.set_page_config(page_title=f"아이폰 정산 시스템 {SW_VERSION}", layout="centered")

# --- 설정 및 함수 정의 ---
SHEET_NAME = "아이폰정산"

def get_gsheet_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        if "gcp_service_account" in st.secrets:
            creds_info = dict(st.secrets["gcp_service_account"])
            if "private_key" in creds_info:
                creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
            creds = Credentials.from_service_account_info(creds_info, scopes=scope)
            return gspread.authorize(creds)
        else:
            st.error("❌ Secrets 설정이 비어있습니다.")
            st.stop()
    except Exception as e:
        st.error(f"⚠️ 인증 오류: {e}")
        st.stop()

def load_data_from_gsheet():
    columns = ["직원명", "날짜", "인센티브", "item1", "item2", "item3", "item4", "item5", "item6", "item7", "합계", "비고", "입력시간"]
    try:
        client = get_gsheet_client()
        sheet = client.open(SHEET_NAME).sheet1
        data = sheet.get_all_records()
        if not data:
            return pd.DataFrame(columns=columns)
        df = pd.DataFrame(data)
        for col in columns:
            if col not in df.columns:
                df[col] = ""
        for i in range(1, 8):
            df[f'item{i}'] = pd.to_numeric(df[f'item{i}'], errors='coerce').fillna(0).astype(int)
        df['인센티브'] = pd.to_numeric(df['인센티브'], errors='coerce').fillna(0).astype(int)
        df['합계'] = pd.to_numeric(df['합계'], errors='coerce').fillna(0).astype(int)
        return df
    except Exception:
        return pd.DataFrame(columns=columns)

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
        if row_idx != -1:
            sheet.update(range_name=f"A{row_idx}", values=[new_values])
        else:
            sheet.append_row(new_values)
        return True 
    except Exception as e:
        if "200" in str(e): return True
        st.error(f"저장 에러: {e}")
        return False

def get_now_kst(): return datetime.now(timezone.utc) + timedelta(hours=9)

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

# --- 메인 데이터 로드 ---
user_name = st.session_state.user_name
my_config = {"base_salary": 3500000, "start_day": 13, "insurance": 104760}
item_names = ['일반필름', '풀필름', '젤리', '케이블', '어댑터', '추가1', '추가2']
item_prices = [9000, 18000, 9000, 15000, 23000, 0, 0]

st.markdown("""
    <style>
    .weekly-container { display: flex; justify-content: space-around; background: #f8f9fa; padding: 10px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #eee; }
    .weekly-item { text-align: center; flex: 1; }
    .weekly-date { font-size: 10px; color: #666; margin-bottom: 5px; }
    .weekly-icon { font-size: 18px; }
    .status-box { padding: 12px; border-radius: 10px; margin-bottom: 15px; text-align: center; font-weight: bold; border: 1px solid #ddd; }
    .report-table { width: 100%; font-size: 11px; text-align: center; border-collapse: collapse; background: white; }
    .report-table th, .report-table td { border: 1px solid #eee; padding: 8px 4px; }
    .total-row { background-color: #f8f9fa; font-weight: bold; }
    .incen-log { font-size: 11px; color: #666; margin-bottom: 10px; padding: 5px; background: #fdfdfd; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

st.write(f"### 💼 {user_name}님 실적")
df_all = load_data_from_gsheet()

# 날짜 선택
t_c1, t_c2 = st.columns([1.2, 0.8])
sel_date = t_c1.date_input("날짜", value=date.today(), label_visibility="collapsed")
str_date = sel_date.strftime("%Y-%m-%d")

# 날짜 변경 감지 시 세션 초기화
if "last_date" not in st.session_state: st.session_state.last_date = str_date
if st.session_state.last_date != str_date:
    st.session_state.current_incen_sum = None # 날짜 바뀌면 다시 불러오도록 설정
    st.session_state.incen_history = []
    st.session_state.last_date = str_date

# 최근 7일 현황
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

# 해당 날짜 데이터 추출
existing_row = df_all[(df_all["날짜"] == str_date) & (df_all["직원명"] == user_name)]
is_edit = not existing_row.empty

# 인센티브 세션값 설정 (수정 모드일 때 기존값 로드)
if st.session_state.get("current_incen_sum") is None:
    if is_edit:
        st.session_state.current_incen_sum = int(existing_row.iloc[0]["인센티브"])
        st.session_state.incen_history = [int(existing_row.iloc[0]["인센티브"])] if int(existing_row.iloc[0]["인센티브"]) > 0 else []
    else:
        st.session_state.current_incen_sum = 0
        st.session_state.incen_history = []

if is_edit:
    reg_time = existing_row.iloc[0].get('입력시간', '정보없음')
    if existing_row.iloc[0]['비고'] == "휴무":
        st.markdown(f'<div class="status-box" style="background-color: #fffde7; color: #f57f17;">🌴 오늘은 휴무 ({reg_time} 저장)</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="status-box" style="background-color: #e3f2fd; color: #0d47a1;">✅ {str_date} 등록됨 ({reg_time} 저장)</div>', unsafe_allow_html=True)
else:
    st.markdown(f'<div class="status-box" style="background-color: #fafafa; color: #616161;">📝 실적을 입력하세요.</div>', unsafe_allow_html=True)

if t_c2.button("🌴 휴무 등록", use_container_width=True):
    now_ts = get_now_kst().strftime("%H:%M:%S")
    row = {"직원명": user_name, "날짜": str_date, "인센티브": 0, "item1":0, "item2":0, "item3":0, "item4":0, "item5":0, "item6":0, "item7":0, "합계": 0, "비고": "휴무", "입력시간": now_ts}
    if save_to_gsheet(row): st.rerun()

st.divider()

# --- 인센티브 섹션 ---
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
    st.rerun()

# --- 품목 수량 (수정 모드 시 값 불러오기 핵심 로직) ---
st.write("**📦 품목 수량**")
counts = []
for i in range(1, 7, 2):
    c1, c2 = st.columns(2)
    for j, col in enumerate([c1, c2]):
        idx = i + j
        # 저장된 데이터가 있으면 그 값을, 없으면 0을 표시
        default_val = int(existing_row.iloc[0][f'item{idx}']) if is_edit else 0
        counts.append(col.number_input(item_names[idx-1], 0, value=default_val, key=f"inp_{idx}"))

default_val7 = int(existing_row.iloc[0]['item7']) if is_edit else 0
counts.append(st.number_input(item_names[6], 0, value=default_val7, key="inp_7"))

if st.button("✅ 최종 실적 저장", type="primary", use_container_width=True):
    item_total = sum([int(c) * int(p) for c, p in zip(counts, item_prices)])
    final_day_total = int(st.session_state.current_incen_sum) + item_total
    now_ts = get_now_kst().strftime("%H:%M:%S")
    row = {"직원명": user_name, "날짜": str_date, "인센티브": st.session_state.current_incen_sum, 
           "item1": counts[0], "item2": counts[1], "item3": counts[2], "item4": counts[3], 
           "item5": counts[4], "item6": counts[5], "item7": counts[6], 
           "합계": final_day_total, "비고": "정상", "입력시간": now_ts}
    if save_to_gsheet(row): 
        st.success("저장 완료!")
        st.rerun()

# --- 정산 리포트 (하단 생략, 기존과 동일) ---
# ... (이전 코드의 리포트 부분 유지)

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
