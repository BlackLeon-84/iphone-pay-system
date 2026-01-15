import streamlit as st
import pandas as pd
from datetime import datetime, date

# 1. 초기 설정 및 세션 상태(임시 저장소) 초기화
if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=["날짜", "인센티브", "일반필름", "풀필름", "젤리", "케이블", "어댑터", "합계"])

BASE_SALARY = 3500000
INSURANCE = 104760
UNIT_PRICES = {"일반필름": 9000, "풀필름": 18000, "젤리": 9000, "케이블": 15000, "어댑터": 23000}

st.title("📱 급여 정산 및 로그 관리")

# 2. 날짜 선택 및 데이터 확인
st.header("🔍 데이터 확인 및 입력")
selected_date = st.date_input("날짜를 선택하세요", value=date.today())
str_date = selected_date.strftime("%Y-%m-%d")

# 해당 날짜에 데이터가 있는지 확인
existing_data = st.session_state.db[st.session_state.db["날짜"] == str_date]
is_edit = not existing_data.empty

if is_edit:
    st.warning(f"⚠️ {str_date}에 이미 입력된 데이터가 있습니다. 수정 후 다시 저장하세요.")
    row = existing_data.iloc[0]
else:
    st.info(f"✨ {str_date}은(는) 새로운 기록입니다.")

# 3. 입력 폼 (기존 데이터가 있으면 불러옴)
with st.form("input_form"):
    v_incen = st.number_input("기본 인센티브", min_value=0, value=int(row["인센티브"]) if is_edit else 0)
    col1, col2 = st.columns(2)
    with col1:
        v_nf = st.number_input("일반필름", min_value=0, value=int(row["일반필름"]) if is_edit else 0)
        v_ff = st.number_input("풀필름", min_value=0, value=int(row["풀필름"]) if is_edit else 0)
        v_j = st.number_input("젤리", min_value=0, value=int(row["젤리"]) if is_edit else 0)
    with col2:
        v_c = st.number_input("케이블", min_value=0, value=int(row["케이블"]) if is_edit else 0)
        v_a = st.number_input("어댑터", min_value=0, value=int(row["어댑터"]) if is_edit else 0)
    
    submit = st.form_submit_button("데이터 저장/수정")

# 4. 저장 로직
if submit:
    daily_sum = v_incen + (v_nf*9000) + (v_ff*18000) + (v_j*9000) + (v_c*15000) + (v_a*23000)
    new_row = [str_date, v_incen, v_nf, v_ff, v_j, v_c, v_a, daily_sum]
    
    if is_edit:
        st.session_state.db = st.session_state.db[st.session_state.db["날짜"] != str_date]
    
    st.session_state.db.loc[len(st.session_state.db)] = new_row
    st.success(f"{str_date} 기록이 저장되었습니다!")

# 5. 전체 로그 및 월급 합산 확인
st.divider()
st.subheader("📊 이번 달 전체 로그 (수정 확인용)")
if not st.session_state.db.empty:
    sorted_db = st.session_state.db.sort_values("날짜", ascending=False)
    st.dataframe(sorted_db, use_container_width=True)
    
    total_extra = st.session_state.db["합계"].sum()
    st.metric("현재까지 누적 수당", f"{total_extra:,}원")
    st.metric("최종 예상 실수령액", f"{BASE_SALARY + total_extra - INSURANCE:,}원")
else:
    st.write("아직 입력된 데이터가 없습니다.")
