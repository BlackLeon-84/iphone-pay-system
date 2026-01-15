import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date, timedelta

# 페이지 설정 (아이폰 최적화)
st.set_page_config(page_title="급여 정산 시스템", layout="centered")

# 1. 구글 시트 연결
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read()
except Exception as e:
    st.error("구글 시트 연결 실패. Secrets 설정과 시트 공유(편집자)를 확인해주세요.")
    st.stop()

# 2. 고정 설정 (성훈 수당양식 기준)
BASE_SALARY = 3500000
INSURANCE = 104760
UNIT_PRICES = {"일반필름": 9000, "풀필름": 18000, "젤리": 9000, "케이블": 15000, "어댑터": 23000}

st.title("💼 월급 정산 시스템 (13일 기준)")

# 3. 날짜 선택 및 데이터 조회
selected_date = st.date_input("근무 날짜 선택", value=date.today())
str_date = selected_date.strftime("%Y-%m-%d")

# 기존 데이터 존재 여부 확인
existing_row = pd.DataFrame()
if not df.empty and '날짜' in df.columns:
    # 시트 내 '날짜' 열과 선택한 날짜 비교
    existing_row = df[df["날짜"].astype(str) == str_date]

is_edit = not existing_row.empty

# 4. 입력 폼
with st.form("input_form"):
    st.subheader(f"📝 {str_date} 데이터 입력")
    # 기존 데이터가 있으면 불러오고, 없으면 0으로 표시
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

# 5. 저장 로직 (업데이트 및 중복 제거)
if save_btn:
    daily_sum = v_incen + (v_nf*9000) + (v_ff*18000) + (v_j*9000) + (v_c*15000) + (v_a*23000)
    new_data = pd.DataFrame([{
        "날짜": str_date, "인센티브": v_incen, "일반필름": v_nf, 
        "풀필름": v_ff, "젤리": v_j, "케이블": v_c, "어댑터": v_a, "합계": daily_sum
    }])
    
    # 기존에 같은 날짜 데이터가 있다면 제거 후 합치기
    if not df.empty and '날짜' in df.columns:
        df = df[df["날짜"].astype(str) != str_date]
    
    updated_df = pd.concat([df, new_data], ignore_index=True)
    
    # 워크시트 이름을 명시하여 저장 권한 에러 방지 (보통 '시트1' 또는 'Sheet1')
    try:
        conn.update(worksheet="시트1", data=updated_df)
    except:
        conn.update(worksheet="Sheet1", data=updated_df)
        
    st.success(f"✅ {str_date} 데이터 저장 완료!")
    st.rerun()

# 6. 정산 주기(13일~다음달 12일) 계산 및 출력
# 오늘 날짜 기준으로 정산 시작일과 종료일 설정
if selected_date.day >= 13:
    start_dt = date(selected_date.year, selected_date.month, 13)
    if selected_date.month == 12:
        end_dt = date(selected_date.year + 1, 1, 12)
    else:
        end_dt = date(selected_date.year, selected_date.month + 1, 12)
else:
    end_dt = date(selected_date.year, selected_date.month, 12)
    if selected_date.month == 1:
        start_dt = date(selected_date.year - 1, 12, 13)
    else:
        start_dt = date(selected_date.year, selected_date.month - 1, 13)

st.divider()
st.subheader(f"📊 정산 현황 ({start_dt.strftime('%m/%d')} ~ {end_dt.strftime('%m/%d')})")

if not df.empty and '날짜' in df.columns:
    # 날짜 데이터 정제 (에러 방지용)
    df['날짜_dt'] = pd.to_datetime(df['날짜'], errors='coerce').dt.date
    # 정산 주기에 포함된 데이터만 필터링
    period_df = df[(df['날짜_dt'] >= start_dt) & (df['날짜_dt'] <= end_dt)]
    
    if not period_df.empty:
        # 화면 출력용 데이터프레임 정리 (필요없는 열 제거)
        display_df = period_df.drop(columns=['날짜_dt']).sort_values("날짜", ascending=False)
        st.dataframe(display_df, use_container_width=True)
        
        total_extra = period_df["합계"].sum()
        
        c1, c2 = st.columns(2)
        c1.metric("누적 수당", f"{total_extra:,}원")
        # 기본급 350만 원 + 수당 - 보험료 104,760원
        final_pay = BASE_SALARY + total_extra - INSURANCE
        c2.metric("예상 실수령액", f"{int(final_pay):,}원", delta=f"보험료 -{INSURANCE:,}")
    else:
        st.info("이 기간에 저장된 데이터가 없습니다.")
else:
    st.info("구글 시트가 비어있습니다. 첫 데이터를 입력해주세요.")
