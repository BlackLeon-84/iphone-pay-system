import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials
import calendar
import time
from io import BytesIO
import hashlib

# --- 상수 및 설정 ---
SW_VERSION = "v4.5.4"

# 페이지 설정
st.set_page_config(page_title=f"정산 {SW_VERSION}", layout="centered", initial_sidebar_state="collapsed")

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
    
    .st-key-incen_buttons [data-testid="stHorizontalBlock"],
    .st-key-fast_btns [data-testid="stHorizontalBlock"],
    .st-key-exp_cols [data-testid="stHorizontalBlock"],
    .st-key-card_list [data-testid="stHorizontalBlock"] {{
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 3px !important;
        width: 100% !important;
    }}
    .st-key-incen_buttons [data-testid="stHorizontalBlock"] > div,
    .st-key-fast_btns [data-testid="stHorizontalBlock"] > div,
    .st-key-exp_cols [data-testid="stHorizontalBlock"] > div,
    .st-key-card_list [data-testid="stHorizontalBlock"] > div {{
        flex: 1 1 0% !important;
        min-width: 0 !important;
    }}
    .st-key-incen_buttons button,
    .st-key-fast_btns button {{
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
    
    /* [New] Borderless Form for Login */
    [data-testid="stForm"] {{ border: 0px; padding: 0px; background: transparent; }}
    .history-card {{ background: #f9f9f9; border-left: 3px solid #ccc; padding: 10px; margin-bottom: 8px; border-radius: 0 5px 5px 0; }}
    .ver-badge {{ font-size: 11px; font-weight: bold; color: #555; background: #eee; padding: 2px 6px; border-radius: 4px; }}
    
    /* [UI] 우측 상단 'Running' 텍스트를 '로딩중...'으로 변경 */
    div[data-testid="stStatusWidget"] * {{
        font-size: 0px !important;
    }}
    div[data-testid="stStatusWidget"]::after {{
        content: "로딩중..." !important;
        font-size: 14px !important;
        color: #333 !important;
        margin-left: 5px !important;
        align-self: center !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 구글 시트 상수 ---
SHEET_NAME = "아이폰정산"
ORDERED_STAFF = ["태완", "남근", "성훈", "대원", "성욱", "테스트"]
USER_HEADER = ["직원명", "날짜", "인센티브", "item1", "item2", "item3", "item4", "item5", "item6", "item7", "합계", "비고", "입력시간", "시간수당", "퇴근시간", "현금", "카드", "카드제외", "기타", "카드상세", "기타지급"]

def safe_int(val, default=0):
    try:
        if val is None: return default
        # "1,000원", "1500.0" 등 다양한 수식과 단위 대응
        s = str(val).replace(",", "").replace("원", "").strip()
        if "." in s: s = s.split(".")[0]
        return int(s) if s else default
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

def gspread_retry(func, *args, **kwargs):
    """Google Sheets API 429 Quota 에러 핸들링을 위한 재시도 헬퍼"""
    max_retries = 5
    for i in range(max_retries):
        try:
            return func(*args, **kwargs)
        except gspread.exceptions.APIError as e:
            if "429" in str(e) and i < max_retries - 1:
                wait_time = (2 ** i) + 1
                time.sleep(wait_time)
                continue
            raise e
        except Exception as e:
            if i < max_retries - 1:
                time.sleep(1)
                continue
            raise e

@st.cache_resource
def get_spreadsheet():
    return gspread_retry(get_gsheet_client().open, SHEET_NAME)

def get_config_worksheet():
    ss = get_spreadsheet()
    headers = ["직원명", "기본급", "정산일", "보험료"] + [f"item{i}_name" for i in range(1,8)] + [f"item{i}_price" for i in range(1,8)] + ["시간수당(10분)", "전체적용", "비밀번호"]
    try:
        ws = gspread_retry(ss.worksheet, "config")
    except:
        try:
            ws = gspread_retry(ss.add_worksheet, title="config", rows="100", cols="25")
            gspread_retry(ws.append_row, headers)
            return ws
        except Exception as e:
            if "already exists" in str(e):
                ws = gspread_retry(ss.worksheet, "config")
            else: raise e
            
    try:
        curr_h = gspread_retry(ws.row_values, 1)
        if len(curr_h) < len(headers) or "비밀번호" not in curr_h:
             gspread_retry(ws.update, range_name=f"A1:{chr(ord('A')+len(headers)-1)}1", values=[headers])
    except: pass
    return ws

@st.cache_data(ttl=600)
def load_staff_salary_config(name):
    try:
        sheet = get_config_worksheet(); rows = gspread_retry(sheet.get_all_values)
        
        base_template_name = "성욱" if name in ["대원", "테스트"] else ("성훈" if name == "성욱" else "")
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
    except Exception: return None

def save_staff_salary_config(name, base, day, ins, names, prices, ov_rate=0, apply_global=False, password_hash=""):
    try:
        sheet = get_config_worksheet(); rows = sheet.get_all_values(); idx = -1
        for i, r in enumerate(rows):
            if r and r[0] == name: idx = i + 1; break
        data = [name, format_curr(base), safe_int(day), format_curr(ins)] + names + [format_curr(p) for p in prices] + [format_curr(ov_rate), str(apply_global).upper(), str(password_hash)]
        if idx != -1: gspread_retry(sheet.update, range_name=f"A{idx}:{chr(ord('A')+len(data)-1)}{idx}", values=[data])
        else: gspread_retry(sheet.append_row, data)
        load_staff_salary_config.clear() # Cache Clear
        return True
    except: return False

def update_password(name, new_hash):
    try:
        cfg = load_staff_salary_config(name)
        save_staff_salary_config(name, cfg["base_salary"], cfg["start_day"], cfg["insurance"], cfg["item_names"], cfg["item_prices"], cfg["overtime_rate"], cfg["apply_global"], new_hash)
        return True
    except: return False

def get_user_worksheet(user_name):
    ss = get_spreadsheet()
    try:
        ws = gspread_retry(ss.worksheet, user_name)
    except:
        try:
            ws = gspread_retry(ss.add_worksheet, title=user_name, rows="1000", cols="20")
            gspread_retry(ws.append_row, USER_HEADER)
            return ws
        except Exception as e:
            if "already exists" in str(e):
                ws = gspread_retry(ss.worksheet, user_name)
            else: raise e

    try:
        curr_h = gspread_retry(ws.row_values, 1)
        if len(curr_h) < len(USER_HEADER) or "시간수당" not in curr_h or curr_h[3] != "item1":
            gspread_retry(ws.update, range_name=f"A1:{chr(ord('A')+len(USER_HEADER)-1)}1", values=[USER_HEADER])
    except: pass
    return ws
@st.cache_data(ttl=60)
def load_data_from_gsheet(user_name):
    try:
        sheet = get_user_worksheet(user_name)
        data = gspread_retry(sheet.get_all_values)
        if len(data) < 2: return pd.DataFrame(columns=USER_HEADER)
        df = pd.DataFrame(data[1:], columns=data[0])
        
        # 컬럼 부족 시 보정 (구버전 데이터 호환)
        for col in USER_HEADER:
            if col not in df.columns: df[col] = 0 if col in ["현금", "카드", "카드제외", "기타", "기타지급"] else ""
            
        num_cols = ["인센티브", "시간수당", "item1", "item2", "item3", "item4", "item5", "item6", "item7", "합계", "현금", "카드", "카드제외", "기타", "기타지급"]
        for c in num_cols:
            if c in df.columns: df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ""), errors='coerce').fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}") # 디버깅용 Error 표시
        return pd.DataFrame(columns=USER_HEADER)

def save_to_gsheet(user_name, df_row):
    try:
        sheet = get_user_worksheet(user_name)
        # 헤더를 가져와서 컬럼 위치 파악 (현장 시트 상태 대응)
        header = gspread_retry(sheet.row_values, 1)
        if not header: header = USER_HEADER
        
        # 날짜 열 위치 찾기
        d_idx = header.index("날짜") + 1 if "날짜" in header else 2
        date_col = gspread_retry(sheet.col_values, d_idx)
        
        idx = -1; existing_row = {}
        target_date = df_row['날짜']
        
        if target_date in date_col:
            idx = date_col.index(target_date) + 1
            row_data = gspread_retry(sheet.row_values, idx)
            # 현재 시트의 헤더 구조에 맞춰 기존 데이터 매핑
            existing_row = {header[k]: row_data[k] for k in range(min(len(header), len(row_data)))}
        
        # 2. 데이터 병합 (기존 데이터 + 새 데이터)
        merged_row = existing_row.copy()
        merged_row.update(df_row)
        
        # 3. 저장할 리스트 생성 (USER_HEADER 순으로 저장하되 시트 헤더가 다를 경우 대비하여 보수적 처리)
        # 기본적으로 USER_HEADER 정의된 순서대로 시트에 기록됨
        vals = [format_curr(merged_row.get(h, 0)) if h in ["인센티브", "시간수당", "합계", "현금", "카드", "카드제외", "기타", "기타지급"] or "item" in h else merged_row.get(h, "") for h in USER_HEADER]
        
        if idx != -1: gspread_retry(sheet.update, range_name=f"A{idx}:{chr(ord('A')+len(USER_HEADER)-1)}{idx}", values=[vals])
        else: gspread_retry(sheet.append_row, vals)
        return True
    except Exception as e:
        st.error(f"저장 실패: {e}")
        return False
    finally: load_data_from_gsheet.clear()

# --- [New] 공제 내역 별도 저장 로직 ---
DEDUCT_HEADER = ["Month", "User", "Cash", "Card", "CardDeduct", "Etc", "EtcAdd", "CardDetail", "UpdatedAt", "EtcAddDesc"]

def get_deduction_worksheet():
    ss = get_spreadsheet()
    try:
        ws = gspread_retry(ss.worksheet, "Deductions"); curr_h = gspread_retry(ws.row_values, 1)
        if len(curr_h) < len(DEDUCT_HEADER):
             gspread_retry(ws.update, range_name=f"A1:{chr(ord('A')+len(DEDUCT_HEADER)-1)}1", values=[DEDUCT_HEADER])
        return ws
    except:
        ws = gspread_retry(ss.add_worksheet, title="Deductions", rows="1000", cols="15")
        gspread_retry(ws.append_row, DEDUCT_HEADER); return ws

def load_monthly_deduction(user_name, yyyy_mm):
    try:
        ws = get_deduction_worksheet(); rows = gspread_retry(ws.get_all_values)
        if len(rows) < 2: return {}
        # 헤더 매핑
        hd = rows[0]
        target_row = {}
        for r in rows[1:]:
            if len(r) > 1 and r[0] == yyyy_mm and r[1] == user_name:
                target_row = {hd[i]: r[i] for i in range(min(len(hd), len(r)))}
                break
        
        # [New] 이번 달 카드 상세가 없으면, 가장 최근 달의 카드 상세를 가져옴 (Carry Over)
        if not target_row.get("CardDetail"):
            # 날짜순 정렬 (최신순)
            sorted_rows = sorted([r for r in rows[1:] if len(r) > 1 and r[1] == user_name and r[0] < yyyy_mm], key=lambda x: x[0], reverse=True)
            if sorted_rows:
                # 가장 최근 데이터의 CardDetail만 복사
                prev_row = {hd[i]: sorted_rows[0][i] for i in range(min(len(hd), len(sorted_rows[0])))}
                if prev_row.get("CardDetail"):
                    target_row["CardDetail"] = prev_row["CardDetail"]
                    # 주의: CardDeduct(제외 총액)는 가져오지 않음 (실제 금액은 매달 다를 수 있으므로? 아니면 템플릿이면 금액도?)
                    # "한번 입력하면 그대로 유지" -> 금액 포함 유지
                    # DetailStr에 금액도 포함되어 있으므로, 파싱하면 금액도 복구됨.
                    # 다만 CardDeduct 값 자체는 DB에만 저장된 합계이므로, 로드 시점에는 DetailStr만 있으면 됨.
                    
        return target_row
    except: return {}

def save_monthly_deduction(user_name, yyyy_mm, data_dict):
    try:
        ws = get_deduction_worksheet(); rows = ws.get_all_values(); idx = -1
        for i, r in enumerate(rows):
            if len(r) > 1 and r[0] == yyyy_mm and r[1] == user_name: idx = i + 1; break
        
        # 기본 데이터 구성
        current_time = get_now_kst().strftime("%Y-%m-%d %H:%M:%S")
        vals = [
            yyyy_mm, user_name, 
            data_dict.get("Cash", 0), 
            data_dict.get("Card", 0), 
            data_dict.get("CardDeduct", 0), 
            data_dict.get("Etc", 0), 
            data_dict.get("EtcAdd", 0), 
            data_dict.get("CardDetail", ""), 
            current_time,
            data_dict.get("EtcAddDesc", "")
        ]
        
        if idx != -1: gspread_retry(ws.update, range_name=f"A{idx}:{chr(ord('A')+len(DEDUCT_HEADER)-1)}{idx}", values=[vals])
        else: gspread_retry(ws.append_row, vals)
        return True
    except Exception as e: return False
    finally: load_data_from_gsheet.clear()

def delete_from_gsheet(user_name, date_str):
    try:
        sheet = get_user_worksheet(user_name)
        date_col = gspread_retry(sheet.col_values, 2)
        if date_str in date_col:
            idx = date_col.index(date_str) + 1
            gspread_retry(sheet.delete_rows, idx)
            return True
        return False
    except: return False
    finally: load_data_from_gsheet.clear()

def get_safe_date(y, m, d): ld = calendar.monthrange(y, m)[1]; return date(y, m, min(safe_int(d, 1), ld))
def get_now_kst(): return datetime.now(timezone.utc) + timedelta(hours=9)

def normalize_end_time(val, default="20:00"):
    valid_times = [f"{h}:{m:02d}" for h in range(20, 24) for m in range(0, 60, 10)] + ["24:00"]
    val = str(val or default).strip()
    return val if val in valid_times else default

def reset_daily_entry_state(row=None):
    row = row if row is not None else {}
    inc_val = safe_int(row.get("인센티브", 0))
    st.session_state.inc_sum = inc_val

    restored_his = []
    remark = str(row.get("비고", ""))
    if "|" in remark:
        try:
            hist_str = remark.split("|")[-1].strip()
            if hist_str:
                restored_his = [{"val": safe_int(x)} for x in hist_str.split("+") if x.strip()]
        except:
            pass
    if not restored_his and inc_val > 0:
        restored_his = [{"val": inc_val}]

    st.session_state.inc_his = restored_his
    st.session_state.inc_input_field = 0
    for i in range(7):
        st.session_state[f"it_input_{i}"] = safe_int(row.get(f"item{i+1}", 0))
    st.session_state.sel_etime_main = normalize_end_time(row.get("퇴근시간", "20:00"))

@st.cache_data(ttl=300)
def to_excel_bytes(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
    return output.getvalue()

# --- 세션 초기화 및 로그인 ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False

@st.cache_data(ttl=600)
def get_staff_list_fixed():
    try:
        sheet = get_config_worksheet(); names = gspread_retry(sheet.col_values, 1)[1:]
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

    # [Fix] st.form 테두리 제거 CSS 적용됨 -> 엔터키 로그인 지원 + 깔끔한 디자인
    with st.form("login_form"):
        user_id = st.selectbox("직원 선택", options=STAFF_LIST)
        user_pw = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("입장", use_container_width=True, key="login_btn")

    if submitted:
        # [UX] 로딩 표시 변경 적용 (st.spinner with custom CSS)
        with st.spinner("로딩중..."):
            try:
                cfg = load_staff_salary_config(user_id)
            except: cfg = None
            
            if cfg is None:
                st.error("설정 정보를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.")
                load_staff_salary_config.clear() # Cache clear on failure
                st.stop()
                
            saved_hash = cfg.get("password_hash", "")
        
        if not saved_hash:
            default_pw = "102030" if user_id == "태완" else "0000"
            if user_pw == default_pw:
                update_password(user_id, hash_password(user_pw))
                st.session_state.logged_in = True; st.session_state.user_name = user_id; st.rerun()
            else: st.error("초기 비밀번호가 잘못되었습니다. (태완:102030, 직원:0000)")
        else:
            if check_password(user_pw, saved_hash):
                st.session_state.logged_in = True; st.session_state.user_name = user_id; st.rerun()
            else: st.error("비밀번호가 일치하지 않습니다.")

    # [New] 업데이트 히스토리 데이터 (DB 없이 코드로 관리)
    UPDATE_HISTORY = [
        {"ver": "v4.5.4", "date": "2026-01-23", "content": "• <b>[안정성]</b> 시트 생성 충돌(Race Condition) 완벽 해결<br>• <b>[최적화]</b> 품목 및 인센티브 입력 렉 제거 (Form 적용)<br>• <b>[업데이트]</b> 로그인 안전 장치 및 버전 정보 갱신"},
        {"ver": "v4.5.3", "date": "2026-01-18", "content": "• <b>[디자인]</b> 인센티브 & 품목 입력 통합 카드 디자인 적용<br>• <b>[모바일]</b> 품목 2단 배열 & 버튼 가로 정렬<br>• <b>[UI]</b> 날짜 선택 및 정렬 개선"},
        {"ver": "v4.5.2", "date": "2026-01-18", "content": "• <b>[디자인]</b> 업데이트 내역 뷰 개선 (카드형 스타일)<br>• <b>[로그인]</b> 엔터키 지원 + 테두리 없는 깔끔한 폼 적용"},
        {"ver": "v4.5.1", "date": "2026-01-18", "content": "• <b>[편의성]</b> 로그인 시 엔터(Enter) 키로 입장 가능"},
        {"ver": "v4.5.0", "date": "2026-01-18", "content": "• <b>[동기화]</b> 날짜 선택 시 하단 리포트 즉시 자동 변경<br>• <b>[UI]</b> 월간 공제 창 '접힘' 기본값 적용<br>• <b>[UI]</b> 리포트 기간 표기 직관적 개선 ('월급' 텍스트 제거)"},
        {"ver": "v4.4.2", "date": "2026-01-18", "content": "• <b>[안정성]</b> 데이터 로딩/로그인 에러 방지 안전장치 추가<br>• <b>[기능]</b> 일일 탭 리포트 기간 선택 기능 추가"},
        {"ver": "v4.4.0", "date": "2026-01-18", "content": "• <b>[UI 혁신]</b> '일일 입력'과 '월간 정산' 탭 분리<br>• <b>[기능]</b> 카드 공제 상세 입력(내역별 추가) 기능"},
        {"ver": "v4.2.0", "date": "2026-01-17", "content": "• <b>[기능]</b> 관리자 설정 페이지 강화<br>• <b>[수정]</b> 초기 비밀번호 오류 해결"},
    ]

    st.markdown("---")
    st.caption("✨ 최근 업데이트")
    
    # [Design Fix] 깔끔한 히스토리 디자인
    st.markdown(f'''
    <div class="history-card" style="border-left-color: #007bff; background: #f0f7ff;">
        <span class="ver-badge" style="background: #e6f0ff; color: #0056b3;">NEW {UPDATE_HISTORY[0]['ver']}</span>
        <span style="font-size:11px; color:#999; margin-left:5px;">{UPDATE_HISTORY[0]['date']}</span>
        <div style="margin-top:5px; font-size:12px; color:#444; line-height:1.4;">{UPDATE_HISTORY[0]['content']}</div>
    </div>
    ''', unsafe_allow_html=True)
    
    with st.expander("� 지난 업데이트 내역"):
        for h in UPDATE_HISTORY[1:]:
             st.markdown(f'''
            <div class="history-card">
                <span class="ver-badge">{h['ver']}</span>
                <span style="font-size:11px; color:#999; margin-left:5px;">{h['date']}</span>
                <div style="margin-top:5px; font-size:12px; color:#555; line-height:1.4;">{h['content']}</div>
            </div>
            ''', unsafe_allow_html=True)
    st.stop()

# 최신 설정 로드
user_name = st.session_state.user_name
try:
    sal_cfg = load_staff_salary_config(user_name)
    if sal_cfg is None: raise Exception("Config Load Failed")
except:
    st.error("설정 정보를 불러오지 못했습니다. (네트워크 지연)")
    if st.button("🔄 설정 다시 불러오기 (Retry)"):
        load_staff_salary_config.clear()
        st.rerun()
    st.stop()

is_ov_staff = user_name in ["태완", "남근"]
df_all = load_data_from_gsheet(user_name)

def render_monthly_report(df_all, target_date, sal_cfg, is_ov_staff, user_name, readonly=False):
    """
    월간 정산 리포트를 렌더링하는 함수 (재사용 가능)
    readonly=True이면 입력 UI 없이 리포트만 출력
    """
    # 1. 정산 기간 계산
    year, month = target_date.year, target_date.month
    s_d = safe_int(sal_cfg['start_day'], 13)
    
    if target_date.day >= s_d: 
        s_dt = date(year, month, s_d)
        # 익월 정산일 전날까지
        next_m = month + 1 if month < 12 else 1
        next_y = year if month < 12 else year + 1
        e_dt = date(next_y, next_m, s_d) - timedelta(days=1)
    else:
        # 전월 정산일부터
        prev_m = month - 1 if month > 1 else 12
        prev_y = year if month > 1 else year - 1
        s_dt = date(prev_y, prev_m, s_d)
        e_dt = date(year, month, s_d) - timedelta(days=1)

    # [Fix] 항상 기간 표시 (User Request: "일일 입력 하단 리포트에 기간도 동일하게 넣어줘")
    st.markdown(f":grey_exclamation: **정산 기간:** {s_dt.month}월 {s_dt.day}일 ~ {e_dt.month}월 {e_dt.day}일")

    # 2. 데이터 필터링
    if df_all.empty:
        st.info("📉 저장된 데이터가 없습니다.")
        return

    df_all['date_dt'] = pd.to_datetime(df_all['날짜']).dt.date
    p_df = df_all[(df_all['date_dt'] >= s_dt) & (df_all['date_dt'] <= e_dt)].sort_values("날짜")

    if p_df.empty:
        st.info("📉 해당 기간에 조회된 데이터가 없습니다.")
        return

    # 3. 급여 계산
    b, ins = safe_int(sal_cfg['base_salary']), safe_int(sal_cfg['insurance'])
    it_n, it_p = sal_cfg["item_names"], sal_cfg["item_prices"]

    if sal_cfg.get("apply_global"):
        t_inc = safe_int(p_df["인센티브"].sum())
        t_ov = safe_int(p_df["시간수당"].sum())
        t_items = sum([safe_int(p_df[f"item{i+1}"].sum()) * safe_int(it_p[i]) for i in range(7)])
        total_sum_val = t_inc + t_ov + t_items
        t_items = sum([safe_int(p_df[f"item{i+1}"].sum()) * safe_int(it_p[i]) for i in range(7)])
        total_sum_val = t_inc + t_ov + t_items
    else:
        total_sum_val = safe_int(p_df["합계"].sum()); t_inc = safe_int(p_df["인센티브"].sum()); t_ov = safe_int(p_df["시간수당"].sum()); t_items = total_sum_val - t_inc - t_ov

    # [Refactor] 공제/지급 내역 별도 로드 (Deductions 시트)
    deduct_key = e_dt.strftime("%Y-%m")
    deduct_data = load_monthly_deduction(user_name, deduct_key)
    
    t_cash = safe_int(deduct_data.get("Cash"))
    t_card = safe_int(deduct_data.get("Card"))
    t_card_ex = safe_int(deduct_data.get("CardDeduct"))
    t_etc = safe_int(deduct_data.get("Etc"))
    t_etc_add = safe_int(deduct_data.get("EtcAdd"))
    t_etc_add_desc = deduct_data.get("EtcAddDesc", "")

    # [핵심 변경] 카드 실 공제액 = 카드 총액 - 카드 제외액
    t_card_real = t_card - t_card_ex
    final_pay = int(b + total_sum_val - ins - t_cash - t_card_real - t_etc + t_etc_add)
    combined_inc = t_inc + t_items + t_ov
    subtotal_pay = int(b + total_sum_val - ins)

    # 4. 리포트 요약 HTML 생성
    summary_html = f'<div class="calc-detail">'
    summary_html += f'<div class="calc-line"><span>기본급</span> <span>+ {b:,}원</span></div>'
    summary_html += f'<div class="calc-line"><span>인센티브</span> <span>+ {combined_inc:,}원</span></div>'
    summary_html += f'<div class="calc-line" style="color:red;"><span>보험료</span> <span>- {ins:,}원</span></div>'
    
    if t_cash > 0 or t_card_real > 0 or t_etc > 0 or t_etc_add > 0:
         summary_html += f'<div style="border-top:1px dashed #ddd; margin:8px 0; padding-top:8px;"></div>'
         summary_html += f'<div class="calc-line" style="color:#555;"><span>급여 합계</span> <span>{subtotal_pay:,}원</span></div>'
         if t_cash > 0: summary_html += f'<div class="calc-line" style="color:#ef6c00;"><span>매장 현금</span> <span>- {t_cash:,}원</span></div>'
         if t_card_real > 0: summary_html += f'<div class="calc-line" style="color:#ef6c00;"><span>카드 사용 ({t_card:,}-{t_card_ex:,})</span> <span>- {t_card_real:,}원</span></div>'
         if t_etc > 0: summary_html += f'<div class="calc-line" style="color:#ef6c00;"><span>기타 공제</span> <span>- {t_etc:,}원</span></div>'
         if t_etc_add > 0: 
             desc_text = f" ({t_etc_add_desc})" if t_etc_add_desc else ""
             summary_html += f'<div class="calc-line"><span>기타 지급{desc_text}</span> <span>+ {t_etc_add:,}원</span></div>'

    summary_html += f'<div class="calc-total"><div class="calc-line"><span>💰 실 수령액</span> <span>{final_pay:,}원</span></div></div>'
    summary_html += '</div>'
    st.markdown(summary_html, unsafe_allow_html=True)

    # 5. 상세 테이블 출력
    h_base = ["날짜", "인센"] + (["수당"] if is_ov_staff else []); hds = h_base + [n[:2] for n in it_n] + ["합계"]
    r_html, i_sums = "", [0]*7
    for _, r in p_df.iterrows():
        md = datetime.strptime(r['날짜'], '%Y-%m-%d').strftime('%m/%d')
        if r['비고'] == "휴무": r_html += f"<tr><td style='font-weight:bold;'>{md}</td><td colspan='{len(hds)-1}' style='color:orange;'>🛌휴무</td></tr>"
        else:
            row_inc, row_ov = safe_int(r['인센티브']), safe_int(r.get('시간수당', 0))
            for i in range(1, 8): i_sums[i-1] += safe_int(r[f'item{i}'])
            row_total = (row_inc + row_ov + sum([safe_int(r[f'item{i+1}']) * safe_int(it_p[i]) for i in range(7)])) if sal_cfg.get("apply_global") else safe_int(r['합계'])
            disp_inc, ov_td = (row_inc if is_ov_staff else row_inc + row_ov), (f"<td>{row_ov:,}</td>" if is_ov_staff else "")
            it_tds = "".join([f"<td>{safe_int(r[f'item{i}'])}</td>" for i in range(1, 8)])
            r_html += f"<tr><td style='font-weight:bold;'>{md}</td><td>{disp_inc:,}</td>{ov_td}{it_tds}<td style='color:blue;'>{row_total:,}</td></tr>"
    
    r_html += f"<tr class='total-row'><td>합계</td><td>{(t_inc if is_ov_staff else t_inc + t_ov):,}</td>" + (f"<td>{t_ov:,}</td>" if is_ov_staff else "") + "".join([f"<td>{s}</td>" for s in i_sums]) + f"<td>{total_sum_val:,}</td></tr>"
    st.markdown(f'<table class="report-table"><tr>{"".join([f"<th>{x}</th>" for x in hds])}</tr>{r_html}</table>', unsafe_allow_html=True)

# --- 화면 전환 ---
# st.tabs는 모든 탭 내용을 매번 렌더링하므로 월 선택 시 일부 브라우저에서
# 이전 화면 아래에 새 화면이 이어붙는 현상이 생길 수 있다.
main_view = st.radio(
    "화면 선택",
    ["📝 일일 입력", "📊 월간 정산"],
    horizontal=True,
    label_visibility="collapsed",
    key="main_view",
)

if main_view == "📝 일일 입력":
    # --- 메인 화면 변수 및 날짜 처리 ---
    st.markdown(f'<div class="version-tag">{SW_VERSION} (Latest)</div>', unsafe_allow_html=True)
    st.write(f"### 💼 {user_name}님 실적")
    
    # [Revert] 깔끔한 기본 달력 폼으로 복귀 (요일 텍스트 제거)
    sel_date = st.date_input("날짜", value=date.today(), label_visibility="collapsed", key="sel_date")
    str_date = sel_date.strftime("%Y-%m-%d")

    # [Reorder] 저장 로그(상태 카드)를 먼저 표시
    existing = df_all[df_all["날짜"] == str_date] if not df_all.empty else pd.DataFrame()
    if not existing.empty: st.markdown(f'<div class="status-card status-saved">✅ {str_date} 데이터가 저장되어 있습니다</div>', unsafe_allow_html=True)
    else: st.markdown(f'<div class="status-card status-missing">⚠️ {str_date} 데이터가 아직 등록되지 않았습니다</div>', unsafe_allow_html=True)

    # [Move] 최근 7일 기록 (상단 이동) & [UI] 요일 추가
    st.write("**📅 최근 7일 기록**")
    w_box = '<div class="weekly-box" style="display:flex; justify-content:space-between;">'
    wk_days = ["(월)", "(화)", "(수)", "(목)", "(금)", "(토)", "(일)"]
    for i in range(6, -1, -1):
        td = get_now_kst().date() - timedelta(days=i); ts = td.strftime("%Y-%m-%d"); dd = df_all[df_all["날짜"] == ts] if not df_all.empty else pd.DataFrame()
        # [Design Change] 2번 스타일: 언더바 (Underbar)
        bar_color = "#e9ecef" # Default (Empty)
        if not dd.empty:
            if dd.iloc[0]['비고'] == "휴무": bar_color = "#fd7e14" # Orange
            else: bar_color = "#198754" # Green
        
        # 오늘 날짜 강조
        bg = "background:#cfe2ff; border:1px solid #9ec5fe; border-radius:8px;" if ts == str_date else "border:1px solid transparent;"
        d_str = wk_days[td.weekday()] # 요일
        
        w_box += f'<div style="text-align:center; padding:4px 2px; width:13.5%; {bg}"><div style="font-size:12px; font-weight:600; color:#333; margin-bottom:2px;">{td.day}일<br>{d_str}</div><div style="width:24px; height:4px; border-radius:2px; background-color:{bar_color}; margin: 5px auto;"></div></div>'
    st.markdown(w_box + '</div>', unsafe_allow_html=True); st.divider()

    # [v4.0.1] 세션 초기값 보장 로직
    if "current_date" not in st.session_state: st.session_state.current_date = str_date
    if "inc_input_field" not in st.session_state: st.session_state.inc_input_field = 0
    if "inc_history_cache" not in st.session_state: st.session_state.inc_history_cache = {}

    # 날짜 변경 감지 및 초기화
    if st.session_state.current_date != str_date:
        st.session_state.current_date = str_date # [Fix] 현재 날짜 상태 업데이트 (무한 루프 방지)
        ext_data = df_all[df_all["날짜"] == str_date] if not df_all.empty else pd.DataFrame()
        
        # 상태 강제 업데이트: '비고' 란에서 상세 내역 파싱 (format: "메모 | 10000+20000")
        inc_val = safe_int(ext_data.iloc[0]["인센티브"]) if not ext_data.empty else 0
        st.session_state.inc_sum = inc_val
        
        # 상세 내역 복원 로직
        restored_his = []
        if not ext_data.empty:
            remark = str(ext_data.iloc[0]["비고"])
            if "|" in remark:
                try:
                     # "정상 | 10000+20000" -> "10000+20000"
                     hist_str = remark.split("|")[-1].strip()
                     if hist_str:
                         restored_his = [{"val": safe_int(x)} for x in hist_str.split("+") if x.strip()]
                except: pass
        
        # 복원된 내역이 없지만 합계가 있다면 (구버전 데이터 호환) -> 합계 1개로 처리
        if not restored_his and inc_val > 0:
            restored_his = [{"val": inc_val}]
            
        st.session_state.inc_his = restored_his
            
        st.session_state.inc_input_field = 0 # 입력필드 리셋
        for i in range(7):
            val = safe_int(ext_data.iloc[0][f"item{i+1}"]) if not ext_data.empty else 0
            st.session_state[f"it_input_{i}"] = val
        
        # 퇴근 시간 초기화
        e_val = ext_data.iloc[0]["퇴근시간"] if not ext_data.empty else "20:00"
        st.session_state.sel_etime_main = normalize_end_time(e_val)
        # st.rerun() # [v4.5.3] 불필요한 rerun 제거 (렉 감소 및 루프 방지)

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
        st.divider()
        if st.button("로그아웃", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    # --- 휴무 및 기록 출력 ---
    st.markdown("##### ⚡ 빠른 동작")
    with st.container(key="fast_btns"):
        b_c1, b_c2, b_c3 = st.columns([1, 1, 1])
        
        with b_c1:
            if st.button("🛌 휴무", use_container_width=True, help="오늘 휴무로 기록합니다."):
                row = {"직원명": user_name, "날짜": str_date, "인센티브": 0, "시간수당": 0, "퇴근시간": "휴무", "item1":0, "item2":0, "item3":0, "item4":0, "item5":0, "item6":0, "item7":0, "합계": 0, "비고": "휴무", "입력시간": get_now_kst().strftime("%H:%M:%S")}
                if save_to_gsheet(user_name, row):
                    reset_daily_entry_state(row)
                    st.rerun()
            
        with b_c2:
            if st.button("🚫 인센없음", use_container_width=True, help="인센티브 0원으로 기록합니다."):
                 row = {"직원명": user_name, "날짜": str_date, "인센티브": 0, "시간수당": 0, "퇴근시간": "20:00", "item1":0, "item2":0, "item3":0, "item4":0, "item5":0, "item6":0, "item7":0, "합계": 0, "비고": "인센없음", "입력시간": get_now_kst().strftime("%H:%M:%S")}
                 if save_to_gsheet(user_name, row):
                    reset_daily_entry_state(row)
                    st.rerun()

        with b_c3:
            if st.button("🗑️ 삭제", type="primary", use_container_width=True, help="현재 날짜의 데이터를 삭제합니다."):
                if delete_from_gsheet(user_name, str_date):
                    reset_daily_entry_state()
                    st.success("데이터 삭제 완료"); time.sleep(0.5); st.rerun()
                else:
                     st.error("삭제 실패 (데이터가 없거나 통신 오류)")

    # --- 수당 및 인센티브 ---
    # [Design Fix] 통합 디자인 적용 (모바일 최적화 & 정렬 통일)
    st.markdown("""
    <style>
    .st-key-inc_card {
        background-color: #f8f9fa;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #e9ecef;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .ui-label {
        color: #666; font-size: 14px; margin-bottom: 4px; font-weight: 500;
    }
    .ui-value {
        color: #007bff; font-size: 24px; font-weight: bold;
    }
    .ui-sub-box {
        background-color: #eaf4ff;
        border-radius: 8px;
        padding: 12px;
        text-align: center;
        margin-top: 10px;
        border: 1px solid #d0e8ff;
    }
    .ui-sub-label {
        font-size: 13px; color: #555; margin-bottom: 2px;
    }
    .ui-sub-val {
        font-size: 18px; font-weight: bold; color: #0056b3;
    }
    
    /* [Mobile] 인센티브 버튼 가로 1열 강제 정렬 */
    @media (max-width: 640px) {
        .st-key-incen_buttons [data-testid="stHorizontalBlock"] {
            display: grid !important;
            grid-template-columns: 1fr 1fr 1fr !important;
            gap: 8px !important;
        }
        .st-key-incen_buttons [data-testid="stColumn"] {
            width: auto !important;
            flex: 1 !important;
        }
        .st-key-incen_buttons button {
            padding: 0.25rem 0.5rem !important;
        }
    }
    
    /* [UI Fix] 인센티브 상세 내역 폰트 확대 */
    .inc-item {
        font-size: 14px !important; /* 기존보다 확대 */
        font-weight: 500 !important;
        color: #333 !important;
        margin-right: 8px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    with st.container(key="inc_card"):
        st.markdown('<div class="section-header" style="margin-top:0;">💰 인센티브</div>', unsafe_allow_html=True)
        
        # [BugFix] 초기 로드시에도 '비고'란을 파싱하여 인센티브 상세 내역 복원 (합쳐지는 현상 수정)
        if "inc_sum" not in st.session_state:
             st.session_state.inc_sum = safe_int(existing.iloc[0]["인센티브"]) if not existing.empty else 0
             
             init_his = []
             if not existing.empty:
                 remark = str(existing.iloc[0]["비고"])
                 if "|" in remark:
                     try:
                         hist_str = remark.split("|")[-1].strip()
                         if hist_str:
                             init_his = [{"val": safe_int(x)} for x in hist_str.split("+") if x.strip()]
                     except: pass
             
             # 파싱 실패했거나 구버전 데이터라면 합계만 넣음
             if not init_his and st.session_state.inc_sum > 0:
                 init_his = [{"val": st.session_state.inc_sum}]
                 
             st.session_state.inc_his = init_his

        # [Refactor] 통합 폼 시작 (Time + Incentive + Item + Save)
        with st.form("daily_input_form", border=False):
            
            # --- 1. 시간 수당 섹션 ---
            ov_pay, sel_etime = 0, "20:00"
            if is_ov_staff:
                # 퇴근 시간 선택 (폼 내부)
                etime_list = [f"{h}:{m:02d}" for h in range(20, 24) for m in range(0, 60, 10)] + ["24:00"]
                e_val = normalize_end_time(existing.iloc[0]["퇴근시간"] if not existing.empty else "20:00")
                e_idx = etime_list.index(e_val) if e_val in etime_list else 0
                sel_etime = st.selectbox("퇴근 시간", options=etime_list, index=e_idx, key="sel_etime_main")
                
                # 시간수당 계산 (현재 렌더링 시점의 값)
                h, m = map(int, sel_etime.split(":")) if sel_etime != "24:00" else (24, 0)
                ov_min = max(0, (h * 60 + m) - 1200); ov_pay = (ov_min // 10) * sal_cfg["overtime_rate"]
                
                st.markdown(f"""
                <div class="ui-sub-box">
                    <div class="ui-sub-label">시간수당</div>
                    <div class="ui-sub-val">{ov_pay:,}원</div>
                </div>
                <hr style='margin: 15px 0; border: 0; border-top: 1px dashed #ddd;'>
                """, unsafe_allow_html=True)

            # --- 2. 인센티브 섹션 ---
            st.markdown(f"""
            <div style="text-align:center; margin-bottom:15px;">
                <div class="ui-label">인센티브 합계</div>
                <div class="ui-value">{st.session_state.inc_sum:,}원</div>
            </div>
            """, unsafe_allow_html=True)

            if st.session_state.inc_his:
                h_html = '<div class="inc-history-box" style="justify-content:center; margin-bottom:15px;">'
                for i, item in enumerate(st.session_state.inc_his): h_html += f'<span class="inc-item">#{i+1} {item["val"]:,}</span>'
                st.markdown(h_html + '</div>', unsafe_allow_html=True)

            st.number_input("추가 금액 입력", 0, step=1000, label_visibility="collapsed", key="inc_input_field", placeholder="금액 입력")
            
            with st.container():
                b1, b2, b3 = st.columns(3)
            
            def add_inc():
                val = st.session_state.inc_input_field
                if val > 0:
                    st.session_state.inc_sum += val
                    st.session_state.inc_his.append({"val": val})
                    st.session_state.inc_input_field = 0

            # 인센티브 버튼 (Submit 동작)
            b1.form_submit_button("➕ 추가", use_container_width=True, type="primary", on_click=add_inc)
            b2.form_submit_button("↩️ 취소", use_container_width=True, on_click=lambda: (st.session_state.update({"inc_sum": st.session_state.inc_sum - (st.session_state.inc_his.pop()['val'] if st.session_state.inc_his else 0)})))
            b3.form_submit_button("🧹 리셋", use_container_width=True, on_click=lambda: (st.session_state.update({"inc_sum": 0, "inc_his": []})))

            # --- 3. 품목 수량 섹션 ---
            # 스타일은 위에서 정의됨 (.st-key-item_card)
            with st.container(key="item_card"):
                st.markdown('<div class="section-header" style="margin-top:20px;">📦 품목 수량 입력</div>', unsafe_allow_html=True)
                
                # 모바일 레이아웃 CSS 재적용 (Form 내부라 동작 모호할 수 있으나 container 내부라 안전)
                st.markdown("""
                <style>
                @media (max-width: 640px) {
                    .st-key-daily_grid [data-testid="stHorizontalBlock"] { display: grid !important; grid-template-columns: 1fr 1fr !important; gap: 10px !important; }
                    .st-key-daily_grid [data-testid="stColumn"] { width: auto !important; flex: unset !important; }
                    .st-key-daily_grid [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child:nth-child(odd) { grid-column: span 2 !important; }
                }
                </style>
                """, unsafe_allow_html=True)
                
                it_n, it_p = sal_cfg["item_names"], sal_cfg["item_prices"]
                for i in range(7):
                    if f"it_input_{i}" not in st.session_state:
                         st.session_state[f"it_input_{i}"] = safe_int(existing.iloc[0][f"item{i+1}"]) if not existing.empty else 0

                with st.container(key="daily_grid"):
                     for i in range(0, 6, 2):
                         c1, c2 = st.columns(2)
                         with c1: st.number_input(it_n[i], 0, key=f"it_input_{i}")
                         with c2: st.number_input(it_n[i+1], 0, key=f"it_input_{i+1}")
                     st.number_input(it_n[6], 0, key="it_input_6")
            
            st.write("")
            
            # --- 4. 최종 저장 로직 ---
            def save_final_cb(u_name, s_date, cfg, exist_df):
                # Callback 시점의 최신 State를 읽어야 함 (Form Widget 값은 Submit 시 session_state에 반영됨)
                cts = [st.session_state[f"it_input_{i}"] for i in range(7)]
                
                # 시간수당 재계산 (최신 선택값 기준)
                s_etime = normalize_end_time(st.session_state.get("sel_etime_main", "20:00"))
                h, m = map(int, s_etime.split(":")) if s_etime != "24:00" else (24, 0)
                ov_min = max(0, (h * 60 + m) - 1200)
                o_pay = (ov_min // 10) * cfg["overtime_rate"]
                
                tot_inc = st.session_state.inc_sum
                
                # [Fix] 인센티브 입력 필드에 값이 남아있으면 '추가'를 안 눌렀어도 합쳐서 저장
                curr_input = safe_int(st.session_state.get("inc_input_field", 0))
                remark_base = "정상"
                final_his = st.session_state.inc_his.copy()
                
                if curr_input > 0:
                    tot_inc += curr_input
                    final_his.append({"val": curr_input})
                    st.session_state.inc_sum = tot_inc # 세션 상태도 업데이트
                    st.session_state.inc_his = final_his
                    st.session_state.inc_input_field = 0 # 입력 필드 비우기
                
                tot_val = tot_inc + o_pay + sum([safe_int(c) * safe_int(p) for c, p in zip(cts, cfg["item_prices"])])
                
                if final_his:
                    valid_vals = [str(item['val']) for item in final_his if item['val'] != 0]
                    if valid_vals: remark_base += " | " + "+".join(valid_vals)
                        
                row = {"직원명": u_name, "날짜": s_date, "인센티브": tot_inc, "시간수당": o_pay, "퇴근시간": s_etime, 
                       "item1": cts[0], "item2": cts[1], "item3": cts[2], "item4": cts[3], 
                       "item5": cts[4], "item6": cts[5], "item7": cts[6], 
                       "합계": tot_val, "비고": remark_base, "입력시간": get_now_kst().strftime("%H:%M:%S")}
                
                # 기존 데이터 중 보존해야 할 항목들 (공제 내역 등)
                for k in ["현금", "카드", "카드제외", "기타", "카드상세", "기타지급"]:
                    if k in exist_df.columns and not exist_df.empty: row[k] = exist_df.iloc[0][k]
                     
                if save_to_gsheet(u_name, row):
                     st.session_state.sv_msg = f"✅ 데이터가 성공적으로 저장되었습니다! ({get_now_kst().strftime('%H:%M:%S')})"

            st.form_submit_button("✅ 최종 데이터 저장", type="primary", use_container_width=True, 
                      on_click=save_final_cb, 
                      args=(user_name, str_date, sal_cfg, existing))

    if st.session_state.get("sv_msg"):
        st.markdown(f'<div class="save-success">{st.session_state.sv_msg}</div>', unsafe_allow_html=True)
        st.session_state.sv_msg = None

    # [New] 하단 리포트 표시 (조회 전용)
    st.divider()
    st.markdown("##### 📊 이달의 정산 현황 (미리보기)")
    
    # 리포트 월 선택기 (일일 입력 탭용)
    # 1. 옵션 생성 (최근 12개월)
    d_m_opts, d_m_ranges = [], []
    curr = date.today()
    if curr.day >= safe_int(sal_cfg['start_day'], 13): t_st = date(curr.year, curr.month, safe_int(sal_cfg['start_day'], 13))
    else:
        prv = curr.replace(day=1) - timedelta(days=1)
        t_st = get_safe_date(prv.year, prv.month, safe_int(sal_cfg['start_day'], 13))

    for i in range(12):
        st_dt = get_safe_date((t_st - timedelta(days=32*i)).year, (t_st - timedelta(days=32*i)).month, safe_int(sal_cfg['start_day'], 13))
        if i > 0:
            y, m = t_st.year, t_st.month - i
            while m < 1: y -= 1; m += 12
            st_dt = get_safe_date(y, m, safe_int(sal_cfg['start_day'], 13))
        
        ed_dt = get_safe_date((st_dt + timedelta(days=33)).year, (st_dt + timedelta(days=33)).month, safe_int(sal_cfg['start_day'], 13)) - timedelta(days=1)
        # [Fix] 13일~12일 -> 2월 월급 명시 (삭제 요청)
        lbl_m = ed_dt.strftime("%Y년 %m월") 
        d_m_opts.append(lbl_m)
        d_m_ranges.append((st_dt, ed_dt))

    # 2. 날짜 선택(sel_date)에 맞는 월 자동 찾기 & 동기화
    # [Fix] sel_date 변경 시 세션 상태 강제 업데이트
    if "last_sel_date_for_report" not in st.session_state: 
        st.session_state.last_sel_date_for_report = sel_date

    curr_idx = 0
    for i, (s, e) in enumerate(d_m_ranges):
        if s <= sel_date <= e: curr_idx = i; break

    # 날짜가 실제로 바뀌었으면 리포트 선택 인덱스도 강제 변경
    if st.session_state.last_sel_date_for_report != sel_date:
        st.session_state.daily_report_month = curr_idx
        st.session_state.last_sel_date_for_report = sel_date

    # 3. 선택기 표시 (동기화된 index 사용)
    # key가 있으면 index param은 초기 로드에만 영향을 줌. 따라서 위에서 직접 session_state를 수정해야 함.
    sel_r_idx = st.selectbox("리포트 기간 선택", range(len(d_m_opts)), index=curr_idx, format_func=lambda x: d_m_opts[x], key="daily_report_month")
    
    # 4. 렌더링
    r_s_dt, r_e_dt = d_m_ranges[sel_r_idx]
    
    # [Fix] render_monthly_report가 date가 아닌 range를 받도록 수정 필요하거나, 여기서 target_date를 넘겨야 함.
    # 기존 함수는 target_date를 받아서 기간을 내부에서 다시 계산함. -> 비효율적/불일치 발생 가능.
    # 함수를 수정하여 (s_dt, e_dt)를 직접 받도록 오버로딩하거나, target_date를 e_dt ("정산 종료일" 기준)로 넘기면 됨.
    # render_monthly_report 내부 로직: target_date가 s_d보다 작으면 전월, 크면 당월...
    # e_dt (종료일)은 항상 s_d보다 작음 (하루 전이니까). 
    # 예: 1/13~2/12. Start=13. e_dt=2/12.
    # render에 2/12를 넘기면? 12 < 13 -> 전월(1/13~2/12)로 계산됨. Correct.
    render_monthly_report(df_all, r_e_dt, sal_cfg, is_ov_staff, user_name, readonly=True)

    # [New] 엑셀 다운로드 (가장 하단)
    if not df_all.empty:
        st.divider()
        # [Modified] 리포트 기반 데이터 생성 (User Request: 하단 리포트 표 토대로 엑셀 다운로드)
        excel_data = None
        
        # 1. 데이터 필터링 (리포트와 동일한 기간)
        df_all['date_dt'] = pd.to_datetime(df_all['날짜']).dt.date
        p_df = df_all[(df_all['date_dt'] >= r_s_dt) & (df_all['date_dt'] <= r_e_dt)].sort_values("날짜")
        
        # [New] 순수 공제 입력용 행(근무 데이터 없음)은 리포트 표에서 제외
        # 조건: 인센티브=0, 시간수당=0, 모든 item=0 인 경우 제외 (현금/카드 공제만 있는 경우)
        def is_work_day(r):
            if safe_int(r["인센티브"]) != 0: return True
            if safe_int(r.get("시간수당", 0)) != 0: return True
            for k in range(1, 8):
                if safe_int(r[f"item{k}"]) != 0: return True
            if r["비고"] == "휴무": return True
            return False
        
        # [Fix] 리포트 데이터(p_df)에는 필터링 적용하되, 계산 로직(total_sum_val 등)에는 영향 주지 않도록 주의
        # 하지만 계산 로직은 'p_df'가 아닌 'df_all' 또는 별도 합계를 사용하거나
        # p_df를 리포트 표시용으로만 쓰면 됨.
        # 기존 로직 유지 위해: table용 df 분리
        p_df_table = p_df[p_df.apply(is_work_day, axis=1)]
        
        if not p_df_table.empty:
            # 2. 리포트 형식으로 컬럼 구성
            # 날짜, 인센티브, (수당), 품목1~7(이름으로), 합계, 비고
            report_data = []
            it_names = sal_cfg["item_names"]
            it_prices = sal_cfg["item_prices"]
            
            for _, r in p_df_table.iterrows():
                row_dict = {}
                row_dict["날짜"] = r["날짜"]
                row_dict["인센티브"] = safe_int(r["인센티브"])
                if is_ov_staff:
                    row_dict["시간수당"] = safe_int(r.get("시간수당", 0))
                
                # 품목 (이름으로 매핑)
                for i in range(7):
                    row_dict[it_names[i]] = safe_int(r[f"item{i+1}"])
                
                # 합계 계산 (전체적용 옵션 고려)
                if sal_cfg.get("apply_global"):
                    row_inc = safe_int(r["인센티브"])
                    row_ov = safe_int(r.get("시간수당", 0))
                    row_items = sum([safe_int(r[f"item{i+1}"]) * safe_int(it_prices[i]) for i in range(7)])
                    row_dict["합계"] = row_inc + row_ov + row_items
                else:
                    row_dict["합계"] = safe_int(r["합계"])
                
                row_dict["비고"] = r["비고"]
                report_data.append(row_dict)
            
            report_df = pd.DataFrame(report_data)
            excel_data = to_excel_bytes(report_df)
            
            # 파일명에 기간 포함
            f_name = f"{user_name}_정산리포트_{r_s_dt.strftime('%m%d')}-{r_e_dt.strftime('%m%d')}.xlsx"
        else:
             # 데이터가 없을 경우 빈 파일 또는 처리 (여기선 버튼 비활성화 대신 빈 데이터)
             f_name = f"{user_name}_정산리포트_NoData.xlsx"
             excel_data = to_excel_bytes(pd.DataFrame())

        st.download_button(
            label="💾 정산 리포트 엑셀로 다운로드",
            data=excel_data,
            file_name=f_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

# --- 월간 정산 ---
if main_view == "📊 월간 정산":
    st.header("📊 월간 정산 리포트")
    # [Fix] NameError 방지: 탭 내에서 변수 재정의
    s_d, b, ins = safe_int(sal_cfg['start_day'], 13), safe_int(sal_cfg['base_salary']), safe_int(sal_cfg['insurance'])
    it_n, it_p = sal_cfg["item_names"], sal_cfg["item_prices"]
    
    # 월별 옵션 생성 (최근 12개월)
    m_opts, m_ranges = [], []
    curr = date.today()
    
    if curr.day >= s_d: t_st = date(curr.year, curr.month, s_d)
    else:
        prv = curr.replace(day=1) - timedelta(days=1)
        t_st = get_safe_date(prv.year, prv.month, s_d)

    for i in range(12):
        st_dt = get_safe_date((t_st - timedelta(days=32*i)).year, (t_st - timedelta(days=32*i)).month, s_d)
        if i > 0:
            y, m = t_st.year, t_st.month - i
            while m < 1: y -= 1; m += 12
            st_dt = get_safe_date(y, m, s_d)
        
        ed_dt = get_safe_date((st_dt + timedelta(days=33)).year, (st_dt + timedelta(days=33)).month, s_d) - timedelta(days=1)
        lbl_m = ed_dt.strftime("%Y년 %m월") # [Fix] "(월급)" 제거
        m_opts.append(lbl_m)
        m_ranges.append((st_dt, ed_dt))

    st.subheader("🗓️ 정산 월 선택")
    sel_idx = st.selectbox("리포트 기간", range(len(m_opts)), format_func=lambda x: m_opts[x], key="monthly_report_month")
    s_dt, e_dt = m_ranges[sel_idx]
    # [Fix] Duplicate period display removed (Handled by render_monthly_report)

    # 월 공제 및 지급 항목 입력 기능 (카드 상세 포함)
    with st.expander("💳 공제/지급 항목 입력 (매장현금, 카드, 기타)", expanded=True): 
        # [Refactor] 별도 시트에서 데이터 로드
        deduct_key = e_dt.strftime("%Y-%m")
        deduct_data = load_monthly_deduction(user_name, deduct_key)
        
        # DB 값 로드
        db_cash = safe_int(deduct_data.get("Cash"))
        db_etc = safe_int(deduct_data.get("Etc"))
        db_etc_add = safe_int(deduct_data.get("EtcAdd"))
        db_etc_add_desc = deduct_data.get("EtcAddDesc", "")
        db_card_total = safe_int(deduct_data.get("Card"))
        db_card_detail = str(deduct_data.get("CardDetail", ""))
        
        # 2. 값 동기화 (월 변경 시 DB 값으로 입력창 초기화)
        # 2. 값 동기화 (월 변경 시 DB 값으로 입력창 초기화)
        # Session State에 값이 없거나 (초기 로드), 월이 변경되었을 때 DB 값 로드
        should_reload = "last_loaded_deduct_key" not in st.session_state or st.session_state.last_loaded_deduct_key != deduct_key
        # 안전장치: DB에는 값이 있는데 세션에는 없는 경우 (새로고침 직후 등)
        if not should_reload and "val_cash" not in st.session_state and db_cash > 0:
            should_reload = True
            
        if should_reload:
             st.session_state.val_cash = db_cash
             st.session_state.val_etc = db_etc
             st.session_state.val_etc_add = db_etc_add
             st.session_state.val_etc_add_desc = db_etc_add_desc
             st.session_state.inp_card_tot = db_card_total
             
             st.session_state.card_exclude_items = []
             if db_card_detail:
                 for item in db_card_detail.split("||"):
                     if "__" in item:
                         parts = item.split("__")
                         if len(parts) >= 3 and parts[2] == "O":
                             st.session_state.card_exclude_items.append({"desc": parts[0], "amt": safe_int(parts[1])})
             st.session_state.last_loaded_deduct_key = deduct_key

        # [Form Start] 일괄 입력을 위한 폼 시작
        with st.form("deduction_form", clear_on_submit=False):
            # 공제/지급 입력 UI
            with st.container(key="exp_cols"):
                 c1, c2, c3 = st.columns(3)
                 # [Key Assigned] value는 초기값 용도, 실제 값은 session_state[key] 사용
                 c1.number_input("매장 현금", step=10000, help="가불 등 (공제)", key="val_cash")
                 c1.caption(f"({st.session_state.get('val_cash', 0):,}원)")
                 c2.number_input("기타 공제", step=10000, help="기타 패널티 등 (공제)", key="val_etc")
                 c2.caption(f"({st.session_state.get('val_etc', 0):,}원)")
                 c3.number_input("기타 지급", step=10000, help="추가 보너스 등 (지급)", key="val_etc_add")
                 c3.text_input("내용 (선택)", placeholder="예: 교통비", key="val_etc_add_desc", label_visibility="collapsed")
                 c3.caption(f"({st.session_state.get('val_etc_add', 0):,}원)")
            
            st.markdown("---")
            st.markdown("**💳 카드 사용분 공제 (회사 사용분 제외)**")
            
            
            # 1. 카드 총 사용액 수동 입력
            st.number_input("카드 총 사용액", step=10000, help="카드 명세서 합계", key="inp_card_tot")
            st.caption(f"({st.session_state.get('inp_card_tot', 0):,}원)")
            
            # 리스트 출력 & 삭제 (Trash Can)
            # 저장 콜백 함수
            def save_deduct_cb():
                # 2. 데이터 구성
                new_list = st.session_state.card_exclude_items
                calc_exclude_sum = sum([x["amt"] for x in new_list])
                detail_str = "||".join([f"{x['desc']}__{x['amt']}__O" for x in new_list])
                
                save_data = {
                    "Cash": st.session_state.val_cash,
                    "Card": st.session_state.inp_card_tot,
                    "CardDeduct": calc_exclude_sum,
                    "Etc": st.session_state.val_etc,
                    "EtcAdd": st.session_state.val_etc_add,
                    "EtcAddDesc": st.session_state.val_etc_add_desc,
                    "CardDetail": detail_str
                }
                
                if save_monthly_deduction(user_name, deduct_key, save_data):
                     st.session_state.sv_deduct_success = True

            # 저장 버튼 (Callback 연결)
            st.form_submit_button("� 공제 내역 저장 (정산일 기준)", type="primary", use_container_width=True, on_click=save_deduct_cb)
            
            if st.session_state.get("sv_deduct_success"):
                st.success("내역이 저장되었습니다!"); st.session_state.sv_deduct_success = False; time.sleep(1); st.rerun()

        # [Refactor] 카드 공제 제외 항목 관리 (별도 UI, 즉시 저장)
        st.markdown("---")
        st.markdown("**❌ 카드 공제 제외 항목 관리 (즉시 저장됨)**")
        st.caption("이달의 리스트는 다음 달에도 자동으로 불러와집니다.")
        
        # 리스트 출력 & 삭제 (Trash Can) 
        # 삭제 버튼은 별도 폼 없이 일반 버튼으로 동작 -> 클릭 시 DB 즉시 업데이트
        with st.container(key="card_list"):
            for i, item in enumerate(st.session_state.card_exclude_items):
                cc1, cc2, cc3 = st.columns([2, 1.2, 0.5])
                cc1.text(item["desc"])
                cc2.text(f"{item['amt']:,}원")
                if cc3.button("🗑️", key=f"del_btn_ex_{i}"):
                    # 삭제 로직 (DB 즉시 반영)
                    del st.session_state.card_exclude_items[i]
                    
                    # DB 저장 호출
                    curr_d = load_monthly_deduction(user_name, deduct_key) # 현재 DB 상태 로드 (현금 등 보존)
                    new_list = st.session_state.card_exclude_items
                    detail_str = "||".join([f"{x['desc']}__{x['amt']}__O" for x in new_list])
                    calc_exclude_sum = sum([x["amt"] for x in new_list])
                    
                    save_data = {
                        "Cash": curr_d.get("Cash", 0),
                        "Card": curr_d.get("Card", 0), # 카드 총액 보존
                        "CardDeduct": calc_exclude_sum,
                        "Etc": curr_d.get("Etc", 0),
                        "EtcAdd": curr_d.get("EtcAdd", 0),
                        "EtcAddDesc": curr_d.get("EtcAddDesc", ""),
                        "CardDetail": detail_str
                    }
                    save_monthly_deduction(user_name, deduct_key, save_data)
                    st.rerun()

        st.write("➕ **제외 항목 추가**")
        with st.form("add_ex_form", clear_on_submit=True):
            ac1, ac2, ac3 = st.columns([2, 1.2, 0.8])
            # key가 form 내부로 들어갔으므로 동작 방식 안정화
            new_item_desc = ac1.text_input("내역", placeholder="예: 식대", key="inp_ex_desc_sep")
            new_item_amt = ac2.number_input("금액", step=1000, key="inp_ex_amt_sep")
            
            # Form submit button
            add_submitted = ac3.form_submit_button("추가", use_container_width=True)
            
            if add_submitted:
                 if new_item_desc and new_item_amt > 0:
                     st.session_state.card_exclude_items.append({"desc": new_item_desc, "amt": int(new_item_amt)})
                     
                     # DB 저장 호출
                     curr_d = load_monthly_deduction(user_name, deduct_key)
                     new_list = st.session_state.card_exclude_items
                     detail_str = "||".join([f"{x['desc']}__{x['amt']}__O" for x in new_list])
                     calc_exclude_sum = sum([x["amt"] for x in new_list])
                     
                     save_data = {
                            "Cash": curr_d.get("Cash", 0),
                            "Card": curr_d.get("Card", 0),
                            "CardDeduct": calc_exclude_sum,
                            "Etc": curr_d.get("Etc", 0),
                            "EtcAdd": curr_d.get("EtcAdd", 0),
                            "EtcAddDesc": curr_d.get("EtcAddDesc", ""),
                            "CardDetail": detail_str
                     }
                     save_monthly_deduction(user_name, deduct_key, save_data)
                     st.rerun()

        # 실시간 계산 미리보기 (폼 밖)
        calc_exclude_sum_view = sum([x["amt"] for x in st.session_state.card_exclude_items])
        calc_real_deduct_view = st.session_state.get("inp_card_tot", 0) - calc_exclude_sum_view
        st.markdown(f"<div style='background:#fff0f0; padding:10px; border-radius:5px; text-align:center; margin-top:10px;'>💳 (저장된 기준) 실 공제액: <b>{st.session_state.get('inp_card_tot', 0):,}</b> - <b>{calc_exclude_sum_view:,}</b> = <b style='color:red;'>{calc_real_deduct_view:,}원</b></div>", unsafe_allow_html=True)


    # 리포트 출력 (Refactored Function Call)
    render_monthly_report(df_all, e_dt, sal_cfg, is_ov_staff, user_name, readonly=False)