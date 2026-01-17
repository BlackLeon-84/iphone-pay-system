import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials

# 소프트웨어 버전
SW_VERSION = "v3.0.9"

# 페이지 설정
st.set_page_config(page_title=f"정산 {SW_VERSION}", layout="centered")

# --- [스마트 레이아웃] 아이폰 100% 최적화 CSS ---
st.markdown(f"""
    <style>
    .block-container {{ padding-top: 3.5rem !important; max-width: 450px !important; padding-left: 10px !important; padding-right: 10px !important; }}
    .version-tag {{ font-size: 10px; color: #ccc; text-align: right; margin-bottom: -10px; }}
    hr {{ border: 0; height: 1px; background: #eee; margin: 15px 0; }}
    div[data-baseweb="base-input"] {{ border: none !important; background-color: #f1f3f5 !important; border-radius: 8px !important; }}

    /* 아이폰용 버튼 가로 정렬 고정 (v3.0.0 스타일) */
    .st-key-incen_buttons [data-testid="stHorizontalBlock"] {{ display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important; gap: 4px !important; width: 100% !important; }}
    .st-key-incen_buttons button {{ font-size: 10px !important; padding: 0px 1px !important; min-height: 40px !important; white-space: nowrap; }}

    /* 로그인 및 강조 스타일 */
    .st-key-login_btn button {{ height: 50px !important; font-size: 18px !important; font-weight: bold !important; background-color: #007bff !important; color: white !important; }}

    /* 테이블 및 로그 스타일 */
    .report-table {{ width: 100%; font-size: 10px; text-align: center; border-collapse: collapse; }}
    .report-table th, .report-table td {{ border: 1px solid #eee; padding: 5px 2px; }}
    .total-row {{ background-color: #f2f2f2 !important; font-weight: bold; }}
    .calc-detail {{ font-size: 11px; color: #888; margin-top: -5px; margin-bottom: 10px; }}
    .incen-log {{ font-size: 11px; color: #666; padding: 8px; background: #fcfcfc; border-radius: 5px; border-left: 3px solid #ddd; margin: 10px 0; }}
    .save-log {{ font-size: 12px; color: #1e88e5; font-weight: bold; margin-bottom: 5px; }}
    .config-log {{ font-size: 11px; color: #28a745; background: #f0fff4; padding: 8px; border-radius: 5px; margin-top: 10px; border: 1px solid #c6f6d5; }}
    .update-log {{ font-size: 11px; color: #777; background: #f9f9f9; padding: 10px; border-radius: 8px; margin-top: 30px; border: 1px solid #eee; }}
    </style>
    """, unsafe_allow_html=True)

# --- 구글 시트 연결 ---
SHEET_NAME = "아이폰정산"

def get_gsheet_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_info = dict(st.secrets["gcp_service_account"])
    creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    return gspread.authorize(creds)

def get_user_sheet(user_name):
    client = get_gsheet_client()
    spreadsheet = client.open(SHEET_NAME)
    try:
        return spreadsheet.worksheet(user_name)
    except gspread.WorksheetNotFound:
        new_sheet = spreadsheet.add_worksheet(title=user_name, rows="1000", cols="20")
        headers = ["직원명", "날짜", "인센티브", "item1", "item2", "item3", "item4", "item5", "item6", "item7", "합계", "비고", "입력시간"]
        new_sheet.append_row(headers)
        return new_sheet

def load_data_from_gsheet(user_name):
    try:
        sheet = get_user_sheet(user_name)
        df = pd.DataFrame(sheet.get_all_records())
        if not df.empty:
            num_cols = ["인센티브", "item1", "item2", "item3", "item4", "item5", "item6", "item7", "합계"]
            for col in num_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        return df
    except: return pd.DataFrame()

def save_to_gsheet(user_name, df_row):
    try:
        sheet = get_user_sheet(user_name)
        all_data = sheet.get_all_values()
        row_idx = -1
        for i, row in enumerate(all_data):
            if len(row) > 1 and row[1] == df_row['날짜']:
                row_idx = i + 1; break
        if row_idx != -1: sheet.update(range_name=f"A{row_idx}", values=[list(df_row.values())])
        else: sheet.append_row(list(df_row.values()))
        return True
    except: return False

def get_now_kst(): return datetime.now(timezone.utc) + timedelta(hours=9)

# --- 세션 및 설정 ---
STAFF_LIST = ["태완", "남근", "성훈"]
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "config_dict" not in st.session_state:
    st.session_state.config_dict = {name: {
        "base_salary": 3500000, "start_day": 13, "insurance": 104760, 
        "item_names": ['일반필름', '풀필름', '젤리', '케이블', '어댑터', '추가1', '추가2'],
        "item_prices": [9000, 18000, 9000, 15000, 23000, 0, 0]
    } for name in STAFF_LIST}
if "admin_log" not in st.session_state: st.session_state.admin_log = []

# --- 로그인 페이지 ---
if not st.session_state.logged_in:
    st.title("🔐 로그인")
    user_id = st.selectbox("직원 선택", options=STAFF_LIST)
    admin_pw = st.text_input("비번", type="password") if user_id == "태완" else ""
    if st.button("입장", use_container_width=True, key="login_btn"):
        if user_id == "태완" and admin_pw != "102030": st.error("비번 오류")
        else: st.session_state.logged_in = True; st.session_state.user_name = user_id; st.rerun()
    
    now_d = get_now_kst().strftime("%Y-%m-%d")
    st.markdown(f"""
        <div class="update-log">
            <b>🚀 시스템 업데이트 로그 ({now_d})</b><br>
            • <b>숫자 가독성 개선</b>: 관리자 설정창의 모든 금액 입력 시 천 단위 콤마(,) 표시<br>
            • <b>관리자 설정 로그</b>: 설정 변경 이력을 하단에서 실시간 확인 가능<br>
            • <b>정산 리포트 복구 완료</b> 및 <b>직원별 독립 시트</b> 운영 중
        </div>
    """, unsafe_allow_html=True)
    st.stop()

# --- 메인 본문 로직 ---
user_name = st.session_state.user_name
cfg = st.session_state.config_dict[user_name]

with st.sidebar:
    st.header("⚙️ 설정")
    if user_name == "태완":
        st.subheader("🛠️ 관리자 설정")
        target_staff = st.selectbox("수정 대상 직원", STAFF_LIST)
        t_cfg = st.session_state.config_dict[target_staff]
        
        new_names = []; new_prices = []
        for i in range(7):
            c1, c2 = st.columns(2)
            n = c1.text_input(f"명칭{i+1}", value=t_cfg["item_names"][i], key=f"sn_{target_staff}_{i}")
            # 숫자 입력 시 콤마 표시 (format="%d" -> 기본값 혹은 콤마 지원)
            p = c2.number_input(f"가격{i+1}", value=t_cfg["item_prices"][i], step=1000, key=f"sp_{target_staff}_{i}")
            new_names.append(n); new_prices.append(p)
        
        base = st.number_input("기본급", value=t_cfg["base_salary"], step=10000)
        s_day = st.slider("정산 시작일", 1, 31, t_cfg["start_day"])
        ins = st.number_input("보험료", value=t_cfg["insurance"], step=10)
        
        if st.button(f"💿 {target_staff} 설정 저장", use_container_width=True):
            st.session_state.config_dict[target_staff].update({
                "base_salary": base, "start_day": s_day, "insurance": ins, 
                "item_names": new_names, "item_prices": new_prices
            })
            log_msg = f"{get_now_kst().strftime('%m-%d %H:%M:%S')} | {target_staff}님의 설정이 저장되었습니다."
            st.session_state.admin_log.insert(0, log_msg) # 최신 로그를 위로
            st.success("설정 저장 완료!"); st.rerun()
            
        # 설정 변경 로그 기록창
        if st.session_state.admin_log:
            st.markdown("**📝 설정 변경 로그**")
            log_display = "<br>".join(st.session_state.admin_log[:5]) # 최근 5개만
            st.markdown(f'<div class="config-log">{log_display}</div>', unsafe_allow_html=True)
            
    if st.button("로그아웃"): st.session_state.logged_in = False; st.rerun()

st.markdown(f'<div class="version-tag">{SW_VERSION}</div>', unsafe_allow_html=True)
df_all = load_data_from_gsheet(user_name)
st.write(f"### 💼 {user_name}님 실적")

sel_date = st.date_input("날짜", value=date.today(), label_visibility="collapsed")
str_date = sel_date.strftime("%Y-%m-%d")

# 상단 저장 기록 로그
existing_row = df_all[df_all["날짜"] == str_date] if not df_all.empty else pd.DataFrame()
if not existing_row.empty:
    save_time = existing_row.iloc[0].get('입력시간', '기록없음')
    st.markdown(f'<div class="save-log">📝 {str_date} {save_time}에 저장된 기록이 있습니다.</div>', unsafe_allow_html=True)
else:
    st.markdown(f'<div style="font-size:12px; color:#999; margin-bottom:5px;">⚪ {str_date}에 저장된 기록이 없습니다.</div>', unsafe_allow_html=True)

if st.button("🌴 오늘 휴무 등록", use_container_width=True):
    row = {"직원명": user_name, "날짜": str_date, "인센티브": 0, "item1":0, "item2":0, "item3":0, "item4":0, "item5":0, "item6":0, "item7":0, "합계": 0, "비고": "휴무", "입력시간": get_now_kst().strftime("%H:%M:%S")}
    if save_to_gsheet(user_name, row): st.rerun()

st.write("**📅 최근 7일 기록**")
weekly_html = '<div style="display: flex; justify-content: space-around; background: #f8f9fa; padding: 10px; border-radius: 10px; margin-bottom: 15px;">'
today_kst = get_now_kst().date()
for i in range(6, -1, -1):
    target_d = today_kst - timedelta(days=i)
    target_str = target_d.strftime("%Y-%m-%d")
    day_data = df_all[df_all["날짜"] == target_str] if not df_all.empty else pd.DataFrame()
    icon = "✅" if not day_data.empty and day_data.iloc[0]['비고'] != "휴무" else ("🌴" if not day_data.empty else "⚪")
    weekly_html += f'<div style="text-align:center;"><div style="font-size:10px;">{target_d.day}일</div><div>{icon}</div></div>'
st.markdown(weekly_html + '</div>', unsafe_allow_html=True)

st.divider()
is_edit = not existing_row.empty
if "incen_sum" not in st.session_state or st.session_state.get("last_date") != str_date:
    st.session_state.incen_sum = int(existing_row.iloc[0]["인센티브"]) if is_edit else 0
    st.session_state.incen_history = [{"val": int(existing_row.iloc[0]["인센티브"]), "time": "기존"}] if is_edit and int(existing_row.iloc[0]["인센티브"]) > 0 else []
    st.session_state.last_date = str_date

st.write(f"**💰 인센 합계: {st.session_state.incen_sum:,}원**")
if st.session_state.incen_history:
    st.markdown(f'<div class="incen-log">📋 상세: {" / ".join([f"{h['val']:,}" for h in st.session_state.incen_history])}</div>', unsafe_allow_html=True)

add_amt = st.number_input("인센 금액", min_value=0, step=1000, value=0, label_visibility="collapsed")
with st.container(key="incen_buttons"):
    col1, col2, col3 = st.columns(3)
    if col1.button("➕추가", use_container_width=True):
        st.session_state.incen_sum += add_amt
        st.session_state.incen_history.append({"val": add_amt, "time": get_now_kst().strftime("%H:%M")})
        st.rerun()
    if col2.button("↩️취소", use_container_width=True) and st.session_state.incen_history:
        st.session_state.incen_sum -= st.session_state.incen_history.pop()['val']; st.rerun()
    if col3.button("🧹리셋", use_container_width=True):
        st.session_state.incen_sum = 0; st.session_state.incen_history = []; st.rerun()

st.divider()
st.write("**📦 품목 수량**")
counts = []
for i in range(0, 6, 2):
    c1, c2 = st.columns(2)
    with c1: counts.append(st.number_input(cfg["item_names"][i], 0, value=int(existing_row.iloc[0][f'item{i+1}']) if is_edit else 0, key=f"it_{i}"))
    with c2: counts.append(st.number_input(cfg["item_names"][i+1], 0, value=int(existing_row.iloc[0][f'item{i+2}']) if is_edit else 0, key=f"it_{i+1}"))
counts.append(st.number_input(cfg["item_names"][6], 0, value=int(existing_row.iloc[0]['item7']) if is_edit else 0, key="it_6"))

if st.button("✅ 최종 데이터 저장", type="primary", use_container_width=True):
    item_total = sum([int(c) * int(p) for c, p in zip(counts, cfg["item_prices"])])
    row = {"직원명": user_name, "날짜": str_date, "인센티브": st.session_state.incen_sum, 
           "item1": counts[0], "item2": counts[1], "item3": counts[2], "item4": counts[3], 
           "item5": counts[4], "item6": counts[5], "item7": counts[6], 
           "합계": st.session_state.incen_sum + item_total, "비고": "정상", "입력시간": get_now_kst().strftime("%H:%M:%S")}
    if save_to_gsheet(user_name, row): st.success(f"{str_date} 데이터 저장 성공!"); st.rerun()

# --- 정산 리포트 ---
st.divider()
st.subheader("📊 정산 리포트")
s_day = cfg['start_day']
start_dt = date(sel_date.year, sel_date.month, s_day) if sel_date.day >= s_day else (date(sel_date.year, sel_date.month, s_day) - timedelta(days=30)).replace(day=s_day)
end_dt = (start_dt + timedelta(days=32)).replace(day=s_day) - timedelta(days=1)

if not df_all.empty:
    p_df = df_all[(pd.to_datetime(df_all['날짜']).dt.date >= start_dt) & (pd.to_datetime(df_all['날짜']).dt.date <= end_dt)].sort_values("날짜")
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
