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

# --- 가로 정렬 CSS ---
st.markdown("""
    <style>
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 5px !important;
    }
    div[data-testid="stHorizontalBlock"] > div {
        flex: 1 1 0% !important;
        min-width: 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 1. 상단: 날짜 및 휴무
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

# 2. 최근 기입 현황
st.write("**🗓️ 최근 기입 현황**")
table_html = """<table style="width:100%; border-collapse: collapse; table-layout: fixed;"><tr style="background-color: #f8f9fa;">"""
for i in range(7):
    d = date.today() - timedelta(days=6-i)
    table_html += f"<th style='border:1px solid #ddd; padding:5px; font-size:10px; text-align:center;'>{d.day}일</th>"
table_html += "</tr><tr>"
for i in range(7):
    d = date.today() - timedelta(days=6-i)
    str_check = d.strftime("%Y-%m-%d")
    target_row = df_all[df_all["날짜"] == str_check]
    icon, bg = "⚪", "#ffffff"
    if not target_row.empty:
        if target_row.iloc[0]["비고"] == "휴무": icon, bg = "💤", "#e1f5fe"
        else: icon, bg = "✅", "#e8f5e9"
    table_html += f"<td style='border:1px solid #ddd; padding:8px; text-align:center; background-color:{bg}; font-size:16px;'>{icon}</td>"
table_html += "</tr></table>"
st.markdown(table_html, unsafe_allow_html=True)

st.divider()

# 3. 인센티브 및 수량 입력
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

# 4. 정산 현황 및 상세 리포트 통합
st.divider()
st.subheader("📊 정산 및 제출 리포트")
BASE_SALARY, INSURANCE = 3500000, 104760

if selected_date.day >= 13:
    start_dt, end_dt = date(selected_date.year, selected_date.month, 13), (selected_date.replace(day=28) + timedelta(days=20)).replace(day=12)
else:
    end_dt, start_dt = selected_date.replace(day=12), (selected_date.replace(day=1) - timedelta(days=10)).replace(day=13)

period_df = df_all[(pd.to_datetime(df_all['날짜']).dt.date >= start_dt) & (pd.to_datetime(df_all['날짜']).dt.date <= end_dt)].sort_values("날짜", ascending=True)

if not period_df.empty:
    total_extra = period_df["합계"].sum()
    final_pay = int(BASE_SALARY + total_extra - INSURANCE)
    
    st.markdown(f"""
        <div style="background-color:#f0f2f6; padding:15px; border-radius:10px; border-left:5px solid #ff4b4b; margin-bottom:15px;">
            <p style="margin:0; font-size:12px; color:#666;">정산 기간: {start_dt} ~ {end_dt}</p>
            <p style="margin:5px 0; font-size:18px; font-weight:bold;">💰 총 수당(인센+판매): {total_extra:,}원</p>
            <p style="margin:0; font-size:22px; font-weight:bold; color:#ff4b4b;">🏦 최종 실수령액: {final_pay:,}원</p>
        </div>
    """, unsafe_allow_html=True)
    
    # [제출용 표] 제목 복구 및 간격 최적화
    html_code = """<table style="width:100%; border-collapse:collapse; table-layout:fixed; font-size:10px; text-align:center;">
        <tr style="background-color:#f8f9fa; border-bottom:2px solid #ddd;">
            <th style="padding:4px; border:1px solid #eee; width:14%;">날짜</th>
            <th style="padding:4px; border:1px solid #eee;">인센티브</th>
            <th style="padding:4px; border:1px solid #eee;">일반</th>
            <th style="padding:4px; border:1px solid #eee;">풀</th>
            <th style="padding:4px; border:1px solid #eee;">젤리</th>
            <th style="padding:4px; border:1px solid #eee;">케이블</th>
            <th style="padding:4px; border:1px solid #eee;">어댑터</th>
            <th style="padding:4px; border:1px solid #eee;">합계</th>
        </tr>"""
    
    for _, r in period_df.iterrows():
        d_short = r['날짜'][5:]
        html_code += f"""<tr style="border-bottom:1px solid #eee;">
            <td style="padding:4px; border:1px solid #eee;">{d_short}</td>
            <td style="padding:4px; border:1px solid #eee;">{r['인센티브']:,}</td>
            <td style="padding:4px; border:1px solid #eee;">{r['일반필름']}</td>
            <td style="padding:4px; border:1px solid #eee;">{r['풀필름']}</td>
            <td style="padding:4px; border:1px solid #eee;">{r['젤리']}</td>
            <td style="padding:4px; border:1px solid #eee;">{r['케이블']}</td>
            <td style="padding:4px; border:1px solid #eee;">{r['어댑터']}</td>
            <td style="padding:4px; border:1px solid #eee; font-weight:bold;">{r['합계']:,}</td>
        </tr>"""
    html_code += "</table>"
    st.markdown(html_code, unsafe_allow_html=True)
    
    st.write("")
    
    # [개별 상세 기록] 항목 순서 맞춤
    st.write("**📝 개별 상세 기록 (최신순)**")
    for _, row in period_df.sort_values("날짜", ascending=False).iterrows():
        is_off = row['비고'] == "휴무"
        title = f"📅 {row['날짜']} ({row['합계']:,}원)" if not is_off else f"📅 {row['날짜']} (🌴 휴무)"
        with st.expander(title):
            if is_off: st.write("휴무")
            else:
                # 위 표와 동일하게 인센티브부터 순서대로 표시
                st.write(f"💰 **인센티브**: {row['인센티브']:,}원")
                st.write(f"📱 **필름**: 일반 {row['일반필름']} / 풀 {row['풀필름']}")
                st.write(f"🔌 **기타**: 젤리 {row['젤리']} / 케이블 {row['케이블']} / 어댑터 {row['어댑터']}")
