import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import sqlite3

# 페이지 설정
st.set_page_config(page_title="급여 정산 시스템", layout="centered")

# --- 로컬 데이터베이스 연결 (영구 저장용) ---
def get_connection():
    return sqlite3.connect("data.db", check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS salary
                 (날짜 TEXT PRIMARY KEY, 인센티브 INTEGER, 일반필름 INTEGER, 
                  풀필름 INTEGER, 젤리 INTEGER, 케이블 INTEGER, 어댑터 INTEGER, 합계 INTEGER)''')
    conn.commit()
    conn.close()

init_db()

# 고정 수치
BASE_SALARY = 3500000
INSURANCE = 104760

st.title("💼 월급 정산 시스템 (영구 저장형)")

# 1. 날짜 선택
selected_date = st.date_input("근무 날짜", value=date.today())
str_date = selected_date.strftime("%Y-%m-%d")

# 2. 데이터 불러오기 함수
def load_data():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM salary", conn)
    conn.close()
    return df

df = load_data()
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
    
    save_btn = st.form_submit_button("✅ 이 날짜 데이터 저장하기")

# 4. 저장 로직 (SQLite 사용)
if save_btn:
    daily_sum = v_incen + (v_nf*9000) + (v_ff*18000) + (v_j*9000) + (v_c*15000) + (v_a*23000)
    conn = get_connection()
    c = conn.cursor()
    # 이미 있으면 덮어쓰기(REPLACE)
    c.execute('''INSERT OR REPLACE INTO salary VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
              (str_date, v_incen, v_nf, v_ff, v_j, v_c, v_a, daily_sum))
    conn.commit()
    conn.close()
    st.success(f"✅ {str_date} 데이터가 안전하게 저장되었습니다!")
    st.rerun()

# 5. 정산 주기 계산
if selected_date.day >= 13:
    start_dt = date(selected_date.year, selected_date.month, 13)
    end_dt = (selected_date.replace(day=28) + timedelta(days=20)).replace(day=12)
else:
    end_dt = selected_date.replace(day=12)
    start_dt = (selected_date.replace(day=1) - timedelta(days=1)).replace(day=13)

st.divider()
st.subheader(f"📊 정산 현황 ({start_dt.strftime('%m/%d')} ~ {end_dt.strftime('%m/%d')})")

# 6. 필터링 및 출력
df = load_data()
if not df.empty:
    df['날짜_dt'] = pd.to_datetime(df['날짜']).dt.date
    period_df = df[(df['날짜_dt'] >= start_dt) & (df['날짜_dt'] <= end_dt)]
    
    if not period_df.empty:
        st.dataframe(period_df.drop(columns=['날짜_dt']).sort_values("날짜", ascending=False), use_container_width=True)
        total_extra = period_df["합계"].sum()
        c1, c2 = st.columns(2)
        c1.metric("누적 수당", f"{total_extra:,}원")
        c2.metric("예상 실수령액", f"{int(BASE_SALARY + total_extra - INSURANCE):,}원")
    else:
        st.info("기록된 데이터가 없습니다.")

    st.divider()
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 백업용 전체 데이터 다운로드", csv, "salary_backup.csv", "text/csv")
