import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials

# ======================
# 기본 설정
# ======================
SW_VERSION = "v2.2.6"
SHEET_NAME = "아이폰정산"

st.set_page_config(
    page_title=f"아이폰 정산 시스템 {SW_VERSION}",
    layout="centered"
)

# ======================
# 아이폰 대응 CSS
# ======================
st.markdown("""
<style>
[data-testid="column"] {
    flex: 1 1 0% !important;
    min-width: 0px !important;
}
div[data-testid="stHorizontalBlock"] {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    gap: 8px !important;
}
.stButton button {
    padding: 5px 2px !important;
    font-size: 13px !important;
}

/* 주간 표시 */
.weekly-container {
    display: flex;
    justify-content: space-around;
    background: #f8f9fa;
    padding: 10px;
    border-radius: 10px;
    margin-bottom: 15px;
    border: 1px solid #eee;
}
.weekly-item { text-align: center; flex: 1; }
.weekly-date { font-size: 10px; color: #666; }
.weekly-icon { font-size: 18px; }

/* 상태 박스 */
.status-box {
    padding: 12px;
    border-radius: 10px;
    margin-bottom: 10px;
    text-align: center;
    font-weight: bold;
    border: 1px solid #ddd;
}
.incen-log {
    font-size: 11px;
    color: #666;
    margin-bottom: 10px;
    padding: 8px;
    background: #fdfdfd;
    border-radius: 5px;
    border-left: 3px solid #ddd;
}

/* 리포트 테이블 */
.report-table {
    width: 100%;
    font-size: 11px;
    text-align: center;
    border-collapse: collapse;
    background: white;
}
.report-table th, .report-table td {
    border: 1px solid #eee;
    padding: 6px 2px;
}
.total-row {
    background-color: #f2f2f2 !important;
    font-weight: bold;
}

/* 아이폰 품목 2열 고정 */
.item-row {
    display: flex;
    gap: 8px;
}
.item-box {
    width: 48%;
}
</style>
""", unsafe_allow_html=True)

# ======================
# 구글시트 함수
# ======================
def get_gsheet_client():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_info = dict(st.secrets["gcp_service_account"])
    creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    return gspread.authorize(creds)

def load_data_from_gsheet():
    try:
        sheet = get_gsheet_client().open(SHEET_NAME).sheet1
        df = pd.DataFrame(sheet.get_all_records())

        num_cols = ["인센티브","item1","item2","item3","item4","item5","item6","item7","합계"]
        for c in num_cols:
            if c not in df.columns:
                df[c] = 0
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

        df["날짜_dt"] = pd.to_datetime(df["날짜"], errors="coerce")
        return df
    except:
        return pd.DataFrame()

def save_to_gsheet(row):
    try:
        sheet = get_gsheet_client().open(SHEET_NAME).sheet1
        all_rows = sheet.get_all_values()

        for i, r in enumerate(all_rows):
            if len(r) > 1 and r[0] == row["직원명"] and r[1] == row["날짜"]:
                sheet.update(f"A{i+1}", [list(row.values())])
                return True

        sheet.append_row(list(row.values()))
        return True
    except:
        return False

def get_now_kst():
    return datetime.now(timezone.utc) + timedelta(hours=9)

# ======================
# 세션 초기화
# ======================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "config" not in st.session_state:
    st.session_state.config = {
        "base_salary": 3500000,
        "start_day": 13,
        "insurance": 104760,
        "item_names": ["일반필름","풀필름","젤리","케이블","어댑터","추가1","추가2"],
        "item_prices": [9000,18000,9000,15000,23000,0,0]
    }

# ======================
# 로그인
# ======================
STAFF_LIST = ["태완","남근","성훈"]

if not st.session_state.logged_in:
    st.title("🔐 로그인")
    user = st.selectbox("직원 선택", STAFF_LIST)
    pw = st.text_input("비밀번호", type="password") if user == "태완" else ""

    if st.button("입장하기"):
        if user == "태완" and pw != "102030":
            st.error("비밀번호 오류")
        else:
            st.session_state.logged_in = True
            st.session_state.user_name = user
            st.rerun()
    st.stop()

# ======================
# 메인 화면
# ======================
user_name = st.session_state.user_name
cfg = st.session_state.config
df_all = load_data_from_gsheet()

st.write(f"### 💼 {user_name}님 실적")

c1, c2 = st.columns(2)
sel_date = c1.date_input("날짜", date.today(), label_visibility="collapsed")
str_date = sel_date.strftime("%Y-%m-%d")

existing = df_all[(df_all["직원명"] == user_name) & (df_all["날짜"] == str_date)]
is_edit = not existing.empty

if "current_incen_sum" not in st.session_state:
    st.session_state.current_incen_sum = int(existing.iloc[0]["인센티브"]) if is_edit else 0
    st.session_state.incen_history = []

# ======================
# 인센티브
# ======================
st.markdown(f"**💰 인센 합계: {st.session_state.current_incen_sum:,}원**")

amt = st.number_input("금액", 0, step=1000, label_visibility="collapsed")
b1, b2, b3 = st.columns(3)

if b1.button("➕ 추가"):
    st.session_state.current_incen_sum += amt
    st.session_state.incen_history.append(amt)
    st.rerun()

if b2.button("↩️ 취소") and st.session_state.incen_history:
    v = st.session_state.incen_history.pop()
    st.session_state.current_incen_sum -= v
    st.rerun()

if b3.button("🧹 리셋"):
    st.session_state.current_incen_sum = 0
    st.session_state.incen_history = []
    st.rerun()

# ======================
# 📦 품목 수량 (아이폰 2열 고정)
# ======================
st.write("**📦 품목 수량**")

counts = []
defaults = [
    int(existing.iloc[0][f"item{i}"]) if is_edit else 0
    for i in range(1, 8)
]

for i in range(0, 7, 2):
    st.markdown('<div class="item-row">', unsafe_allow_html=True)

    counts.append(
        st.number_input(
            cfg["item_names"][i],
            0,
            value=defaults[i],
            key=f"item_{i}",
            label_visibility="collapsed"
        )
    )

    if i + 1 < 7:
        counts.append(
            st.number_input(
                cfg["item_names"][i+1],
                0,
                value=defaults[i+1],
                key=f"item_{i+1}",
                label_visibility="collapsed"
            )
        )

    st.markdown('</div>', unsafe_allow_html=True)

# ======================
# 저장
# ======================
if st.button("✅ 최종 실적 저장", use_container_width=True, type="primary"):
    item_total = sum(c * p for c, p in zip(counts, cfg["item_prices"]))
    row = {
        "직원명": user_name,
        "날짜": str_date,
        "인센티브": st.session_state.current_incen_sum,
        "item1": counts[0],
        "item2": counts[1],
        "item3": counts[2],
        "item4": counts[3],
        "item5": counts[4],
        "item6": counts[5],
        "item7": counts[6],
        "합계": st.session_state.current_incen_sum + item_total,
        "비고": "정상",
        "입력시간": get_now_kst().strftime("%H:%M:%S")
    }
    if save_to_gsheet(row):
        st.success("저장 완료")
        st.rerun()
