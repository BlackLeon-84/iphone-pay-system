import streamlit as st
import pandas as pd

# 1. 직원별 데이터베이스 (엑셀의 기본 정보를 여기에 설정)
# 직원마다 시급과 직책수당 등이 다르므로 이 부분을 수정하며 관리합니다.
STAFF_INFO = {
    "직원 1": {"시급": 10030, "직책수당": 100000, "주휴대상": True},
    "직원 2": {"시급": 11000, "직책수당": 0, "주휴대상": True},
    "직원 3": {"시급": 10030, "직책수당": 50000, "주휴대상": False},
}

st.title("📅 2025년 1월 급여 정산")

# 2. 아이폰 입력창
with st.container():
    name = st.selectbox("정산할 직원을 선택하세요", list(STAFF_INFO.keys()))
    
    col1, col2 = st.columns(2)
    with col1:
        normal_hours = st.number_input("기본 근무 시간", min_value=0.0, value=160.0)
        over_hours = st.number_input("연장 근무 시간 (1.5배)", min_value=0.0)
    with col2:
        night_hours = st.number_input("야간 근무 시간 (0.5배)", min_value=0.0)
        holiday_hours = st.number_input("휴일 근무 시간 (1.5배)", min_value=0.0)

# 3. 엑셀 수식 그대로 계산
info = STAFF_INFO[name]
wage = info["시급"]

total_basic = normal_hours * wage
total_over = over_hours * wage * 1.5
total_night = night_hours * wage * 0.5
total_holiday = holiday_hours * wage * 1.5
# 주휴수당 (통상 1주 15시간 이상 시 발생 - 엑셀 로직 반영 가능)
weekly_holiday_pay = (normal_hours / 40) * 8 * wage if info["주휴대상"] else 0

total_before_tax = total_basic + total_over + total_night + total_holiday + weekly_holiday_pay + info["직책수당"]

# 공제 (25년 요율 반영)
emp_ins = int(total_before_tax * 0.009) # 고용보험 0.9%
income_tax = int(total_before_tax * 0.03) # 소득세(간이세액표 대신 3.3% 혹은 엑셀 기준 적용)
resident_tax = int(income_tax * 0.1) # 지방세

net_pay = total_before_tax - (emp_ins + income_tax + resident_tax)

# 4. 결과 보기
st.metric(label="실수령액", value=f"{int(net_pay):,} 원")

with st.expander("상세 내역 확인"):
    st.write(f"기본급: {int(total_basic):,}원")
    st.write(f"주휴수당: {int(weekly_holiday_pay):,}원")
    st.write(f"세금 공제 총합: {int(emp_ins + income_tax + resident_tax):,}원")
