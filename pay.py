import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials

# 소프트웨어 버전
SW_VERSION = "v2.2.8 - 모바일 최적화 강화"

# 페이지 설정
st.set_page_config(page_title=f"아이폰 정산 {SW_VERSION}", layout="centered", initial_sidebar_state="collapsed")

# ── 매우 강력한 모바일(아이폰) 최적화 CSS ──
st.markdown("""
    <style>
    /* 전체 여백 최소화 */
    .main .block-container {
        padding: 0.8rem 0.4rem !important;
        max-width: 100% !important;
    }
    
    /* 사이드바 기본 접힘 + 모바일 최적화 */
    section[data-testid="stSidebar"] {
        min-width: 220px !important;
        max-width: 260px !important;
    }
    
    /* 컬럼 강제 좁고 촘촘하게 */
    [data-testid="column"] {
        flex: 1 1 48% !important;
        max-width: 50% !important;
        min-width: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    
    /* 모든 가로 배치 강제 유지 + 스크롤 */
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        overflow-x: auto !important;
        gap: 6px !important;
        padding: 2px 0 !important;
        margin: 4px 0 !important;
    }
    
    /* 버튼 아주 작고 촘촘하게 */
    .stButton > button {
        padding: 4px 8px !important;
        font-size: 12px !important;
        min-height: 30px !important;
        line-height: 1.1 !important;
        white-space: nowrap !important;
        margin: 2px 0 !important;
    }
    
    /* 입력창 작게 */
    .stNumberInput > div > div > input,
    .stTextInput > div > div > input {
        font-size: 13px !important;
        padding: 4px 6px !important;
        height: 32px !important;
    }
    
    /* 라벨 작게 */
    label {
        font-size: 11px !important;
        margin-bottom: 2px !important;
    }
    
    /* 주간 현황 */
    .weekly-container {
        display: flex;
        flex-direction: row;
        overflow-x: auto;
        gap: 6px;
        padding: 6px;
        background: #f8f9fa;
        border-radius: 8px;
        margin: 8px 0;
    }
    .weekly-item {
        flex: 0 0 42px;
        text-align: center;
        font-size: 10px;
    }
    
    /* 인센 로그 */
    .incen-log {
        font-size: 11px;
        max-height: 110px;
        overflow-y: auto;
        background: #fdfdfd;
        padding: 6px;
        border-radius: 6px;
        border-left: 3px solid #ccc;
        margin: 6px 0;
    }
    
    /* 테이블 스크롤 가능하게 */
    .report-table-container {
        overflow-x: auto;
        margin: 8px 0;
    }
    .report-table {
        font-size: 10.5px !important;
        white-space: nowrap;
        min-width: 100%;
    }
    .report-table th, .report-table td {
        padding: 4px 5px !important;
        min-width: 42px;
    }
    
    /* 휴무 표시 */
    .holiday-row { background-color: #fffde7 !important; }
    </style>
""", unsafe_allow_html=True)

# ── 기본 함수들 ──
SHEET_NAME = "아이폰정산"

def get_gsheet_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    if "gcp_service_account" in st.secrets:
        creds_info = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_info:
            creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        return gspread.authorize(creds)
    st.error("Google 서비스 계정 정보가 없습니다.")
    st.stop()

def load_data_from_gsheet():
    try:
        client = get_gsheet_client()
        sheet = client.open(SHEET_NAME).sheet1
        data = sheet.get_all_records()
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        num_cols = ["인센티브", "item1", "item2", "item3", "item4", "item5", "item6", "item7", "합계"]
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"데이터 불러오기 실패\n{str(e)}")
        return pd.DataFrame()

def save_to_gsheet(row_dict):
    try:
        client = get_gsheet_client()
        sheet = client.open(SHEET_NAME).sheet1
        all_values = sheet.get_all_values()
        
        row_idx = -1
        for i, row in enumerate(all_values):
            if len(row) >= 2 and row[0] == row_dict['직원명'] and row[1] == row_dict['날짜']:
                row_idx = i + 1
                break
                
        values = list(row_dict.values())
        if row_idx != -1:
            sheet.update(range_name=f"A{row_idx}", values=[values])
        else:
            sheet.append_row(values)
        return True
    except Exception as e:
        st.error(f"저장 실패\n{str(e)}")
        return False

def get_now_kst():
    return datetime.now(timezone.utc) + timedelta(hours=9)

# ── 세션 초기화 ──
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "config" not in st.session_state:
    st.session_state.config = {
        "base_salary": 3500000,
        "start_day": 13,
        "insurance": 104760,
        "item_names": ['일반필름', '풀필름', '젤리', '케이블', '어댑터', '추가1', '추가2'],
        "item_prices": [9000, 18000, 9000, 15000, 23000, 0, 0]
    }

# ── 로그인 화면 ──
STAFF_LIST = ["태완", "남근", "성훈"]

if not st.session_state.logged_in:
    st.title("🔐 로그인")
    user_id = st.selectbox("직원 선택", STAFF_LIST)
    admin_pw = st.text_input("비밀번호 (태완만)", type="password") if user_id == "태완" else ""
    
    if st.button("입장하기", use_container_width=True):
        if user_id == "태완" and admin_pw != "102030":
            st.error("비밀번호가 틀렸습니다.")
        else:
            st.session_state.logged_in = True
            st.session_state.user_name = user_id
            st.rerun()
    st.stop()

# ── 사이드바 (설정) ──
user_name = st.session_state.user_name
cfg = st.session_state.config

with st.sidebar:
    st.header(f"⚙️ {user_name} 설정")
    
    if user_name == "태완":
        st.subheader("관리자 설정")
        target = st.selectbox("수정 대상", STAFF_LIST)
        
        st.markdown("**품목 단가**")
        new_names, new_prices = [], []
        for i in range(7):
            c1, c2 = st.columns([3,2], gap="small")
            n = c1.text_input(f"품명", value=cfg["item_names"][i], key=f"name_{i}")
            p = c2.number_input("", value=cfg["item_prices"][i], step=1000, key=f"price_{i}")
            new_names.append(n)
            new_prices.append(p)
        
        st.markdown("**정산 기본값**")
        base = st.number_input("기본급", value=cfg["base_salary"], step=10000)
        sday = st.slider("시작일", 1, 31, cfg["start_day"])
        ins = st.number_input("보험료", value=cfg["insurance"], step=1000)
        
        if st.button("💾 설정 저장", type="primary", use_container_width=True):
            st.session_state.config.update({
                "base_salary": base,
                "start_day": sday,
                "insurance": ins,
                "item_names": new_names,
                "item_prices": new_prices
            })
            st.success("저장되었습니다!")
            st.rerun()
    
    if st.button("로그아웃", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

# ── 메인 화면 ──
df_all = load_data_from_gsheet()

st.title(f"💼 {user_name} 실적입력")

col_date, col_holiday = st.columns([3,2])
sel_date = col_date.date_input("날짜", value=date.today())
str_date = sel_date.strftime("%Y-%m-%d")

# 최근 7일
st.markdown("**최근 7일**")
weekly_html = '<div class="weekly-container">'
today = get_now_kst().date()
for i in range(6, -1, -1):
    d = today - timedelta(days=i)
    ds = d.strftime("%Y-%m-%d")
    day_data = df_all[(df_all["날짜"] == ds) & (df_all["직원명"] == user_name)]
    icon = "✅" if not day_data.empty and day_data.iloc[0].get('비고') != "휴무" else "🌴" if not day_data.empty else "⚪"
    weekly_html += f'<div class="weekly-item">{d.day}일<br>{icon}</div>'
st.markdown(weekly_html + '</div>', unsafe_allow_html=True)

# 날짜 바뀌면 초기화
if "last_date" not in st.session_state or st.session_state.last_date != str_date:
    st.session_state.last_date = str_date
    st.session_state.current_incen_sum = 0
    st.session_state.incen_history = []

existing = df_all[(df_all["날짜"] == str_date) & (df_all["직원명"] == user_name)]
is_edit = not existing.empty

if is_edit and st.session_state.current_incen_sum == 0:
    st.session_state.current_incen_sum = int(existing.iloc[0]["인센티브"])
    st.session_state.incen_history = [{"time": get_now_kst().strftime("%m/%d %H:%M"), "val": st.session_state.current_incen_sum}]

st.markdown(f"**인센 합계 : {st.session_state.current_incen_sum:,} 원**")

if st.session_state.incen_history:
    log_html = '<div class="incen-log">'
    for h in st.session_state.incen_history:
        sign = "+" if h["val"] >= 0 else ""
        log_html += f'<div>{h["time"]}  {sign}{h["val"]:,}원</div>'
    log_html += '</div>'
    st.markdown(log_html, unsafe_allow_html=True)

add_amt = st.number_input("추가/차감 금액", min_value=0, step=1000, value=0)

b1, b2, b3 = st.columns(3, gap="small")
if b1.button("➕ 추가"):
    if add_amt > 0:
        st.session_state.current_incen_sum += add_amt
        st.session_state.incen_history.append({"time": get_now_kst().strftime("%m/%d %H:%M"), "val": add_amt})
    st.rerun()

if b2.button("↩️ 취소"):
    if st.session_state.incen_history:
        last = st.session_state.incen_history.pop()
        st.session_state.current_incen_sum -= last["val"]
    st.rerun()

if b3.button("🧹 리셋"):
    st.session_state.current_incen_sum = 0
    st.session_state.incen_history = []
    st.rerun()

# 휴무 버튼
if st.button("🌴 오늘 휴무 등록", use_container_width=True):
    row = {
        "직원명": user_name, "날짜": str_date, "인센티브": 0,
        "item1":0, "item2":0, "item3":0, "item4":0, "item5":0, "item6":0, "item7":0,
        "합계": 0, "비고": "휴무", "입력시간": get_now_kst().strftime("%H:%M:%S")
    }
    if save_to_gsheet(row):
        st.success("휴무 등록 완료")
        st.rerun()

st.divider()

# 품목 입력
st.subheader("품목 수량")
counts = []

for i in range(0, 6, 2):
    c1, c2 = st.columns(2, gap="small")
    idx1 = i
    idx2 = i + 1
    
    def1 = int(existing.iloc[0][f'item{idx1+1}']) if is_edit else 0
    def2 = int(existing.iloc[0][f'item{idx2+1}']) if is_edit else 0
    
    counts.append(
        c1.number_input(cfg["item_names"][idx1], min_value=0, value=def1, key=f"item{idx1+1}")
    )
    if idx2 < 6:
        counts.append(
            c2.number_input(cfg["item_names"][idx2], min_value=0, value=def2, key=f"item{idx2+1}")
        )

# 마지막 품목 (7번째)
counts.append(
    st.number_input(cfg["item_names"][6], min_value=0, value=int(existing.iloc[0]['item7']) if is_edit else 0)
)

if st.button("✅ 실적 저장하기", type="primary", use_container_width=True):
    item_total = sum(c * p for c, p in zip(counts, cfg["item_prices"]))
    total = st.session_state.current_incen_sum + item_total
    
    row = {
        "직원명": user_name,
        "날짜": str_date,
        "인센티브": st.session_state.current_incen_sum,
        "item1": counts[0], "item2": counts[1], "item3": counts[2],
        "item4": counts[3], "item5": counts[4], "item6": counts[5], "item7": counts[6],
        "합계": total,
        "비고": "정상",
        "입력시간": get_now_kst().strftime("%H:%M:%S")
    }
    
    if save_to_gsheet(row):
        st.success("저장 완료!")
        st.rerun()

# ── 정산 리포트 ──
st.divider()
st.subheader("📊 이번 정산 예상")

s_day = cfg["start_day"]
if sel_date.day >= s_day:
    start = date(sel_date.year, sel_date.month, s_day)
    end_year, end_month = (sel_date.year, sel_date.month + 1) if sel_date.month < 12 else (sel_date.year + 1, 1)
    end = date(end_year, end_month, s_day) - timedelta(days=1)
else:
    end = date(sel_date.year, sel_date.month, s_day) - timedelta(days=1)
    start_year, start_month = (sel_date.year, sel_date.month - 1) if sel_date.month > 1 else (sel_date.year - 1, 12)
    start = date(start_year, start_month, s_day)

period_df = df_all[
    (df_all["직원명"] == user_name) &
    (pd.to_datetime(df_all["날짜"]).dt.date >= start) &
    (pd.to_datetime(df_all["날짜"]).dt.date <= end)
].sort_values("날짜")

if not period_df.empty:
    total_incen = period_df["인센티브"].sum()
    total_sum = period_df["합계"].sum()
    
    expected = cfg["base_salary"] + total_sum - cfg["insurance"]
    
    st.markdown(f"**실수령 예상** : **{int(expected):,} 원**")
    st.caption(f"기본급 {cfg['base_salary']:,} + 추가 {total_sum:,} - 4대보험 {cfg['insurance']:,}")
    
    with st.container():
        st.markdown('<div class="report-table-container">', unsafe_allow_html=True)
        
        headers = ["날짜", "인센"] + [n[:2] for n in cfg["item_names"]] + ["합계"]
        
        html = '<table class="report-table"><thead><tr>'
        for h in headers:
            html += f"<th>{h}</th>"
        html += "</tr></thead><tbody>"
        
        item_sums = [0] * 7
        
        for _, r in period_df.iterrows():
            is_holiday = r.get("비고", "") == "휴무"
            html += f'<tr {"class=holiday-row" if is_holiday else ""}>'
            html += f'<td>{datetime.strptime(r["날짜"], "%Y-%m-%d").day}일</td>'
            
            if is_holiday:
                html += '<td colspan="9" style="color:#e67e22; font-weight:bold;">휴무</td>'
            else:
                html += f'<td>{int(r["인센티브"]):,}</td>'
                for i in range(7):
                    v = int(r[f"item{i+1}"])
                    html += f"<td>{v}</td>"
                    item_sums[i] += v
                html += f'<td>{int(r["합계"]):,}</td>'
            html += "</tr>"
        
        html += '<tr class="total-row"><td>합계</td>'
        html += f'<td>{total_incen:,}</td>'
        for s in item_sums:
            html += f"<td>{s}</td>"
        html += f'<td>{total_sum:,}</td></tr>'
        
        html += "</tbody></table>"
        st.markdown(html, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

else:
    st.info("이번 정산 기간에 기록된 실적이 없습니다.")
