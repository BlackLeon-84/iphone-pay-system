import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials

# 소프트웨어 버전
SW_VERSION = "v2.2.5"

# 페이지 설정
st.set_page_config(page_title=f"아이폰 정산 시스템 {SW_VERSION}", layout="centered")

# --- 아이폰 최적화 및 콤마 스타일 CSS ---
st.markdown("""
    <style>
    /* 화면 밖으로 나가지 않게 조절 */
    .stApp { max-width: 100%; overflow-x: hidden; }
    
    /* 아이폰 가로 2열/3열 유지하되 화면 안으로 고정 */
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: wrap !important; /* 화면 넘치면 안으로 들어오게 */
        gap: 5px !important;
    }
    div[data-testid="column"] {
        min-width: 120px !important; /* 최소 너비 확보 */
        flex: 1 1 0% !important;
    }
    
    /* 버튼 및 입력창 모바일 최적화 */
    .stButton button { width: 100%; padding: 5px; font-size: 14px; }
    .stNumberInput input { font-size: 16px !important; } /* 아이폰 줌 방지 */

    .weekly-container { display: flex; justify-content: space-around; background: #f8f9fa; padding: 10px; border-radius: 10px; border: 1px solid #eee; }
    .weekly-item { text-align: center; flex: 1; }
    .status-box { padding: 12px; border-radius: 10px; margin-bottom: 10px; text-align: center; font-weight: bold; border: 1px solid #ddd; }
    
    /* 리포트 표 스타일 (콤마 및 합계 행) */
    .report-table { width: 100%; font-size: 11px; text-align: center; border-collapse: collapse; background: white; }
    .report-table th, .report-table td { border: 1px solid #eee; padding: 6px 2px; }
    .total-row { background-color: #eee !important; font-weight: bold; color: #000; }
    </style>
    """, unsafe_allow_html=True)

# --- 구글 시트 함수 ---
SHEET_NAME = "아이폰정산"

def get_gsheet_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    if "gcp_service_account" in st.secrets:
        creds_info = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_info:
            creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        return gspread.authorize(creds)
    st.error("인증 설정 필요"); st.stop()

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

# --- 세션 관리 ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "config" not in st.session_state:
    st.session_state.config = {"base_salary": 3500000, "start_day": 13, "insurance": 104760, 
                               "item_names": ['일반필름', '풀필름', '젤리', '케이블', '어댑터', '추가1', '추가2'],
                               "item_prices": [9000, 18000, 9000, 15000, 23000, 0, 0]}

# --- 로그인 ---
STAFF_LIST = ["태완", "남근", "성훈"]
if not st.session_state.logged_in:
    st.title("🔐 로그인")
    user_id = st.selectbox("직원 선택", options=STAFF_LIST)
    admin_pw = st.text_input("비밀번호", type="password") if user_id == "태완" else ""
    if st.button("입장하기"):
        if user_id == "태완" and admin_pw != "102030": st.error("비밀번호 틀림")
        else: st.session_state.logged_in = True; st.session_state.user_name = user_id; st.rerun()
    st.stop()

# --- 사이드바 (설정 메뉴 아이폰 가로 정렬) ---
user_name = st.session_state.user_name
cfg = st.session_state.config
with st.sidebar:
    st.header("⚙️ 시스템 설정")
    if user_name == "태완":
        st.subheader("🛠️ 관리자 설정")
        target_staff = st.selectbox("수정 대상", STAFF_LIST)
        
        st.write("**📦 품목 단가 (한 줄 배치)**")
        new_names = []; new_prices = []
        for i in range(7):
            c1, c2 = st.columns([1, 1])
            n = c1.text_input(f"품명{i}", value=cfg["item_names"][i], key=f"sn_{i}", label_visibility="collapsed")
            p = c2.number_input(f"금액{i}", value=cfg["item_prices"][i], step=1000, key=f"sp_{i}", label_visibility="collapsed")
            new_names.append(n); new_prices.append(p)
        
        st.write("**💰 정산 설정**")
        base = st.number_input("기본급", value=cfg["base_salary"], step=10000); st.write(f"👉 {base:,}원")
        s_day = st.slider("시작일", 1, 31, cfg["start_day"])
        ins = st.number_input("보험료", value=cfg["insurance"]); st.write(f"👉 {ins:,}원")
        
        if st.button("💿 설정 저장", use_container_width=True):
            st.session_state.config.update({"base_salary": base, "start_day": s_day, "insurance": ins, "item_names": new_names, "item_prices": new_prices})
            st.success("설정 저장됨!"); st.rerun()
    
    if st.button("로그아웃"): st.session_state.logged_in = False; st.rerun()

# --- 메인 실적 입력 ---
df_all = load_data_from_gsheet()
st.write(f"### 💼 {user_name}님 실적")

t_c1, t_c2 = st.columns([1, 1])
sel_date = t_c1.date_input("날짜", value=date.today(), label_visibility="collapsed")
str_date = sel_date.strftime("%Y-%m-%d")

if "last_date" not in st.session_state: st.session_state.last_date = str_date
if st.session_state.last_date != str_date:
    st.session_state.current_incen_sum = None; st.session_state.incen_history = []; st.session_state.last_date = str_date

existing_row = df_all[(df_all["날짜"] == str_date) & (df_all["직원명"] == user_name)] if not df_all.empty else pd.DataFrame()
is_edit = not existing_row.empty

if st.session_state.get("current_incen_sum") is None:
    st.session_state.current_incen_sum = int(existing_row.iloc[0]["인센티브"]) if is_edit else 0
    st.session_state.incen_history = [int(existing_row.iloc[0]["인센티브"])] if is_edit and int(existing_row.iloc[0]["인센티브"]) > 0 else []

# 상태 표시 및 휴무
st.markdown(f'<div class="status-box" style="background-color: {"#e3f2fd" if is_edit else "#fafafa"};">'
            f'{f"📌 {str_date} 기록 중" if is_edit else "📝 실적을 입력하세요."}</div>', unsafe_allow_html=True)

if t_c2.button("🌴 휴무 등록", use_container_width=True):
    row = {"직원명": user_name, "날짜": str_date, "인센티브": 0, "item1":0, "item2":0, "item3":0, "item4":0, "item5":0, "item6":0, "item7":0, "합계": 0, "비고": "휴무", "입력시간": get_now_kst().strftime("%H:%M:%S")}
    if save_to_gsheet(row): st.rerun()

# 인센티브 섹션 (콤마 적용)
st.markdown(f"**💰 인센 합계: {st.session_state.current_incen_sum:,}원**")
add_amt = st.number_input("추가금액", min_value=0, step=1000, value=0, label_visibility="collapsed")
b_c1, b_c2, b_c3 = st.columns(3)
if b_c1.button("➕ 추가"): st.session_state.current_incen_sum += add_amt; st.session_state.incen_history.append(add_amt); st.rerun()
if b_c2.button("↩️ 취소") and st.session_state.incen_history: st.session_state.current_incen_sum -= st.session_state.incen_history.pop(); st.rerun()
if b_c3.button("🧹 리셋"): st.session_state.current_incen_sum = 0; st.session_state.incen_history = []; st.rerun()

# 품목 수량 (아이폰 2열)
st.write("**📦 품목 수량**")
counts = []
for i in range(1, 7, 2):
    c1, c2 = st.columns(2)
    for j, col in enumerate([c1, c2]):
        idx = i + j
        def_val = int(existing_row.iloc[0][f'item{idx}']) if is_edit else 0
        counts.append(col.number_input(cfg["item_names"][idx-1], 0, value=def_val, key=f"inp_{idx}"))
counts.append(st.number_input(cfg["item_names"][6], 0, value=(int(existing_row.iloc[0]['item7']) if is_edit else 0)))

if st.button("✅ 최종 실적 저장", type="primary", use_container_width=True):
    item_total = sum([int(c) * int(p) for c, p in zip(counts, cfg["item_prices"])])
    row = {"직원명": user_name, "날짜": str_date, "인센티브": st.session_state.current_incen_sum, 
           "item1": counts[0], "item2": counts[1], "item3": counts[2], "item4": counts[3], 
           "item5": counts[4], "item6": counts[5], "item7": counts[6], 
           "합계": st.session_state.current_incen_sum + item_total, "비고": "정상", "입력시간": get_now_kst().strftime("%H:%M:%S")}
    if save_to_gsheet(row): st.success("저장 완료!"); st.rerun()

# --- 정산 리포트 (콤마 & 하단 합계 행) ---
st.divider()
st.subheader("📊 정산 리포트")
s_day = cfg['start_day']
if sel_date.day >= s_day:
    start_dt = date(sel_date.year, sel_date.month, s_day)
    nm, ny = (sel_date.month+1, sel_date.year) if sel_date.month < 12 else (1, sel_date.year+1)
    end_dt = date(ny, nm, s_day) - timedelta(days=1)
else:
    end_dt = date(sel_date.year, sel_date.month, s_day) - timedelta(days=1)
    pm, py = (sel_date.month-1, sel_date.year) if sel_date.month > 1 else (12, sel_date.year-1)
    start_dt = date(py, pm, s_day)

if not df_all.empty:
    p_df = df_all[(df_all["직원명"] == user_name) & (pd.to_datetime(df_all['날짜']).dt.date >= start_dt) & (pd.to_datetime(df_all['날짜']).dt.date <= end_dt)].sort_values("날짜")
    if not p_df.empty:
        total_incen = p_df["인센티브"].sum()
        total_extra = p_df["합계"].sum()
        st.markdown(f"### **🏦 실수령: {int(cfg['base_salary'] + total_extra - cfg['insurance']):,}원**")
        st.caption(f"기본 {cfg['base_salary']:,} + 추가 {total_extra:,} - 보험 {cfg['insurance']:,}")
        
        headers = ["날짜", "인센"] + [n[:2] for n in cfg["item_names"]] + ["합계"]
        rows_html = ""
        item_sums = [0]*7
        for _, r in p_df.iterrows():
            is_h = r['비고'] == "휴무"
            rows_html += f"<tr {'style=\"background-color:#fffde7;\"' if is_h else ''}><td>{datetime.strptime(r['날짜'], '%Y-%m-%d').day}일</td>"
            if is_h: rows_html += '<td colspan="9" style="color:#f57f17;">🌴 휴무</td>'
            else:
                rows_html += f"<td>{int(r['인센티브']):,}</td>"
                for i in range(1, 8):
                    val = int(r[f'item{i}'])
                    rows_html += f"<td>{val}</td>"
                    item_sums[i-1] += val
                rows_html += f"<td>{int(r['합계']):,}</td>"
            rows_html += "</tr>"
        
        # [복구] 하단 합계 행 추가
        rows_html += f"<tr class='total-row'><td>합계</td><td>{total_incen:,}</td>"
        for s in item_sums: rows_html += f"<td>{s}</td>"
        rows_html += f"<td>{total_extra:,}</td></tr>"
        
        st.markdown(f'<table class="report-table"><tr>{"".join([f"<th>{h}</th>" for h in headers])}</tr>{rows_html}</table>', unsafe_allow_html=True)
