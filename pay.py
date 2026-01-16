import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3
import re

# 페이지 설정
st.set_page_config(page_title="아이폰 정산 시스템 v1.3.9", layout="centered")

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

# --- 데이터베이스 설정 ---
def get_connection():
    return sqlite3.connect("data.db", check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # 실적 테이블 (입력시간 컬럼 추가)
    c.execute('''CREATE TABLE IF NOT EXISTS salary
                 (직원명 TEXT, 날짜 TEXT, 인센티브 INTEGER, 
                  item1 INTEGER DEFAULT 0, item2 INTEGER DEFAULT 0, item3 INTEGER DEFAULT 0, 
                  item4 INTEGER DEFAULT 0, item5 INTEGER DEFAULT 0, item6 INTEGER DEFAULT 0, 
                  item7 INTEGER DEFAULT 0, 합계 INTEGER, 비고 TEXT, 
                  입력시간 TEXT, PRIMARY KEY(직원명, 날짜))''')
    
    # 컬럼 자동 보정
    cursor = c.execute("PRAGMA table_info(salary)")
    cols = [row[1] for row in cursor.fetchall()]
    if '입력시간' not in cols:
        try: c.execute("ALTER TABLE salary ADD COLUMN 입력시간 TEXT")
        except: pass
    for i in range(1, 8):
        if f'item{i}' not in cols:
            try: c.execute(f"ALTER TABLE salary ADD COLUMN item{i} INTEGER DEFAULT 0")
            except: pass

    c.execute('''CREATE TABLE IF NOT EXISTS settings_v3
                 (직원명 TEXT, id TEXT, display_name TEXT, price INTEGER, PRIMARY KEY(직원명, id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS staff_configs
                 (직원명 TEXT PRIMARY KEY, base_salary INTEGER, start_day INTEGER, insurance INTEGER)''')
    conn.commit()
    conn.close()

init_db()

# --- 데이터 로드 ---
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

# --- 로그인 ---
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

# --- 사이드바 설정창 ---
with st.sidebar:
    st.header("⚙️ 시스템 관리")
    if user_name == "태완":
        target_staff = st.selectbox("👤 설정 직원", STAFF_LIST)
        u_sets = load_user_settings(target_staff)
        u_conf = load_staff_config(target_staff)
        
        with st.expander("📦 품목 설정", expanded=True):
            with st.form(f"items_{target_staff}"):
                new_it = []
                for i, row in u_sets.iterrows():
                    c1, c2 = st.columns([2, 1])
                    nm = c1.text_input(f"품목{i+1}", row['display_name'], key=f"n_{target_staff}_{row['id']}")
                    pr = c2.text_input(f"단가", format_comma(row['price']), key=f"p_{target_staff}_{row['id']}")
                    new_it.append((nm, parse_int(pr), target_staff, row['id']))
                if st.form_submit_button("품목 저장"):
                    conn = get_connection(); c = conn.cursor()
                    c.executemany("UPDATE settings_v3 SET display_name=?, price=? WHERE 직원명=? AND id=?", new_it)
                    conn.commit(); conn.close(); add_log(f"✅ {target_staff} 품목 저장"); st.rerun()

        with st.expander("💰 급여 설정"):
            with st.form(f"sal_{target_staff}"):
                bv = st.text_input("기본급", format_comma(u_conf['base_salary']))
                iv = st.text_input("보험료", format_comma(u_conf['insurance']))
                sd = st.number_input("시작일", 1, 28, int(u_conf['start_day']))
                if st.form_submit_button("급여 저장"):
                    conn = get_connection(); c = conn.cursor()
                    c.execute("INSERT OR REPLACE INTO staff_configs VALUES (?, ?, ?, ?)", (target_staff, parse_int(bv), sd, parse_int(iv)))
                    conn.commit(); conn.close(); add_log(f"✅ {target_staff} 급여 저장"); st.rerun()
    if st.button("로그아웃"): st.session_state.logged_in = False; st.rerun()

# --- 데이터 전처리 ---
curr_sets = load_user_settings(user_name)
item_names = curr_sets['display_name'].tolist()
item_prices = curr_sets['price'].tolist()
my_config = load_staff_config(user_name)

conn = get_connection()
df_all = pd.read_sql("SELECT * FROM salary WHERE 직원명 = ?", conn, params=(user_name,))
conn.close()

for i in range(1, 8):
    col = f'item{i}'
    if col not in df_all.columns: df_all[col] = 0
    df_all[col] = pd.to_numeric(df_all[col], errors='coerce').fillna(0).astype(int)
df_all['인센티브'] = pd.to_numeric(df_all['인센티브'], errors='coerce').fillna(0).astype(int)
df_all['합계'] = pd.to_numeric(df_all['합계'], errors='coerce').fillna(0).astype(int)

# --- CSS ---
st.markdown("""
    <style>
    [data-testid="stHorizontalBlock"] { display: flex !important; flex-direction: row !important; flex-wrap: wrap !important; gap: 8px !important; }
    [data-testid="stHorizontalBlock"] > div { flex: 1 1 calc(50% - 10px) !important; min-width: calc(50% - 10px) !important; }
    .stButton>button { width: 100%; font-weight: bold; }
    .status-box { padding: 12px; border-radius: 8px; margin-bottom: 15px; text-align: center; font-weight: bold; font-size: 14px; border: 1px solid #ddd; }
    .incen-log { font-size: 12px; background: #f9f9f9; padding: 5px 10px; border-radius: 4px; border-left: 3px solid #007bff; margin-top: 5px; }
    .report-table { width: 100%; font-size: 10px; text-align: center; border-collapse: collapse; }
    .report-table th, .report-table td { border: 1px solid #eee; padding: 6px; white-space: nowrap; }
    </style>
    """, unsafe_allow_html=True)

# 1. 실적 입력
st.write(f"### 💼 {user_name}님 실적")
t_c1, t_c2 = st.columns(2)
sel_date = t_c1.date_input("날짜", value=date.today(), label_visibility="collapsed")
str_date = sel_date.strftime("%Y-%m-%d")

# 🟢 [수정] 상단 상태 표시 로직 (등록 시간 및 휴무 여부 포함)
existing_row = df_all[df_all["날짜"] == str_date]
is_edit = not existing_row.empty

if is_edit:
    reg_time = existing_row.iloc[0].get('입력시간', '정보없음')
    is_off = existing_row.iloc[0]['비고'] == "휴무"
    if is_off:
        st.markdown(f'<div class="status-box" style="background-color: #fffde7; color: #f57f17; border-color: #fbc02d;">🌴 오늘은 휴무로 등록됨 ({reg_time} 저장됨)</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="status-box" style="background-color: #e3f2fd; color: #0d47a1; border-color: #2196f3;">✅ {str_date} 데이터 등록됨 ({reg_time} 저장됨)</div>', unsafe_allow_html=True)
else:
    st.markdown(f'<div class="status-box" style="background-color: #fafafa; color: #616161;">📝 실적을 입력하거나 휴무를 등록해주세요.</div>', unsafe_allow_html=True)

if t_c2.button("🌴 휴무"):
    conn = get_connection(); c = conn.cursor()
    now_ts = datetime.now().strftime("%H:%M:%S")
    c.execute("INSERT OR REPLACE INTO salary (직원명, 날짜, 인센티브, item1, item2, item3, item4, item5, item6, item7, 합계, 비고, 입력시간) VALUES (?, ?, 0, 0, 0, 0, 0, 0, 0, 0, 0, ?, ?)", (user_name, str_date, "휴무", now_ts))
    conn.commit(); conn.close(); st.rerun()

st.divider()

# 💰 인센티브 합계 및 로그 (복구 완료)
if "current_incen_sum" not in st.session_state or st.session_state.get("last_date") != str_date:
    st.session_state.current_incen_sum = int(existing_row.iloc[0]["인센티브"]) if is_edit else 0
    st.session_state.incen_history = [int(existing_row.iloc[0]["인센티브"])] if is_edit and int(existing_row.iloc[0]["인센티브"]) > 0 else []
    st.session_state.last_date = str_date

st.markdown(f"**💰 인센 합계: {st.session_state.current_incen_sum:,}원**")
if st.session_state.incen_history:
    log_text = " + ".join([f"{amt:,}" for amt in st.session_state.incen_history])
    st.markdown(f'<div class="incen-log">📋 입력 로그: {log_text}</div>', unsafe_allow_html=True)

add_amt = st.number_input("금액 입력", min_value=0, step=1000, value=0, label_visibility="collapsed")
bc1, bc2, bc3 = st.columns(3)
if bc1.button("➕ 추가"): 
    st.session_state.current_incen_sum += add_amt
    st.session_state.incen_history.append(add_amt)
    st.rerun()
if bc2.button("↩️ 취소") and st.session_state.incen_history: 
    st.session_state.current_incen_sum -= st.session_state.incen_history.pop()
    st.rerun()
if bc3.button("🧹 리셋"): 
    st.session_state.current_incen_sum = 0
    st.session_state.incen_history = []
    st.rerun()

# 📦 품목 수량 입력
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
    now_ts = datetime.now().strftime("%H:%M:%S")
    
    conn = get_connection(); c = conn.cursor()
    sql = "INSERT OR REPLACE INTO salary (직원명, 날짜, 인센티브, item1, item2, item3, item4, item5, item6, item7, 합계, 비고, 입력시간) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    c.execute(sql, (user_name, str_date, st.session_state.current_incen_sum, *counts, final_day_total, "정상", now_ts))
    conn.commit(); conn.close(); st.success("저장 완료!"); st.rerun()

# 📊 정산 리포트
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

p_df = df_all[(pd.to_datetime(df_all['날짜']).dt.date >= start_dt) & (pd.to_datetime(df_all['날짜']).dt.date <= end_dt)].sort_values("날짜")

if not p_df.empty:
    total_extra = p_df["합계"].sum()
    final_pay = int(my_config['base_salary'] + total_extra - my_config['insurance'])
    st.info(f"📅 정산 기간: {start_dt.strftime('%m/%d')} ~ {end_dt.strftime('%m/%d')}")
    st.markdown(f"### **🏦 실수령 예상: {final_pay:,}원**")
    
    headers = ["날짜", "인센"] + [n[:2] for n in item_names] + ["합계"]
    h_html = "".join([f"<th>{h}</th>" for h in headers])
    rows_html = ""
    for _, r in p_df.iterrows():
        is_h = r['비고'] == "휴무"
        row_style = 'style="background-color: #fff9c4;"' if is_h else ""
        rows_html += f"<tr {row_style}><td>{datetime.strptime(r['날짜'], '%Y-%m-%d').day}일</td>"
        if is_h:
            rows_html += '<td colspan="9" style="text-align:center; color:#f57f17; font-weight:bold;">🌴 휴무 등록됨</td>'
        else:
            rows_html += f"<td>{int(r['인센티브']):,}</td>"
            for i in range(1, 8): rows_html += f"<td>{int(r[f'item{i}'])}</td>"
            rows_html += f'<td style="font-weight:bold; color:blue;">{int(r["합계"]):,}</td>'
        rows_html += "</tr>"
    st.markdown(f'<div style="overflow-x:auto;"><table class="report-table"><tr>{h_html}</tr>{rows_html}</table></div>', unsafe_allow_html=True)
