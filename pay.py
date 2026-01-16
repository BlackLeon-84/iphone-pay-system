import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3
import re

# 페이지 설정
st.set_page_config(page_title="아이폰 정산 시스템 v1.2.7", layout="centered")

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

# --- 데이터베이스 및 기본 설정 ---
def get_connection():
    return sqlite3.connect("data.db", check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # 1. 기본 테이블 생성
    c.execute('''CREATE TABLE IF NOT EXISTS salary
                 (직원명 TEXT, 날짜 TEXT, 인센티브 INTEGER, 
                  item1 INTEGER, item2 INTEGER, item3 INTEGER, item4 INTEGER, item5 INTEGER, 
                  item6 INTEGER DEFAULT 0, item7 INTEGER DEFAULT 0, 합계 INTEGER, 비고 TEXT, PRIMARY KEY(직원명, 날짜))''')
    
    # 2. 기존 사용자를 위한 컬럼 강제 추가 (KeyError 방지)
    columns = [row[1] for row in c.execute("PRAGMA table_info(salary)")]
    if 'item6' not in columns:
        c.execute("ALTER TABLE salary ADD COLUMN item6 INTEGER DEFAULT 0")
    if 'item7' not in columns:
        c.execute("ALTER TABLE salary ADD COLUMN item7 INTEGER DEFAULT 0")
    
    c.execute('''CREATE TABLE IF NOT EXISTS settings_v3
                 (직원명 TEXT, id TEXT, display_name TEXT, price INTEGER, PRIMARY KEY(직원명, id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS staff_configs
                 (직원명 TEXT PRIMARY KEY, base_salary INTEGER, start_day INTEGER, insurance INTEGER)''')
    conn.commit()
    conn.close()

init_db()

# --- 데이터 로드 함수 ---
def load_user_settings(name):
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM settings_v3 WHERE 직원명 = ?", conn, params=(name,))
    # 항목이 7개가 아니면 초기화
    if df.empty or len(df) < 7:
        c = conn.cursor()
        c.execute("DELETE FROM settings_v3 WHERE 직원명 = ?", (name,))
        default = [
            (name, 'item1', '일반필름', 9000), (name, 'item2', '풀필름', 18000), 
            (name, 'item3', '젤리', 9000), (name, 'item4', '케이블', 15000), 
            (name, 'item5', '어댑터', 23000), (name, 'item6', '추가항목1', 0), (name, 'item7', '추가항목2', 0)
        ]
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
            if user_id == "태완" and admin_pw != "102030":
                st.error("비밀번호가 틀렸습니다.")
            else:
                st.session_state.logged_in = True
                st.session_state.user_name = user_id
                st.rerun()
    st.stop()

user_name = st.session_state.user_name

# --- 사이드바 (관리자 설정 및 로그) ---
with st.sidebar:
    st.header("⚙️ 시스템 관리")
    if user_name == "태완":
        target_staff = st.selectbox("👤 설정할 직원 선택", STAFF_LIST)
        st.divider()
        
        user_settings = load_user_settings(target_staff)
        config = load_staff_config(target_staff)
        new_items = []
        
        with st.form(f"admin_form_{target_staff}"):
            st.subheader(f"📦 {target_staff} 품목 설정")
            for i, row in user_settings.iterrows():
                n_name = st.text_input(f"품목{i+1} 이름", value=row['display_name'], key=f"it_n_{target_staff}_{row['id']}")
                p_val = st.text_input(f"{n_name} 단가", value=format_comma(row['price']), key=f"it_p_{target_staff}_{row['id']}")
                new_items.append((n_name, parse_int(p_val), target_staff, row['id']))
            
            st.divider()
            b_val = st.text_input("기본급", value=format_comma(config['base_salary']))
            i_val = st.text_input("보험료(공제액)", value=format_comma(config['insurance']))
            new_start = st.number_input("정산 시작일", value=int(config['start_day']), min_value=1, max_value=28)
            
            if st.form_submit_button(f"{target_staff} 설정 저장"):
                conn = get_connection()
                c = conn.cursor()
                c.executemany("UPDATE settings_v3 SET display_name=?, price=? WHERE 직원명=? AND id=?", new_items)
                c.execute("INSERT OR REPLACE INTO staff_configs VALUES (?, ?, ?, ?)", 
                          (target_staff, parse_int(b_val), new_start, parse_int(i_val)))
                conn.commit()
                conn.close()
                add_log(f"✅ {target_staff} 설정 저장 성공")
                st.rerun()

        if st.session_state.admin_logs:
            st.markdown("---")
            st.caption("🕒 **관리 로그 (최근 5건)**")
            for log in st.session_state.admin_logs:
                st.code(log, language="text")
    else:
        st.info(f"✅ 로그인 중: {user_name}")
    
    if st.button("로그아웃"):
        st.session_state.logged_in = False
        st.rerun()

# 현재 사용자 정보 로드
current_user_settings = load_user_settings(user_name)
item_names = current_user_settings['display_name'].tolist()
item_prices = current_user_settings['price'].tolist()
my_config = load_staff_config(user_name)

# --- CSS (1.0 디자인 유지) ---
st.markdown("""
    <style>
    .version-text { font-size: 10px; color: #ccc; text-align: right; margin-bottom: -10px; }
    div[data-testid="stHorizontalBlock"] { display: flex !important; flex-direction: row !important; gap: 5px !important; }
    div[data-testid="stHorizontalBlock"] > div { flex: 1 1 0% !important; min-width: 0 !important; }
    .stButton>button { width: 100% !important; height: 42px !important; padding: 0px !important; font-weight: bold; }
    .report-table { width: 100%; border-collapse: collapse; font-size: 9px; text-align: center; }
    .report-table th, .report-table td { border: 1px solid #eee; padding: 4px 1px !important; white-space: nowrap; }
    .report-table th { background-color: #f8f9fa; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)
st.markdown('<p class="version-text">v1.2.7-stable</p>', unsafe_allow_html=True)

# 1. 상단 실적 입력
st.write(f"### 💼 {user_name}님 실적")
top_c1, top_c2 = st.columns([2, 1])
selected_date = top_c1.date_input("날짜", value=date.today(), label_visibility="collapsed")
str_date = selected_date.strftime("%Y-%m-%d")

df_all = pd.read_sql("SELECT * FROM salary WHERE 직원명 = ?", get_connection(), params=(user_name,))
existing_row = df_all[df_all["날짜"] == str_date]
is_edit = not existing_row.empty

if top_c2.button("🌴 휴무", use_container_width=True):
    conn = get_connection()
    conn.cursor().execute('''INSERT OR REPLACE INTO salary VALUES (?, ?, 0, 0, 0, 0, 0, 0, 0, 0, 0, ?)''', (user_name, str_date, "휴무"))
    conn.commit()
    conn.close()
    st.rerun()

# 최근 현황 표
st.write("**🗓️ 최근 기입 현황**")
t_html = """<table style="width:100%; border-collapse: collapse; table-layout: fixed;"><tr style="background-color: #f8f9fa;">"""
for i in range(7):
    d = date.today() - timedelta(days=6-i)
    t_html += f"<th style='border:1px solid #ddd; padding:5px; font-size:10px; text-align:center;'>{d.day}일</th>"
t_html += "</tr><tr>"
for i in range(7):
    d = date.today() - timedelta(days=6-i)
    target_row = df_all[df_all["날짜"] == d.strftime("%Y-%m-%d")]
    icon, bg = ("💤", "#e1f5fe") if not target_row.empty and target_row.iloc[0]["비고"] == "휴무" else (("✅", "#e8f5e9") if not target_row.empty else ("⚪", "#ffffff"))
    t_html += f"<td style='border:1px solid #ddd; padding:8px; text-align:center; background-color:{bg}; font-size:16px;'>{icon}</td>"
t_html += "</tr></table>"
st.markdown(t_html, unsafe_allow_html=True)

st.divider()

# 인센티브
if "current_incen_sum" not in st.session_state or st.session_state.get("last_date") != str_date:
    st.session_state.current_incen_sum = int(existing_row.iloc[0]["인센티브"]) if is_edit else 0
    st.session_state.incen_history = [int(existing_row.iloc[0]["인센티브"])] if is_edit and existing_row.iloc[0]["인센티브"] > 0 else []
    st.session_state.last_date = str_date

h_text = f" ({' + '.join([f'{x:,}' for x in st.session_state.incen_history])})" if st.session_state.incen_history else ""
st.markdown(f"**💰 인센 합계: {st.session_state.current_incen_sum:,}원**{h_text}")

add_amount = st.number_input("금액 입력", min_value=0, step=1000, value=0, label_visibility="collapsed")
btn_c1, btn_c2, btn_c3 = st.columns(3)
if btn_c1.button("➕ 추가"):
    st.session_state.current_incen_sum += add_amount
    st.session_state.incen_history.append(add_amount)
    st.rerun()
if btn_c2.button("↩️ 취소") and st.session_state.incen_history:
    st.session_state.current_incen_sum -= st.session_state.incen_history.pop()
    st.rerun()
if btn_c3.button("🧹 리셋"):
    st.session_state.current_incen_sum = 0
    st.session_state.incen_history = []
    st.rerun()

# 수량 입력
f_c1, f_c2 = st.columns(2)
v1 = f_c1.number_input(item_names[0], 0, value=int(existing_row.iloc[0]["item1"]) if is_edit and 'item1' in existing_row else 0)
v2 = f_c2.number_input(item_names[1], 0, value=int(existing_row.iloc[0]["item2"]) if is_edit and 'item2' in existing_row else 0)
v3 = f_c1.number_input(item_names[2], 0, value=int(existing_row.iloc[0]["item3"]) if is_edit and 'item3' in existing_row else 0)
v4 = f_c2.number_input(item_names[3], 0, value=int(existing_row.iloc[0]["item4"]) if is_edit and 'item4' in existing_row else 0)
v5 = f_c1.number_input(item_names[4], 0, value=int(existing_row.iloc[0]["item5"]) if is_edit and 'item5' in existing_row else 0)
v6 = f_c2.number_input(item_names[5], 0, value=int(existing_row.iloc[0]["item6"]) if is_edit and 'item6' in existing_row else 0)
v7 = st.number_input(item_names[6], 0, value=int(existing_row.iloc[0]["item7"]) if is_edit and 'item7' in existing_row else 0)

if st.button("✅ 최종 실적 저장", use_container_width=True, type="primary"):
    daily_sum = st.session_state.current_incen_sum + (v1*item_prices[0]) + (v2*item_prices[1]) + (v3*item_prices[2]) + (v4*item_prices[3]) + (v5*item_prices[4]) + (v6*item_prices[5]) + (v7*item_prices[6])
    conn = get_connection()
    conn.cursor().execute('''INSERT OR REPLACE INTO salary VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
              (user_name, str_date, st.session_state.current_incen_sum, v1, v2, v3, v4, v5, v6, v7, daily_sum, "정상"))
    conn.commit()
    conn.close()
    st.success("저장 완료!")
    st.rerun()

# 정산 리포트
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
    st.info(f"📅 **정산 기간:** {start_dt.strftime('%m/%d')} ~ {end_dt.strftime('%m/%d')}")
    st.markdown(f"""<div style="background-color:#f0f2f6; padding:15px; border-radius:10px; border-left:5px solid #ff4b4b; margin-bottom:15px;">
        <p style="margin:0; font-size:14px;">기본급: {my_config['base_salary']:,}원 / 공제(보험료): {my_config['insurance']:,}원</p>
        <p style="margin:5px 0; font-size:18px; font-weight:bold;">💰 총 수당 합계: {total_extra:,}원</p>
        <p style="margin:0; font-size:22px; font-weight:bold; color:#ff4b4b;">🏦 실수령 예상: {final_pay:,}원</p></div>""", unsafe_allow_html=True)
    
    headers = ["날짜", "인센"] + [name[:2] for name in item_names] + ["합계"]
    html = f"""<table class="report-table"><tr>"""
    for h in headers: html += f"<th>{h}</th>"
    html += "</tr>"
    
    for _, r in period_df.iterrows():
        # r[컬럼명] 접근 시 안전하게 처리
        vals = [r.get(f'item{i}', 0) for i in range(1, 8)]
        html += f"<tr><td>{datetime.strptime(r['날짜'], '%Y-%m-%d').day}일</td><td>{r['인센티브']:,}</td>"
        for v in vals: html += f"<td>{v}</td>"
        html += f"<td style='font-weight:bold;'>{r['합계']:,}</td></tr>"
    
    sums = [period_df[f'item{i}'].sum() if f'item{i}' in period_df else 0 for i in range(1, 8)]
    html += f"<tr style='background-color:#fff3f3; font-weight:bold;'><td>합계</td><td>{period_df['인센티브'].sum():,}</td>"
    for s in sums: html += f"<td>{s}</td>"
    html += f"<td style='color:#ff4b4b;'>{total_extra:,}</td></tr></table>"
    st.markdown(html, unsafe_allow_html=True)
