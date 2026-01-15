import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date, timedelta

# 페이지 설정
st.set_page_config(page_title="급여 정산 시스템", layout="centered")

# 1. 구글 시트 연결
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read()
except Exception as e:
    st.error("구글 시트 연결 실패. Secrets 설정과 시트 공유(편집자)를 확인해주세요.")
    st.stop()

# 2. 고정 설정
BASE_SALARY = 3500000
INSURANCE = 104760
UNIT_PRICES = {"일반필름": 9000, "풀필름": 18000, "젤리": 9000, "케이블": 15000, "어댑터": 23000}

st.title("💼 월급 정산 시스템 (13일 기준)")

# 3. 날짜 선택 및 데이터 조회
selected_date = st.date_input("근무 날짜 선택", value=date.today())
str_date = selected_date.strftime("%Y-%m-%d")

# 기존 데이터 확인
existing_row = pd.DataFrame()
if not df.empty and '날짜' in df.columns:
    existing_row = df[df["날짜"].astype(str) == str_date]

is_edit = not existing_row.empty

# 4. 입력 폼
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

# 5. 저장 로직
if save_btn:
    daily_sum = v_incen + (v_nf*9000) + (v_ff*18000) + (v_j*9000) + (v_c*15000) + (v_a*23000)
    new_data = pd.DataFrame([{
        "날짜": str_date, "인센티브": v_incen, "일반필름": v_nf, 
        "풀필름": v_ff, "젤리": v_j, "케이블": v_c, "어댑터": v_a, "합계": daily_sum
    }])
    
    if not df.empty and '날짜' in df.columns:
        df = df[df["날짜"].astype(str) != str_date]
    
    updated_df = pd.concat([df, new_data], ignore_index=True)
    
    try:
        conn.update(worksheet="시트1", data=updated_df)
    except:
        conn.update(worksheet="Sheet1", data=updated_df)
        
    st.success(f"✅ {str_date} 데이터 저장 완료!")
    st.rerun()

# 6. 정산 주기(13일~12일) 계산 (안전한 비교 로직)
if selected_date.day >= 13:
    start_dt = date(selected_date.year, selected_date.month, 13)
    end_dt = (start_dt + timedelta(days=32)).replace(day=12)
else:
    end_dt = date(selected_date.year, selected_date.month, 12)
    start_dt = (end_dt - timedelta(days=32)).replace(day=13)

st.divider()
st.subheader(f"📊 정산 현황 ({start_dt.strftime('%m/%d')} ~ {end_dt.strftime('%m/%d')})")

if not df.empty and '날짜' in df.columns:
    # 핵심 수정: 날짜 형식이 아닌 데이터는 NaT로 바꾸고 제거함
    df['날짜_dt'] = pd.to_datetime(df['날짜'], errors='coerce').dt.date
    df = df.dropna(subset=['날짜_dt'])
    
    # 타입 일치 후 비교 (오류 방지)
    period_df = df[(df['날짜_dt'] >= start_dt) & (df['날짜_dt'] <= end_dt)]
    
    if not period_df.empty:
        display_df = period_df.drop(columns=['날짜_dt']).sort_values("날짜", ascending=False)
        st.dataframe(display_df, use_container_width=True)
        total_extra = period_df["합계"].sum()
        c1, c2 = st.columns(2)
        c1.metric("누적 수당", f"{total_extra:,}원")
        c2.metric("예상 실수령액", f"{int(BASE_SALARY + total_extra - INSURANCE):,}원")
    else:
        st.info("해당 기간의 데이터가 없습니다.")
else:
    st.info("데이터가 없습니다. 첫 기록을 저장해주세요.")
