import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials

# 소프트웨어 버전
SW_VERSION = "v2.4.4"

# 페이지 설정
st.set_page_config(page_title=f"정산 {SW_VERSION}", layout="centered")

# --- [스마트 레이아웃] 아이폰 가로 3열 버튼 강제 고정 CSS ---
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

    /* 2. 불필요한 서식 제거 */
    hr {{ border: 0; height: 1px; background: #eee; margin: 15px 0; }}
    div[data-testid="stVerticalBlock"] > div {{ border: none !important; }}
    div[data-baseweb="base-input"] {{ border: none !important; background-color: #f1f3f5 !important; border-radius: 8px !important; }}

    /* 3. ★ 핵심: 좁은 화면에서도 가로 3열 강제 유지 ★ */
    [data-testid="stHorizontalBlock"] {{
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important; /* 아래로 떨어지지 않게 설정 */
        align-items: center !important;
        gap: 4px !important; /* 버튼 사이 간격 최소화 */
    }}
    [data-testid="stHorizontalBlock"] > div {{
        flex: 1 1 0% !important; /* 모든 컬럼이 동일한 폭을 가짐 */
        min-width: 0 !important;
    }}
    div[data-testid="stHorizontalBlock"] button {{
        font-size: 11px !important; /* 아이폰용 글자 크기 최적화 */
        padding: 0px !important;
        width: 100% !important;
        min-height: 40px !important;
        white-space: nowrap !important; /* 글자 줄바꿈 방지 */
    }}

    /* 4. 텍스트 및 테이블 스타일 */
    input {{ font-size: 16px !important; }}
    label p {{ font-size: 12px !important; font-weight: bold !important; color: #444 !important; }}
    .weekly-box {{ display: flex; justify-content: space-around; background: #f8f9fa; padding: 10px; border-radius: 10px; margin-bottom: 15px; }}
    .report-table {{ width: 100%; font-size: 10px; text-align: center; border-collapse: collapse; }}
    .report-table th, .report-table td {{ border: 1px solid #eee; padding: 5px 2px; }}
    .total-row {{ background-color: #f2f2f2 !important; font-weight: bold; }}
    .calc-detail {{ font-size: 11px; color: #888; margin-top: -5px; margin-bottom: 10px; }}
    .incen-log {{ font-size: 11px; color: #666; padding: 8px; background: #fcfcfc; border-radius: 5px; border-left: 3px solid #ddd; margin: 10px 0; }}
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

# --- 세션 및 설정 ---
STAFF_LIST = ["태완", "남근", "성훈"]
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "config" not in st.session_state:
    st.session_state.config = {"base_salary": 3500000, "start_day": 13, "insurance": 104760, 
                               "item_names": ['일반필름', '풀필름', '젤리', '케이블', '어댑터', '추가1', '추가2'],
                               "item_prices": [9000, 18000, 9000, 15000, 23000, 0, 0]}

# --- 로그인 ---
if not st.session_state.logged_in:
    st.title("🔐 로그인")
    user_id = st.selectbox("직원 선택", options=STAFF_LIST)
    admin_pw = st.text_input("비번", type="password") if user_id == "태완" else ""
    if st.button("입장"):
        if user_id == "태완" and admin_pw != "102030": st.error("비번 오류")
        else: st.session_state.logged_in = True; st.session_state.user_name = user_id; st.rerun()
    st.stop()

# --- 사이드바 ---
user_name = st.session_state.user_name
cfg = st.session_state.config
with st.sidebar:
    st.header("⚙️ 설정")
    if user_name == "태완":
        st.subheader("🛠️ 관리자 설정")
        target_staff = st.selectbox("수정 대상 직원", STAFF_LIST)
        new_names = []; new_prices = []
        for i in range(7):
            c1, c2 = st.columns(2)
            n = c1.text_input(f"명칭{i+1}", value=cfg["item_names"][i], key=f"sn_{i}")
            p = c2.number_input(f"가격{i+1}", value=cfg["item_prices"][i], step=1000, key=f"sp_{i}")
            new_names.append(n); new_prices.append(p)
        base = st.number_input("기본급", value=cfg["base_salary"])
        s_day = st.slider("정산 시작일", 1, 31, cfg["start_day"])
        ins = st.number_input("보험료", value=cfg["insurance"])
        if st.button("💿 설정 저장", use_container_width=True):
            st.session_state.config.update({"base_salary": base, "start_day": s_day, "insurance": ins, "item_names": new_names, "item_prices": new_prices})
            st.success("저장 완료"); st.rerun()
    if st.button("로그아웃"): st.session_state.logged_in = False; st.rerun()

# --- 메인 화면 ---
st.markdown(f'<div class="version-tag">{SW_VERSION}</div>', unsafe_allow_html=True)
df_all = load_data_from_gsheet()
st.write(f"### 💼 {user_name}님 실적")

sel_date = st.date_input("날짜", value=date.today(), label_visibility="collapsed")
str_date = sel_date.strftime("%Y-%m-%d")
if st.button("🌴 오늘 휴무 등록", use_container_width=True):
    row = {"직원명": user_name, "날짜": str_date, "인센티브": 0, "item1":0, "item2":0, "item3":0, "item4":0, "item5":0, "item6":0, "item7":0, "합계": 0, "비고": "휴무", "입력시간": get_now_kst().strftime("%H:%M:%S")}
    if save_to_gsheet(row): st.rerun()

st.write("**📅 최근 7일**")
weekly_html = '<div class="weekly-box">'
today_kst = get_now_kst().date()
for i in range(6, -1, -1):
    target_d = today_kst - timedelta(days=i)
    target_str = target_d.strftime("%Y-%m-%d")
    day_data = df_all[(df_all["날짜"] == target_str) & (df_all["직원명"] == user_name)] if not df_all.empty else pd.DataFrame()
    icon = "✅" if not day_data.empty and day_data.iloc[0]['비고'] != "휴무" else ("🌴" if not day_data.empty else "⚪")
    weekly_html += f'<div style="text-align:center;"><div style="font-size:10px;">{target_d.day}일</div><div>{icon}</div></div>'
st.markdown(weekly_html + '</div>', unsafe_allow_html=True)

st.divider()
existing_row = df_all[(df_all["날짜"] == str_date) & (df_all["직원명"] == user_name)] if not df_all.empty else pd.DataFrame()
is_edit = not existing_row.empty

if "current_incen_sum" not in st.session_state or st.session_state.get("last_date") != str_date:
    st.session_state.current_incen_sum = int(existing_row.iloc[0]["인센티브"]) if is_edit else 0
    st.session_state.incen_history = [{"val": int(existing_row.iloc[0]["인센티브"]), "time": "기존"}] if is_edit and int(existing_row.iloc[0]["인센티브"]) > 0 else []
    st.session_state.last_date = str_date

st.write(f"**💰 인센 합계: {st.session_state.current_incen_sum:,}원**")
if st.session_state.incen_history:
    st.markdown(f'<div class="incen-log">📋 상세: {" / ".join([f"{h['val']:,}" for h in st.session_state.incen_history])}</div>', unsafe_allow_html=True)

add_amt = st.number_input("인센 금액", min_value=0, step=1000, value=0)

# 가로 3열 강제 고정 버튼
col1, col2, col3 = st.columns(3)
if col1.button("➕추가", use_container_width=True):
    st.session_state.current_incen_sum += add_amt
    st.session_state.incen_history.append({"val": add_amt, "time": get_now_kst().strftime("%H:%M")})
    st.rerun()
if col2.button("↩️취소", use_container_width=True) and st.session_state.incen_history:
    pop_item = st.session_state.incen_history.pop()
    st.session_state.current_incen_sum -= pop_item['val']; st.rerun()
if col3.button("🧹리셋", use_container_width=True):
    st.session_state.current_incen_sum = 0; st.session_state.incen_history = []; st.rerun()

st.divider()
st.write("**📦 품목 수량**")
counts = []
for i in range(0, 6, 2):
    c1, c2 = st.columns(2)
    with c1:
        v1 = int(existing_row.iloc[0][f'item{i+1}']) if is_edit else 0
        counts.append(st.number_input(cfg["item_names"][i], 0, value=v1, key=f"it_{i}"))
    with c2:
        v2 = int(existing_row.iloc[0][f'item{i+2}']) if is_edit else 0
        counts.append(st.number_input(cfg["item_names"][i+1], 0, value=v2, key=f"it_{i+1}"))
v7 = int(existing_row.iloc[0]['item7']) if is_edit else 0
counts.append(st.number_input(cfg["item_names"][6], 0, value=v7, key="it_6"))

if st.button("✅ 최종 데이터 저장", type="primary", use_container_width=True):
    item_total = sum([int(c) * int(p) for c, p in zip(counts, cfg["item_prices"])])
    row = {"직원명": user_name, "날짜": str_date, "인센티브": st.session_state.current_incen_sum, 
           "item1": counts[0], "item2": counts[1], "item3": counts[2], "item4": counts[3], 
           "item5": counts[4], "item6": counts[5], "item7": counts[6], 
           "합계": st.session_state.current_incen_sum + item_total, "비고": "정상", "입력시간": get_now_kst().strftime("%H:%M:%S")}
    if save_to_gsheet(row): st.success("성공적으로 저장되었습니다."); st.rerun()

st.divider()
st.subheader("📊 정산 리포트")
s_day = cfg['start_day']
start_dt = date(sel_date.year, sel_date.month, s_day) if sel_date.day >= s_day else (date(sel_date.year, sel_date.month, s_day) - timedelta(days=30)).replace(day=s_day)
end_dt = (start_dt + timedelta(days=32)).replace(day=s_day) - timedelta(days=1)

if not df_all.empty:
    p_df = df_all[(df_all["직원명"] == user_name) & (pd.to_datetime(df_all['날짜']).dt.date >= start_dt) & (pd.to_datetime(df_all['날짜']).dt.date <= end_dt)].sort_values("날짜")
    if not p_df.empty:
        total_extra = p_df["합계"].sum()
        total_incen = p_df["인센티브"].sum()
        st.write(f"**🏦 예상 수령: {int(cfg['base_salary'] + total_extra - cfg['insurance']):,}원**")
        st.markdown(f'<div class="calc-detail">(기본 {cfg["base_salary"]:,} + 추가 {total_extra:,} - 보험 {cfg["insurance"]:,})</div>', unsafe_allow_html=True)
        
        headers = ["날", "인센"] + [n[:1] for n in cfg["item_names"]] + ["합계"]
        rows_html = ""; item_sums = [0]*7
        for _, r in p_df.iterrows():
            d = datetime.strptime(r['날짜'], '%Y-%m-%d').day
            if r['비고'] == "휴무": rows_html += f"<tr><td>{d}</td><td colspan='9' style='color:orange;'>🌴휴무</td></tr>"
            else:
                item_tds = "".join([f"<td>{int(r[f'item{i}'])}</td>" for i in range(1, 8)])
                for i in range(1, 8): item_sums[i-1] += int(r[f'item{i}'])
                rows_html += f"<tr><td>{d}</td><td>{int(r['인센티브']):,}</td>{item_tds}<td style='color:blue;'>{int(r['합계']):,}</td></tr>"
        
        rows_html += f"<tr class='total-row'><td>합</td><td>{total_incen:,}</td>" + "".join([f"<td>{s}</td>" for s in item_sums]) + f"<td>{total_extra:,}</td></tr>"
        st.markdown(f'<table class="report-table"><tr>{"".join([f"<th>{h}</th>" for h in headers])}</tr>{rows_html}</table>', unsafe_allow_html=True)
