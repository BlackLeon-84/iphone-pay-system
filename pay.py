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
    # 비고(NOTE) 컬럼을 추가하여 휴무 여부 기록
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS salary
                     (직원명 TEXT, 날짜 TEXT, 인센티브 INTEGER, 일반필름 INTEGER, 
                      풀필름 INTEGER, 젤리 INTEGER, 케이블 INTEGER, 어댑터 INTEGER, 
                      합계 INTEGER, 비고 TEXT, PRIMARY KEY(직원명, 날짜))''')
    except:
        pass # 이미 테이블이 있으면 통과
    conn.commit()
    conn.close()

init_db()

# --- 설정 및 로그인 ---
STAFF_LIST = ["성훈", "남근"]

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_name = ""

if not st.session_state.logged_in:
    st.title("🔐 테스트용 로그인")
    with st.form("login_form"):
        user_id = st.selectbox("테스트할 직원을 선택하세요", options=STAFF_LIST)
        login_btn = st.form_submit_button("입장하기", use_container_width=True)
        if login_btn:
            st.session_state.logged_in = True
            st.session_state.user_name = user_id
            st.rerun()
    st.stop()

# --- 메인 로직 ---
user_name = st.session_state.user_name
st.sidebar.title(f"👋 {user_name}님")
if st.sidebar.button("로그아웃"):
    st.session_state.logged_in = False
    st.rerun()

BASE_SALARY = 3500000
INSURANCE = 104760

st.title(f"💼 {user_name}님 정산")

# 1. 데이터 로드 함수
def load_data(name):
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM salary WHERE 직원명 = ?", conn, params=(name,))
    conn.close()
    return df

df_all = load_data(user_name)

# 2. 날짜 선택 및 기입 상태 확인 달력
selected_date = st.date_input("📅 날짜 선택", value=date.today())
str_date = selected_date.strftime("%Y-%m-%d")

# --- 기입 상태 시각화 (달력형 로그) ---
st.caption("🗓️ 최근 기입 현황 (✅완료 | 💤휴무 | ⚠️미기입)")
cols = st.columns(7) # 최근 7일간 상태 표시
for i in range(7):
    check_date = date.today() - timedelta(days=6-i)
    str_check = check_date.strftime("%Y-%m-%d")
    status = "⚠️"
    target_row = df_all[df_all["날짜"] == str_check]
    
    if not target_row.empty:
        status = "💤" if target_row.iloc[0]["비고"] == "휴무" else "✅"
    
    with cols[i]:
        color = "blue" if status == "💤" else ("green" if status == "✅" else "red")
        st.markdown(f"<p style='text-align:center; font-size:12px; margin-bottom:0;'>{check_date.day}일</p>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align:center; font-size:20px; color:{color}; margin-top:0;'>{status}</p>", unsafe_allow_html=True)

st.divider()

# 3. 입력 폼 로직
existing_row = df_all[df_all["날짜"] == str_date]
is_edit = not existing_row.empty
is_off = is_edit and existing_row.iloc[0]["비고"] == "휴무"

if "current_incen_sum" not in st.session_state or st.session_state.get("last_date") != str_date:
    st.session_state.current_incen_sum = int(existing_row.iloc[0]["인센티브"]) if is_edit else 0
    st.session_state.incen_history = [int(existing_row.iloc[0]["인센티브"])] if is_edit and existing_row.iloc[0]["인센티브"] > 0 else []
    st.session_state.last_date = str_date

with st.form("input_form"):
    if is_off:
        st.info(f"🌴 {str_date}은 현재 '휴무'로 설정되어 있습니다.")
    
    st.subheader("📝 실적 입력")
    st.markdown(f"### 💵 인센티브 총액: `{st.session_state.current_incen_sum:,}`원")
    
    if st.session_state.incen_history:
        st.caption(f"🕒 내역: {' > '.join([f'{amt:,}' for amt in st.session_state.incen_history])}")

    add_amount = st.number_input("금액 입력", min_value=0, step=1000, value=1000)
    c_inc1, c_inc2, c_inc3 = st.columns([1, 1, 1])
    if c_inc1.form_submit_button("➕ 추가"):
        st.session_state.current_incen_sum += add_amount
        st.session_state.incen_history.append(add_amount)
        st.rerun()
    if c_inc2.form_submit_button("↩️ 취소") and st.session_state.incen_history:
        st.session_state.current_incen_sum -= st.session_state.incen_history.pop()
        st.rerun()
    if c_inc3.form_submit_button("🧹 리셋"):
        st.session_state.current_incen_sum = 0
        st.session_state.incen_history = []
        st.rerun()
    
    st.divider()
    c1, c2 = st.columns(2)
    v_nf = c1.number_input("일반필름", 0, value=int(existing_row.iloc[0]["일반필름"]) if is_edit else 0)
    v_ff = c2.number_input("풀필름", 0, value=int(existing_row.iloc[0]["풀필름"]) if is_edit else 0)
    v_j = c1.number_input("젤리", 0, value=int(existing_row.iloc[0]["젤리"]) if is_edit else 0)
    v_c = c2.number_input("케이블", 0, value=int(existing_row.iloc[0]["케이블"]) if is_edit else 0)
    v_a = st.number_input("어댑터", 0, value=int(existing_row.iloc[0]["어댑터"]) if is_edit else 0)
    
    save_col, off_col = st.columns([2, 1])
    save_btn = save_col.form_submit_button("✅ 실적 저장하기", use_container_width=True)
    off_btn = off_col.form_submit_button("🌴 휴무 설정", use_container_width=True)

# 4. 저장 로직 (일반 저장 vs 휴무 저장)
if save_btn or off_btn:
    conn = get_connection()
    c = conn.cursor()
    if off_btn:
        # 휴무일 경우 모든 수치 0으로 저장
        c.execute('''INSERT OR REPLACE INTO salary VALUES (?, ?, 0, 0, 0, 0, 0, 0, 0, ?)''',
                  (user_name, str_date, "휴무"))
    else:
        daily_sum = st.session_state.current_incen_sum + (v_nf*9000) + (v_ff*18000) + (v_j*9000) + (v_c*15000) + (v_a*23000)
        c.execute('''INSERT OR REPLACE INTO salary VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (user_name, str_date, st.session_state.current_incen_sum, v_nf, v_ff, v_j, v_c, v_a, daily_sum, "정상"))
    conn.commit()
    conn.close()
    st.rerun()

# --- 정산 현황 ---
st.divider()
st.subheader("📊 정산 현황")
# (정산 기간 계산 및 요약 지표 출력 로직은 기존과 동일)
if selected_date.day >= 13:
    start_dt = date(selected_date.year, selected_date.month, 13)
    next_month = selected_date.replace(day=28) + timedelta(days=20)
    end_dt = next_month.replace(day=12)
else:
    end_dt = selected_date.replace(day=12)
    last_month = selected_date.replace(day=1) - timedelta(days=10)
    start_dt = last_month.replace(day=13)

df_all = load_data(user_name)
if not df_all.empty:
    df_all['날짜_dt'] = pd.to_datetime(df_all['날짜']).dt.date
    period_df = df_all[(df_all['날짜_dt'] >= start_dt) & (df_all['날짜_dt'] <= end_dt)].sort_values("날짜", ascending=False)
    
    if not period_df.empty:
        total_extra = period_df["합계"].sum()
        c_res1, c_res2 = st.columns(2)
        c_res1.metric("누적 수당", f"{total_extra:,}원")
        c_res2.metric("실수령액", f"{int(BASE_SALARY + total_extra - INSURANCE):,}원")
        
        for idx, row in period_df.iterrows():
            title = f"📅 {row['날짜']} " + ("(🌴 휴무)" if row['비고']=="휴무" else f"(합계: {row['합계']:,}원)")
            with st.expander(title):
                if row['비고'] == "휴무":
                    st.write("이날은 휴무로 기록되었습니다.")
                else:
                    st.write(f"🔹 **기본 인센**: {row['인센티브']:,}원")
                    st.write(f"🔹 **필름**: 일반 {row['일반필름']} / 풀 {row['풀필름']}")
                    st.write(f"🔹 **기타**: 젤리 {row['젤리']} / 케이블 {row['케이블']} / 어댑터 {row['어댑터']}")
