import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials
import calendar
import time

# 소프트웨어 버전
SW_VERSION = "v4.0.1"

# 페이지 설정
st.set_page_config(page_title=f"정산 {SW_VERSION}", layout="centered")

# --- [애플 스타일 디자인 업그레이드] CSS ---
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
        background-color: #F5F5F7 !important;
    }}

    .block-container {{
        padding-top: 2rem !important;
        max-width: 480px !important;
        padding-left: 16px !important;
        padding-right: 16px !important;
        background-color: #F5F5F7 !important;
    }}

    /* 카드 공통 스타일 */
    .apple-card {{
        background: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 24px;
        margin-bottom: 24px;
        border: 1px solid rgba(255, 255, 255, 0.3);
        box-shadow: 0 4px 6px rgba(0,0,0,0.02), 0 1px 3px rgba(0,0,0,0.08);
    }}

    .version-tag {{ 
        font-size: 11px; 
        color: #86868B; 
        text-align: right; 
        margin-bottom: 15px;
        font-weight: 500;
    }}

    .section-header {{
        font-size: 17px; 
        font-weight: 700; 
        color: #1D1D1F; 
        margin: 30px 0 15px 0;
        padding-left: 0;
        letter-spacing: -0.5px;
    }}

    /* 인센티브 버튼 정렬 개선 */
    .st-key-incen_buttons [data-testid="stHorizontalBlock"] {{
        gap: 12px !important;
    }}
    .st-key-incen_buttons button {{
        border-radius: 14px !important;
        border: none !important;
        background-color: #E8E8ED !important;
        color: #1D1D1F !important;
        font-size: 13px !important;
        font-weight: 600 !important;
        min-height: 52px !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }}
    .st-key-incen_buttons button:hover {{
        background-color: #D2D2D7 !important;
        transform: scale(0.97);
    }}

    /* 메인 로그인 버튼 */
    .st-key-login_btn button {{
        height: 60px !important;
        border-radius: 18px !important;
        font-size: 19px !important;
        font-weight: 600 !important;
        background: linear-gradient(180deg, #0077ED 0%, #0060DF 100%) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(0, 119, 237, 0.35) !important;
    }}

    /* 상태 표시 배지 */
    .status-card {{ 
        padding: 16px; 
        border-radius: 18px; 
        margin-bottom: 25px; 
        text-align: center; 
        font-weight: 600; 
        font-size: 15px; 
    }}
    .status-saved {{ background-color: #E3F2FD; color: #0071E3; border: 1px solid #CEE7FE; }}
    .status-missing {{ background-color: #FFF4E5; color: #FF8800; border: 1px solid #FFE7CC; }}

    /* 주간 집계 박스 */
    .weekly-box {{ 
        display: flex; 
        justify-content: space-around; 
        background: white; 
        padding: 18px; 
        border-radius: 18px; 
        margin-bottom: 25px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }}

    /* 리포트 테이블 */
    .report-table {{ 
        width: 100%; 
        font-size: 11px; 
        text-align: center; 
        border-collapse: separate; 
        border-spacing: 0;
        table-layout: fixed; 
        background: white;
        border-radius: 14px;
        overflow: hidden;
        border: 1px solid #F0F0F2;
    }}
    .report-table th {{ background-color: #FBFBFD; color: #86868B; font-weight: 600; padding: 12px 4px; border-bottom: 1px solid #F0F0F2; }}
    .report-table td {{ padding: 12px 4px; border-bottom: 1px solid #F0F0F2; color: #1D1D1F; }}
    .total-row {{ background-color: #FBFBFD !important; font-weight: 700; color: #0071E3 !important; }}

    /* 인센티브 내역 */
    .inc-history-box {{ 
        background: white; 
        border: 1px solid #E8E8ED; 
        border-radius: 14px; 
        padding: 12px; 
        margin-top: 10px; 
        font-size: 13px; 
        color: #1D1D1F; 
    }}
    .inc-item {{ 
        display: inline-block; 
        background: #F5F5F7; 
        padding: 6px 12px; 
        border-radius: 10px; 
        margin: 3px; 
        font-weight: 500;
        color: #424245;
    }}

    /* 정산 정보 상세 박스 */
    .calc-detail {{ 
        font-size: 15px; 
        color: #1D1D1F; 
        margin: 15px 0; 
        background: white; 
        padding: 28px; 
        border-radius: 22px; 
        box-shadow: 0 8px 20px rgba(0,0,0,0.06);
        line-height: 1.7; 
    }}
    .calc-line {{ display: flex; justify-content: space-between; margin-bottom: 10px; }}
    .calc-label {{ color: #86868B; }}
    .calc-val {{ font-weight: 600; }}
    .calc-total {{ 
        font-size: 24px; 
        font-weight: 700; 
        color: #1D1D1F; 
        border-top: 1px solid #F5F5F7; 
        padding-top: 18px; 
        margin-top: 18px; 
    }}

    /* 사이드바 스타일 */
    [data-testid="stSidebar"] {{
        background-color: #FAFAFB !important;
    }}
    [data-testid="stSidebar"] .stSubheader {{ 
        font-size: 16px; 
        font-weight: 700; 
        color: #1D1D1F; 
        margin-top: 25px; 
    }}
    .info-box {{ 
        background: white; 
        padding: 18px; 
        border-radius: 18px; 
        font-size: 14px; 
        line-height: 1.9; 
        border: 1px solid #E8E8ED;
        box-shadow: 0 4px 10px rgba(0,0,0,0.03);
    }}
    .info-label {{ color: #86868B; font-weight: 500; width: 85px; display: inline-block; }}
    .info-val {{ color: #1D1D1F; font-weight: 600; }}

    /* 저장 성공 알림 */
    .save-success {{ 
        color: #008037; 
        background-color: #E8F5E9; 
        padding: 18px; 
        border-radius: 18px; 
        font-weight: 600; 
        margin-top: 20px; 
        text-align: center; 
        font-size: 15px; 
        border: 1px solid #C8E6C9;
    }}
    
    /* 입력 위젯 커스텀 */
    div[data-baseweb="input"] {{
        border-radius: 14px !important;
        border: 1px solid #D2D2D7 !important;
        background-color: white !important;
        transition: border-color 0.2s ease !important;
    }}
    div[data-baseweb="input"]:focus-within {{
        border-color: #0071E3 !important;
    }}
    .amt-label {{ color: #0071E3; font-size: 13px; font-weight: 600; display: block; margin-top: -10px; margin-bottom: 14px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 구글 시트 상수 ---
SHEET_NAME = "아이폰정산"
ORDERED_STAFF = ["태완", "남근", "성훈", "성욱"]
USER_HEADER = ["직원명", "날짜", "인센티브", "item1", "item2", "item3", "item4", "item5", "item6", "item7", "합계", "비고", "입력시간", "시간수당", "퇴근시간"]

def safe_int(val, default=0):
    try:
        if val is None: return default
        return int(str(val).replace(",", "").strip())
    except: return default

def format_curr(val): return f"{safe_int(val):,}"

@st.cache_resource
def get_gsheet_client():
    if "gcp_service_account" not in st.secrets: st.error("Secrets 설정에 gcp_service_account 정보가 없습니다."); st.stop()
    creds_info = dict(st.secrets["gcp_service_account"])
    if "private_key" in creds_info: creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(creds_info, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds)

@st.cache_resource
def get_spreadsheet():
    for _ in range(3):
        try: return get_gsheet_client().open(SHEET_NAME)
        except: time.sleep(1)
    st.error("구글 시트 연결 실패"); st.stop()

def get_config_worksheet():
    ss = get_spreadsheet()
    headers = ["직원명", "기본급", "정산일", "보험료"] + [f"item{i}_name" for i in range(1,8)] + [f"item{i}_price" for i in range(1,8)] + ["시간수당(10분)", "전체적용"]
    try:
        ws = ss.worksheet("config"); curr_h = ws.row_values(1)
        if len(curr_h) < len(headers) or curr_h[0] != "직원명": ws.update(range_name=f"A1:{chr(ord('A')+len(headers)-1)}1", values=[headers])
        return ws
    except:
        ws = ss.add_worksheet(title="config", rows="100", cols="20")
        ws.append_row(headers); return ws

@st.cache_data(ttl=300)
def load_staff_salary_config(name):
    try: sheet = get_config_worksheet(); rows = sheet.get_all_values()
    except: return None
    
    base_template_name = "성훈" if name == "성욱" else ""
    template_data = None
    
    if len(rows) > 1:
        hd = rows[0]
        for r in rows[1:]:
            if r and r[0] == name:
                d = {hd[i]: r[i] for i in range(min(len(hd), len(r)))}
                return {
                    "base_salary": safe_int(d.get("기본급"), 3500000), "start_day": safe_int(d.get("정산일"), 13), "insurance": safe_int(d.get("보험료"), 104760),
                    "item_names": [d.get(f"item{i}_name") or "" for i in range(1,8)],
                    "item_prices": [safe_int(d.get(f"item{i}_price")) for i in range(1,8)],
                    "overtime_rate": safe_int(d.get("시간수당(10분)")), "apply_global": d.get("전체적용", "FALSE").upper() == "TRUE"
                }
            if base_template_name and r and r[0] == base_template_name:
                template_data = r
        
    if template_data:
        hd = rows[0]
        d = {hd[i]: template_data[i] for i in range(min(len(hd), len(template_data)))}
        res = {
            "base_salary": safe_int(d.get("기본급"), 3500000), "start_day": safe_int(d.get("정산일"), 13), "insurance": safe_int(d.get("보험료"), 104760),
            "item_names": [d.get(f"item{i}_name") or "" for i in range(1,8)],
            "item_prices": [safe_int(d.get(f"item{i}_price")) for i in range(1,8)],
            "overtime_rate": safe_int(d.get("시간수당(10분)")), "apply_global": d.get("전체적용", "FALSE").upper() == "TRUE"
        }
        save_staff_salary_config(name, res["base_salary"], res["start_day"], res["insurance"], res["item_names"], res["item_prices"], res["overtime_rate"], res["apply_global"])
        return res
    
    defaults = {"base_salary": 3500000, "start_day": 13, "insurance": 104760, "item_names": ['일반필름', '풀필름', '젤리', '케이블', '어댑터', '추가1', '추가2'], "item_prices": [9000, 18000, 9000, 15000, 23000, 0, 0], "overtime_rate": 4000 if name == "태완" else (3000 if name == "남근" else 0), "apply_global": False}
    save_staff_salary_config(name, defaults["base_salary"], defaults["start_day"], defaults["insurance"], defaults["item_names"], defaults["item_prices"], defaults["overtime_rate"], defaults["apply_global"])
    return defaults

def save_staff_salary_config(name, base, day, ins, names, prices, ov_rate=0, apply_global=False):
    sheet = get_config_worksheet(); rows = sheet.get_all_values(); idx = -1
    for i, r in enumerate(rows):
        if r and r[0] == name: idx = i + 1; break
    data = [name, format_curr(base), safe_int(day), format_curr(ins)] + names + [format_curr(p) for p in prices] + [format_curr(ov_rate), str(apply_global).upper()]
    if idx != -1: sheet.update(range_name=f"A{idx}:{chr(ord('A')+len(data)-1)}{idx}", values=[data])
    else: sheet.append_row(data)
    st.cache_data.clear()

def get_user_worksheet(user_name):
    ss = get_spreadsheet()
    try:
        ws = ss.worksheet(user_name); curr_h = ws.row_values(1)
        if len(curr_h) < len(USER_HEADER) or "시간수당" not in curr_h or curr_h[3] != "item1":
            ws.update(range_name=f"A1:{chr(ord('A')+len(USER_HEADER)-1)}1", values=[USER_HEADER])
        return ws
    except:
        ws = ss.add_worksheet(title=user_name, rows="1000", cols="20")
        ws.append_row(USER_HEADER); return ws

def load_data_from_gsheet(user_name):
    try:
        sheet = get_user_worksheet(user_name); data = sheet.get_all_values()
        if len(data) <= 1: return pd.DataFrame()
        df = pd.DataFrame(data[1:], columns=data[0])
        num_cols = ["인센티브", "시간수당", "item1", "item2", "item3", "item4", "item5", "item6", "item7", "합계"]
        for c in num_cols:
            if c in df.columns: df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ""), errors='coerce').fillna(0).astype(int)
        return df
    except: return pd.DataFrame()

def save_to_gsheet(user_name, df_row):
    try:
        sheet = get_user_worksheet(user_name); rows = sheet.get_all_values(); idx = -1
        for i, r in enumerate(rows):
            if len(r) > 1 and r[1] == df_row['날짜']: idx = i + 1; break
        vals = [format_curr(df_row.get(h, 0)) if h in ["인센티브", "시간수당", "합계"] or "item" in h else df_row.get(h, "") for h in USER_HEADER]
        if idx != -1: sheet.update(range_name=f"A{idx}:{chr(ord('A')+len(USER_HEADER)-1)}{idx}", values=[vals])
        else: sheet.append_row(vals)
        return True
    except: return False

def get_safe_date(y, m, d): ld = calendar.monthrange(y, m)[1]; return date(y, m, min(safe_int(d, 1), ld))
def get_now_kst(): return datetime.now(timezone.utc) + timedelta(hours=9)

# --- 세션 초기화 및 로그인 ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False

@st.cache_data(ttl=600)
def get_staff_list_fixed():
    try:
        sheet = get_config_worksheet(); names = sheet.col_values(1)[1:]
        res = []
        for s in ORDERED_STAFF:
            if (s in names or s in ORDERED_STAFF) and s not in res: res.append(s)
        for n in names:
            if n and n not in res: res.append(n)
        return res
    except: return ORDERED_STAFF

STAFF_LIST = get_staff_list_fixed()

if not st.session_state.logged_in:
    st.title("🔐 로그인")
    user_id = st.selectbox("직원 선택", options=STAFF_LIST)
    admin_pw = st.text_input("비번", type="password") if user_id == "태완" else ""
    if st.button("입장", use_container_width=True, key="login_btn"):
        if user_id == "태완" and admin_pw != "102030": st.error("비번 오류")
        else: st.session_state.logged_in = True; st.session_state.user_name = user_id; st.rerun()
    st.markdown(f'<div class="admin-log"><b>🕒 {get_now_kst().strftime("%H:%M:%S")} v4.0.1 패치</b><br>• [fix] 인센티브 위젯 Session State 충돌 오류 수정<br>• 날짜 변경 시 초기화 안정성 강화</div>', unsafe_allow_html=True); st.stop()

# 최신 설정 로드
user_name = st.session_state.user_name
sal_cfg = load_staff_salary_config(user_name)
is_ov_staff = user_name in ["태완", "남근"]
df_all = load_data_from_gsheet(user_name)

# --- 메인 화면 변수 및 날짜 처리 ---
st.markdown(f'<div class="version-tag">{SW_VERSION}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="apple-card"><h2 style="margin:0; font-size:22px; color:#1D1D1F;">💼 {user_name}님 실적</h2></div>', unsafe_allow_html=True)
sel_date = st.date_input("날짜", value=date.today(), label_visibility="collapsed"); str_date = sel_date.strftime("%Y-%m-%d")

# [v4.0.1] 세션 초기값 보장 로직
if "current_date" not in st.session_state: st.session_state.current_date = str_date
if "inc_input_field" not in st.session_state: st.session_state.inc_input_field = 0

# 날짜 변경 감지 및 초기화
if st.session_state.current_date != str_date:
    st.session_state.current_date = str_date
    ext_data = df_all[df_all["날짜"] == str_date] if not df_all.empty else pd.DataFrame()
    # 상태 강제 업데이트
    st.session_state.inc_sum = safe_int(ext_data.iloc[0]["인센티브"]) if not ext_data.empty else 0
    st.session_state.inc_his = [{"val": safe_int(ext_data.iloc[0]["인센티브"])}] if not ext_data.empty and safe_int(ext_data.iloc[0]["인센티브"]) > 0 else []
    st.session_state.inc_input_field = 0 # 입력필드 리셋
    for i in range(7):
        val = safe_int(ext_data.iloc[0][f"item{i+1}"]) if not ext_data.empty else 0
        st.session_state[f"it_input_{i}"] = val
    st.rerun()

existing = df_all[df_all["날짜"] == str_date] if not df_all.empty else pd.DataFrame()
if not existing.empty: st.markdown(f'<div class="status-card status-saved">✅ {str_date} 데이터가 저장되어 있습니다</div>', unsafe_allow_html=True)
else: st.markdown(f'<div class="status-card status-missing">⚠️ {str_date} 데이터가 아직 등록되지 않았습니다</div>', unsafe_allow_html=True)

# --- 사이드바 ---
with st.sidebar:
    st.header("⚙️ 설정")
    if user_name != "태완":
        st.subheader("👤 내 정보 (보기 전용)")
        info_html = f"<div class='info-box'><span class='info-label'>기본급:</span> <span class='info-val'>{sal_cfg['base_salary']:,}원</span><br>"
        if is_ov_staff: info_html += f"<span class='info-label'>시간수당:</span> <span class='info-val'>10분당 {sal_cfg['overtime_rate']:,}원</span><br>"
        info_html += f"<span class='info-label'>보험료:</span> <span class='info-val'>{sal_cfg['insurance']:,}원</span><br><span class='info-label'>정산일:</span> <span class='info-val'>매달 {sal_cfg['start_day']}일</span><hr style='margin:5px 0;'><b>[품목 단가]</b><br>"
        for n, p in zip(sal_cfg["item_names"], sal_cfg["item_prices"]): info_html += f"<span class='info-label'>{n[:4]}:</span> <span class='info-val'>{p:,}원</span><br>"
        st.markdown(info_html + "</div>", unsafe_allow_html=True)
    if user_name == "태완":
        st.subheader("🛠️ 관리자 설정")
        target = st.selectbox("수정 대상 직원", STAFF_LIST); t_sal = load_staff_salary_config(target)
        st.subheader("📦 품목 명칭 및 단가")
        new_n, new_p = [], []
        for i in range(7):
            c1, c2 = st.columns([1.2, 1]); n = c1.text_input(f"명칭{i+1}", value=t_sal["item_names"][i], key=f"sn_{target}_{i}")
            p = c2.number_input(f"단가{i+1}", value=t_sal["item_prices"][i], step=1000, key=f"sp_{target}_{i}")
            with c2: st.markdown(f"<span class='amt-label'>({p:,}원)</span>", unsafe_allow_html=True)
            new_n.append(n); new_p.append(p)
        st.divider(); st.subheader("💰 급여 및 수당 설정")
        base = st.number_input(f"기본급 수정", value=safe_int(t_sal["base_salary"]), step=10000)
        st.markdown(f"<span class='amt-label'>({base:,}원)</span>", unsafe_allow_html=True)
        ov_r = st.number_input(f"시간수당(10분당)", value=safe_int(t_sal["overtime_rate"]), step=100) if target in ["태완", "남근"] else 0
        if target in ["태완", "남근"]: st.markdown(f"<span class='amt-label'>({ov_r:,}원)</span>", unsafe_allow_html=True)
        ins = st.number_input(f"보험료 수정", value=safe_int(t_sal["insurance"]), step=1000)
        st.markdown(f"<span class='amt-label'>({ins:,}원)</span>", unsafe_allow_html=True)
        st.divider(); s_day = st.slider(f"시작일 설정", 1, 31, value=min(max(1, t_sal["start_day"]), 31))
        app_gl = st.checkbox("현재 단가를 과거 기록에도 전체 적용", value=t_sal.get("apply_global", False))
        if st.button(f"💿 {target} 설정 저장", use_container_width=True): 
            save_staff_salary_config(target, base, s_day, ins, new_n, new_p, ov_r, app_gl)
            st.session_state.admin_log = f"✅ {target} 저장 완료 ({get_now_kst().strftime('%H:%M:%S')})"; st.rerun()
        if "admin_log" in st.session_state: st.markdown(f'<div class="admin-log">{st.session_state.admin_log}</div>', unsafe_allow_html=True)
    st.divider();
    if st.button("로그아웃", use_container_width=True): st.session_state.clear(); st.rerun()

# --- 휴무 및 기록 출력 ---
if st.button("🌴 오늘 휴무 등록", use_container_width=True):
    row = {"직원명": user_name, "날짜": str_date, "인센티브": 0, "시간수당": 0, "퇴근시간": "휴무", "item1":0, "item2":0, "item3":0, "item4":0, "item5":0, "item6":0, "item7":0, "합계": 0, "비고": "휴무", "입력시간": get_now_kst().strftime("%H:%M:%S")}
    if save_to_gsheet(user_name, row): st.rerun()

st.write("**📅 최근 7일 기록**")
w_box = '<div class="weekly-box">'
for i in range(6, -1, -1):
    td = get_now_kst().date() - timedelta(days=i); ts = td.strftime("%Y-%m-%d"); dd = df_all[df_all["날짜"] == ts] if not df_all.empty else pd.DataFrame()
    icon = "✅" if not dd.empty and dd.iloc[0]['비고'] != "휴무" else ("🌴" if not dd.empty else "⚪")
    w_box += f'<div style="text-align:center;"><div style="font-size:10px;">{td.day}일</div><div>{icon}</div></div>'
st.markdown(w_box + '</div>', unsafe_allow_html=True); st.divider()

# --- 수당 및 인센티브 ---
st.markdown('<div class="section-header">💰 수당 및 인센티브</div>', unsafe_allow_html=True)
if "inc_sum" not in st.session_state:
    st.session_state.inc_sum = safe_int(existing.iloc[0]["인센티브"]) if not existing.empty else 0
    st.session_state.inc_his = [{"val": safe_int(existing.iloc[0]["인센티브"])}] if not existing.empty and safe_int(existing.iloc[0]["인센티브"]) > 0 else []

ov_pay, sel_etime = 0, "20:00"
if is_ov_staff:
    etime_list = [f"{h}:{m:02d}" for h in range(20, 24) for m in range(0, 60, 10)] + ["24:00"]
    e_val = existing.iloc[0]["퇴근시간"] if not existing.empty else "20:00"
    e_idx = etime_list.index(e_val) if e_val in etime_list else 0
    sel_etime = st.selectbox("퇴근 시간 선택", options=etime_list, index=e_idx)
    h, m = map(int, sel_etime.split(":")) if sel_etime != "24:00" else (24, 0)
    ov_min = max(0, (h * 60 + m) - 1200); ov_pay = (ov_min // 10) * sal_cfg["overtime_rate"]
    st.markdown(f"<div style='background:#f0f8ff; padding:12px; border-radius:12px; border:2px solid #d0e8ff; margin-bottom:15px; text-align:center;'>현재 시간수당: <b style='color:#007bff; font-size:20px;'>{ov_pay:,}원</b></div>", unsafe_allow_html=True)
    st.metric("인센티브 합계", f"{st.session_state.inc_sum:,}원")
else: st.metric("인센티브 합계", f"{st.session_state.inc_sum:,}원")

if st.session_state.inc_his:
    h_html = '<div class="inc-history-box">'
    for i, item in enumerate(st.session_state.inc_his): h_html += f'<span class="inc-item">#{i+1}: {item["val"]:,}원</span>'
    st.markdown(h_html + '</div>', unsafe_allow_html=True)

# [v4.0.1] 위젯 중복 선언 오류 수정: value= 인자 제거 및 key 에만 의존
st.number_input("인센티브 추가 금액 (입력 후 추가 버튼 클릭)", 0, step=1000, label_visibility="collapsed", key="inc_input_field")
with st.container(key="incen_buttons"):
    b1, b2, b3 = st.columns(3)
    def add_inc():
        val = st.session_state.inc_input_field
        if val > 0:
            st.session_state.inc_sum += val
            st.session_state.inc_his.append({"val": val})
            st.session_state.inc_input_field = 0
    b1.button("➕추가", use_container_width=True, on_click=add_inc)
    b2.button("↩️취소", use_container_width=True, on_click=lambda: (st.session_state.update({"inc_sum": st.session_state.inc_sum - (st.session_state.inc_his.pop()['val'] if st.session_state.inc_his else 0)})))
    b3.button("🧹리셋", use_container_width=True, on_click=lambda: (st.session_state.update({"inc_sum": 0, "inc_his": []})))

# --- 품목 수량 입력 ---
st.markdown('<div class="section-header">📦 품목 수량 입력</div>', unsafe_allow_html=True)
it_n, it_p = sal_cfg["item_names"], sal_cfg["item_prices"]
# 초기 세션값 할당 (로드된 값 또는 0)
for i in range(7):
    if f"it_input_{i}" not in st.session_state:
        st.session_state[f"it_input_{i}"] = safe_int(existing.iloc[0][f"item{i+1}"]) if not existing.empty else 0

for i in range(0, 6, 2):
    c1, c2 = st.columns(2)
    with c1: st.number_input(it_n[i], 0, key=f"it_input_{i}")
    with c2: st.number_input(it_n[i+1], 0, key=f"it_input_{i+1}")
st.number_input(it_n[6], 0, key="it_input_6")

if st.button("✅ 최종 데이터 저장", type="primary", use_container_width=True):
    cts = [st.session_state[f"it_input_{i}"] for i in range(7)]
    tot_val = st.session_state.inc_sum + ov_pay + sum([safe_int(c) * safe_int(p) for c, p in zip(cts, it_p)])
    row = {"직원명": user_name, "날짜": str_date, "인센티브": st.session_state.inc_sum, "시간수당": ov_pay, "퇴근시간": sel_etime, "item1": cts[0], "item2": cts[1], "item3": cts[2], "item4": cts[3], "item5": cts[4], "item6": cts[5], "item7": cts[6], "합계": tot_val, "비고": "정상", "입력시간": get_now_kst().strftime("%H:%M:%S")}
    if save_to_gsheet(user_name, row):
        st.session_state.sv_msg = f"✅ 데이터가 성공적으로 저장되었습니다! ({get_now_kst().strftime('%H:%M:%S')})"
        st.rerun()

if st.session_state.get("sv_msg"):
    st.markdown(f'<div class="save-success">{st.session_state.sv_msg}</div>', unsafe_allow_html=True)
    st.session_state.sv_msg = None

# --- 정산 리포트 ---
st.divider()
s_d, b, ins = safe_int(sal_cfg['start_day'], 13), safe_int(sal_cfg['base_salary']), safe_int(sal_cfg['insurance'])
if sel_date.day >= s_d: s_dt = get_safe_date(sel_date.year, sel_date.month, s_d)
else: prv = sel_date.replace(day=1) - timedelta(days=1); s_dt = get_safe_date(prv.year, prv.month, s_d)
e_dt = get_safe_date((s_dt + timedelta(days=32)).year, (s_dt + timedelta(days=32)).month, s_d) - timedelta(days=1)
st.subheader(f"📊 정산 리포트 ({s_dt.strftime('%m/%d')} ~ {e_dt.strftime('%m/%d')})")

if not df_all.empty:
    df_all['date_dt'] = pd.to_datetime(df_all['날짜']).dt.date
    p_df = df_all[(df_all['date_dt'] >= s_dt) & (df_all['date_dt'] <= e_dt)].sort_values("날짜")
    if not p_df.empty:
        if sal_cfg.get("apply_global"):
            t_inc = safe_int(p_df["인센티브"].sum())
            t_ov = safe_int(p_df["시간수당"].sum())
            t_items = sum([safe_int(p_df[f"item{i+1}"].sum()) * safe_int(it_p[i]) for i in range(7)])
            total_sum_val = t_inc + t_ov + t_items
        else:
            total_sum_val = safe_int(p_df["합계"].sum()); t_inc = safe_int(p_df["인센티브"].sum()); t_ov = safe_int(p_df["시간수당"].sum()); t_items = total_sum_val - t_inc - t_ov
        final_pay = int(b + total_sum_val - ins); combined_inc = t_inc + t_items + t_ov
        st.markdown(f'<div class="calc-detail"><div class="calc-line"><span>기본급</span> <span>+ {b:,}원</span></div><div class="calc-line"><span>인센티브</span> <span>+ {combined_inc:,}원</span></div><div class="calc-line"><span>보험료</span> <span>- {ins:,}원</span></div><div class="calc-total"><div class="calc-line"><span>💰 총급여</span> <span>{final_pay:,}원</span></div></div></div>', unsafe_allow_html=True)
        h_base = ["날짜", "인센"] + (["수당"] if is_ov_staff else []); hds = h_base + [n[:2] for n in it_n] + ["합계"]
        r_html, i_sums = "", [0]*7
        for _, r in p_df.iterrows():
            md = datetime.strptime(r['날짜'], '%Y-%m-%d').strftime('%m/%d')
            if r['비고'] == "휴무": r_html += f"<tr><td style='font-weight:bold;'>{md}</td><td colspan='{len(hds)-1}' style='color:orange;'>🌴휴무</td></tr>"
            else:
                row_inc, row_ov = safe_int(r['인센티브']), safe_int(r.get('시간수당', 0)); 
                for i in range(1, 8): i_sums[i-1] += safe_int(r[f'item{i}'])
                row_total = (row_inc + row_ov + sum([safe_int(r[f'item{i+1}']) * safe_int(it_p[i]) for i in range(7)])) if sal_cfg.get("apply_global") else safe_int(r['합계'])
                disp_inc, ov_td = (row_inc if is_ov_staff else row_inc + row_ov), (f"<td>{row_ov:,}</td>" if is_ov_staff else "")
                it_tds = "".join([f"<td>{safe_int(r[f'item{i}'])}</td>" for i in range(1, 8)])
                r_html += f"<tr><td style='font-weight:bold;'>{md}</td><td>{disp_inc:,}</td>{ov_td}{it_tds}<td style='color:blue;'>{row_total:,}</td></tr>"
        r_html += f"<tr class='total-row'><td>합계</td><td>{(t_inc if is_ov_staff else t_inc + t_ov):?}</td>" + (f"<td>{t_ov:,}</td>" if is_ov_staff else "") + "".join([f"<td>{s}</td>" for s in i_sums]) + f"<td>{total_sum_val:,}</td></tr>"
        st.markdown(f'<table class="report-table"><tr>{"".join([f"<th>{x}</th>" for x in hds])}</tr>{r_html}</table>', unsafe_allow_html=True)
