import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta

# 페이지 설정
st.set_page_config(page_title="급여 정산 시스템", layout="centered")

st.title("💼 월급 정산 시스템 (13일 기준)")

# 1. 고정 설정 (엑셀 분석 내용 반영)
BASE_SALARY = 3500000  # 기본급
INSURANCE = 104760     # 보험료
UNIT_PRICES = {
    "일반필름": 9000,
    "풀필름": 18000,
    "젤리": 9000,
    "케이블": 15000,
    "어댑터": 23000
}

# 2. 날짜 로직 (매월 13일 ~ 다음달 12일)
today = date.today()
if today.day >= 13:
    start_date = date(today.year, today.month, 13)
    # 다음 달 계산
    if today.month == 12:
        end_date = date(today.year + 1, 1, 12)
    else:
        end_date = date(today.year, today.month + 1, 12)
else:
    # 이전 달 13일부터 이번 달 12일까지
    if today.month == 1:
        start_date = date(today.year - 1, 12, 13)
    else:
        start_date = date(today.year, today.month - 1, 13)
    end_date = date(today.year, today.month, 12)

st.info(f"📅 이번 정산 주기: {start_date} ~ {end_date}")

# 3. 데이터 입력 (일일 로그용)
with st.form("daily_input"):
    st.subheader("📝 일일 근무 로그 입력")
    work_date = st.date_input("근무 날짜", value=today)
    daily_incen = st.number_input("기본 인센티브", min_value=0, step=1000)
    
    col1, col2 = st.columns(2)
    with col1:
        n_film = st.number_input("일반필름 (개)", min_value=0)
        f_film = st.number_input("풀필름 (개)", min_value=0)
        j_case = st.number_input("젤리 (개)", min_value=0)
    with col2:
        cable = st.number_input("케이블 (개)", min_value=0)
        adapter = st.number_input("어댑터 (개)", min_value=0)
    
    submit = st.form_submit_button("오늘 데이터 저장 및 계산")

# 4. 일일 계산 결과 (로그)
if submit:
    # 필름 및 액세서리 수당 계산
    film_pay = (n_film * UNIT_PRICES["일반필름"]) + (f_film * UNIT_PRICES["풀필름"])
    acc_pay = (j_case * UNIT_PRICES["젤리"]) + (cable * UNIT_PRICES["케이블"]) + (adapter * UNIT_PRICES["어댑터"])
    daily_total = daily_incen + film_pay + acc_pay
    
    st.success(f"✅ {work_date} 정산 완료")
    st.write(f"**오늘의 추가 수당 합계:** {daily_total:,}원")
    st.caption(f"(인센: {daily_incen:,} / 필름: {film_pay:,} / 액세서리: {acc_pay:,})")

# 5. 월간 총합 미리보기 (누적 데이터가 있다고 가정 시의 레이아웃)
st.divider()
st.subheader(f"📊 {start_date.month}월분 정산 요약 (현재까지)")
# 실제 운영 시에는 입력한 데이터를 파일이나 DB에 저장하여 아래 합산에 반영합니다.
total_extra = 0 # 일일 로그들의 합계가 들어갈 자리
final_gross = BASE_SALARY + total_extra
final_net = final_gross - INSURANCE

c1, c2, c3 = st.columns(3)
c1.metric("기본급", f"{BASE_SALARY:,}원")
c2.metric("누적 수당", f"{total_extra:,}원")
c3.metric("예상 실수령액", f"{final_net:,}원", delta=f"보험료 -{INSURANCE:,}")
