import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials
import calendar
import time

# 소프트웨어 버전
SW_VERSION = "v3.7.0"

# 페이지 설정
st.set_page_config(page_title=f"정산 {SW_VERSION}", layout="centered")

# --- [디자인 보존 및 강화] CSS ---
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
    .st-key-incen_buttons [data-testid="stHorizontalBlock"] > div {{
        flex: 1 1 0% !important; min-width: 0 !important;
    }}
    .st-key-incen_buttons button {{
        font-size: 10px !important; padding: 0px 1px !important; width: 100% !important; min-height: 40px !important; white-space: nowrap !important;
    }}

    .admin-log {{
        font-size: 11px; color: #155724; background-color: #d4edda; padding: 10px; border-radius: 5px; margin-top: 10px; border: 1px solid #c3e6cb;
    }}
    .st-key-login_btn button {{
        height: 50px !important; font-size: 18px !important; font-weight: bold !important; background-color: #007bff !important; color: white !important;
    }}

    .status-card {{
        padding: 12px; border-radius: 12px; margin-bottom: 15px; text-align: center; font-weight: bold; font-size: 14px;
    }}
    .status-saved {{ background-color: #e3f2fd; color: #1e88e5; border: 1px solid #bbdefb; }}
    .status-missing {{ background-color: #fff3e0; color: #ef6c00; border: 1px solid #ffe0b2; }}

    .weekly-box {{ display: flex; justify-content: space-around; background: #f8f9fa; padding: 10px; border-radius: 10px; margin-bottom: 15px; }}
    
    /* 리포트 표 최적화 (v3.7.0 초소형 아이폰용 9px) */
    .report-table {{ width: 100%; font-size: 9px; text-align: center; border-collapse: collapse; }}
    .report-table th, .report-table td {{ border: 1px solid #eee; padding: 4px 0.5px; word-break: keep-all; }}
    .total-row {{ background-color: #f2f2f2 !important; font-weight: bold; }}
    .update-log {{ font-size: 11px; color: #777; background: #f9f9f9; padding: 10px; border-radius: 8px; margin-top: 30px; border: 1px solid #eee; }}
    
    .inc-history-box {{
        background: #fdfdfd; border: 1px solid #f0f0f0; border-radius: 8px; padding: 8px; margin-top: 5px; font-size: 11px; color: #666;
    }}
    .inc-item {{ display: inline-block; background: #eee; padding: 2px 6px; border-radius: 4px; margin: 2px; }}
    
    .calc-detail {{ 
        font-size: 13px; color: #333; margin: 10px 0; background: #f0f7ff; 
        padding: 15px; border-radius: 10px; border: 1px solid #c2e0ff;
        line-height: 1.8;
    }}
    .calc-line {{ display: flex; justify-content: space-between; margin-bottom: 5px; }}
    .calc-total {{ font-size: 18px; font-weight: bold; color: #007bff; border-top: 1px dashed #abc; padding-top: 10px; margin-top: 10px; }}
    
    [data-testid="stSidebar"] .st-at {{ font-size: 12px; }}
    [data-testid="stSidebar"] .stSubheader {{ font-size: 14px; font-weight: bold; color: #007bff; margin-top: 15px; }}

    .info-box {{
        background: #fafafa; border: 1px solid #eee; padding: 10px; border-radius: 8px; font-size: 12px; line-height: 1.6;
    }}
    .info-label {{ color: #777; font-weight: bold; width: 70px; display: inline-block; }}
    .info-val {{ color: #333; font-weight: bold; }}
    </style>
    """, unsafe_allow_html=True)

# --- 구글 시트 로직 ---
SHEET_NAME = "아이폰정산"
ORDERED_STAFF = ["태완", "남근", "성훈"]

def safe_int(val, default=0):
    try:
        if val is None: return default
        return int(str(val).replace(",", "").strip())
    except: return default

def format_curr(val):
    return f"{safe_int(val):,}"

@st.cache_resource
def get_gsheet_client():
    if "gcp_service_account" not in st.secrets:
        st.error("Secrets 설정에 gcp_service_account 정보가 없습니다.")
        st.stop()
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_info = dict(st.secrets["gcp_service_account"])
    if "private_key" in creds_info: creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    return gspread.authorize(creds)

@st.cache_resource
def get_spreadsheet():
    for _ in range(3):
        try:
            return get_gsheet_client().open(SHEET_NAME)
        except:
            time.sleep(1)
    st.error("구글 시트 연결 실패")
    st.stop()

def get_config_worksheet():
    ss = get_spreadsheet()
    try:
        ws = ss.worksheet("config")
        # [v3.7.0] 시간수당 컬럼 확인 (A~S까지 19개 컬럼)
        header = ws.row_values(1)
        if len(header) < 19:
             ws.update(range_name="S1", values=[["시간수당(10분)"]])
        return ws
    except:
        headers = ["직원명", "기본급", "정산일", "보험료"] + [f"item{i}_name" for i in range(1,8)] + [f"item{i}_price" for i in range(1,8)] + ["시간수당(10분)"]
        ws = ss.add_worksheet(title="config", rows="100", cols="20")
        ws.append_row(headers)
        return ws

@st.cache_data(ttl=600)
def get_dynamic_staff_list():
    try:
        sheet = get_config_worksheet()
        names = sheet.col_values(1)[1:]
        res = []
        for s in ORDERED_STAFF:
            if s in names or s in ORDERED_STAFF: res.append(s)
        for n in names:
            if n and n not in res: res.append(n)
        return res
    except:
        return ORDERED_STAFF

@st.cache_data(ttl=300)
def load_staff_salary_config(name):
    try:
        sheet = get_config_worksheet()
        rows = sheet.get_all_values()
    except: 
        return {"base_salary": 3500000, "start_day": 13, "insurance": 104760, 
                "item_names": ['일반필름', '풀필름', '젤리', '케이블', '어댑터', '추가1', '추가2'],
                "item_prices": [9000, 18000, 9000, 15000, 23000, 0, 0],
                "overtime_rate": 0}

    # 기본 수당 설정 (태완: 4000, 남근: 3000)
    ov_defaults = {"태완": 4000, "남근": 3000}
    defaults = {"base_salary": 3500000, "start_day": 13, "insurance": 104760, 
                "item_names": ['일반필름', '풀필름', '젤리', '케이블', '어댑터', '추가1', '추가2'],
                "item_prices": [9000, 18000, 9000, 15000, 23000, 0, 0],
                "overtime_rate": ov_defaults.get(name, 0)}
    
    if len(rows) > 1:
        hd = rows[0]
        for r in rows[1:]:
            if r and r[0] == name:
                d = {hd[i]: r[i] for i in range(min(len(hd), len(r)))}
                return {
                    "base_salary": safe_int(d.get("기본급"), 3500000),
                    "start_day": safe_int(d.get("정산일"), 13),
                    "insurance": safe_int(d.get("보험료"), 104760),
                    "item_names": [d.get(f"item{i}_name", defaults["item_names"][i-1]) or defaults["item_names"][i-1] for i in range(1,8)],
                    "item_prices": [safe_int(d.get(f"item{i}_price"), defaults["item_prices"][i-1]) for i in range(1,8)],
                    "overtime_rate": safe_int(d.get("시간수당(10분)"), defaults["overtime_rate"])
                }
    save_staff_salary_config(name, defaults["base_salary"], defaults["start_day"], defaults["insurance"], defaults["item_names"], defaults["item_prices"], defaults["overtime_rate"])
    return defaults

def save_staff_salary_config(name, base, day, ins, names, prices, ov_rate=0):
    sheet = get_config_worksheet()
    rows = sheet.get_all_values()
    idx = -1
    for i, r in enumerate(rows):
        if r and r[0] == name: idx = i + 1; break
    data = [name, format_curr(base), safe_int(day), format_curr(ins)] + names + [format_curr(p) for p in prices] + [format_curr(ov_rate)]
    if idx != -1:
        col = chr(ord('A') + len(data) - 1)
        sheet.update(range_name=f"A{idx}:{col}{idx}", values=[data])
    else: sheet.append_row(data)
    st.cache_data.clear()

def get_user_worksheet(user_name):
    ss = get_spreadsheet()
    try:
        ws = ss.worksheet(user_name)
        header = ws.row_values(1)
        # [v3.7.0] 시간수당, 퇴근시간 컬럼 추가 확인
        if "시간수당" not in header:
            ws.update(range_name="N1:O1", values=[["시간수당", "퇴근시간"]])
        return ws
    except:
        ws = ss.add_worksheet(title=user_name, rows="1000", cols="20")
        ws.append_row(["직원명", "날짜", "인센티브", "시간수당", "퇴근시간", "item1", "item2", "item3", "item4", "item5", "item6", "item7", "합계", "비고", "입력시간"])
        return ws

def load_data_from_gsheet(user_name):
    try:
        sheet = get_user_worksheet(user_name)
        data = sheet.get_all_values()
        if len(data) <= 1: return pd.DataFrame()
        df = pd.DataFrame(data[1:], columns=data[0])
        cols = ["인센티브", "시간수당", "item1", "item2", "item3", "item4", "item5", "item6", "item7", "합계"]
        for c in cols:
            if c in df.columns: 
                df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ""), errors='coerce').fillna(0).astype(int)
        return df
    except: return pd.DataFrame()

def save_to_gsheet(user_name, df_row):
    try:
        sheet = get_user_worksheet(user_name)
        rows = sheet.get_all_values()
        idx = -1
        for i, r in enumerate(rows):
            if len(r) > 1 and r[1] == df_row['날짜']: idx = i + 1; break
        
        # 순서 맞춤 (헤더 기준) 
        # ["직원명", "날짜", "인센티브", "시간수당", "퇴근시간", "item1"..."item7", "합계", "비고", "입력시간"]
        header = ["직원명", "날짜", "인센티브", "시간수당", "퇴근시간", "item1", "item2", "item3", "item4", "item5", "item6", "item7", "합계", "비고", "입력시간"]
        vals = []
        for h in header:
            v = df_row.get(h, "")
            if h in ["인센티브", "시간수당", "합계"] or "item" in h:
                vals.append(format_curr(v))
            else:
                vals.append(v)
        
        if idx != -1:
            col = "O" # 15번째 컬럼까지
            sheet.update(range_name=f"A{idx}:{col}{idx}", values=[vals])
        else: sheet.append_row(vals)
        return True
    except: return False

def get_safe_date(y, m, d):
    ld = calendar.monthrange(y, m)[1]
    return date(y, m, min(safe_int(d, 1), ld))

def get_now_kst(): return datetime.now(timezone.utc) + timedelta(hours=9)

# --- 메인 코드 ---
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
    st.markdown(f'<div class="update-log"><b>🚀 {SW_VERSION} 수당 시스템</b><br>• 퇴근 시간에 따른 수당 자동 계산 추가<br>• 20시 이후 근무 수당 자동 정산<br>• 아이폰 최적화 전용 레이아웃 적용</div>', unsafe_allow_html=True)
    st.stop()

user_name, sal_cfg = st.session_state.user_name, st.session_state.salary_cfg

# --- 사이드바 ---
with st.sidebar:
    st.header("⚙️ 설정")
    
    if user_name != "태완":
        st.subheader("👤 내 정보 (보기 전용)")
        info_html = f"""
        <div class="info-box">
            <span class="info-label">기본급:</span> <span class="info-val">{sal_cfg['base_salary']:,}원</span><br>
            <span class="info-label">시간수당:</span> <span class="info-val">10분당 {sal_cfg['overtime_rate']:,}원</span><br>
            <span class="info-label">보험료:</span> <span class="info-val">{sal_cfg['insurance']:,}원</span><br>
            <span class="info-label">정산일:</span> <span class="info-val">매달 {sal_cfg['start_day']}일</span><hr style='margin:5px 0;'>
            <b>[품목 단가]</b><br>
        """
        for n, p in zip(sal_cfg["item_names"], sal_cfg["item_prices"]):
            info_html += f"<span class='info-label'>{n[:4]}:</span> <span class='info-val'>{p:,}원</span><br>"
        st.markdown(info_html + "</div>", unsafe_allow_html=True)

    if user_name == "태완":
        st.subheader("🛠️ 관리자 설정")
        target = st.selectbox("수정 대상 직원", STAFF_LIST)
        t_sal = load_staff_salary_config(target)
        
        st.subheader("📦 품목 명칭 및 단가")
        new_n, new_p = [], []
        for i in range(7):
            c1, c2 = st.columns([1.2, 1])
            n = c1.text_input(f"명칭{i+1}", value=t_sal["item_names"][i], key=f"sn_{target}_{i}")
            p_val = t_sal["item_prices"][i]
            p = c2.number_input(f"단가{i+1}", value=p_val, step=1000, key=f"sp_{target}_{i}")
            new_n.append(n); new_p.append(p)
        
        st.divider()
        st.subheader("💰 급여 및 수당 설정")
        base = st.number_input(f"기본급 수정", value=safe_int(t_sal["base_salary"]), step=10000)
        ov_rate = st.number_input(f"시간수당(10분당)", value=safe_int(t_sal["overtime_rate"]), step=100)
        ins = st.number_input(f"보험료 수정", value=safe_int(t_sal["insurance"]), step=1000)
        
        st.divider()
        st.subheader("📅 정산 시작일")
        s_day = st.slider(f"시작일 설정", 1, 31, value=min(max(1, t_sal["start_day"]), 31))
        
        st.divider()
        if st.button(f"💿 {target} 설정 저장", use_container_width=True):
            save_staff_salary_config(target, base, s_day, ins, new_n, new_p, ov_rate)
            if target == user_name: st.session_state.salary_cfg = load_staff_salary_config(user_name)
            st.session_state.admin_log = f"✅ {target} 저장 완료 ({get_now_kst().strftime('%H:%M:%S')})"
            st.rerun()
        if "admin_log" in st.session_state: st.markdown(f'<div class="admin-log">{st.session_state.admin_log}</div>', unsafe_allow_html=True)
    
    st.divider()
    if st.button("로그아웃", use_container_width=True):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()

# --- 메인 화면 ---
st.markdown(f'<div class="version-tag">{SW_VERSION}</div>', unsafe_allow_html=True)
df_all = load_data_from_gsheet(user_name)
st.write(f"### 💼 {user_name}님 실적")
sel_date = st.date_input("날짜", value=date.today(), label_visibility="collapsed")
str_date = sel_date.strftime("%Y-%m-%d")

existing = df_all[df_all["날짜"] == str_date] if not df_all.empty else pd.DataFrame()
if not existing.empty:
    save_time = existing.iloc[0].get("입력시간", "기록없음")
    st.markdown(f'<div class="status-card status-saved">✅ {str_date} 데이터가 저장되어 있습니다 ({save_time})</div>', unsafe_allow_html=True)
else:
    st.markdown(f'<div class="status-card status-missing">⚠️ {str_date} 데이터가 아직 등록되지 않았습니다</div>', unsafe_allow_html=True)

if st.button("🌴 오늘 휴무 등록", use_container_width=True):
    row = {"직원명": user_name, "날짜": str_date, "인센티브": 0, "시간수당": 0, "퇴근시간": "휴무", "item1":0, "item2":0, "item3":0, "item4":0, "item5":0, "item6":0, "item7":0, "합계": 0, "비고": "휴무", "입력시간": get_now_kst().strftime("%H:%M:%S")}
    if save_to_gsheet(user_name, row): st.rerun()

st.write("**📅 최근 7일 기록**")
w_box = '<div class="weekly-box">'
today_k = get_now_kst().date()
for i in range(6, -1, -1):
    td = today_k - timedelta(days=i)
    ts = td.strftime("%Y-%m-%d")
    dd = df_all[df_all["날짜"] == ts] if not df_all.empty else pd.DataFrame()
    icon = "✅" if not dd.empty and dd.iloc[0]['비고'] != "휴무" else ("🌴" if not dd.empty else "⚪")
    w_box += f'<div style="text-align:center;"><div style="font-size:10px;">{td.day}일</div><div>{icon}</div></div>'
st.markdown(w_box + '</div>', unsafe_allow_html=True)

st.divider()

# --- 수당 섹션 ---
st.markdown('<div class="section-header">💰 수당 및 퇴근시간 입력</div>', unsafe_allow_html=True)
is_edit = not existing.empty

# 인센티브 초기화
if "inc_sum" not in st.session_state or st.session_state.get("last_date") != str_date:
    st.session_state.inc_sum = safe_int(existing.iloc[0]["인센티브"]) if is_edit else 0
    st.session_state.inc_his = [{"val": safe_int(existing.iloc[0]["인센티브"])}] if is_edit and safe_int(existing.iloc[0]["인센티브"]) > 0 else []
    st.session_state.last_date = str_date

# 퇴근 시간 리스트 (20:00 ~ 24:00, 10분 단위)
etime_list = ["20:00"]
for h in range(20, 24):
    for m in range(0, 60, 10):
        t_str = f"{h}:{m:02d}"
        if t_str not in etime_list: etime_list.append(t_str)
etime_list.append("24:00")

# 기존 퇴근시간 로드
e_idx = etime_list.index(existing.iloc[0]["퇴근시간"]) if is_edit and existing.iloc[0]["퇴근시간"] in etime_list else 0
sel_etime = st.selectbox("퇴근 시간 (20:00 이후부터 수당 발생)", options=etime_list, index=e_idx)

# 시간수당 계산
h, m = map(int, sel_etime.split(":")) if sel_etime != "24:00" else (24, 0)
ov_min = max(0, (h * 60 + m) - 1200) # 20:00 = 1200분
ov_pay = (ov_min // 10) * sal_cfg["overtime_rate"]

c1, c2 = st.columns(2)
c1.metric("인센티브 합계", f"{st.session_state.inc_sum:,}원")
c2.metric("시간수당", f"{ov_pay:,}원", f"{ov_min}분 초과")

if st.session_state.inc_his:
    h_html = '<div class="inc-history-box">'
    for i, item in enumerate(st.session_state.inc_his):
        h_html += f'<span class="inc-item">#{i+1}: {item["val"]:,}원</span>'
    st.markdown(h_html + '</div>', unsafe_allow_html=True)

add_amt = st.number_input("인센 추가 금액", 0, step=1000, value=0)
with st.container(key="incen_buttons"):
    b1, b2, b3 = st.columns(3)
    if b1.button("➕추가", use_container_width=True):
        st.session_state.inc_sum += add_amt
        st.session_state.inc_his.append({"val": add_amt}); st.rerun()
    if b2.button("↩️취소", use_container_width=True) and st.session_state.inc_his:
        removed = st.session_state.inc_his.pop()
        st.session_state.inc_sum -= removed['val']
        st.rerun()
    if b3.button("🧹리셋", use_container_width=True):
        st.session_state.inc_sum = 0
        st.session_state.inc_his = []
        st.rerun()

st.markdown('<div class="section-header">📦 품목 수량 입력</div>', unsafe_allow_html=True)
cts = []
it_n, it_p = sal_cfg["item_names"], sal_cfg["item_prices"]
for i in range(0, 6, 2):
    c1, c2 = st.columns(2)
    with c1: cts.append(st.number_input(it_n[i], 0, value=safe_int(existing.iloc[0][f'item{i+1}']) if is_edit and f'item{i+1}' in existing.columns else 0, key=f"it_{i}"))
    with c2: cts.append(st.number_input(it_n[i+1], 0, value=safe_int(existing.iloc[0][f'item{i+2}']) if is_edit and f'item{i+2}' in existing.columns else 0, key=f"it_{i+1}"))
cts.append(st.number_input(it_n[6], 0, value=safe_int(existing.iloc[0]['item7']) if is_edit and 'item7' in existing.columns else 0, key="it_6"))

if st.button("✅ 최종 데이터 저장", type="primary", use_container_width=True):
    item_val = sum([safe_int(c) * safe_int(p) for c, p in zip(cts, it_p)])
    tot_val = st.session_state.inc_sum + ov_pay + item_val
    row = {
        "직원명": user_name, "날짜": str_date, "인센티브": st.session_state.inc_sum, 
        "시간수당": ov_pay, "퇴근시간": sel_etime,
        "item1": cts[0], "item2": cts[1], "item3": cts[2], "item4": cts[3], "item5": cts[4], "item6": cts[5], "item7": cts[6], 
        "합계": tot_val, "비고": "정상", "입력시간": get_now_kst().strftime("%H:%M:%S")
    }
    if save_to_gsheet(user_name, row): st.success("저장 완료!"); st.rerun()

# --- 정산 리포트 ---
st.divider()
s_d, b, ins = safe_int(sal_cfg['start_day'], 13), safe_int(sal_cfg['base_salary']), safe_int(sal_cfg['insurance'])
if sel_date.day >= s_d: s_dt = get_safe_date(sel_date.year, sel_date.month, s_d)
else:
    prv = sel_date.replace(day=1) - timedelta(days=1)
    s_dt = get_safe_date(prv.year, prv.month, s_d)
e_dt = (s_dt + timedelta(days=32)).replace(day=1)
e_dt = get_safe_date(e_dt.year, e_dt.month, s_d) - timedelta(days=1)

st.subheader(f"📊 정산 리포트 ({s_dt.strftime('%m/%d')} ~ {e_dt.strftime('%m/%d')})")

if not df_all.empty:
    df_all['date_dt'] = pd.to_datetime(df_all['날짜']).dt.date
    p_df = df_all[(df_all['date_dt'] >= s_dt) & (df_all['date_dt'] <= e_dt)].sort_values("날짜")
    if not p_df.empty:
        t_inc = safe_int(p_df["인센티브"].sum())
        t_ov = safe_int(p_df["시간수당"].sum()) if "시간수당" in p_df.columns else 0
        t_items = safe_int(p_df["합계"].sum()) - t_inc - t_ov
        final_pay = int(b + t_inc + t_ov + t_items - ins)
        
        st.markdown(f"""
        <div class="calc-detail">
            <div class="calc-line"><span>기본급</span> <span>+ {b:,}원</span></div>
            <div class="calc-line"><span>인센티브</span> <span>+ {t_inc + t_items:,}원</span></div>
            <div class="calc-line"><span>시간수당</span> <span>+ {t_ov:,}원</span></div>
            <div class="calc-line"><span>보험료</span> <span>- {ins:,}원</span></div>
            <div class="calc-total">
                <div class="calc-line"><span>💰 총급여</span> <span>{final_pay:,}원</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 리포트 표 (시간수당 포함)
        hds = ["날짜", "인센", "시간"] + [n[:1] for n in it_n] + ["합계"]
        r_html, i_sums = "", [0]*7
        for _, r in p_df.iterrows():
            md = datetime.strptime(r['날짜'], '%Y-%m-%d').strftime('%m/%d')
            if r['비고'] == "휴무": r_html += f"<tr><td style='font-weight:bold;'>{md}</td><td colspan='10' style='color:orange;'>🌴휴무</td></tr>"
            else:
                inc_val = safe_int(r['인센티브'])
                ov_val = safe_int(r.get('시간수당', 0))
                it_tds = "".join([f"<td>{safe_int(r[f'item{i}'])}</td>" for i in range(1, 8)])
                for i in range(1, 8): i_sums[i-1] += safe_int(r[f'item{i}'])
                r_html += f"<tr><td style='font-weight:bold;'>{md}</td><td>{inc_val:,}</td><td>{ov_val:,}</td>{it_tds}<td style='color:blue;'>{safe_int(r['합계']):,}</td></tr>"
        
        r_html += f"<tr class='total-row'><td>합계</td><td>{t_inc:,}</td><td>{t_ov:,}</td>" + "".join([f"<td>{s}</td>" for s in i_sums]) + f"<td>{safe_int(p_df['합계'].sum()):,}</td></tr>"
        st.markdown(f'<table class="report-table"><tr>{"".join([f"<th>{x}</th>" for x in hds])}</tr>{r_html}</table>', unsafe_allow_html=True)
