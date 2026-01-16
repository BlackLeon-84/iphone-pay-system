import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3
import re

# 페이지 설정
st.set_page_config(page_title="아이폰 정산 시스템 v1.3.4", layout="centered")

# --- 유틸리티 함수 ---
def format_comma(val):
    try:
        return "{:,}".format(int(str(val).replace(",", "")))
    except:
        return "0"

def parse_int(val):
    try:
        return int(re.sub(r'[^0-9]', '', str(val)))
    except:
        return 0

if "admin_logs" not in st.session_state:
    st.session_state.admin_logs = []

def add_log(msg):
    now = datetime.now().strftime("%H:%M:%S")
    st.session_state.admin_logs.insert(0, f"[{now}] {msg}")
    if len(st.session_state.admin_logs) > 5:
        st.session_state.admin_logs.pop()

# --- 데이터베이스 설정 (오류 수정 완료) ---
def get_connection():
    return sqlite3.connect("data.db", check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # 1. 실적 테이블
    c.execute('''CREATE TABLE IF NOT EXISTS salary
                 (직원명 TEXT, 날짜 TEXT, 인센티브 INTEGER, 
                  item1 INTEGER DEFAULT 0, item2 INTEGER DEFAULT 0, item3 INTEGER DEFAULT 0, 
                  item4 INTEGER DEFAULT 0, item5 INTEGER DEFAULT 0, item6 INTEGER DEFAULT 0, 
                  item7 INTEGER DEFAULT 0, 합계 INTEGER, 비고 TEXT, PRIMARY KEY(직원명, 날짜))''')
    
    # 컬럼 체크 및 추가
    cursor = c.execute("PRAGMA table_info(salary)")
    cols = [row[1] for row in cursor.fetchall()]
    for i in range(1, 8):
        if f'item{i}' not in cols:
            try:
                c.execute(f"ALTER TABLE salary ADD COLUMN item{i} INTEGER DEFAULT 0")
            except: pass

    # 2. 품목 설정 테이블
    c.execute('''CREATE TABLE IF NOT EXISTS settings_v3
                 (직원명 TEXT, id TEXT, display_name TEXT, price INTEGER, PRIMARY KEY(직원명, id))''')
    
    # 3. 직원 기본급 설정 테이블 (문법 오류 수정 포인트)
    c.execute('''CREATE TABLE IF NOT EXISTS staff_configs
                 (직원명 TEXT PRIMARY KEY, base_salary INTEGER, start_day INTEGER, insurance INTEGER)''')
    
    conn.commit()
    conn.close()

init_db()

# --- 데이터 로드 함수 ---
def load_user_settings(name):
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM settings_v3 WHERE 직원명 = ?", conn, params=(name,))
    if df.empty or len(df) < 7:
        c = conn.cursor()
        c.execute("DELETE FROM settings_v3 WHERE 직원명 = ?", (name,))
        default = [(name, f'item{i}', n, p) for i, (n, p) in enumerate([('일반필름', 9000), ('풀필름', 18000), ('젤리', 9000), ('케이블', 15000), ('어댑터', 23000), ('추가항목1', 0), ('추가항목2', 0)], 1)]
        c.executemany("INSERT INTO settings_v3 VALUES (?, ?, ?, ?)", default)
        conn.commit()
        df = pd.read_sql("SELECT * FROM settings_v3 WHERE 직원명 = ?", conn, params=(name,))
    conn.close()
    return df

def load_staff_config(name):
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM staff_configs WHERE 직원명 = ?", conn, params=(name,))
    conn.close()
    if df.empty: return {"base_salary": 3500000, "start_day": 13, "insurance": 104760}
    return {"base_salary": df.iloc[0]['base_salary'], "start_day": df.iloc[0]['start_day'], "insurance": df.iloc[0]['insurance']}

# --- 로그인 세션 ---
STAFF_LIST = ["태완", "남근", "성훈"]
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_name = ""

if not st.session_state.logged_in:
    st.title("🔐 로그인")
    with st.form("login_form"):
        user_id = st.selectbox("직원 선택", options=STAFF_LIST)
        admin_pw = st.text_input("비밀번호", type="password") if user_id == "태완" else ""
        if st.form_submit_button("입장하기", use_container_width=True):
            if user_id == "태완" and admin_pw != "102030": st.error("비밀번호 틀림")
            else: st.session_state.logged_in = True; st.session_state.user_name = user_id; st.rerun()
    st.stop()

user_name = st.session_state.user_name

# --- 사이드바 (설정창 분리형 디자인) ---
with st.sidebar:
    st.header("⚙️ 시스템 관리")
    if user_name == "태완":
        target_staff = st.selectbox("👤 설정 직원", STAFF_LIST)
        user_settings = load_user_settings(target_staff)
        config = load_staff_config(target_staff)
        
        # [섹션 1] 품목 설정
        st.markdown("### 📦 품목 및 단가 설정")
        with st.form(f"items_form_{target_staff}"):
            new_items = []
            for i, row in user_settings.iterrows():
                c1, c2 = st.columns([2, 1])
                n = c1.text_input(f"품목{i+1}", row['display_name'], key=f"nm_{target_staff}_{row['id']}")
                p = c2.text_input(f"단가", format_comma(row['price']), key=f"pr_{target_staff}_{row['id']}")
                new_items.append((n, parse_int(p), target_staff, row['id']))
            if st.form_submit_button("품목 정보 저장"):
                conn = get_connection(); c = conn.cursor()
                c.executemany("UPDATE settings_v3 SET display_name=?, price=? WHERE 직원명=? AND id=?", new_items)
                conn.commit(); conn.close(); add_log(f"✅ {target_staff} 품목 저장 성공"); st.rerun()

        st.divider()

        # [섹션 2] 기본급 및 정산 설정
        st.markdown("### 💰 급여 및 정산 설정")
        with st.form(f"salary_form_{target_staff}"):
            b_val = st.text_input("기본급", format_comma(config['base_salary']))
            i_val = st.text_input("보험료(공제)", format_comma(config['insurance']))
            new_start = st.number_input("정산 시작일", 1, 28, int(config['start_day']))
            if st.form_submit_button("기본 설정 저장"):
                conn = get_connection(); c = conn.cursor()
                c.execute("INSERT OR REPLACE INTO staff_configs VALUES (?, ?, ?, ?)", (target_staff, parse_int(b_val), new_start, parse_int(i_val)))
                conn.commit(); conn.close(); add_log(f"✅ {target_staff} 급여 설정 완료"); st.rerun()

        if st.session_state.admin_logs:
            st.divider()
            for log in st.session_state.admin_logs: st.code(log)
    
    if st.button("로그아웃"): st.session_state.logged_in = False; st.rerun()

# 사용자 데이터 로드
current_user_settings = load_user_settings(user_name)
item_names = current_user_settings['display_name'].tolist()
item_prices = current_user_settings['price'].tolist()
my_config = load_staff_config(user_name)

# --- CSS (모바일 2열 고정) ---
st.markdown("""
    <style>
    [data-testid="stHorizontalBlock"] { display: flex !important; flex-direction: row !important; flex-wrap: wrap !important; gap: 8px !important; }
    [data-testid="stHorizontalBlock"] > div { flex: 1 1 calc(50% - 10px) !important; min-width: calc(50% - 10px) !important; }
    .stButton>button { width: 100%; font-weight: bold; }
    .report-table { width: 100%; font-size: 9px; text-align: center; border-collapse: collapse; }
    .report-table th, .report-table td { border: 1px solid #eee; padding: 4px; white-space: nowrap; }
    </style>
    """, unsafe_allow_html=True)

# 1. 실적 입력
st.write(f"### 💼 {user_name}님 실적")
top_c1, top_c2 = st.columns(2)
selected_date = top_c1.date_input("날짜", value=date.today(), label_visibility="collapsed")
str_date = selected_date.strftime("%Y-%m-%d")

conn = get_connection()
df_all = pd.read_sql("SELECT * FROM salary WHERE 직원명 = ?", conn, params=(user_name,))
conn.close()
existing_row = df_all[df_all["날짜"] == str_date]
is_edit = not existing_row.empty

if top_c2.button("🌴 휴무"):
    conn = get_connection(); c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO salary VALUES (?, ?, 0, 0, 0, 0, 0, 0, 0, 0, 0, ?)", (user_name, str_date, "휴무"))
    conn.commit(); conn.close(); st.rerun()

st.divider()

# 인센티브 합계
if "current_incen_sum" not in st.session_state or st.session_state.get("last_date") != str_date:
    st.session_state.current_incen_sum = int(existing_row.iloc[0]["인센티브"]) if is_edit else 0
    st.session_state.incen_history = [int(existing_row.iloc[0]["인센티브"])] if is_edit and int(existing_row.iloc[0]["인센티브"]) > 0 else []
    st.session_state.last_date = str_date

st.markdown(f"**💰 인센 합계: {st.session_state.current_incen_sum:,}원**")
add_amount = st.number_input("금액 입력", min_value=0, step=1000, value=0, label_visibility="collapsed")
bc1, bc2, bc3 = st.columns(3)
if bc1.button("➕ 추가"): st.session_state.current_incen_sum += add_amount; st.session_state.incen_history.append(add_amount); st.rerun()
if bc2.button("↩️ 취소") and st.session_state.incen_history: st.session_state.current_incen_sum -= st.session_state.incen_history.pop(); st.rerun()
if bc3.button("🧹 리셋"): st.session_state.current_incen_sum = 0; st.session_state.incen_history = []; st.rerun()

# 수량 입력 (모바일 가로 2열 고정)
st.write("**📦 품목 수량**")
counts = []
for i in range(1, 7, 2):
    c1, c2 = st.columns(2)
    for j, col in enumerate([c1, c2]):
        idx = i + j
        col_name = f'item{idx}'
        val = int(existing_row.iloc[0][col_name]) if is_edit and col_name in existing_row.columns else 0
        counts.append(col.number_input(item_names[idx-1], 0, value=val, key=f"inp_{idx}"))
val7 = int(existing_row.iloc[0]['item7']) if is_edit and 'item7' in existing_row.columns else 0
counts.append(st.number_input(item_names[6], 0, value=val7, key="inp_7"))

if st.button("✅ 최종 실적 저장", type="primary"):
    total = st.session_state.current_incen_sum + sum([c*p for c, p in zip(counts, item_prices)])
    conn = get_connection(); c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO salary VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
              (user_name, str_date, st.session_state.current_incen_sum, *counts, total, "정상"))
    conn.commit(); conn.close(); st.success("저장 완료!"); st.rerun()

# 📊 정산 리포트
st.divider()
st.subheader("📊 정산 리포트")
s_day = my_config['start_day']
if selected_date.day >= s_day:
    start_dt = date(selected_date.year, selected_date.month, s_day)
    nm, ny = (selected_date.month+1, selected_date.year) if selected_date.month < 12 else (1, selected_date.year+1)
    end_dt = date(ny, nm, s_day) - timedelta(days=1)
else:
    end_dt = date(selected_date.year, selected_date.month, s_day) - timedelta(days=1)
    pm, py = (selected_date.month-1, selected_date.year) if selected_date.month > 1 else (12, selected_date.year-1)
    start_dt = date(py, pm, s_day)

period_df = df_all[(pd.to_datetime(df_all['날짜']).dt.date >= start_dt) & (pd.to_datetime(df_all['날짜']).dt.date <= end_dt)].sort_values("날짜")

if not period_df.empty:
    total_extra = period_df["합계"].sum()
    final_pay = int(my_config['base_salary'] + total_extra - my_config['insurance'])
    st.info(f"📅 정산 기간: {start_dt.strftime('%m/%d')} ~ {end_dt.strftime('%m/%d')}")
    st.markdown(f"**🏦 실수령 예상: {final_pay:,}원**")
    
    headers = ["날짜", "인센"] + [n[:2] for n in item_names] + ["합계"]
    h_html = "".join([f"<th>{h}</th>" for h in headers])
    rows_html = ""
    for _, r in period_df.iterrows():
        rows_html += f"<tr><td>{datetime.strptime(r['날짜'], '%Y-%m-%d').day}일</td><td>{r['인센티브']:,}</td>"
        for i in range(1, 8): rows_html += f"<td>{r.get(f'item{i}', 0)}</td>"
        rows_html += f"<td>{r['합계']:,}</td></tr>"
    st.markdown(f'<div style="overflow-x:auto;"><table class="report-table"><tr>{h_html}</tr>{rows_html}</table></div>', unsafe_allow_html=True)
