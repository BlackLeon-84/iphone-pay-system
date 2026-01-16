import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3

# 페이지 설정
st.set_page_config(page_title="아이폰 정산 시스템 v1.1.7", layout="centered")

# --- 데이터베이스 및 기본 설정 ---
def get_connection():
    return sqlite3.connect("data.db", check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # 실적 데이터 테이블
    c.execute('''CREATE TABLE IF NOT EXISTS salary
                 (직원명 TEXT, 날짜 TEXT, 인센티브 INTEGER, 일반필름 INTEGER, 
                  풀필름 INTEGER, 젤리 INTEGER, 케이블 INTEGER, 어댑터 INTEGER, 
                  합계 INTEGER, 비고 TEXT, PRIMARY KEY(직원명, 날짜))''')
    # 개인별 설정 테이블 (직원별로 데이터가 따로 관리됨)
    c.execute('''CREATE TABLE IF NOT EXISTS settings_v3
                 (직원명 TEXT, id TEXT, display_name TEXT, price INTEGER, PRIMARY KEY(직원명, id))''')
    
    conn.commit()
    conn.close()

init_db()

# --- 로그인 세션 ---
STAFF_LIST = ["태완", "남근", "성훈"]
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_name = ""

if not st.session_state.logged_in:
    st.title("🔐 로그인")
    with st.form("login_form"):
        user_id = st.selectbox("직원 선택", options=STAFF_LIST)
        # 태완님 로그인 시에만 보안을 위해 비밀번호 확인 (선택 사항)
        admin_pw_login = ""
        if user_id == "태완":
            admin_pw_login = st.text_input("접속 비밀번호", type="password")
            
        if st.form_submit_button("입장하기", use_container_width=True):
            if user_id == "태완" and admin_pw_login != "102030":
                st.error("비밀번호가 틀렸습니다.")
            else:
                st.session_state.logged_in = True
                st.session_state.user_name = user_id
                st.rerun()
    st.stop()

user_name = st.session_state.user_name

# --- 개별 설정 불러오기 로직 ---
def load_user_settings(name):
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM settings_v3 WHERE 직원명 = ?", conn, params=(name,))
    if df.empty:
        # 설정이 없으면 기본값 생성
        default_settings = [
            (name, 'item1', '일반필름', 9000), (name, 'item2', '풀필름', 18000), 
            (name, 'item3', '젤리', 9000), (name, 'item4', '케이블', 15000), (name, 'item5', '어댑터', 23000)
        ]
        c = conn.cursor()
        c.executemany("INSERT INTO settings_v3 VALUES (?, ?, ?, ?)", default_settings)
        conn.commit()
        df = pd.read_sql("SELECT * FROM settings_v3 WHERE 직원명 = ?", conn, params=(name,))
    conn.close()
    return df

# --- 사이드바 (비밀번호 기반 개별 수정) ---
with st.sidebar:
    st.header(f"⚙️ {user_name} 전용 설정")
    user_settings = load_user_settings(user_name)
    new_data = []
    
    with st.form("settings_form"):
        for i, row in user_settings.iterrows():
            st.markdown(f"**품목 {i+1}**")
            n_name = st.text_input(f"이름", value=row['display_name'], key=f"nm_{row['id']}")
            n_price = st.number_input(f"단가", value=int(row['price']), step=1000, key=f"pr_{row['id']}")
            new_data.append((n_name, n_price, user_name, row['id']))
        
        st.divider()
        st.write("⚠️ 수정 승인")
        confirm_pw = st.text_input("관리자 비밀번호", type="password", help="태완님의 비밀번호를 입력하세요.")
        
        if st.form_submit_button("설정 저장 (비밀번호 필수)"):
            if confirm_pw == "102030":
                conn = get_connection()
                c = conn.cursor()
                c.executemany("UPDATE settings_v3 SET display_name=?, price=? WHERE 직원명=? AND id=?", new_data)
                conn.commit()
                conn.close()
                st.success("설정이 저장되었습니다.")
                st.rerun()
            else:
                st.error("관리자 비밀번호가 틀려 저장할 수 없습니다.")
    
    if st.button("로그아웃"):
        st.session_state.logged_in = False
        st.rerun()

# 현재 로그인한 사용자의 품목명과 가격 적용
current_settings = load_user_settings(user_name)
item_names = current_settings['display_name'].tolist()
item_prices = current_settings['price'].tolist()

# --- CSS 및 리포트 디자인 (1.0 버전 유지) ---
st.markdown("""
    <style>
    .version-text { font-size: 10px; color: #ccc; text-align: right; margin-bottom: -10px; }
    div[data-testid="stHorizontalBlock"] { display: flex !important; flex-direction: row !important; gap: 5px !important; }
    div[data-testid="stHorizontalBlock"] > div { flex: 1 1 0% !important; min-width: 0 !important; }
    .stButton>button { width: 100% !important; height: 42px !important; padding: 0px !important; }
    .report-table { width: 100%; border-collapse: collapse; font-size: 10px; text-align: center; }
    .report-table th, .report-table td { border: 1px solid #eee; padding: 4px 1px !important; white-space: nowrap; }
    .report-table th { background-color: #f8f9fa; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<p class="version-text">v1.1.7-stable</p>', unsafe_allow_html=True)

# [이후 실적 입력 및 리포트 로직은 1.0과 완벽히 동일]
# ... (인센티브 계산 로그, 수량 입력, 실수령액 계산 등) ...
