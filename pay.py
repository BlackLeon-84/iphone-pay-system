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
    # 테이블 생성 (직원명, 날짜를 복합 키로 사용)
    c.execute('''CREATE TABLE IF NOT EXISTS salary
                 (직원명 TEXT, 날짜 TEXT, 인센티브 INTEGER, 일반필름 INTEGER, 
                  풀필름 INTEGER, 젤리 INTEGER, 케이블 INTEGER, 어댑터 INTEGER, 
                  합계 INTEGER, PRIMARY KEY(직원명, 날짜))''')
    conn.commit()
    conn.close()

init_db()

# --- 고정 직원 정보 설정 ---
# 여기에 직원 이름과 비밀번호를 관리하세요.
USER_CREDENTIALS = {
    "성훈": "1234",
    "남근": "5678"
}

# --- 로그인 상태 확인 ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_name = ""

if not st.session_state.logged_in:
    st.title("🔐 직원 로그인")
    with st.form("login_form"):
        # 1. 아이디를 직접 입력하는 대신 선택 상자로 변경
        user_id = st.selectbox("직원 이름을 선택하세요", options=list(USER_CREDENTIALS.keys()))
        # 2. 비밀번호 입력
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

# --- 로그인 성공 후 메인 화면 ---
user_name = st.session_state.user_name
st.sidebar.title(f"👋 {user_name}님")
if st.sidebar.button("로그아웃"):
    st.session_state.logged_in = False
    st.rerun()

# 급여 기본 설정
BASE_SALARY = 3500000
INSURANCE = 104760

st.title(f"💼 {user_name}님 정산 시스템")

# 1. 날짜 선택
selected_date = st.date_input("근무 날짜", value=date.today())
str_date = selected_date.strftime("%Y-%m-%d")

# 2. 본인 데이터 불러오기 함수
def load_data(name):
    conn = get_connection()
    try:
        df = pd.read_sql("SELECT * FROM salary WHERE 직원명 = ?", conn, params=(name,))
    except:
        df = pd.DataFrame(columns=["직원명", "날짜", "인센티브", "일반필름", "풀필름", "젤리", "케이블", "어댑터", "합계"])
    conn.close()
    return df

df = load_data(user_name)
existing_row = df[df["날짜"] == str_date]
is_edit = not existing_row.empty

# 3. 입력 폼
with st.form("input_form"):
    st.subheader(f"📝 {str_date} 데이터 입력")
    v_incen = st.number_input("기본 인센티브", min_value=0, value=int(existing_row.iloc[0]["인센티브"]) if is_edit else 0)
    
    col1, col2 = st.columns(2)
    with col1:
        v_nf = st.number_input("일반필름", 0, value=int(existing_row.iloc[0]["일반필름"]) if is_edit else 0)
        v_ff = st.number_input("풀필름", 0, value=int(existing_row.iloc[0]["풀필름"]) if is_edit else 0)
        v_j = st.number_input("젤리", 0, value=int(existing_row.iloc[0]["젤리"]) if is_edit else 0)
    with col2:
        v_c = st.number_input("케이블", 0, value=int(existing_row.iloc[0]["케이블"]) if is_edit else 0)
        v_a = st.number_input("어댑터", 0, value=int(existing_row.iloc[0]["어댑터"]) if is_edit else 0)
    
    save_btn = st.form_submit_button("✅ 데이터 저장하기")

# 4. 저장 로직
if save_btn:
    daily_sum = v_incen + (v_nf*9000) + (v_ff*18000) + (v_j*9000) + (v_c*15000) + (v_a*23000)
    conn = get_connection()
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO salary VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (user_name, str_date, v_incen, v_nf, v_ff, v_j, v_c, v_a, daily_sum))
    conn.commit()
    conn.close()
    st.success(f"✅ {user_name}님의 {str_date} 데이터 저장 완료!")
    st.rerun()

# 5. 정산 주기(13일~12일) 계산
if selected_date.day >= 13:
    start_dt = date(selected_date.year, selected_date.month, 13)
    # 다음 달 12일 계산
    next_month = selected_date.replace(day=28) + timedelta(days=20)
    end_dt = next_month.replace(day=12)
else:
    end_dt = selected_date.replace(day=12)
    # 이전 달 13일 계산
    last_month = selected_date.replace(day=1) - timedelta(days=10)
    start_dt = last_month.replace(day=13)

st.divider()
st.subheader(f"📊 {user_name}님 정산 현황")

# 6. 본인 필터링 데이터 출력
df = load_data(user_name)
if not df.empty:
    df['날짜_dt'] = pd.to_datetime(df['날짜']).dt.date
    period_df = df[(df['날짜_dt'] >= start_dt) & (df['날짜_dt'] <= end_dt)]
    
    if not period_df.empty:
        # 화면 출력 시 '직원명' 열은 숨김 처리
        st.dataframe(period_df.drop(columns=['날짜_dt', '직원명']).sort_values("날짜", ascending=False), use_container_width=True)
        total_extra = period_df["합계"].sum()
        c1, c2 = st.columns(2)
        c1.metric("누적 수당 합계", f"{total_extra:,}원")
        c2.metric("예상 실수령액", f"{int(BASE_SALARY + total_extra - INSURANCE):,}원")
    else:
        st.info("이 정산 기간에 저장된 데이터가 없습니다.")
