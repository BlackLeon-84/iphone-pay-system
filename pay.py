import streamlit as st
import pandas as pd

# 페이지 설정 (아이폰 최적화)
st.set_page_config(page_title="급여 정산 시스템", layout="centered")

st.title("📱 직원 급여 정산 (25년 1월)")

# 1. 직원별 고정 정보 설정 (엑셀 상단 기준)
# 직원마다 보험료나 품목별 단가가 다르다면 이 부분을 수정하세요.
staff_config = {
    "기본설정": {
        "보험료": 104760,
        "단가": {
            "일반필름": 9000,
            "풀필름": 18000,
            "젤리": 9000,
            "케이블": 15000,
            "어댑터": 23000
        }
    }
}

# 2. 입력 섹션
st.header("🔢 오늘 판매/근무 입력")

with st.form("salary_form"):
    date = st.date_input("날짜 선택")
    incentive = st.number_input("기본 인센티브 (원)", min_value=0, step=1000)
    
    st.subheader("📦 판매 개수 입력")
    col1, col2 = st.columns(2)
    with col1:
        normal_f = st.number_input("일반필름 (개)", min_value=0, step=1)
        full_f = st.number_input("풀필름 (개)", min_value=0, step=1)
        jelly = st.number_input("젤리 (개)", min_value=0, step=1)
    with col2:
        cable = st.number_input("케이블 (개)", min_value=0, step=1)
        adapter = st.number_input("어댑터 (개)", min_value=0, step=1)
    
    submitted = st.form_submit_button("정산하기")

# 3. 계산 로직 (엑셀 수식 반영)
if submitted:
    prices = staff_config["기본설정"]["단가"]
    
    # 품목별 합계 계산
    film_total = (normal_f * prices["일반필름"]) + (full_f * prices["풀필름"])
    acc_total = (jelly * prices["젤리"]) + (cable * prices["케이블"]) + (adapter * prices["어댑터"])
    
    # 총급여 계산
    gross_pay = incentive + film_total + acc_total
    
    # 보험료 공제 (엑셀 기준)
    insurance = staff_config["기본설정"]["보험료"]
    net_pay = gross_pay - insurance
    
    # 4. 결과 출력
    st.divider()
    st.balloons()
    st.success(f"### {date.strftime('%m월 %d일')} 정산 결과")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("총 급여", f"{gross_pay:,}원")
    c2.metric("보험료 공제", f"-{insurance:,}원")
    c3.metric("실수령액", f"{max(0, net_pay):,}원")

    # 상세 내역 표
    detail_data = {
        "항목": ["기본 인센티브", "필름 판매 합계", "액세서리 합계", "보험료"],
        "금액": [f"{incentive:,}원", f"{film_total:,}원", f"{acc_total:,}원", f"-{insurance:,}원"]
    }
    st.table(pd.DataFrame(detail_data))
