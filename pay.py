import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3

# 페이지 설정
st.set_page_config(page_title="아이폰 정산 시스템", layout="centered")

# --- 데이터베이스 및 기본 설정 ---
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

# --- 로그인 세션 ---
STAFF_LIST = ["성훈", "남근"]
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if not st.session_state.logged_in:
    st.title("🔐 로그인")
    with st.form("login_form"):
        user_id = st.selectbox("직원 선택", options=STAFF_LIST)
        if st.form_submit_button("입장하기"):
            st.session_state.logged_in = True
            st.session_state.user_name = user_id
            st.rerun()
    st.stop()

user_name = st.session_state.user_name

# --- 메인 메뉴 (기입용 / 스샷용 분리) ---
menu = st.radio("모드 선택", ["📝 실적 기입", "📸 제출용 스샷"], horizontal=True)

# 1. [📝 실적 기입 모드] - 태완님이 쓰시던 기존 디자인 그대로 유지
if menu == "📝 실적 기입":
    # 가로 버튼용 간단 CSS (기입 페이지에만 적용)
    st.markdown("<style>div[data-testid='stHorizontalBlock']{display:flex!important;flex-direction:row!important;gap:5px!important;}</style>", unsafe_allow_html=True)
    
    st.write(f"### 💼 {user_name}님 기입현황")
    
    # 날짜 및 휴무
    top_c1, top_c2 = st.columns([2, 1])
    selected_date = top_c1.date_input("날짜", value=date.today(), label_visibility="collapsed")
    str_date = selected_date.strftime("%Y-%m-%d")
    
    df_all = pd.read_sql("SELECT * FROM salary WHERE 직원명 = ?", get_connection(), params=(user_name,))
    existing_row = df_all[df_all["날짜"] == str_date]
    is_edit = not existing_row.empty
    
    if top_c2.button("🌴 휴무", use_container_width=True):
        conn = get_connection()
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO salary VALUES (?, ?, 0, 0, 0, 0, 0, 0, 0, ?)''', (user_name, str_date, "휴무"))
        conn.commit()
        conn.close()
        st.rerun()

    # 인센티브 계산부
    if "current_incen_sum" not in st.session_state or st.session_state.get("last_date") != str_date:
        st.session_state.current_incen_sum = int(existing_row.iloc[0]["인센티브"]) if is_edit else 0
        st.session_state.incen_history = [int(existing_row.iloc[0]["인센티브"])] if is_edit and existing_row.iloc[0]["인센티브"] > 0 else []
        st.session_state.last_date = str_date

    st.write(f"**💰 인센 합계: {st.session_state.current_incen_sum:,}원**")
    add_amount = st.number_input("금액 입력", min_value=0, step=1000, value=1000, label_visibility="collapsed")
    
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

    # 판매 수량
    f_c1, f_c2 = st.columns(2)
    v_nf = f_c1.number_input("일반필름", 0, value=int(existing_row.iloc[0]["일반필름"]) if is_edit else 0)
    v_ff = f_c2.number_input("풀필름", 0, value=int(existing_row.iloc[0]["풀필름"]) if is_edit else 0)
    v_j = f_c1.number_input("젤리", 0, value=int(existing_row.iloc[0]["젤리"]) if is_edit else 0)
    v_c = f_c2.number_input("케이블", 0, value=int(existing_row.iloc[0]["케이블"]) if is_edit else 0)
    v_a = st.number_input("어댑터", 0, value=int(existing_row.iloc[0]["어댑터"]) if is_edit else 0)

    if st.button("✅ 실적 저장", use_container_width=True, type="primary"):
        daily_sum = st.session_state.current_incen_sum + (v_nf*9000) + (v_ff*18000) + (v_j*9000) + (v_c*15000) + (v_a*23000)
        conn = get_connection()
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO salary VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (user_name, str_date, st.session_state.current_incen_sum, v_nf, v_ff, v_j, v_c, v_a, daily_sum, "정상"))
        conn.commit()
        conn.close()
        st.success("저장되었습니다!")
        st.rerun()

# 2. [📸 제출용 스샷 모드] - 오직 스샷을 위한 전용 디자인
else:
    st.write(f"### 📸 {user_name}님 정산 리포트")
    
    # 정산 기준일 선택 (이 날짜를 기준으로 기간 자동 계산)
    report_date = st.date_input("정산 기준일 선택", value=date.today())
    
    if report_date.day >= 13:
        start_dt, end_dt = date(report_date.year, report_date.month, 13), (report_date.replace(day=28) + timedelta(days=20)).replace(day=12)
    else:
        end_dt, start_dt = report_date.replace(day=12), (report_date.replace(day=1) - timedelta(days=10)).replace(day=13)
    
    df_now = pd.read_sql("SELECT * FROM salary WHERE 직원명 = ?", get_connection(), params=(user_name,))
    if not df_now.empty:
        df_now['날짜_dt'] = pd.to_datetime(df_now['날짜']).dt.date
        period_df = df_now[(df_now['날짜_dt'] >= start_dt) & (df_now['날짜_dt'] <= end_dt)].sort_values("날짜", ascending=True)
        
        if not period_df.empty:
            BASE_SALARY, INSURANCE = 3500000, 104760
            total_extra = period_df["합계"].sum()
            final_pay = int(BASE_SALARY + total_extra - INSURANCE)
            
            # [스샷 포인트 1] 실수령액을 아주 크게!
            st.metric(label="🏦 예상 실수령액 (기본급 포함)", value=f"{final_pay:,}원")
            st.write(f"📅 기간: {start_dt} ~ {end_dt} | 수당합계: {total_extra:,}원")
            
            # [스샷 포인트 2] 표 칸 너비와 폰트를 스샷에 최적화 (순정 table 활용)
            st.write("**📄 일별 상세 내역**")
            
            rep_df = period_df.copy()
            rep_df['날짜'] = rep_df['날짜'].apply(lambda x: x[5:]) # MM-DD
            rep_df = rep_df[['날짜', '인센티브', '일반필름', '풀필름', '젤리', '케이블', '어댑터', '합계']]
            rep_df.columns = ['날짜', '인센', '일', '풀', '젤', '케', '어', '합계']
            
            # 콤마 처리
            rep_df['인센'] = rep_df['인센'].apply(lambda x: f"{x:,}")
            rep_df['합계'] = rep_df['합계'].apply(lambda x: f"{x:,}")
            
            # 스샷용 고정 표
            st.table(rep_df)
            
            st.caption("위 화면을 스크린샷 찍어서 제출하세요.")
        else:
            st.warning("해당 기간에 저장된 데이터가 없습니다.")
