import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta

# 페이지 설정
st.set_page_config(page_title="급여 정산 시스템", layout="centered")

# --- 데이터베이스 초기화 (Streamlit 내장 저장소 사용) ---
if "salary_db" not in st.session_state:
    # 처음 실행 시 빈 데이터프레임 생성
    st.session_state.salary_db = pd.DataFrame(columns=[
        "날짜", "인센티브", "일반필름", "풀필름", "젤리", "케이블", "어댑터", "합계"
    ])

# 고정 수치
BASE_SALARY = 3500000
INSURANCE = 104760

st.title("💼 월급 정산 시스템 (로컬 저장형)")
st.info("💡 데이터는 앱 내부에 저장됩니다. 엑셀이 필요하면 하단에서 다운로드하세요.")

# 1. 날짜 선택
selected_date = st.date_input("근무 날짜", value=date.today())
str_date = selected_date.strftime("%Y-%m-%d")

# 2. 기존 데이터 불러오기
df = st.session_state.salary_db
existing_row = df[df["날짜"] == str_date]
is_edit = not existing_row.empty

# 3. 입력 폼
with st.form("input_form"):
    st.subheader(f"📝 {str_date} 데이터 입력")
    v_incen = st.number_input("기본 인센티브", min_value=0, value=int(existing_row.iloc[0]["인센티브"]) if is_edit else 0)
    
    col1, col2 = st.columns(2)
    with col1:
        v_nf = st.number_input("일반필름", 0, value=int(existing_row.iloc[0]["일반필름"]) if is_edit else 0)
        v_ff = st.number_input("풀필름", 0, value=int(existing_row.iloc[0]["풀필름"]) if is_edit else 0)
        v_j = st.number_input("젤리", 0, value=int(existing_row.iloc[0]["젤리"]) if is_edit else 0)
    with col2:
        v_c = st.number_input("케이블", 0, value=int(existing_row.iloc[0]["케이블"]) if is_edit else 0)
        v_a = st.number_input("어댑터", 0, value=int(existing_row.iloc[0]["어댑터"]) if is_edit else 0)
    
    save_btn = st.form_submit_button("✅ 이 날짜 데이터 저장하기")

# 4. 저장 로직
if save_btn:
    daily_sum = v_incen + (v_nf*9000) + (v_ff*18000) + (v_j*9000) + (v_c*15000) + (v_a*23000)
    new_row = pd.DataFrame([[str_date, v_incen, v_nf, v_ff, v_j, v_c, v_a, daily_sum]], 
                           columns=df.columns)
    
    # 중복 제거 후 합치기
    df = df[df["날짜"] != str_date]
    st.session_state.salary_db = pd.concat([df, new_row], ignore_index=True)
    st.success(f"{str_date} 데이터가 저장되었습니다!")
    st.rerun()

# 5. 정산 주기(13일~12일) 계산
if selected_date.day >= 13:
    start_dt = date(selected_date.year, selected_date.month, 13)
    end_dt = (selected_date.replace(day=28) + timedelta(days=20)).replace(day=12)
else:
    end_dt = selected_date.replace(day=12)
    start_dt = (selected_date.replace(day=1) - timedelta(days=1)).replace(day=13)

st.divider()
st.subheader(f"📊 정산 현황 ({start_dt.strftime('%m/%d')} ~ {end_dt.strftime('%m/%d')})")

# 6. 필터링 및 출력
df = st.session_state.salary_db
if not df.empty:
    # 날짜 필터링
    df['날짜_dt'] = pd.to_datetime(df['날짜']).dt.date
    period_df = df[(df['날짜_dt'] >= start_dt) & (df['날짜_dt'] <= end_dt)]
    
    if not period_df.empty:
        st.dataframe(period_df.drop(columns=['날짜_dt']).sort_values("날짜", ascending=False), use_container_width=True)
        total_extra = period_df["합계"].sum()
        
        c1, c2 = st.columns(2)
        c1.metric("누적 수당", f"{total_extra:,}원")
        c2.metric("예상 실수령액", f"{int(BASE_SALARY + total_extra - INSURANCE):,}원")
    else:
        st.info("기록된 데이터가 없습니다.")

    # 7. 엑셀 다운로드 기능 (구글 시트 대신 사용)
    st.divider()
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 전체 데이터를 엑셀(CSV)로 받기", csv, "salary_data.csv", "text/csv")
else:
    st.info("아직 저장된 데이터가 없습니다.")
