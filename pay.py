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

# --- 로그인 (비밀번호 없음 테스트 버전) ---
STAFF_LIST = ["성훈", "남근"]
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_name = ""

if not st.session_state.logged_in:
    st.title("🔐 로그인")
    with st.form("login_form"):
        user_id = st.selectbox("직원 선택", options=STAFF_LIST)
        if st.form_submit_button("입장하기", use_container_width=True):
            st.session_state.logged_in = True
            st.session_state.user_name = user_id
            st.rerun()
    st.stop()

# --- 메인 로직 ---
user_name = st.session_state.user_name

# 1. 최상단: 날짜 선택 및 휴무 버튼 (가로 정렬)
st.write(f"### 💼 {user_name}님 실적")
top_c1, top_c2 = st.columns([2, 1])
selected_date = top_c1.date_input("날짜", value=date.today(), label_visibility="collapsed")
str_date = selected_date.strftime("%Y-%m-%d")

# 데이터 로드
def load_data(name):
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM salary WHERE 직원명 = ?", conn, params=(name,))
    conn.close()
    return df

df_all = load_data(user_name)
existing_row = df_all[df_all["날짜"] == str_date]
is_edit = not existing_row.empty
is_off = is_edit and existing_row.iloc[0]["비고"] == "휴무"

if top_c2.button("🌴 휴무", use_container_width=True):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO salary VALUES (?, ?, 0, 0, 0, 0, 0, 0, 0, ?)''',
              (user_name, str_date, "휴무"))
    conn.commit()
    conn.close()
    st.rerun()

# 2. [요청반영] 1주일 현황 아이콘화 (가로 한 줄 배치)
# 아이콘 형태로 아주 작게 배치하여 공간 절약
st.write("") 
badge_cols = st.columns(7)
for i in range(7):
    check_date = date.today() - timedelta(days=6-i)
    str_check = check_date.strftime("%Y-%m-%d")
    target_row = df_all[df_all["날짜"] == str_check]
    
    icon, color, bg = "⚪", "#ccc", "#f0f0f0" # 미기입
    if not target_row.empty:
        if target_row.iloc[0]["비고"] == "휴무":
            icon, color, bg = "💤", "#007bff", "#e1f5fe"
        else:
            icon, color, bg = "✅", "#28a745", "#e8f5e9"
    
    with badge_cols[i]:
        st.markdown(f"""
            <div style="text-align:center; padding:5px 2px; background:{bg}; border-radius:5px; border:1px solid {color}55;">
                <div style="font-size:10px; font-weight:bold; color:{color};">{check_date.day}</div>
                <div style="font-size:12px;">{icon}</div>
            </div>
        """, unsafe_allow_html=True)

st.divider()

# 3. 인센티브 입력 섹션 (가로 버튼 배치)
if "current_incen_sum" not in st.session_state or st.session_state.get("last_date") != str_date:
    st.session_state.current_incen_sum = int(existing_row.iloc[0]["인센티브"]) if is_edit else 0
    st.session_state.incen_history = [int(existing_row.iloc[0]["인센티브"])] if is_edit and existing_row.iloc[0]["인센티브"] > 0 else []
    st.session_state.last_date = str_date

st.markdown(f"**💰 인센 합계: {st.session_state.current_incen_sum:,}원**")
if st.session_state.incen_history:
    st.caption(f"📜 {' > '.join([f'{amt:,}' for amt in st.session_state.incen_history])}")

add_amount = st.number_input("금액 입력", min_value=0, step=1000, value=1000, label_visibility="collapsed")

# [요청반영] 추가, 취소, 리셋 가로 한 줄 정렬
btn_c1, btn_c2, btn_c3 = st.columns(3)
if btn_c1.button("➕ 추가", use_container_width=True):
    st.session_state.current_incen_sum += add_amount
    st.session_state.incen_history.append(add_amount)
    st.rerun()
if btn_c2.button("↩️ 취소", use_container_width=True) and st.session_state.incen_history:
    st.session_state.current_incen_sum -= st.session_state.incen_history.pop()
    st.rerun()
if btn_c3.button("🧹 리셋", use_container_width=True):
    st.session_state.current_incen_sum = 0
    st.session_state.incen_history = []
    st.rerun()

st.write("")

# 4. 필름 및 기타 (압축 2열)
with st.container():
    f_c1, f_c2 = st.columns(2)
    v_nf = f_c1.number_input("일반필름", 0, value=int(existing_row.iloc[0]["일반필름"]) if is_edit else 0)
    v_ff = f_c2.number_input("풀필름", 0, value=int(existing_row.iloc[0]["풀필름"]) if is_edit else 0)
    v_j = f_c1.number_input("젤리", 0, value=int(existing_row.iloc[0]["젤리"]) if is_edit else 0)
    v_c = f_c2.number_input("케이블", 0, value=int(existing_row.iloc[0]["케이블"]) if is_edit else 0)
    v_a = st.number_input("어댑터", 0, value=int(existing_row.iloc[0]["어댑터"]) if is_edit else 0)
    
    if st.button("✅ 최종 실적 저장", use_container_width=True, type="primary"):
        daily_sum = st.session_state.current_incen_sum + (v_nf*9000) + (v_ff*18000) + (v_j*9000) + (v_c*15000) + (v_a*23000)
        conn = get_connection()
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO salary VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (user_name, str_date, st.session_state.current_incen_sum, v_nf, v_ff, v_j, v_c, v_a, daily_sum, "정상"))
        conn.commit()
        conn.close()
        st.success("저장 성공!")
        st.rerun()

# 5. 하단 정산 (생략 가능하도록 접기 메뉴 활용)
st.divider()
with st.expander("📊 이번 달 정산 요약 정보 확인", expanded=True):
    # 정산 기간 (13일~12일)
    if selected_date.day >= 13:
        start_dt = date(selected_date.year, selected_date.month, 13)
        next_month = selected_date.replace(day=28) + timedelta(days=20)
        end_dt = next_month.replace(day=12)
    else:
        end_dt = selected_date.replace(day=12)
        last_month = selected_date.replace(day=1) - timedelta(days=10)
        start_dt = last_month.replace(day=13)

    period_df = df_all.copy()
    if not period_df.empty:
        period_df['날짜_dt'] = pd.to_datetime(period_df['날짜']).dt.date
        period_df = period_df[(period_df['날짜_dt'] >= start_dt) & (period_df['날짜_dt'] <= end_dt)]
        total_extra = period_df["합계"].sum()
        
        st.metric("예상 실수령액", f"{int(3500000 + total_extra - 104760):,}원")
        st.caption(f"기간: {start_dt} ~ {end_dt}")
