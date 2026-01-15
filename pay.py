import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date, timedelta

# 페이지 설정
st.set_page_config(page_title="급여 정산 시스템", layout="centered")

# 1. 구글 시트 연결
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # 시트1에서 데이터를 읽어옴
    df = conn.read(worksheet="시트1")
except Exception as e:
    st.error("구글 시트 연결 실패. 시트 이름이 '시트1'인지 확인해주세요.")
    st.stop()

# 2. 고정 설정
BASE_SALARY = 3500000
INSURANCE = 104760

st.title("💼 월급 정산 시스템 (13일 기준)")

# 3. 날짜 선택 (기본값은 항상 '오늘')
# 여기서 날짜만 선택하고 아래 '저장하기'를 누르면 시트에 날짜가 자동으로 찍힙니다.
selected_date = st.date_input("근무 날짜 선택", value=date.today())
str_date = selected_date.strftime("%Y-%m-%d")

# 기존 데이터 확인
existing_row = pd.DataFrame()
if not df.empty and '날짜' in df.columns:
    df['날짜'] = df['날짜'].astype(str).str.strip()
    existing_row = df[df["날짜"] == str_date]

is_edit = not existing_row.empty

# 4. 입력 폼
with st.form("input_form"):
    st.subheader(f"📝 {str_date} 데이터 입력")
    st.info("숫자만 입력하고 [저장하기]를 누르면 시트에 날짜와 합계가 자동 기록됩니다.")
    
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

# 5. 저장 로직 (날짜 자동 입력 포함)
if save_btn:
    daily_sum = v_incen + (v_nf*9000) + (v_ff*18000) + (v_j*9000) + (v_c*15000) + (v_a*23000)
    
    # 이 데이터프레임이 시트에 한 줄로 들어갑니다 (날짜 포함)
    new_data = pd.DataFrame([{
        "날짜": str_date, # 앱에서 선택한 날짜가 자동으로 들어감
        "인센티브": v_incen, 
        "일반필름": v_nf, 
        "풀필름": v_ff, 
        "젤리": v_j, 
        "케이블": v_c, 
        "어댑터": v_a, 
        "합계": daily_sum
    }])
    
    if not df.empty and '날짜' in df.columns:
        df = df[df["날짜"] != str_date]
    
    updated_df = pd.concat([df, new_data], ignore_index=True)
    
    # '시트1'에 데이터 쓰기
    conn.update(worksheet="시트1", data=updated_df)
    st.success(f"✅ {str_date} 데이터가 '시트1'에 자동 저장되었습니다!")
    st.rerun()

# 6. 정산 주기(13일~12일) 계산 로직
if selected_date.day >= 13:
    start_dt = date(selected_date.year, selected_date.month, 13)
    # 다음달 12일 계산
    if selected_date.month == 12:
        end_dt = date(selected_date.year + 1, 1, 12)
    else:
        end_dt = date(selected_date.year, selected_date.month + 1, 12)
else:
    # 이번달 12일이 마감, 시작은 저번달 13일
    end_dt = date(selected_date.year, selected_date.month, 12)
    if selected_date.month == 1:
        start_dt = date(selected_date.year - 1, 12, 13)
    else:
        start_dt = date(selected_date.year, selected_date.month - 1, 13)

st.divider()
st.subheader(f"📊 정산 현황 ({start_dt.strftime('%m/%d')} ~ {end_dt.strftime('%m/%d')})")

if not df.empty and '날짜' in df.columns:
    temp_df = df.copy()
    temp_df['날짜_str'] = pd.to_datetime(temp_df['날짜'], errors='coerce').dt.strftime('%Y-%m-%d')
    temp_df = temp_df.dropna(subset=['날짜_str'])
    
    s_str = start_dt.strftime('%Y-%m-%d')
    e_str = end_dt.strftime('%Y-%m-%d')
    
    period_df = temp_df[(temp_df['날짜_str'] >= s_str) & (temp_df['날짜_str'] <= e_str)]
    
    if not period_df.empty:
        display_df = period_df.drop(columns=['날짜_str']).sort_values("날짜", ascending=False)
        st.dataframe(display_df, use_container_width=True)
        total_extra = period_df["합계"].sum()
        c1, c2 = st.columns(2)
        c1.metric("누적 수당", f"{total_extra:,}원")
        c2.metric("예상 실수령액", f"{int(BASE_SALARY + total_extra - INSURANCE):,}원")
    else:
        st.info("기록된 데이터가 없습니다.")
