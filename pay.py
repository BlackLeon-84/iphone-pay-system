import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3

# 페이지 설정
st.set_page_config(page_title="아이폰 정산 시스템 v1.2.0", layout="centered")

# --- 데이터베이스 및 기본 설정 ---
def get_connection():
    return sqlite3.connect("data.db", check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # 1. 실적 데이터
    c.execute('''CREATE TABLE IF NOT EXISTS salary
                 (직원명 TEXT, 날짜 TEXT, 인센티브 INTEGER, 일반필름 INTEGER, 
                  풀필름 INTEGER, 젤리 INTEGER, 케이블 INTEGER, 어댑터 INTEGER, 
                  합계 INTEGER, 비고 TEXT, PRIMARY KEY(직원명, 날짜))''')
    # 2. 직원별 품목 설정 (v3 유지: 개별 제어용)
    c.execute('''CREATE TABLE IF NOT EXISTS settings_v3
                 (직원명 TEXT, id TEXT, display_name TEXT, price INTEGER, PRIMARY KEY(직원명, id))''')
    # 3. 직원별 급여/정산일 설정
    c.execute('''CREATE TABLE IF NOT EXISTS staff_configs
                 (직원명 TEXT PRIMARY KEY, base_salary INTEGER, start_day INTEGER)''')
    conn.commit()
    conn.close()

init_db()

# --- 데이터 로드/저장 함수 ---
def load_user_settings(name):
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM settings_v3 WHERE 직원명 = ?", conn, params=(name,))
    if df.empty:
        default = [(name, 'item1', '일반필름', 9000), (name, 'item2', '풀필름', 18000), 
                   (name, 'item3', '젤리', 9000), (name, 'item4', '케이블', 15000), (name, 'item5', '어댑터', 23000)]
        c = conn.cursor()
        c.executemany("INSERT INTO settings_v3 VALUES (?, ?, ?, ?)", default)
        conn.commit()
        df = pd.read_sql("SELECT * FROM settings_v3 WHERE 직원명 = ?", conn, params=(name,))
    conn.close()
    return df

def load_staff_config(name):
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM staff_configs WHERE 직원명 = ?", conn, params=(name,))
    conn.close()
    if df.empty: return {"base_salary": 3500000, "start_day": 13}
    return {"base_salary": df.iloc[0]['base_salary'], "start_day": df.iloc[0]['start_day']}

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

# --- 사이드바 (관리자 통합 제어 메뉴) ---
with st.sidebar:
    st.header("⚙️ 시스템 관리")
    if user_name == "태완":
        # 상단 이름 선택 메뉴
        target_staff = st.selectbox("👤 설정할 직원 선택", STAFF_LIST)
        st.divider()
        
        # 1. 선택된 직원의 품목 및 단가 관리
        st.subheader(f"📦 {target_staff} 품목 설정")
        user_settings = load_user_settings(target_staff)
        new_items = []
        with st.form(f"items_form_{target_staff}"):
            for i, row in user_settings.iterrows():
                n_name = st.text_input(f"품목{i+1}", value=row['display_name'], key=f"it_n_{target_staff}_{row['id']}")
                n_price = st.number_input(f"가격", value=int(row['price']), step=1000, key=f"it_p_{target_staff}_{row['id']}")
                new_items.append((n_name, n_price, target_staff, row['id']))
            
            st.write(f"💰 {target_staff} 급여 설정")
            config = load_staff_config(target_staff)
            new_base = st.number_input("기본급", value=int(config['base_salary']), step=10000, key=f"base_{target_staff}")
            new_start = st.number_input("정산 시작일", value=int(config['start_day']), min_value=1, max_value=28, key=f"start_{target_staff}")
            
            if st.form_submit_button(f"{target_staff} 모든 설정 저장"):
                conn = get_connection()
                c = conn.cursor()
                # 품목 업데이트
                c.executemany("UPDATE settings_v3 SET display_name=?, price=? WHERE 직원명=? AND id=?", new_items)
                # 급여 설정 업데이트
                c.execute("INSERT OR REPLACE INTO staff_configs VALUES (?, ?, ?)", (target_staff, new_base, new_start))
                conn.commit()
                conn.close()
                st.success(f"{target_staff}님의 설정이 변경되었습니다!")
                st.rerun()
    else:
        st.info("관리자 권한이 없습니다.")
    
    if st.button("로그아웃"):
        st.session_state.logged_in = False
        st.rerun()

# 현재 로그인한 사용자의 데이터 로드
current_user_settings = load_user_settings(user_name)
item_names = current_user_settings['display_name'].tolist()
item_prices = current_user_settings['price'].tolist()
my_config = load_staff_config(user_name)

# --- 디자인 및 CSS (1.0 유지) ---
st.markdown("""
    <style>
    .version-text { font-size: 10px; color: #ccc; text-align: right; margin-bottom: -10px; }
    div[data-testid="stHorizontalBlock"] { display: flex !important; flex-direction: row !important; gap: 5px !important; }
    div[data-testid="stHorizontalBlock"] > div { flex: 1 1 0% !important; min-width: 0 !important; }
    .stButton>button { width: 100% !important; height: 42px !important; padding: 0px !important; font-weight: bold; }
    .report-table { width: 100%; border-collapse: collapse; font-size: 10px; text-align: center; }
    .report-table th, .report-table td { border: 1px solid #eee; padding: 4px 1px !important; white-space: nowrap; }
    .report-table th { background-color: #f8f9fa; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)
st.markdown('<p class="version-text">v1.2.0-admin</p>', unsafe_allow_html=True)

# --- 실적 입력 및 리포트 영역 (1.0 로직 동일) ---
st.write(f"### 💼 {user_name}님 실적")
# ... (이하 실적 입력 및 리포트 코드는 v1.1.9와 동일하게 작동합니다) ...
# (중략된 부분은 기존의 모든 입력 폼과 정산 리포트 로직을 포함합니다)
