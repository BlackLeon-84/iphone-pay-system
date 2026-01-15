import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date, timedelta

# 1. 페이지 설정
st.set_page_config(page_title="급여 정산 시스템", layout="centered")

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. 데이터 읽어오기 (가장 앞에 있는 시트)
try:
    df = conn.read(worksheet=0)
except:
    df = pd.DataFrame(columns=["날짜", "인센티브", "일반필름", "풀필름", "젤리", "케이블", "어댑터", "합계"])

# 고정 수치
BASE_SALARY = 3500000
INSURANCE = 104760

st.title("💼 월급 정산 시스템")

# 4. 날짜 및 입력
selected_date = st.date_input("근무 날짜", value=date.today())
str_date = selected_date.strftime("%Y-%m-%d")

with st.form("input_form"):
    v_incen = st.number_input("기본 인센티브", min_value=0, value=0)
    col1, col2 = st.columns(2)
    with col1:
        v_nf = st.number_input("일반필름", 0)
        v_ff = st.number_input("풀필름", 0)
        v_j = st.number_input("젤리", 0)
    with col2:
        v_c = st.number_input("케이블", 0)
        v_a = st.number_input("어댑터", 0)
    
    save_btn = st.form_submit_button("저장하기")

# 5. 저장 시도 (가장 단순한 방식으로 변경)
if save_btn:
    daily_sum = v_incen + (v_nf*9000) + (v_ff*18000) + (v_j*9000) + (v_c*15000) + (v_a*23000)
    new_data = pd.DataFrame([[str_date, v_incen, v_nf, v_ff, v_j, v_c, v_a, daily_sum]], 
                            columns=["날짜", "인센티브", "일반필름", "풀필름", "젤리", "케이블", "어댑터", "합계"])
    
    # 중복 날짜 제거 후 합치기
    if not df.empty:
        df = df[df["날짜"].astype(str) != str_date]
    updated_df = pd.concat([df, new_data], ignore_index=True)
    
    # 여기서 에러가 나면 구글 보안 문제입니다.
    try:
        conn.update(data=updated_df)
        st.success("✅ 저장되었습니다!")
        st.rerun()
    except Exception as e:
        st.error("저장 실패. 구글 시트 공유 설정을 [편집자]로 바꿨는지 다시 확인해주세요.")
        st.info(f"에러 내용: {e}")

# 6. 현황 출력
st.divider()
if not df.empty:
    st.write("### 최근 기록")
    st.dataframe(df.sort_values("날짜", ascending=False).head(5), use_container_width=True)
