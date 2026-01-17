import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials
import calendar

# 소프트웨어 버전
SW_VERSION = "v3.4.5"

# 페이지 설정
st.set_page_config(page_title=f"정산 {SW_VERSION}", layout="centered")

# --- CSS ---
st.markdown(f"""
    <style>
    .block-container {{ padding-top: 3.5rem !important; max-width: 450px !important; padding-left: 10px !important; padding-right: 10px !important; }}
    .version-tag {{ font-size: 10px; color: #ccc; text-align: right; margin-bottom: -10px; }}
    .section-header {{ font-size: 14px; font-weight: bold; color: #333; margin: 20px 0 10px 0; padding-left: 5px; border-left: 4px solid #007bff; }}
    .st-key-incen_buttons [data-testid="stHorizontalBlock"] {{ display: flex !important; flex-wrap: nowrap !important; gap: 4px !important; width: 100% !important; }}
    .st-key-incen_buttons [data-testid="stHorizontalBlock"] > div {{ flex: 1 1 0% !important; min-width: 0 !important; }}
    .st-key-incen_buttons button {{ font-size: 10px !important; padding: 0px 1px !important; width: 100% !important; min-height: 40px !important; }}
    .admin-log {{ font-size: 11px; color: #155724; background-color: #d4edda; padding: 10px; border-radius: 5px; margin-top: 10px; border: 1px solid #c3e6cb; }}
    .st-key-login_btn button {{ height: 50px !important; font-size: 18px !important; font-weight: bold !important; background-color: #007bff !important; color: white !important; }}
    .weekly-box {{ display: flex; justify-content: space-around; background: #f8f9fa; padding: 10px; border-radius: 10px; margin-bottom: 15px; }}
    .report-table {{ width: 100%; font-size: 10px; text-align: center; border-collapse: collapse; }}
    .report-table th, .report-table td {{ border: 1px solid #eee; padding: 5px 2px; }}
    .total-row {{ background-color: #f2f2f2 !important; font-weight: bold; }}
    .save-log {{ font-size: 12px; color: #1e88e5; font-weight: bold; margin-bottom: 5px; }}
    .update-log {{ font-size: 11px; color: #777; background: #f9f9f9; padding: 10px; border-radius: 8px; margin-top: 30px; border: 1px solid #eee; }}
    </style>
    """, unsafe_allow_html=True)

# --- 구글 시트 로직 ---
SHEET_NAME = "아이폰정산"
BASE_STAFF = ["태완", "남근", "성훈"]

@st.cache_resource
def get_gsheet_client():
    if "gcp_service_account" not in st.secrets:
        st.error("구글 서비스 계정 설정이 없습니다.")
        st.stop()
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_info = dict(st.secrets["gcp_service_account"])
    if "private_key" in creds_info: creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    return gspread.authorize(creds)

@st.cache_resource
def get_spreadsheet():
    return get_gsheet_client().open(SHEET_NAME)

def get_config_worksheet():
    ss = get_spreadsheet()
    headers = ["직원명", "기본급", "정산일", "보험료"] + [f"item{i}_name" for i in range(1,8)] + [f"item{i}_price" for i in range(1,8)]
    ws_list = [sh.title for sh in ss.worksheets()]
    if "config" in ws_list:
        ws = ss.worksheet("config")
        curr = ws.row_values(1)
        if not curr or curr[0] != "직원명": ws.update(range_name="A1:R1", values=[headers])
    else:
        ws = ss.add_worksheet(title="config", rows="100", cols="20")
        ws.append_row(headers)
    return ws

def get_dynamic_staff_list():
    try:
        sheet = get_config_worksheet()
        names = sheet.col_values(1)[1:]
        return sorted(list(set(BASE_STAFF + [n for n in names if n])))
    except: return BASE_STAFF

def load_staff_salary_config(name):
    sheet = get_config_worksheet()
    rows = sheet.get_all_values()
    defaults = {"base_salary": 3500000, "start_day": 13, "insurance": 104760, 
                "item_names": ['일반필름', '풀필름', '젤리', '케이블', '어댑터', '추가1', '추가2'],
                "item_prices": [9000, 18000, 9000, 15000, 23000, 0, 0]}
    
    if len(rows) > 1:
        hd = rows[0]
        for r in rows[1:]:
            if r and r[0] == name:
                d = {hd[i]: r[i] for i in range(min(len(hd), len(r)))}
                res = {
                    "base_salary": int(d.get("기본급", 3500000)) if d.get("기본급") else 3500000,
                    "start_day": int(d.get("정산일", 13)) if d.get("정산일") else 13,
                    "insurance": int(d.get("보험료", 104760)) if d.get("보험료") else 104760,
                    "item_names": [d.get(f"item{i}_name", defaults["item_names"][i-1]) for i in range(1,8)],
                    "item_prices": [int(d.get(f"item{i}_price", defaults["item_prices"][i-1])) if d.get(f"item{i}_price") else defaults["item_prices"][i-1] for i in range(1,8)]
                }
                return res
    save_staff_salary_config(name, defaults["base_salary"], defaults["start_day"], defaults["insurance"], defaults["item_names"], defaults["item_prices"])
    return defaults

def save_staff_salary_config(name, base, day, ins, names, prices):
    sheet = get_config_worksheet()
    rows = sheet.get_all_values()
    idx = -1
    for i, r in enumerate(rows):
        if r and r[0] == name: idx = i + 1; break
    data = [name, int(base), int(day), int(ins)] + names + prices
    if idx != -1:
        col = chr(ord('A') + len(data) - 1)
        sheet.update(range_name=f"A{idx}:{col}{idx}", values=[data])
    else: sheet.append_row(data)

def get_user_worksheet(user_name):
    ss = get_spreadsheet()
    ws_list = [sh.title for sh in ss.worksheets()]
    if user_name in ws_list: return ss.worksheet(user_name)
    else:
        ws = ss.add_worksheet(title=user_name, rows="1000", cols="20")
        ws.append_row(["직원명", "날짜", "인센티브", "item1", "item2", "item3", "item4", "item5", "item6", "item7", "합계", "비고", "입력시간"])
        return ws

def load_data_from_gsheet(user_name):
    try:
        sheet = get_user_worksheet(user_name)
        data = sheet.get_all_values()
        if len(data) <= 1: return pd.DataFrame()
        df = pd.DataFrame(data[1:], columns=data[0])
        for c in ["인센티브", "item1", "item2", "item3", "item4", "item5", "item6", "item7", "합계"]:
            if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0).astype(int)
        return df
    except: return pd.DataFrame()

def save_to_gsheet(user_name, df_row):
    try:
        sheet = get_user_worksheet(user_name)
        rows = sheet.get_all_values()
        idx = -1
        for i, r in enumerate(rows):
            if len(r) > 1 and r[1] == df_row['날짜']: idx = i + 1; break
        vals = list(df_row.values())
        if idx != -1:
            col = chr(ord('A') + len(vals) - 1)
            sheet.update(range_name=f"A{idx}:{col}{idx}", values=[vals])
        else: sheet.append_row(vals)
        return True
    except: return False

def get_safe_date(y, m, d):
    ld = calendar.monthrange(y, m)[1]
    return date(y, m, min(int(d), ld))

def get_now_kst(): return datetime.now(timezone.utc) + timedelta(hours=9)

# --- 메인 실행 ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
STAFF_LIST = get_dynamic_staff_list()

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
    st.markdown(f'<div class="update-log"><b>🚀 {SW_VERSION} 업데이트</b><br>• 변수명 불일치 수정 (NameError 해결)<br>• 구글 시트 중복 생성 방지<br>• 직원별 개별 설정 기능</div>', unsafe_allow_html=True)
    st.stop()

user_name, sal_cfg = st.session_state.user_name, st.session_state.salary_cfg

with st.sidebar:
    st.header("⚙️ 설정")
    if user_name == "태완":
        st.subheader("🛠️ 관리자 설정")
        target = st.selectbox("수정 대상 직원", STAFF_LIST)
        t_sal = load_staff_salary_config(target)
        new_n, new_p = [], []
        for i in range(7):
            c1, c2 = st.columns(2)
            n = c1.text_input(f"명칭{i+1}", value=t_sal["item_names"][i], key=f"sn_{target}_{i}")
            p = c2.number_input(f"가격{i+1}", value=t_sal["item_prices"][i], step=1000, key=f"sp_{target}_{i}")
            new_n.append(n); new_p.append(p)
        st.divider()
        base = st.number_input("기본급", value=t_sal["base_salary"])
        s_day = st.slider("정산 시작일", 1, 31, value=min(max(1, t_sal["start_day"]), 31))
        ins = st.number_input("보험료", value=t_sal["insurance"])
        if st.button(f"💿 {target} 설정 저장", use_container_width=True):
            save_staff_salary_config(target, base, s_day, ins, new_n, new_p)
            if target == user_name: st.session_state.salary_cfg = load_staff_salary_config(user_name)
            st.session_state.admin_log = f"✅ {target} 저장 완료 ({get_now_kst().strftime('%H:%M:%S')})"
            st.rerun()
        if "admin_log" in st.session_state: st.markdown(f'<div class="admin-log">{st.session_state.admin_log}</div>', unsafe_allow_html=True)
    if st.button("로그아웃"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

st.markdown(f'<div class="version-tag">{SW_VERSION}</div>', unsafe_allow_html=True)
df_all = load_data_from_gsheet(user_name)
st.write(f"### 💼 {user_name}님 실적")
sel_date = st.date_input("날짜", value=date.today(), label_visibility="collapsed")
str_date = sel_date.strftime("%Y-%m-%d")

existing = df_all[df_all["날짜"] == str_date] if not df_all.empty else pd.DataFrame()
if not existing.empty: st.markdown(f'<div class="save-log">📝 {existing.iloc[0].get("입력시간", "기록없음")} 저장됨</div>', unsafe_allow_html=True)

if st.button("🌴 오늘 휴무 등록", use_container_width=True):
    row = {"직원명": user_name, "날짜": str_date, "인센티브": 0, "item1":0, "item2":0, "item3":0, "item4":0, "item5":0, "item6":0, "item7":0, "합계": 0, "비고": "휴무", "입력시간": get_now_kst().strftime("%H:%M:%S")}
    if save_to_gsheet(user_name, row): st.rerun()

st.write("**📅 최근 7일 기록**")
w_html = '<div class="weekly-box">'
today = get_now_kst().date()
for i in range(6, -1, -1):
    td = today - timedelta(days=i)
    ts = td.strftime("%Y-%m-%d")
    dd = df_all[df_all["날짜"] == ts] if not df_all.empty else pd.DataFrame()
    icon = "✅" if not dd.empty and dd.iloc[0]['비고'] != "휴무" else ("🌴" if not dd.empty else "⚪")
    w_html += f'<div style="text-align:center;"><div style="font-size:10px;">{td.day}일</div><div>{icon}</div></div>'
st.markdown(w_html + '</div>', unsafe_allow_html=True)

st.divider()
st.markdown('<div class="section-header">💰 인센티브 입력</div>', unsafe_allow_html=True)
is_edit = not existing.empty
if "inc_sum" not in st.session_state or st.session_state.get("last_date") != str_date:
    st.session_state.inc_sum = int(existing.iloc[0]["인센티브"]) if is_edit else 0
    st.session_state.inc_his = [{"val": int(existing.iloc[0]["인센티브"])}] if is_edit and int(existing.iloc[0]["인센티브"]) > 0 else []
    st.session_state.last_date = str_date

st.write(f"현재 합계: **{st.session_state.inc_sum:,}원**")
add_amt = st.number_input("인센 금액", 0, step=1000, value=0, label_visibility="collapsed")
with st.container(key="incen_buttons"):
    c1, c2, c3 = st.columns(3)
    if c1.button("➕추가"):
        st.session_state.inc_sum += add_amt
        st.session_state.inc_his.append({"val": add_amt}); st.rerun()
    if c2.button("↩️취소") and st.session_state.inc_his:
        st.session_state.inc_sum -= st.session_state.inc_his.pop()['val']; st.rerun()
    if c3.button("🧹리셋"):
        st.session_state.inc_sum = 0; st.session_state.inc_his = []; st.rerun()

st.markdown('<div class="section-header">📦 품목 수량 입력</div>', unsafe_allow_html=True)
cts = []
it_n, it_p = sal_cfg["item_names"], sal_cfg["item_prices"]
for i in range(0, 6, 2):
    c1, c2 = st.columns(2)
    with c1: cts.append(st.number_input(it_n[i], 0, value=int(existing.iloc[0][f'item{i+1}']) if is_edit else 0, key=f"it_{i}"))
    with c2: cts.append(st.number_input(it_n[i+1], 0, value=int(existing.iloc[0][f'item{i+2}']) if is_edit else 0, key=f"it_{i+1}"))
cts.append(st.number_input(it_n[6], 0, value=int(existing.iloc[0]['item7']) if is_edit else 0, key="it_6"))

if st.button("✅ 최종 데이터 저장", type="primary", use_container_width=True):
    total_val = sum([int(c) * int(p) for c, p in zip(cts, it_p)])
    row = {"직원명": user_name, "날짜": str_date, "인센티브": st.session_state.inc_sum, "item1": cts[0], "item2": cts[1], "item3": cts[2], "item4": cts[3], "item5": cts[4], "item6": cts[5], "item7": cts[6], "합계": st.session_state.inc_sum + total_val, "비고": "정상", "입력시간": get_now_kst().strftime("%H:%M:%S")}
    if save_to_gsheet(user_name, row): st.success("저장 완료!"); st.rerun()

st.divider()
st.subheader("📊 정산 리포트")
s_d, b, ins = sal_cfg['start_day'], sal_cfg['base_salary'], sal_cfg['insurance']
if sel_date.day >= s_d: s_dt = get_safe_date(sel_date.year, sel_date.month, s_d)
else:
    prv = sel_date.replace(day=1) - timedelta(days=1)
    s_dt = get_safe_date(prv.year, prv.month, s_d)
e_dt = (s_dt + timedelta(days=32)).replace(day=1)
e_dt = get_safe_date(e_dt.year, e_dt.month, s_d) - timedelta(days=1)

if not df_all.empty:
    df_all['date_dt'] = pd.to_datetime(df_all['날짜']).dt.date
    p_df = df_all[(df_all['date_dt'] >= s_dt) & (df_all['date_dt'] <= e_dt)].sort_values("날짜")
    if not p_df.empty:
        t_ex = p_df["합계"].sum()
        st.write(f"**🏦 예상 수령: {int(b + t_ex - ins):,}원**")
        st.markdown(f'<div style="font-size:11px; color:#888; margin-top:-5px;">({s_dt.strftime("%m/%d")}~{e_dt.strftime("%m/%d")} 정산 기준)</div>', unsafe_allow_html=True)
        hds = ["날", "인센"] + [n[:1] for n in it_n] + ["합계"]
        r_html, i_sums = "", [0]*7
        for _, r in p_df.iterrows():
            d = datetime.strptime(r['날짜'], '%Y-%m-%d').day
            if r['비고'] == "휴무": r_html += f"<tr><td>{d}</td><td colspan='9' style='color:orange;'>🌴휴무</td></tr>"
            else:
                it_tds = "".join([f"<td>{int(r[f'item{i}'])}</td>" for i in range(1, 8)])
                for i in range(1, 8): i_sums[i-1] += int(r[f'item{i}'])
                r_html += f"<tr><td>{d}</td><td>{int(r['인센티브']):,}</td>{it_tds}<td style='color:blue;'>{int(r['합계']):,}</td></tr>"
        r_html += f"<tr class='total-row'><td>합</td><td>{p_df['인센티브'].sum():,}</td>" + "".join([f"<td>{s}</td>" for s in i_sums]) + f"<td>{t_ex:,}</td></tr>"
        st.markdown(f'<table class="report-table"><tr>{"".join([f"<th>{x}</th>" for x in hds])}</tr>{r_html}</table>', unsafe_allow_html=True)