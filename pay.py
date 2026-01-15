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

user_name = st.session_state.user_name

# --- 가로 정렬 및 표 슬림화 CSS ---
st.markdown("""
    <style>
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 5px !important;
    }
    /* 제출용 표 스타일: 칸 간격을 극한으로 줄임 */
    .compact-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 11px;
        table-layout: fixed; /* 칸 너비 고정 */
    }
    .compact-table th, .compact-table td {
        border: 1px solid #ddd;
        padding: 3px 1px !important; /* 위아래 3px, 좌우 1px */
        text-align: center;
        overflow: hidden;
        white-space: nowrap;
    }
    .bg-header { background-color: #f1f3f5; font-weight: bold; }
    .bg-off { background-color: #f9f9f9; color: #ccc; }
    .text-sum { font-weight: bold; color: #ff4b4b; }
    </style>
    """, unsafe_allow_html=True)

# 1. 상단 입력 (기존 로직 유지)
st.write(f"### 💼 {user_name}님 실적")
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

# 인센 계산 및 입력 (생략 없이 유지)
if "current_incen_sum" not in st.session_state or st.session_state.get("last_date") != str_date:
    st.session_state.current_incen_sum = int(existing_row.iloc[0]["인센티브"]) if is_edit else 0
    st.session_state.incen_history = [int(existing_row.iloc[0]["인센티브"])] if is_edit and existing_row.iloc[0]["인센티브"] > 0 else []
    st.session_state.last_date = str_date

st.markdown(f"**💰 인센 합계: {st.session_state.current_incen_sum:,}원**")
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
    c.execute('''INSERT OR REPLACE INTO salary VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (user_name, str_date, st.session_state.current_incen_sum, v_nf, v_ff, v_j, v_c, v_a, daily_sum, "정상"))
    conn.commit()
    conn.close()
    st.success("저장 성공!")
    st.rerun()

# 2. 정산 현황 및 초슬림 표
st.divider()
st.subheader("📊 정산 및 제출용")
BASE_SALARY, INSURANCE = 3500000, 104760

if selected_date.day >= 13:
    start_dt = date(selected_date.year, selected_date.month, 13)
    next_month = selected_date.replace(day=28) + timedelta(days=20)
    end_dt = next_month.replace(day=12)
else:
    end_dt = selected_date.replace(day=12)
    last_month = selected_date.replace(day=1) - timedelta(days=10)
    start_dt = last_month.replace(day=13)

df_now = pd.read_sql("SELECT * FROM salary WHERE 직원명 = ?", get_connection(), params=(user_name,))
if not df_now.empty:
    df_now['날짜_dt'] = pd.to_datetime(df_now['날짜']).dt.date
    period_df = df_now[(df_now['날짜_dt'] >= start_dt) & (df_now['날짜_dt'] <= end_dt)].sort_values("날짜", ascending=True)
    
    if not period_df.empty:
        total_extra = period_df["합계"].sum()
        final_pay = int(BASE_SALARY + total_extra - INSURANCE)
        
        # 금액 크게 표시
        st.write(f"**💰 누적 수당: {total_extra:,}원**")
        st.markdown(f"<h2 style='color:#ff4b4b; margin-top:-10px;'>🏦 {final_pay:,}원</h2>", unsafe_allow_html=True)
        
        st.write("**📄 제출용 상세 (한 장 스샷용)**")
        
        # --- [핵심] 초슬림 테이블 구현 ---
        html_code = """
        <table class="compact-table">
            <tr class="bg-header">
                <th style="width:13%;">날짜</th><th style="width:17%;">인센</th>
                <th>일</th><th>풀</th><th>젤</th><th>케</th><th>어</th>
                <th style="width:17%;">합계</th>
            </tr>
        """
        for _, row in period_df.iterrows():
            is_off = row['비고'] == "휴무"
            m_d = row['날짜'][5:]
            if is_off:
                html_code += f"<tr class='bg-off'><td>{m_d}</td><td colspan='6'>🌴 휴 무</td><td class='text-sum'>-</td></tr>"
            else:
                html_code += f"""
                <tr>
                    <td>{m_d}</td>
                    <td>{row['인센티브']:,}</td>
                    <td>{row['일반필름']}</td>
                    <td>{row['풀필름']}</td>
                    <td>{row['젤리']}</td>
                    <td>{row['케이블']}</td>
                    <td>{row['어댑터']}</td>
                    <td class="text-sum">{row['합계']:,}</td>
                </tr>
                """
        html_code += "</table>"
        
        # 깨짐 방지: 한 줄로 묶어서 마크다운 출력
        st.markdown(html_code, unsafe_allow_html=True)

st.divider()
st.caption("가로 폭을 최소화하여 아이폰 한 화면에 쏙 들어오게 맞췄습니다.")
