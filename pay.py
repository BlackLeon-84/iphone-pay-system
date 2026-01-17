import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials

# 소프트웨어 버전
SW_VERSION = "v3.0.6"

# 페이지 설정
st.set_page_config(page_title=f"정산 {SW_VERSION}", layout="centered")

# --- [스마트 레이아웃] 아이폰 100% 최적화 CSS ---
st.markdown(f"""
    <style>
    /* 1. 전체 여백 최적화 */
    .block-container {{
        padding-top: 3.5rem !important;
        max-width: 450px !important;
        padding-left: 10px !important;
        padding-right: 10px !important;
    }}
    .version-tag {{ font-size: 10px; color: #ccc; text-align: right; margin-bottom: -10px; }}

    /* 2. 입력창 스타일 */
    hr {{ border: 0; height: 1px; background: #eee; margin: 15px 0; }}
    div[data-testid="stVerticalBlock"] > div {{ border: none !important; }}
    div[data-baseweb="base-input"] {{ border: none !important; background-color: #f1f3f5 !important; border-radius: 8px !important; }}

    /* 3. ★ 아이폰용 버튼 탈출 방지 설정 ★ */
    .st-key-incen_buttons [data-testid="stHorizontalBlock"] {{
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 4px !important;
        width: 100% !important;
    }}
    .st-key-incen_buttons [data-testid="stHorizontalBlock"] > div {{
        flex: 1 1 0% !important;
        min-width: 0 !important;
    }}
    .st-key-incen_buttons button {{
        font-size: 10px !important;
        padding: 0px 1px !important;
        width: 100% !important;
        min-height: 40px !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: clip !important;
    }}

    /* 4. 로그인 입장 버튼 강조 */
    .st-key-login_btn button {{
        height: 50px !important;
        font-size: 18px !important;
        font-weight: bold !important;
        background-color: #007bff !important;
        color: white !important;
    }}

    /* 5. 텍스트 및 테이블 스타일 */
    input {{ font-size: 16px !important; }}
    label p {{ font-size: 12px !important; font-weight: bold !important; color: #444 !important; }}
    .weekly-box {{ display: flex; justify-content: space-around; background: #f8f9fa; padding: 10px; border-radius: 10px; margin-bottom: 15px; }}
    .report-table {{ width: 100%; font-size: 10px; text-align: center; border-collapse: collapse; }}
    .report-table th, .report-table td {{ border: 1px solid #eee; padding: 5px 2px; }}
    .total-row {{ background-color: #f2f2f2 !important; font-weight: bold; }}
    .calc-detail {{ font-size: 11px; color: #888; margin-top: -5px; margin-bottom: 10px; }}
    .incen-log {{ font-size: 11px; color: #666; padding: 8px; background: #fcfcfc; border-radius: 5px; border-left: 3px solid #ddd; margin: 10px 0; }}
    .save-log {{ font-size: 12px; color: #1e88e5; font-weight: bold; margin-bottom: 5px; }}
    
    /* 버전 히스토리 스타일 */
    .update-log {{ font-size: 11px; color: #777; background: #f9f9f9; padding: 10px; border-radius: 8px; margin-top: 30px; border: 1px solid #eee; }}
    </style>
    """, unsafe_allow_html=True)

# --- 구글 시트 연결 ---
SHEET_NAME = "아이폰정산"

def get_gsheet_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    if "gcp_service_account" in st.secrets:
        creds_info = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_info:
            creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        return gspread.authorize(creds)
    st.stop()

@st.cache_data(ttl=60)
def load_data_from_gsheet():
    try:
        client = get_gsheet_client()
        sheet = client.open(SHEET_NAME).sheet1
        df = pd.DataFrame(sheet.get_all_records())
        num_cols = ["인센티브", "item1", "item2", "item3", "item4", "item5", "item6", "item7", "합계"]
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        return df
    except: return pd.DataFrame()

def save_to_gsheet(df_row):
    try:
        client = get_gsheet_client()
        sheet = client.open(SHEET_NAME).sheet1
        all_data = sheet.get_all_values()
        row_idx = -1
        for i, row in enumerate(all_data):
            if len(row) > 1 and row[0] == df_row['직원명'] and row[1] == df_row['날짜']:
                row_idx = i + 1; break
        if row_idx != -1: sheet.update(range_name=f"A{row_idx}", values=[list(df_row.values())])
        else: sheet.append_row(list(df_row.values()))
        return True
    except: return False

def get_now_kst(): return datetime.now(timezone.utc) + timedelta(hours=9)

# --- 세션 및 설정 (전역 공유 설정 반영) ---
STAFF_LIST = ["태완", "남근", "성훈"]
if "logged_in" not in st.session_state: st.session_state.logged_in = False

# [중요] 모든 직원에게 동일하게 반영되도록 설정 초기값 고정
if "config" not in st.session_state:
    st.session_state.config = {
        "base_salary": 3500000, "start_day": 13, "insurance": 104760, 
        "item_names": ['일반필름', '풀필름', '젤리', '케이블', '어댑터', '추가1', '추가2'],
        "item_prices": [9000, 18000, 9000, 15000, 23000, 0, 0]
    }

# --- 로그인 ---
if not st.session_state.logged_in:
    st.title("🔐 로그인")
    user_id = st.selectbox("직원 선택", options=STAFF_LIST)
    admin_pw = st.text_input("비번", type="password") if user_id == "태완" else ""
    
    if st.button("입장", use_container_width=True, key="login_btn"):
        if user_id == "태완" and admin_pw != "102030": st.error("비번 오류")
        else: st.session_state.logged_in = True; st.session_state.user_name = user_id; st.rerun()
    
    # 하단 수정 내역 로그 (날짜 추가)
    now_date = get_now_kst().strftime("%Y-%m-%d")
    st.markdown(f"""
        <div class="update-log">
            <b>🚀 업데이트 로그 ({now_date})</b><br>
            • <b>전직원 설정 동기화</b>: 관리자 설정 변경 시 모든 직원 화면에 즉시 반영 로직 수정<br>
            • <b>날짜 표시 강화</b>: 모든 저장 로그 및 업데이트 로그에 날짜 추가<br>
            • <b>UI 안정화</b>: 로그인 버튼 및 v3.0.0 가로 버튼 레이아웃 유지
        </div>
    """, unsafe_allow_html=True)
    st.stop()

# --- 사이드바 ---
user_name = st.session_state.user_name
cfg = st.session_state.config
with st.sidebar:
    st.header("⚙️ 설정")
    if user_name == "태완":
        st.subheader("🛠️ 관리자 설정")
        # 모든 직원의 설정을 한 번에 제어하도록 함
        new_names = []; new_prices = []
        for i in range(7):
            c1, c2 = st.columns(2)
            n = c1.text_input(f"명칭{i+1}", value=cfg["item_names"][i], key=f"sn_{i}")
            p = c2.number_input(f"가격{i+1}", value=cfg["item_prices"][i], step=1000, key=f"sp_{i}")
            new_names.append(n); new_prices.append(p)
        base = st.number_input("기본급", value=cfg["base_salary"])
        s_day = st.slider("정산 시작일", 1, 31, cfg["start_day"])
        ins = st.number_input("보험료", value=cfg["insurance"])
        if st.button("💿 설정 저장 (전직원 반영)", use_container_width=True):
            st.session_state.config.update({"base_salary": base, "start_day": s_day, "insurance": ins, "item_names": new_names, "item_prices": new_prices})
            st.success("전직원 설정에
