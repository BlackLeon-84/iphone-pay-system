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
    try:
        c.execute("SELECT 비고 FROM salary LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("DROP TABLE IF EXISTS salary")
    
    c.execute('''CREATE TABLE IF NOT EXISTS salary
                 (직원명 TEXT, 날짜 TEXT, 인센티브 INTEGER, 일반필름 INTEGER, 
                  풀필름 INTEGER, 젤리 INTEGER, 케이블 INTEGER, 어댑터 INTEGER, 
                  합계 INTEGER, 비고 TEXT, PRIMARY KEY(직원명, 날짜))''')
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
        user_id = st.selectbox("직원을 선택하세요", options=STAFF_LIST)
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

# 1. 데이터 로드
def load_data(name):
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM salary WHERE 직원명 = ?", conn, params=(name,))
    conn.close()
    return df

df_all = load_data(user_name)

# 2. 상단 날짜 배지 (디자인 개선)
st.subheader("🗓️ 최근 1주일 현황")
badge_cols = st.columns(7)

for i in range(7):
    check_date = date.today() - timedelta(days=6-i)
    str_check = check_date.strftime("%Y-%m-%d")
    
    target_row = df_all[df_all["날짜"] == str_check]
    
    # 상태 판별 및 색상 설정
    if not target_row.empty:
        if target_row.iloc[0]["비고"] == "휴무":
            bg_color, label = "#E1F5FE", "💤" # 파랑 (휴무)
            text_color = "#01579B"
        else:
            bg_color, label = "#E8F5E9", "✅" # 초록 (완료)
            text_color = "#1B5E20"
    else:
        bg_color, label = "#FFEBEE", "⚠️" # 빨강 (미기입)
        text_color = "#B71C1C"

    with badge_cols[i]:
        # HTML/CSS를 이용한 카드형 배지 디자인
        st.markdown(
            f"""
            <div style="
                background-color: {bg_color};
                border-radius: 10px;
                padding: 10px 5px;
                text-align: center;
                border: 1px solid {text_color}33;
            ">
                <p style="margin:0; font-size:11px; color:{text_color}; font-weight:bold;">{check_date.strftime('%m/%d')}</p>
                <p style="margin:2px 0; font-size:18px;">{label}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

st.divider()

# 3. 날짜 선택 및 입력 세션 관리
selected_date = st.date_input("📅 날짜 선택 (기입/수정)", value=date.today())
str_date = selected_date.strftime("%Y-%m-%d")

existing_row = df_all[df_all["날짜"] == str_date]
is_edit = not existing_row.empty
is_off = is_edit and existing_row.iloc[0]["비고"] == "휴무"

if "current_incen_sum" not in st.session_state or st.session_state.get("last_date") != str_date:
    st.session_state.current_incen_sum = int(existing_row.iloc[0]["인센티브"]) if is_edit else 0
    st.session_state.incen_history = [int(existing_row.iloc[0]["인센티브"])] if is_edit and existing_row.iloc[0]["인센티브"] > 0 else []
    st.session_state.last_date = str_date

# 4. 입력 폼
with st.form("input_form"):
    if is_off:
        st.info(f"🌴 {str_date}은 '휴무' 상태입니다.")
    
    st.markdown(f"### 💵 인센 합계: `{st.session_state.current_incen_sum:,}`원")
    if st.session_state.incen_history:
        st.caption(f"🕒 내역: {' > '.join([f'{amt:,}' for amt in st.session_state.incen_history])}")

    add_amount = st.number_input("추가 금액", min_value=0, step=1000, value=1000)
    c_inc1, c_inc2, c_inc3 = st.columns(3)
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
    save_btn = save_col.form_submit_button("✅ 실적 저장", use_container_width=True)
    off_btn = off_col.form_submit_button("🌴 휴무", use_container_width=True)

# 5. 저장 로직
if save_btn or off_btn:
    conn = get_connection()
    c = conn.cursor()
    if off_btn:
        c.execute('''INSERT OR REPLACE INTO salary VALUES (?, ?, 0, 0, 0, 0, 0, 0, 0, ?)''',
                  (user_name, str_date, "휴무"))
    else:
        daily_sum = st.session_state.current_incen_sum + (v_nf*9000) + (v_ff*18000) + (v_j*9000) + (v_c*15000) + (v_a*23000)
        c.execute('''INSERT OR REPLACE INTO salary VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (user_name, str_date, st.session_state.current_incen_sum, v_nf, v_ff, v_j, v_c, v_a, daily_sum, "정상"))
    conn.commit()
    conn.close()
    st.rerun()

# 6. 정산 현황
st.divider()
st.subheader("📊 정산 현황")
if selected_date.day >= 13:
    start_dt = date(selected_date.year, selected_date.month, 13)
    next_month = selected_date.replace(day=28) + timedelta(days=20)
    end_dt = next_month.replace(day=12)
else:
    end_dt = selected_date.replace(day=12)
    last_month = selected_date.replace(day=1) - timedelta(days=10)
    start_dt = last_month.replace(day=13)

df_now = load_data(user_name)
if not df_now.empty:
    df_now['날짜_dt'] = pd.to_datetime(df_now['날짜']).dt.date
    period_df = df_now[(df_now['날짜_dt'] >= start_dt) & (df_now['날짜_dt'] <= end_dt)].sort_values("날짜", ascending=False)
    
    if not period_df.empty:
        total_extra = period_df["합계"].sum()
        c_res1, c_res2 = st.columns(2)
        c_res1.metric("누적 수당", f"{total_extra:,}원")
        c_res2.metric("실수령액", f"{int(BASE_SALARY + total_extra - INSURANCE):,}원")
        
        for idx, row in period_df.iterrows():
            is_off_row = row['비고'] == "휴무"
            title = f"📅 {row['날짜']} " + ("(🌴 휴무)" if is_off_row else f"({row['합계']:,}원)")
            with st.expander(title):
                if is_off_row: st.write("휴무")
                else:
                    st.write(f"🔹 **인센**: {row['인센티브']:,}원 | **필름**: {row['일반필름']}/{row['풀필름']}")
                    st.write(f"🔹 **기타**: 젤리{row['젤리']} 케이블{row['케이블']} 어댑터{row['어댑터']}")
