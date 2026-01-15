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

# --- 로그인 ---
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

# 1. 최상단: 날짜 선택 및 휴무 버튼 (가로 배치)
st.subheader("📅 날짜 설정")
date_col, off_col = st.columns([2, 1])
selected_date = date_col.date_input("날짜 선택", value=date.today(), label_visibility="collapsed")
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

# 휴무 버튼을 상단에 배치
if off_col.button("🌴 휴무", use_container_width=True):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO salary VALUES (?, ?, 0, 0, 0, 0, 0, 0, 0, ?)''',
              (user_name, str_date, "휴무"))
    conn.commit()
    conn.close()
    st.rerun()

# 2. 최근 현황 (슬림한 2줄 배치)
st.write("")
badge_data = []
for i in range(8): # 오늘 포함 8일치
    check_date = date.today() - timedelta(days=7-i)
    str_check = check_date.strftime("%Y-%m-%d")
    target_row = df_all[df_all["날짜"] == str_check]
    
    status = "⚠️"
    bg = "#FFEBEE"
    if not target_row.empty:
        if target_row.iloc[0]["비고"] == "휴무":
            status, bg = "💤", "#E1F5FE"
        else:
            status, bg = "✅", "#E8F5E9"
    badge_data.append({"day": check_date.day, "status": status, "bg": bg})

# 4개씩 2줄로 표시
row1 = st.columns(4)
row2 = st.columns(4)
for idx, item in enumerate(badge_data):
    target_row = row1 if idx < 4 else row2
    with target_row[idx % 4]:
        st.markdown(f"""
            <div style="background-color:{item['bg']}; border-radius:5px; padding:2px; text-align:center; border:1px solid #ddd; margin-bottom:5px;">
                <p style="margin:0; font-size:10px;">{item['day']}일</p>
                <p style="margin:0; font-size:14px;">{item['status']}</p>
            </div>
        """, unsafe_allow_html=True)

st.divider()

# 3. 입력 세션 관리
if "current_incen_sum" not in st.session_state or st.session_state.get("last_date") != str_date:
    st.session_state.current_incen_sum = int(existing_row.iloc[0]["인센티브"]) if is_edit else 0
    st.session_state.incen_history = [int(existing_row.iloc[0]["인센티브"])] if is_edit and existing_row.iloc[0]["인센티브"] > 0 else []
    st.session_state.last_date = str_date

# 4. 실적 입력 (압축형)
with st.container():
    if is_off: st.warning(f"현재 {str_date}은 '휴무'입니다.")
    
    st.markdown(f"**💰 인센 합계: {st.session_state.current_incen_sum:,}원**")
    if st.session_state.incen_history:
        st.caption(f"📜 {' > '.join([f'{amt:,}' for amt in st.session_state.incen_history])}")

    add_amount = st.number_input("금액 입력", min_value=0, step=1000, value=1000, label_visibility="collapsed")
    
    # 버튼 3개를 한 줄로 가로 정렬
    btn_col1, btn_col2, btn_col3 = st.columns(3)
    if btn_col1.button("➕ 추가", use_container_width=True):
        st.session_state.current_incen_sum += add_amount
        st.session_state.incen_history.append(add_amount)
        st.rerun()
    if btn_col2.button("↩️ 취소", use_container_width=True) and st.session_state.incen_history:
        st.session_state.current_incen_sum -= st.session_state.incen_history.pop()
        st.rerun()
    if btn_col3.button("🧹 리셋", use_container_width=True):
        st.session_state.current_incen_sum = 0
        st.session_state.incen_history = []
        st.rerun()

    st.write("")
    # 필름 및 기타 항목 (2열 압축)
    c1, c2 = st.columns(2)
    v_nf = c1.number_input("일반필름", 0, value=int(existing_row.iloc[0]["일반필름"]) if is_edit else 0)
    v_ff = c2.number_input("풀필름", 0, value=int(existing_row.iloc[0]["풀필름"]) if is_edit else 0)
    v_j = c1.number_input("젤리", 0, value=int(existing_row.iloc[0]["젤리"]) if is_edit else 0)
    v_c = c2.number_input("케이블", 0, value=int(existing_row.iloc[0]["케이블"]) if is_edit else 0)
    v_a = st.number_input("어댑터", 0, value=int(existing_row.iloc[0]["어댑터"]) if is_edit else 0)
    
    if st.button("✅ 실적 저장 완료", use_container_width=True, type="primary"):
        daily_sum = st.session_state.current_incen_sum + (v_nf*9000) + (v_ff*18000) + (v_j*9000) + (v_c*15000) + (v_a*23000)
        conn = get_connection()
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO salary VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (user_name, str_date, st.session_state.current_incen_sum, v_nf, v_ff, v_j, v_c, v_a, daily_sum, "정상"))
        conn.commit()
        conn.close()
        st.success("저장되었습니다!")
        st.rerun()

# 5. 정산 현황 (하단 배치)
st.divider()
st.subheader("📊 이번 달 현황")
# (정산 기간 계산 로직은 이전과 동일)
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
    period_df = period_df[(period_df['날짜_dt'] >= start_dt) & (period_df['날짜_dt'] <= end_dt)].sort_values("날짜", ascending=False)
    
    if not period_df.empty:
        total_extra = period_df["합계"].sum()
        st.metric("예상 실수령액", f"{int(BASE_SALARY + total_extra - INSURANCE):,}원")
        
        for idx, row in period_df.iterrows():
            is_off_row = row['비고'] == "휴무"
            with st.expander(f"{row['날짜']} " + ("(🌴)" if is_off_row else f"({row['합계']:,}원)")):
                if is_off_row: st.write("휴무")
                else: st.write(f"인센:{row['인센티브']:,} | 필름:{row['일반필름']}/{row['풀필름']} | 기타:{row['젤리']}/{row['케이블']}/{row['어댑터']}")

st.sidebar.button("로그아웃", on_click=lambda: st.session_state.update({"logged_in": False}))
