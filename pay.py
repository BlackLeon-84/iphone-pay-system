import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials
import calendar

# 소프트웨어 버전
SW_VERSION = "v3.4.3"

# 페이지 설정
st.set_page_config(page_title=f"정산 {SW_VERSION}", layout="centered")

# --- [디자인 보존] CSS ---
st.markdown(f"""
    <style>
    .block-container {{
        padding-top: 3.5rem !important;
        max-width: 450px !important;
        padding-left: 10px !important;
        padding-right: 10px !important;
    }}
    .version-tag {{ font-size: 10px; color: #ccc; text-align: right; margin-bottom: -10px; }}
    .section-header {{
        font-size: 14px; font-weight: bold; color: #333; margin: 20px 0 10px 0;
        padding-left: 5px; border-left: 4px solid #007bff;
    }}
    .st-key-incen_buttons [data-testid="stHorizontalBlock"] {{
        display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important; gap: 4px !important; width: 100% !important;
    }}
    .st-key-incen_buttons [data-testid="stHorizontalBlock"] > div {{ flex: 1 1 0% !important; min-width: 0 !important; }}
    .st-key-incen_buttons button {{
        font-size: 10px !important; padding: 0px 1px !important; width: 100% !important; min-height: 40px !important; white-space: nowrap !important;
    }}
    .admin-log {{
        font-size: 11px; color: #155724; background-color: #d4edda; padding: 10px; border-radius: 5px; margin-top: 10px; border: 1px solid #c3e6cb;
    }}
    .st-key-login_btn button {{
        height: 50px !important; font-size: 18px !important; font-weight: bold !important; background-color: #007bff !important; color: white !important;
    }}
    .weekly-box {{ display: flex; justify-content: space-around; background: #f8f9fa; padding: 10px; border-radius: 10px; margin-bottom: 15px; }}
    .report-table {{ width: 100%; font-size: 10px; text-align: center; border-collapse: collapse; }}
    .report-table th, .report-table td {{ border: 1px solid #eee; padding: 5px 2px; }}
    .total-row {{ background-color: #f2f2f2 !important; font-weight: bold; }}
    .save-log {{ font-size: 12px; color: #1e88e5; font-weight: bold; margin-bottom: 5px; }}
    .update-log {{ font-size: 11px; color: #777; background: #f9f9f9; padding: 10px; border-radius: 8px; margin-top: 30px; border: 1px solid #eee; }}
    </style>
    """, unsafe_allow_html=True)

# --- 시트 및 설정 로직 ---
SHEET_NAME = "아이폰정산"
BASE_STAFF = ["태완", "남근", "성훈"]

@st.cache_resource
def get_gsheet_client():
    if "gcp_service_account" not in st.secrets:
        st.error("구글 서비스 계정 설정(Secrets)이 필요합니다.")
        st.stop()
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_info = dict(st.secrets["gcp_service_account"])
    if "private_key" in creds_info:
        creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    return gspread.authorize(creds)

@st.cache_resource
def get_spreadsheet():
    client = get_gsheet_client()
    return client.open(SHEET_NAME)

def get_config_worksheet():
    spreadsheet = get_spreadsheet()
    headers = ["직원명", "기본급", "정산일", "보험료"] + [f"item{i}_name" for i in range(1,8)] + [f"item{i}_price" for i in range(1,8)]
    try:
        ws = spreadsheet.worksheet("config")
        # 헤더가 어지러우면 자동 교정
        current_headers = ws.row_values(1)
        if not current_headers or current_headers[0] != "직원명":
            ws.update(range_name="A1:R1", values=[headers])
        return ws
    except:
        ws = spreadsheet.add_worksheet(title="config", rows="100", cols="20")
        ws.append_row(headers)
        return ws

def get_dynamic_staff_list():
    sheet = get_config_worksheet()
    names = sheet.col_values(1)[1:] # 첫 줄(헤더) 제외
    full_list = sorted(list(set(BASE_STAFF + [n for n in names if n])))
    return full_list

def load_staff_salary_config(name):
    sheet = get_config_worksheet()
    rows = sheet.get_all_values()
    
    default_names = ['일반필름', '풀필름', '젤리', '케이블', '어댑터', '추가1', '추가2']
    default_prices = [9000, 18000, 9000, 15000, 23000, 0, 0]
    res = {"base_salary": 3500000, "start_day": 13, "insurance": 104760, "item_names": default_names, "item_prices": default_prices}
    
    if len(rows) > 1:
        headers = rows[0]
        for row in rows[1:]:
            if row and row[0] == name:
                d = {headers[i]: row[i] for i in range(min(len(headers), len(row)))}
                res["base_salary"] = int(d.get("기본급", 3500000)) if d.get("기본급") else 3500000
                res["start_day"] = int(d.get("정산일", 13)) if d.get("정산일") else 13
                res["insurance"] = int(d.get("보험료", 104760)) if d.get("보험료") else 104760
                
                item_names, item_prices = [], []
                for i in range(1, 8):
                    n = d.get(f"item{i}_name", default_names[i-1])
                    p = d.get(f"item{i}_price", default_prices[i-1])
                    item_names.append(n if n else default_names[i-1])
                    item_prices.append(int(p) if p else default_prices[i-1])
                res["item_names"], res["item_prices"] = item_names, item_prices
                return res

    # 관리자 설정이 없으면 기본값으로 저장하고 시트도 생성
    save_staff_salary_config(name, res["base_salary"], res["start_day"], res["insurance"], res["item_names"], res["item_prices"])
    get_user_worksheet(name) # 데이터 시트 자동 생성
    return res

def save_staff_salary_config(name, base, day, ins, item_names, item_prices):
    sheet = get_config_worksheet()
    rows = sheet.get_all_values()
    row_idx = -1
    for i, row in enumerate(rows):
        if row and row[0] == name: row_idx = i + 1; break
    
    new_data = [name, int(base), int(day), int(ins)] + item_names + item_prices
    if row_idx != -1:
        col_end = chr(ord('A') + len(new_data) - 1)
        sheet.update(range_name=f"A{row_idx}:{col_end}{row_idx}", values=[new_data])
    else:
        sheet.append_row(new_data)

def get_user_worksheet(user_name):
    spreadsheet = get_spreadsheet()
    try: return spreadsheet.worksheet(user_name)
    except:
        ws = spreadsheet.add_worksheet(title=user_name, rows="1000", cols="20")
        ws.append_row(["직원명", "날짜", "인센티브", "item1", "item2", "item3", "item4", "item5", "item6", "item7", "합계", "비고", "입력시간"])
        return ws

def load_data_from_gsheet(user_name):
    try:
        sheet = get_user_worksheet(user_name)
        data = sheet.get_all_values()
        if len(data) <= 1: return pd.DataFrame()
        df = pd.DataFrame(data[1:], columns=data[0])
        cols = ["인센티브", "item1", "item2", "item3", "item4", "item5", "item6", "item7", "합계"]
        for col in cols:
            if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        return df
    except: return pd.DataFrame()

def save_to_gsheet(user_name, df_row):
    try:
        sheet = get_user_worksheet(user_name)
        all_data = sheet.get_all_values()
        row_idx = -1
        for i, row in enumerate(all_data):
            if len(row) > 1 and row[1] == df_row['날짜']: row_idx = i + 1; break
        row_values = list(df_row.values())
        if row_idx != -1:
            col_end = chr(ord('A') + len(row_values) - 1)
            sheet.update(range_name=f"A{row_idx}:{col_end}{row_idx}", values=[row_values])
        else:
            sheet.append_row(row_values)
        return True
    except: return False

def get_safe_date(year, month, day):
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(int(day), last_day))

def get_now_kst(): return datetime.now(timezone.utc) + timedelta(hours=9)

# --- 세션 및 데이터 로드 ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
STAFF_LIST = get_dynamic_staff_list()

# --- 로그인 ---
if not st.session_state.logged_in:
    st.title("🔐 로그인")
    user_id = st.selectbox("직원 선택", options=STAFF_LIST)
    admin_pw = st.text_input("비번", type="password") if user_id == "태완" else ""
    if st.button("입장", use_container_width=True, key="login_btn"):
        if user_id == "태완" and admin_pw != "102030": st.error("비번 오류")
        else:
            st.session_state.logged_in = True
            st.session_state.user_name = user_id
            st.session_state.salary_cfg = load_staff_salary_config(user_id)
            st.rerun()
    st.markdown(f'<div class="update-log"><b>🚀 소프트웨어 버전: {SW_VERSION}</b><br>• 직원별 시트 및 설정 자동 분리<br>• 신규 직원 로그인 시 시트 자동 생성<br>• 구글 시트 구조 실시간 최적화</div>', unsafe_allow_html=True)
    st.stop()

user_name = st.session_state.user_name
sal_cfg = st.session_state.salary_cfg

# --- 사이드바 ---
with st.sidebar:
    st.header("⚙️ 설정")
    if user_name == "태완":
        st.subheader("🛠️ 관리자 설정")
        target_staff = st.selectbox("수정 대상 직원", STAFF_LIST)
        t_sal = load_staff_salary_config(target_staff)

        new_names, new_prices = [], []
        for i in range(7):
            c1, c2 = st.columns(2)
            n = c1.text_input(f"명칭{i+1}", value=t_sal["item_names"][i], key=f"sn_{target_staff}_{i}")
            p = c2.number_input(f"가격{i+1}", value=t_sal["item_prices"][i], step=1000, key=f"sp_{target_staff}_{i}")
            new_names.append(n); new_prices.append(p)

        st.divider()
        base = st.number_input("기본급", value=t_sal["base_salary"])
        s_day = st.slider("정산 시작일", 1, 31, value=min(max(1, t_sal["start_day"]), 31))
        ins = st.number_input("보험료", value=t_sal["insurance"])

        if st.button(f"💿 {target_staff} 설정 즉시 저장", use_container_width=True):
            save_staff_salary_config(target_staff, base, s_day, ins, new_names, new_prices)
            get_user_worksheet(target_staff)
            if target_staff == user_name: st.session_state.salary_cfg = load_staff_salary_config(user_name)
            st.session_state.admin_log = f"✅ [{get_now_kst().strftime('%H:%M:%S')}] {target_staff} 정보 저장 완료"
            st.rerun()
        if "admin_log" in st.session_state:
            st.markdown(f'<div class="admin-log">{st.session_state.admin_log}</div>', unsafe_allow_html=True)
            
    if st.button("로그아웃"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# --- 메인 화면 ---
st.markdown(f'<div class="version-tag">{SW_VERSION}</div>', unsafe_allow_html=True)
df_all = load_data_from_gsheet(user_name)
st.write(f"### 💼 {user_name}님 실적")

sel_date = st.date_input("날짜", value=date.today(), label_visibility="collapsed")
str_date = sel_date.strftime("%Y-%m-%d")

existing_row = df_all[df_all["날짜"] == str_date] if not df_all.empty else pd.DataFrame()
if not existing_row.empty:
    st.markdown(f'<div class="save-log">📝 {existing_row.iloc[0].get("입력시간", "기록없음")} 저장됨</div>', unsafe_allow_html=True)

if st.button("🌴 오늘 휴무 등록", use_container_width=True):
    row = {"직원명": user_name, "날짜": str_date, "인센티브": 0, "item1":0, "item2":0, "item3":0, "item4":0, "item5":0, "item6":0, "item7":0, "합계": 0, "비고": "휴무", "입력시간": get_now_kst().strftime("%H:%M:%S")}
    if save_to_gsheet(user_name, row): st.rerun()

# --- 최근 7일 기록 ---
st.write("**📅 최근 7일 기록**")
weekly_box_html = '<div class="weekly-box">'
today_kst = get_now_kst().date()
for i in range(6, -1, -1):
    target_d = today_kst - timedelta(days=i)
    target_str = target_d.strftime("%Y-%m-%d")
    day_data = df_all[df_all["날짜"] == target_str] if not df_all.empty else pd.DataFrame()
    icon = "✅" if not day_data.empty and day_data.iloc[0]['비고'] != "휴무" else ("🌴" if not day_data.empty else "⚪")
    weekly_box_html += f'<div style="text-align:center;"><div style="font-size:10px;">{target_d.day}일</div><div>{icon}</div></div>'
st.markdown(weekly_box_html + '</div>', unsafe_allow_html=True)

st.divider()

# --- 인센티브 섹션 ---
st.markdown('<div class="section-header">💰 인센티브 입력</div>', unsafe_allow_html=True)
is_edit = not existing_row.empty
if "inc_sum" not in st.session_state or st.session_state.get("last_date") != str_date:
    st.session_state.inc_sum = int(existing_row.iloc[0]["인센티브"]) if is_edit else 0
    st.session_state.inc_history = [{"val": int(existing_row.iloc[0]["인센티브"])}] if is_edit and int(existing_row.iloc[0]["인센티브"]) > 0 else []
    st.session_state.last_date = str_date

st.write(f"현재 합계: **{st.session_state.inc_sum:,}원**")
add_amt = st.number_input("인센 금액", 0, step=1000, value=0, label_visibility="collapsed")
with st.container(key="incen_buttons"):
    c1, c2, c3 = st.columns(3)
    if c1.button("➕추가", use_container_width=True):
        st.session_state.inc_sum += add_amt
        st.session_state.inc_history.append({"val": add_amt}); st.rerun()
    if c2.button("↩️취소", use_container_width=True) and st.session_state.inc_history:
        st.session_state.inc_sum -= st.session_state.inc_history.pop()['val']; st.rerun()
    if c3.button("🧹리셋", use_container_width=True):
        st.session_state.inc_sum = 0; st.session_state.inc_history = []; st.rerun()

# --- 품목 섹션 ---
st.markdown('<div class="section-header">📦 품목 수량 입력</div>', unsafe_allow_html=True)
counts = []
item_names, item_prices = sal_cfg["item_names"], sal_cfg["item_prices"]
for i in range(0, 6, 2):
    c1, c2 = st.columns(2)
    with c1: counts.append(st.number_input(item_names[i], 0, value=int(existing_row.iloc[0][f'item{i+1}']) if is_edit else 0, key=f"it_{i}"))
    with c2: counts.append(st.number_input(item_names[i+1], 0, value=int(existing_row.iloc[0][f'item{i+2}']) if is_edit else 0, key=f"it_{i+1}"))
counts.append(st.number_input(item_names[6], 0, value=int(existing_row.iloc[0]['item7']) if is_edit else 0, key="it_6"))

if st.button("✅ 최종 데이터 저장", type="primary", use_container_width=True):
    sub_total = sum([int(c) * int(p) for c, p in zip(counts, item_prices)])
    row = {"직원명": user_name, "날짜": str_date, "인센티브": st.session_state.inc_sum, 
           "item1": counts[0], "item2": counts[1], "item3": counts[2], "item4": counts[3], 
           "item5": counts[4], "item6": counts[5], "item7": counts[6], 
           "합계": st.session_state.inc_sum + sub_total, "비고": "정상", "입력시간": get_now_kst().strftime("%H:%M:%S")}
    if save_to_gsheet(user_name, row): st.success("저장 완료!"); st.rerun()

# --- 정산 리포트 ---
st.divider()
st.subheader("📊 정산 리포트")
s_day, base, ins = sal_cfg['start_day'], sal_cfg['base_salary'], sal_cfg['insurance']
if sel_date.day >= s_day: start_dt = get_safe_date(sel_date.year, sel_date.month, s_day)
else:
    prev = sel_date.replace(day=1) - timedelta(days=1)
    start_dt = get_safe_date(prev.year, prev.month, s_day)
end_dt = (start_dt + timedelta(days=32)).replace(day=1)
end_dt = get_safe_date(end_dt.year, end_dt.month, s_day) - timedelta(days=1)

if not df_all.empty:
    df_all['date_dt'] = pd.to_datetime(df_all['날짜']).dt.date
    p_df = df_all[(df_all['date_dt'] >= start_dt) & (df_all['date_dt'] <= end_dt)].sort_values("날짜")
    if not p_df.empty:
        total_extra = p_df["합계"].sum()
        st.write(f"**🏦 예상 수령: {int(base + total_extra - ins):,}원**")
        st.markdown(f'<div style="font-size:11px; color:#888; margin-top:-5px;">({start_dt.strftime("%m/%d")}~{end_dt.strftime("%m/%d")} 정산 기준)</div>', unsafe_allow_html=True)
        headers = ["날", "인센"] + [n[:1] for n in item_names] + ["합계"]
        rows_html, item_sums = "", [0]*7
        for _, r in p_df.iterrows():
            d = datetime.strptime(r['날짜'], '%Y-%m-%d').day
            if r['비고'] == "휴무": rows_html += f"<tr><td>{d}</td><td colspan='9' style='color:orange;'>🌴휴무</td></tr>"
            else:
                item_tds = "".join([f"<td>{int(r[f'item{i}'])}</td>" for i in range(1, 8)])
                for i in range(1, 8): item_sums[i-1] += int(r[f'item{i}'])
                rows_html += f"<tr><td>{d}</td><td>{int(r['인센티브']):,}</td>{item_tds}<td style='color:blue;'>{int(r['합계']):,}</td></tr>"
        rows_html += f"<tr class='total-row'><td>합</td><td>{p_df['인센티브'].sum():,}</td>" + "".join([f"<td>{s}</td>" for s in item_sums]) + f"<td>{total_extra:,}</td></tr>"
        st.markdown(f'<table class="report-table"><tr>{"".join([f"<th>{h}</th>" for h in headers])}</tr>{rows_html}</table>', unsafe_allow_html=True)
