import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials
import calendar
import time
import hashlib

# 소프트웨어 버전
SW_VERSION = "v4.0.1"

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
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 3px !important;
        width: 100% !important;
    }}
    .st-key-incen_buttons [data-testid="stHorizontalBlock"] > div {{
        flex: 1 1 0% !important;
        min-width: 0 !important;
    }}
    .st-key-incen_buttons button {{
        font-size: 11px !important;
        padding: 0px !important;
        width: 100% !important;
        min-height: 42px !important;
        font-weight: bold !important;
        letter-spacing: -0.5px;
    }}

    .admin-log {{ font-size: 11px; color: #155724; background-color: #d4edda; padding: 10px; border-radius: 5px; margin-top: 10px; border: 1px solid #c3e6cb; }}
    .st-key-login_btn button {{ height: 50px !important; font-size: 18px !important; font-weight: bold !important; background-color: #007bff !important; color: white !important; }}

    .status-card {{ padding: 12px; border-radius: 12px; margin-bottom: 15px; text-align: center; font-weight: bold; font-size: 14px; }}
    .status-saved {{ background-color: #e3f2fd; color: #1e88e5; border: 1px solid #bbdefb; }}
    .status-missing {{ background-color: #fff3e0; color: #ef6c00; border: 1px solid #ffe0b2; }}

    .weekly-box {{ display: flex; justify-content: space-around; background: #f8f9fa; padding: 10px; border-radius: 10px; margin-bottom: 15px; }}
    
    .report-table {{ width: 100%; font-size: 8.8px; text-align: center; border-collapse: collapse; table-layout: fixed; }}
    .report-table th, .report-table td {{ border: 1px solid #eee; padding: 4px 0px; word-break: break-all; letter-spacing: -0.8px; }}
    .total-row {{ background-color: #f2f2f2 !important; font-weight: bold; }}
    
    .inc-history-box {{ background: #fdfdfd; border: 1px solid #f0f0f0; border-radius: 8px; padding: 8px; margin-top: 5px; font-size: 11px; color: #666; }}
    .inc-item {{ display: inline-block; background: #eee; padding: 2px 6px; border-radius: 4px; margin: 2px; }}
    
    .calc-detail {{ font-size: 13px; color: #333; margin: 10px 0; background: #f0f7ff; padding: 15px; border-radius: 10px; border: 1px solid #c2e0ff; line-height: 1.8; }}
    .calc-line {{ display: flex; justify-content: space-between; margin-bottom: 5px; }}
    .calc-total {{ font-size: 18px; font-weight: bold; color: #007bff; border-top: 1px dashed #abc; padding-top: 10px; margin-top: 10px; }}
    
    [data-testid="stSidebar"] .stSubheader {{ font-size: 14px; font-weight: bold; color: #007bff; margin-top: 15px; }}
    .info-box {{ background: #fafafa; border: 1px solid #eee; padding: 10px; border-radius: 8px; font-size: 12px; line-height: 1.6; }}
    .info-label {{ color: #777; font-weight: bold; width: 70px; display: inline-block; }}
    .info-val {{ color: #333; font-weight: bold; }}

    .save-success {{ color: #155724; background-color: #d4edda; border: 1px solid #c3e6cb; padding: 12px; border-radius: 8px; font-weight: bold; margin-top: 10px; text-align: center; font-size: 14px; }}
    .amt-label {{ color: #007bff; font-size: 11px; font-weight: bold; display: block; margin-top: -15px; margin-bottom: 10px; }}
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

def hash_password(password):
    return hashlib.sha256(str(password).encode()).hexdigest()

def check_password(password, hashed_password):
    return hash_password(password) == hashed_password

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
    headers = ["직원명", "기본급", "정산일", "보험료"] + [f"item{i}_name" for i in range(1,8)] + [f"item{i}_price" for i in range(1,8)] + ["시간수당(10분)", "전체적용", "비밀번호"]
    try:
        ws = ss.worksheet("config"); curr_h = ws.row_values(1)
        if len(curr_h) < len(headers) or "비밀번호" not in curr_h:
             ws.update(range_name=f"A1:{chr(ord('A')+len(headers)-1)}1", values=[headers])
        return ws
    except:
        ws = ss.add_worksheet(title="config", rows="100", cols="25")
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
                    "overtime_rate": safe_int(d.get("시간수당(10분)")), "apply_global": d.get("전체적용", "FALSE").upper() == "TRUE",
                    "password_hash": d.get("비밀번호", "")
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
            "overtime_rate": safe_int(d.get("시간수당(10분)")), "apply_global": d.get("전체적용", "FALSE").upper() == "TRUE",
            "password_hash": d.get("비밀번호", "")
        }
        save_staff_salary_config(name, res["base_salary"], res["start_day"], res["insurance"], res["item_names"], res["item_prices"], res["overtime_rate"], res["apply_global"], res["password_hash"])
        return res
    
    defaults = {"base_salary": 3500000, "start_day": 13, "insurance": 104760, "item_names": ['일반필름', '풀필름', '젤리', '케이블', '어댑터', '추가1', '추가2'], "item_prices": [9000, 18000, 9000, 15000, 23000, 0, 0], "overtime_rate": 4000 if name == "태완" else (3000 if name == "남근" else 0), "apply_global": False, "password_hash": ""}
    save_staff_salary_config(name, defaults["base_salary"], defaults["start_day"], defaults["insurance"], defaults["item_names"], defaults["item_prices"], defaults["overtime_rate"], defaults["apply_global"], defaults["password_hash"])
    return defaults

def save_staff_salary_config(name, base, day, ins, names, prices, ov_rate=0, apply_global=False, password_hash=""):
    sheet = get_config_worksheet(); rows = sheet.get_all_values(); idx = -1
    for i, r in enumerate(rows):
        if r and r[0] == name: idx = i + 1; break
    data = [name, format_curr(base), safe_int(day), format_curr(ins)] + names + [format_curr(p) for p in prices] + [format_curr(ov_rate), str(apply_global).upper(), str(password_hash)]
    if idx != -1: sheet.update(range_name=f"A{idx}:{chr(ord('A')+len(data)-1)}{idx}", values=[data])
    else: sheet.append_row(data)
    st.cache_data.clear()

def update_password(name, new_hash):
    cfg = load_staff_salary_config(name)
    if cfg:
        save_staff_salary_config(name, cfg["base_salary"], cfg["start_day"], cfg["insurance"], cfg["item_names"], cfg["item_prices"], cfg["overtime_rate"], cfg["apply_global"], new_hash)
        return True
    return False

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
    user_pw = st.text_input("비밀번호", type="password")
    
    if st.button("입장", use_container_width=True, key="login_btn"):
        cfg = load_staff_salary_config(user_id)
        saved_hash = cfg.get("password_hash", "")
        
        # 1. 초기 비밀번호 설정 (DB에 비번이 없을 경우)
        if not saved_hash:
            default_pw = "102030" if user_id == "태완" else "0000"
            if user_pw == default_pw:
                # 로그인 성공 시 해시 저장 (자동 마이그레이션)
                update_password(user_id, hash_password(user_pw))
                st.session_state.logged_in = True; st.session_state.user_name = user_id; st.rerun()
            else:
                st.error("초기 비밀번호가 잘못되었습니다. (태완:102030, 직원:0000)")
        
        # 2. 저장된 비밀번호 검증
        else:
            if check_password(user_pw, saved_hash):
                st.session_state.logged_in = True; st.session_state.user_name = user_id; st.rerun()
            else:
                st.error("비밀번호가 일치하지 않습니다.")

    st.markdown(f'<div class="admin-log"><b>🕒 {get_now_kst().strftime("%H:%M:%S")} v4.1.0 패치</b><br>• [보안] 전직원 비밀번호 기능 도입<br>• [기능] 비밀번호 변경 및 관리자 초기화 기능 추가</div>', unsafe_allow_html=True); st.stop()

# 최신 설정 로드
user_name = st.session_state.user_name
sal_cfg = load_staff_salary_config(user_name)
is_ov_staff = user_name in ["태완", "남근"]
df_all = load_data_from_gsheet(user_name)

# --- 메인 화면 변수 및 날짜 처리 ---
st.markdown(f'<div class="version-tag">{SW_VERSION}</div>', unsafe_allow_html=True)
st.write(f"### 💼 {user_name}님 실적")
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
    
    with st.expander("🔑 비밀번호 변경"):
        cur_pw = st.text_input("현재 비밀번호", type="password", key="cp_cur")
        new_pw = st.text_input("새 비밀번호", type="password", key="cp_new")
        chk_pw = st.text_input("새 비밀번호 확인", type="password", key="cp_chk")
        if st.button("비밀번호 변경", use_container_width=True):
            if not check_password(cur_pw, sal_cfg.get("password_hash", "")): st.error("현재 비밀번호 불일치")
            elif new_pw != chk_pw: st.error("새 비밀번호가 일치하지 않습니다")
            elif len(new_pw) < 4: st.error("비밀번호는 4자리 이상이어야 합니다")
            else:
                if update_password(user_name, hash_password(new_pw)):
                    st.success("비밀번호 변경 완료! 다시 로그인해주세요."); time.sleep(1)
                    st.session_state.logged_in = False; st.rerun()
                else: st.error("변경 실패")

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
            save_staff_salary_config(target, base, s_day, ins, new_n, new_p, ov_r, app_gl, t_sal.get("password_hash", ""))
            st.session_state.admin_log = f"✅ {target} 설정 저장 완료 ({get_now_kst().strftime('%H:%M:%S')})"; st.rerun()
        
        st.divider()
        if st.button(f"🔄 {target} 비밀번호 초기화 (0000)", type="secondary", use_container_width=True):
             default_hash = hash_password("102030" if target == "태완" else "0000")
             if update_password(target, default_hash):
                 st.session_state.admin_log = f"✅ {target} 비밀번호 초기화 완료"; st.rerun()
                 
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
        r_html += f"<tr class='total-row'><td>합계</td><td>{(t_inc if is_ov_staff else t_inc + t_ov):,}</td>" + (f"<td>{t_ov:,}</td>" if is_ov_staff else "") + "".join([f"<td>{s}</td>" for s in i_sums]) + f"<td>{total_sum_val:,}</td></tr>"
        st.markdown(f'<table class="report-table"><tr>{"".join([f"<th>{x}</th>" for x in hds])}</tr>{r_html}</table>', unsafe_allow_html=True)
