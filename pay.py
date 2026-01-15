import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date, timedelta

# 1. 페이지 설정
st.set_page_config(page_title="급여 정산 시스템", layout="centered")

# 2. 구글 시트 연결 (가장 안전한 방식)
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # worksheet=0으로 설정하여 시트 이름이 '시트1'이든 'Sheet1'이든 첫 번째 탭을 불러옵니다.
    df = conn.read(worksheet=0)
except Exception as e:
    st.error(f"구글 시트 연결 실패: {e}")
    st.info("💡 해결방법: 구글 시트 우측 상단 [공유] -> [링크가 있는 모든 사용자] -> [편집자]로 설정했는지 확인해주세요.")
    st.stop()

# 3. 고정 수치 설정
BASE_SALARY = 3500000
INSURANCE = 104760

st.title("💼 월급 정산 시스템 (13일 기준)")

# 4. 날짜 선택 (기본값: 오늘)
selected_date = st.date_input("근무 날짜 선택", value=date.today())
str_date = selected_date.strftime("%Y-%m-%d")

# 5. 기존 데이터 조회 (수정용)
existing_row = pd.DataFrame()
if not df.empty and '날짜' in df.columns:
    # 날짜를 문자열로 바꿔서 비교 (오류 방지)
    df['날짜'] = df['날짜'].astype(str).str.strip()
    existing_row = df[df["날짜"] == str_date]

is_edit = not existing_row.empty

# 6. 데이터 입력 폼
with st.form("input_form"):
    st.subheader(f"📝 {str_date} 데이터 입력")
    
    # 기존 데이터가 있으면 불러오기
    v_incen = st.number_input("기본 인센티브", min_value=0, value=int(existing_row.iloc[0]["인센티브"]) if is_edit else 0)
    
    col1, col2 = st.columns(2)
    with col1:
        v_nf = st.number_input("일반필름", min_value=0, value=int(existing_row.iloc[0]["일반필름"]) if is_edit else 0)
        v_ff = st.number_input("풀필름", min_value=0, value=int(existing_row.iloc[0]["풀필름"]) if is_edit else 0)
        v_j = st.number_input("젤리", min_value=0, value=int(existing_row.iloc[0]["젤리"]) if is_edit else 0)
    with col2:
        v_c = st.number_input("케이블", min_value=0, value=int(existing_row.iloc[0]["케이블"]) if is_edit else 0)
        v_a = st.number_input("어댑터", min_value=0, value=int(existing_row.iloc[0]["어댑터"]) if is_edit else 0)
    
    save_btn = st.form_submit_button("구글 시트에 저장하기")

# 7. 저장 로직 (날짜 자동 입력)
if save_btn:
    daily_sum = v_incen + (v_nf*9000) + (v_ff*18000) + (v_j*9000) + (v_c*15000) + (v_a*23000)
    
    new_data = pd.DataFrame([{
        "날짜": str_date,
        "인센티브": v_incen, 
        "일반필름": v_nf, 
        "풀필름": v_ff, 
        "젤리": v_j, 
        "케이블": v_c, 
        "어댑터": v_a, 
        "합계": daily_sum
    }])
    
    # 같은 날짜 데이터가 이미 있으면 삭제 (중복 방지)
    if not df.empty and '날짜' in df.columns:
        df = df[df["날짜"] != str_date]
    
    updated_df = pd.concat([df, new_data], ignore_index=True)
    
    # 첫 번째 워크시트에 업데이트
    conn.update(worksheet=0, data=updated_df)
    st.success(f"✅ {str_date} 데이터 저장 완료!")
    st.rerun()

# 8. 정산 주기(13일~12일) 계산
if selected_date.day >= 13:
    start_dt = date(selected_date.year, selected_date.month, 13)
    # 다음 달 12일 계산
    next_month = selected_date.replace(day=28) + timedelta(days=20)
    end_dt = next_month.replace(day=12)
else:
    end_dt = selected_date.replace(day=12)
    # 이전 달 13일 계산
    last_month = selected_date.replace(day=1) - timedelta(days=10)
    start_dt = last_month.replace(day=13)

st.divider()
st.subheader(f"📊 정산 현황 ({start_dt.strftime('%m/%d')} ~ {end_dt.strftime('%m/%d')})")

# 9. 데이터 필터링 및 출력
if not df.empty and '날짜' in df.columns:
    temp_df = df.copy()
    # 모든 날짜를 문자열로 통일하여 비교 (TypeError 방지)
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
        c1.metric("누적 수당 합계", f"{total_extra:,}원")
        c2.metric("예상 실수령액", f"{int(BASE_SALARY + total_extra - INSURANCE):,}원")
    else:
        st.info("해당 정산 기간에 입력된 데이터가 없습니다.")
else:
    st.info("구글 시트에 데이터가 없습니다. 첫 기록을 저장해보세요!")
