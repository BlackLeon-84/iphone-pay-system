import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3

# 페이지 설정
st.set_page_config(page_title="아이폰 정산 시스템", layout="centered")

# --- 데이터베이스 설정 ---
def get_connection():
    return sqlite3.connect("data.db", check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS salary
                 (직원명 TEXT, 날짜 TEXT, 인센티브 INTEGER, 일반필름 INTEGER, 
                  풀필름 INTEGER, 젤리 INTEGER, 케이블 INTEGER, 어댑터 INTEGER, 
                  합계 INTEGER, PRIMARY KEY(직원명, 날짜))''')
    conn.commit()
    conn.close()

init_db()

# --- 직원 정보 ---
USER_CREDENTIALS = {"성훈": "1234", "남근": "5678"}

# --- 로그인 상태 확인 ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_name = ""

if not st.session_state.logged_in:
    st.title("🔐 직원 로그인")
    with st.form("login_form"):
        user_id = st.selectbox("직원 이름을 선택하세요", options=list(USER_CREDENTIALS.keys()))
        password = st.text_input("비밀번호", type="password")
        login_btn = st.form_submit_button("로그인")
        if login_btn:
            if USER_CREDENTIALS[user_id] == password:
                st.session_state.logged_in = True
                st.session_state.user_name = user_id
                st.rerun()
            else:
                st.error("비밀번호가 틀렸습니다.")
    st.stop()

# --- 메인 화면 ---
user_name = st.session_state.user_name
st.sidebar.title(f"👋 {user_name}님")
if st.sidebar.button("로그아웃"):
    st.session_state.logged_in = False
    st.rerun()

BASE_SALARY = 3500000
INSURANCE = 104760

st.title(f"💼 {user_name}님 정산")

# 1. 날짜 선택 및 데이터 로드
selected_date = st.date_input("📅 날짜 선택", value=date.today())
str_date = selected_date.strftime("%Y-%m-%d")

def load_data(name):
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM salary WHERE 직원명 = ?", conn, params=(name,))
    conn.close()
    return df

df = load_data(user_name)
existing_row = df[df["날짜"] == str_date]
is_edit = not existing_row.empty

# 2. 입력 폼 (모바일 가시성 위해 세로 배치 강조)
with st.form("input_form"):
    st.subheader("📝 실적 입력")
    v_incen = st.number_input("💵 기본 인센티브", min_value=0, step=1000, value=int(existing_row.iloc[0]["인센티브"]) if is_edit else 0)
    
    # 2열 배치 (모바일에서도 적당한 크기)
    c1, c2 = st.columns(2)
    v_nf = c1.number_input("일반필름", 0, value=int(existing_row.iloc[0]["일반필름"]) if is_edit else 0)
    v_ff = c2.number_input("풀필름", 0, value=int(existing_row.iloc[0]["풀필름"]) if is_edit else 0)
    v_j = c1.number_input("젤리", 0, value=int(existing_row.iloc[0]["젤리"]) if is_edit else 0)
    v_c = c2.number_input("케이블", 0, value=int(existing_row.iloc[0]["케이블"]) if is_edit else 0)
    v_a = st.number_input("어댑터", 0, value=int(existing_row.iloc[0]["어댑터"]) if is_edit else 0)
    
    save_btn = st.form_submit_button("✅ 저장하기", use_container_width=True)

if save_btn:
    daily_sum = v_incen + (v_nf*9000) + (v_ff*18000) + (v_j*9000) + (v_c*15000) + (v_a*23000)
    conn = get_connection()
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO salary VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (user_name, str_date, v_incen, v_nf, v_ff, v_j, v_c, v_a, daily_sum))
    conn.commit()
    conn.close()
    st.success("저장 완료!")
    st.rerun()

# 3. 정산 기간 계산
if selected_date.day >= 13:
    start_dt = date(selected_date.year, selected_date.month, 13)
    next_month = selected_date.replace(day=28) + timedelta(days=20)
    end_dt = next_month.replace(day=12)
else:
    end_dt = selected_date.replace(day=12)
    last_month = selected_date.replace(day=1) - timedelta(days=10)
    start_dt = last_month.replace(day=13)

st.divider()
st.subheader("📊 정산 현황")

# 4. 상단 요약 지표 (모바일에서 가장 중요)
df = load_data(user_name)
if not df.empty:
    df['날짜_dt'] = pd.to_datetime(df['날짜']).dt.date
    period_df = df[(df['날짜_dt'] >= start_dt) & (df['날짜_dt'] <= end_dt)].sort_values("날짜", ascending=False)
    
    if not period_df.empty:
        total_extra = period_df["합계"].sum()
        col_res1, col_res2 = st.columns(2)
        col_res1.metric("누적 수당", f"{total_extra:,}원")
        col_res2.metric("실수령액", f"{int(BASE_SALARY + total_extra - INSURANCE):,}원")
        
        st.write("---")
        # [핵심 수정] 표 대신 카드형으로 출력
        for index, row in period_df.iterrows():
            with st.expander(f"📅 {row['날짜']} (합계: {row['합계']:,}원)"):
                st.write(f"🔹 **기본 인센**: {row['인센티브']:,}원")
                st.write(f"🔹 **필름**: 일반 {row['일반필름']} / 풀 {row['풀필름']}")
                st.write(f"🔹 **기타**: 젤리 {row['젤리']} / 케이블 {row['케이블']} / 어댑터 {row['어댑터']}")
    else:
        st.info("기간 내 데이터가 없습니다.")
