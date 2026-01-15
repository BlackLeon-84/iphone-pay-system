import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date, timedelta

# 페이지 설정
st.set_page_config(page_title="급여 정산 시스템", layout="centered")

# 구글 시트 연결
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read()
except Exception as e:
    st.error("구글 시트 연결에 실패했습니다. Secrets 설정을 확인해주세요.")
    st.stop()

# 엑셀 분석 기반 고정값
BASE_SALARY = 3500000
INSURANCE = 104760
UNIT_PRICES = {"일반필름": 9000, "풀필름": 18000, "젤리": 9000, "케이블": 15000, "어댑터": 23000}

st.title("💼 월급 정산 시스템 (13일 기준)")

# 1. 날짜 선택 및 기존 데이터 조회
selected_date = st.date_input("근무 날짜 선택", value=date.today())
str_date = selected_date.strftime("%Y-%m-%d")

# 기존 데이터가 있는지 확인 (수정 모드)
existing_row = df[df["날짜"] == str_date] if not df.empty else pd.DataFrame()
is_edit = not existing_row.empty

# 2. 입력 폼
with st.form("input_form"):
    st.subheader(f"📝 {str_date} 데이터 입력")
    v_incen = st.number_input("기본 인센티브", min_value=0, value=int(existing_row.iloc[0]["인센티브"]) if is_edit else 0)
    
    col1, col2 = st.columns(2)
    with col1:
        v_nf = st.number_input("일반필름", min_value=0, value=int(existing_row.iloc[0]["일반필름"]) if is_edit else 0)
        v_ff = st.number_input("풀필름", min_value=0, value=int(existing_row.iloc[0]["풀필름"]) if is_edit else 0)
        v_j = st.number_input("젤리", min_value=0, value=int(existing_row.iloc[0]["젤리"]) if is_edit else 0)
    with col2:
        v_c = st.number_input("케이블", min_value=0, value=int(existing_row.iloc[0]["케이블"]) if is_edit else 0)
        v_a = st.number_input("어댑터", min_value=0, value=int(existing_row.iloc[0]["어댑터"]) if is_edit else 0)
    
    save_btn = st.form_submit_button("저장하기")

# 3. 저장 및 구글 시트 업데이트
if save_btn:
    daily_sum = v_incen + (v_nf*9000) + (v_ff*18000) + (v_j*9000) + (v_c*15000) + (v_a*23000)
    new_data = pd.DataFrame([{
        "날짜": str_date, "인센티브": v_incen, "일반필름": v_nf, 
        "풀필름": v_ff, "젤리": v_j, "케이블": v_c, "어댑터": v_a, "합계": daily_sum
    }])
    
    # 수정인 경우 기존 데이터 삭제
    if is_edit:
        df = df[df["날짜"] != str_date]
    
    updated_df = pd.concat([df, new_data], ignore_index=True)
    conn.update(data=updated_df)
    st.success("✅ 구글 시트에 저장되었습니다!")
    st.rerun()

# 4. 정산 주기(13일~다음달 12일) 계산
if selected_date.day >= 13:
    start_dt = date(selected_date.year, selected_date.month, 13)
    # 다음 달 계산
    if selected_date.month == 12:
        end_dt = date(selected_date.year + 1, 1, 12)
    else:
        end_dt = date(selected_date.year, selected_date.month + 1, 12)
else:
    # 이전 달 13일부터 이번 달 12일까지
    if selected_date.month == 1:
        start_dt = date(selected_date.year - 1, 12, 13)
    else:
        start_dt = date(selected_date.year, selected_date.month - 1, 13)
    end_dt = date(selected_date.year, selected_date.month, 12)

# 5. 결과 필터링 및 출력
st.divider()
st.subheader(f"📊 {start_dt.strftime('%m/%d')} ~ {end_dt.strftime('%m/%d')} 정산 현황")

if not df.empty:
    df['날짜_dt'] = pd.to_datetime(df['날짜']).dt.date
    period_df = df[(df['날짜_dt'] >= start_dt) & (df['날짜_dt'] <= end_dt)]
    
    if not period_df.empty:
        st.dataframe(period_df.drop(columns=['날짜_dt']).sort_values("날짜", ascending=False), use_container_width=True)
        total_extra = period_df["합계"].sum()
        
        c1, c2 = st.columns(2)
        c1.metric("누적 수당", f"{total_extra:,}원")
        c2.metric("예상 실수령액", f"{BASE_SALARY + total_extra - INSURANCE:,}원")
    else:
        st.info("해당 기간의 데이터가 없습니다.")
