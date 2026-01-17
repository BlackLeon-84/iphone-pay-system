import time

# 소프트웨어 버전
SW_VERSION = "v4.0.0"
SW_VERSION = "v4.0.1"

# 페이지 설정
st.set_page_config(page_title=f"정산 {SW_VERSION}", layout="centered")
@@ -79,7 +79,6 @@

# --- 구글 시트 상수 ---
SHEET_NAME = "아이폰정산"
# [v4.0.0] 성욱 직원 추가
ORDERED_STAFF = ["태완", "남근", "성훈", "성욱"]
USER_HEADER = ["직원명", "날짜", "인센티브", "item1", "item2", "item3", "item4", "item5", "item6", "item7", "합계", "비고", "입력시간", "시간수당", "퇴근시간"]

@@ -122,7 +121,6 @@ def load_staff_salary_config(name):
try: sheet = get_config_worksheet(); rows = sheet.get_all_values()
except: return None

    # [v4.0.0] 성욱 님 기본값은 성훈 님 데이터 기반
base_template_name = "성훈" if name == "성욱" else ""
template_data = None

@@ -140,7 +138,6 @@ def load_staff_salary_config(name):
if base_template_name and r and r[0] == base_template_name:
template_data = r

    # 데이터가 없을 경우
if template_data:
hd = rows[0]
d = {hd[i]: template_data[i] for i in range(min(len(hd), len(template_data)))}
@@ -150,11 +147,9 @@ def load_staff_salary_config(name):
"item_prices": [safe_int(d.get(f"item{i}_price")) for i in range(1,8)],
"overtime_rate": safe_int(d.get("시간수당(10분)")), "apply_global": d.get("전체적용", "FALSE").upper() == "TRUE"
}
        # 성욱 님 초기 설정 강제 저장
save_staff_salary_config(name, res["base_salary"], res["start_day"], res["insurance"], res["item_names"], res["item_prices"], res["overtime_rate"], res["apply_global"])
return res

    # 완전 쌩 기본값
defaults = {"base_salary": 3500000, "start_day": 13, "insurance": 104760, "item_names": ['일반필름', '풀필름', '젤리', '케이블', '어댑터', '추가1', '추가2'], "item_prices": [9000, 18000, 9000, 15000, 23000, 0, 0], "overtime_rate": 4000 if name == "태완" else (3000 if name == "남근" else 0), "apply_global": False}
save_staff_salary_config(name, defaults["base_salary"], defaults["start_day"], defaults["insurance"], defaults["item_names"], defaults["item_prices"], defaults["overtime_rate"], defaults["apply_global"])
return defaults
@@ -204,7 +199,7 @@ def save_to_gsheet(user_name, df_row):
def get_safe_date(y, m, d): ld = calendar.monthrange(y, m)[1]; return date(y, m, min(safe_int(d, 1), ld))
def get_now_kst(): return datetime.now(timezone.utc) + timedelta(hours=9)

# --- 실행 체크 ---
# --- 세션 초기화 및 로그인 ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False

@st.cache_data(ttl=600)
@@ -228,12 +223,39 @@ def get_staff_list_fixed():
if st.button("입장", use_container_width=True, key="login_btn"):
if user_id == "태완" and admin_pw != "102030": st.error("비번 오류")
else: st.session_state.logged_in = True; st.session_state.user_name = user_id; st.rerun()
    st.markdown(f'<div class="admin-log"><b>🕒 {get_now_kst().strftime("%H:%M:%S")} v4.0.0 업데이트</b><br>• 신규 직원 [성욱] 추가 (성훈 데이터 기반)<br>• 날짜 변경 시 입력값 자동 0점 초기화 기능 도입<br>• 인센티브 연속 입력 및 취소 로직 정밀화</div>', unsafe_allow_html=True); st.stop()
    st.markdown(f'<div class="admin-log"><b>🕒 {get_now_kst().strftime("%H:%M:%S")} v4.0.1 패치</b><br>• [fix] 인센티브 위젯 Session State 충돌 오류 수정<br>• 날짜 변경 시 초기화 안정성 강화</div>', unsafe_allow_html=True); st.stop()

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
@@ -271,31 +293,7 @@ def get_staff_list_fixed():
st.divider();
if st.button("로그아웃", use_container_width=True): st.session_state.clear(); st.rerun()

# --- 메인 화면 ---
st.markdown(f'<div class="version-tag">{SW_VERSION}</div>', unsafe_allow_html=True)
df_all = load_data_from_gsheet(user_name)
st.write(f"### 💼 {user_name}님 실적")
sel_date = st.date_input("날짜", value=date.today(), label_visibility="collapsed"); str_date = sel_date.strftime("%Y-%m-%d")

# [v4.0.0] 날짜 변경 시 모든 입력값 초기화 로직
if "current_date" not in st.session_state: st.session_state.current_date = str_date
if st.session_state.current_date != str_date:
    st.session_state.current_date = str_date
    ext_data = df_all[df_all["날짜"] == str_date] if not df_all.empty else pd.DataFrame()
    # 인센티브 초기화
    st.session_state.inc_sum = safe_int(ext_data.iloc[0]["인센티브"]) if not ext_data.empty else 0
    st.session_state.inc_his = [{"val": safe_int(ext_data.iloc[0]["인센티브"])}] if not ext_data.empty and safe_int(ext_data.iloc[0]["인센티브"]) > 0 else []
    # 품목 수량 초기화
    for i in range(7):
        key = f"it_field_{i}" # input widget key와는 다름, 위젯에서 사용할 기본값 제어용
        val = safe_int(ext_data.iloc[0][f"item{i+1}"]) if not ext_data.empty else 0
        st.session_state[key] = val
    st.rerun()

existing = df_all[df_all["날짜"] == str_date] if not df_all.empty else pd.DataFrame()
if not existing.empty: st.markdown(f'<div class="status-card status-saved">✅ {str_date} 데이터가 저장되어 있습니다</div>', unsafe_allow_html=True)
else: st.markdown(f'<div class="status-card status-missing">⚠️ {str_date} 데이터가 아직 등록되지 않았습니다</div>', unsafe_allow_html=True)

# --- 휴무 및 기록 출력 ---
if st.button("🌴 오늘 휴무 등록", use_container_width=True):
row = {"직원명": user_name, "날짜": str_date, "인센티브": 0, "시간수당": 0, "퇴근시간": "휴무", "item1":0, "item2":0, "item3":0, "item4":0, "item5":0, "item6":0, "item7":0, "합계": 0, "비고": "휴무", "입력시간": get_now_kst().strftime("%H:%M:%S")}
if save_to_gsheet(user_name, row): st.rerun()
@@ -308,7 +306,7 @@ def get_staff_list_fixed():
w_box += f'<div style="text-align:center;"><div style="font-size:10px;">{td.day}일</div><div>{icon}</div></div>'
st.markdown(w_box + '</div>', unsafe_allow_html=True); st.divider()

# 수당 및 인센티브
# --- 수당 및 인센티브 ---
st.markdown('<div class="section-header">💰 수당 및 인센티브</div>', unsafe_allow_html=True)
if "inc_sum" not in st.session_state:
st.session_state.inc_sum = safe_int(existing.iloc[0]["인센티브"]) if not existing.empty else 0
@@ -331,39 +329,36 @@ def get_staff_list_fixed():
for i, item in enumerate(st.session_state.inc_his): h_html += f'<span class="inc-item">#{i+1}: {item["val"]:,}원</span>'
st.markdown(h_html + '</div>', unsafe_allow_html=True)

# [v4.0.0] 인센티브 입력값 혼동 방지 로직
add_amt = st.number_input("인센티브 추가 금액 (입력 후 추가 버튼 클릭)", 0, step=1000, value=0, label_visibility="collapsed", key="inc_input_field")
# [v4.0.1] 위젯 중복 선언 오류 수정: value= 인자 제거 및 key 에만 의존
st.number_input("인센티브 추가 금액 (입력 후 추가 버튼 클릭)", 0, step=1000, label_visibility="collapsed", key="inc_input_field")
with st.container(key="incen_buttons"):
b1, b2, b3 = st.columns(3)
    # on_click 콜백에서 상태 변경을 확실히 처리
def add_inc():
val = st.session_state.inc_input_field
if val > 0:
st.session_state.inc_sum += val
st.session_state.inc_his.append({"val": val})
            st.session_state.inc_input_field = 0 # 입력필드 초기화
    
            st.session_state.inc_input_field = 0
b1.button("➕추가", use_container_width=True, on_click=add_inc)
b2.button("↩️취소", use_container_width=True, on_click=lambda: (st.session_state.update({"inc_sum": st.session_state.inc_sum - (st.session_state.inc_his.pop()['val'] if st.session_state.inc_his else 0)})))
b3.button("🧹리셋", use_container_width=True, on_click=lambda: (st.session_state.update({"inc_sum": 0, "inc_his": []})))

# 품목 수량 입력
# --- 품목 수량 입력 ---
st.markdown('<div class="section-header">📦 품목 수량 입력</div>', unsafe_allow_html=True)
cts, it_n, it_p = [], sal_cfg["item_names"], sal_cfg["item_prices"]
it_n, it_p = sal_cfg["item_names"], sal_cfg["item_prices"]
# 초기 세션값 할당 (로드된 값 또는 0)
for i in range(7):
    s_key = f"it_field_{i}"
    if s_key not in st.session_state:
        st.session_state[s_key] = safe_int(existing.iloc[0][f"item{i+1}"]) if not existing.empty else 0
    if f"it_input_{i}" not in st.session_state:
        st.session_state[f"it_input_{i}"] = safe_int(existing.iloc[0][f"item{i+1}"]) if not existing.empty else 0

for i in range(0, 6, 2):
c1, c2 = st.columns(2)
    with c1: cts.append(st.number_input(it_n[i], 0, key=f"it_input_{i}", value=st.session_state[f"it_field_{i}"]))
    with c2: cts.append(st.number_input(it_n[i+1], 0, key=f"it_input_{i+1}", value=st.session_state[f"it_field_{i+1}"]))
cts.append(st.number_input(it_n[6], 0, key="it_input_6", value=st.session_state["it_field_6"]))
    with c1: st.number_input(it_n[i], 0, key=f"it_input_{i}")
    with c2: st.number_input(it_n[i+1], 0, key=f"it_input_{i+1}")
st.number_input(it_n[6], 0, key="it_input_6")

if st.button("✅ 최종 데이터 저장", type="primary", use_container_width=True):
    # 세션 상태도 최신 위젯 값으로 동기화
    for i in range(7): st.session_state[f"it_field_{i}"] = cts[i]
    cts = [st.session_state[f"it_input_{i}"] for i in range(7)]
tot_val = st.session_state.inc_sum + ov_pay + sum([safe_int(c) * safe_int(p) for c, p in zip(cts, it_p)])
row = {"직원명": user_name, "날짜": str_date, "인센티브": st.session_state.inc_sum, "시간수당": ov_pay, "퇴근시간": sel_etime, "item1": cts[0], "item2": cts[1], "item3": cts[2], "item4": cts[3], "item5": cts[4], "item6": cts[5], "item7": cts[6], "합계": tot_val, "비고": "정상", "입력시간": get_now_kst().strftime("%H:%M:%S")}
if save_to_gsheet(user_name, row):
@@ -374,7 +369,7 @@ def add_inc():
st.markdown(f'<div class="save-success">{st.session_state.sv_msg}</div>', unsafe_allow_html=True)
st.session_state.sv_msg = None

# 정산 리포트
# --- 정산 리포트 ---
st.divider()
s_d, b, ins = safe_int(sal_cfg['start_day'], 13), safe_int(sal_cfg['base_salary']), safe_int(sal_cfg['insurance'])
if sel_date.day >= s_d: s_dt = get_safe_date(sel_date.year, sel_date.month, s_d)
@@ -392,29 +387,20 @@ def add_inc():
t_items = sum([safe_int(p_df[f"item{i+1}"].sum()) * safe_int(it_p[i]) for i in range(7)])
total_sum_val = t_inc + t_ov + t_items
else:
            total_sum_val = safe_int(p_df["합계"].sum())
            t_inc = safe_int(p_df["인센티브"].sum())
            t_ov = safe_int(p_df["시간수당"].sum())
            t_items = total_sum_val - t_inc - t_ov
        
        final_pay = int(b + total_sum_val - ins)
        combined_inc = t_inc + t_items + t_ov
            total_sum_val = safe_int(p_df["합계"].sum()); t_inc = safe_int(p_df["인센티브"].sum()); t_ov = safe_int(p_df["시간수당"].sum()); t_items = total_sum_val - t_inc - t_ov
        final_pay = int(b + total_sum_val - ins); combined_inc = t_inc + t_items + t_ov
st.markdown(f'<div class="calc-detail"><div class="calc-line"><span>기본급</span> <span>+ {b:,}원</span></div><div class="calc-line"><span>인센티브</span> <span>+ {combined_inc:,}원</span></div><div class="calc-line"><span>보험료</span> <span>- {ins:,}원</span></div><div class="calc-total"><div class="calc-line"><span>💰 총급여</span> <span>{final_pay:,}원</span></div></div></div>', unsafe_allow_html=True)

        h_base = ["날짜", "인센"] + (["수당"] if is_ov_staff else [])
        hds = h_base + [n[:2] for n in it_n] + ["합계"]
        h_base = ["날짜", "인센"] + (["수당"] if is_ov_staff else []); hds = h_base + [n[:2] for n in it_n] + ["합계"]
r_html, i_sums = "", [0]*7
for _, r in p_df.iterrows():
md = datetime.strptime(r['날짜'], '%Y-%m-%d').strftime('%m/%d')
if r['비고'] == "휴무": r_html += f"<tr><td style='font-weight:bold;'>{md}</td><td colspan='{len(hds)-1}' style='color:orange;'>🌴휴무</td></tr>"
else:
                row_inc, row_ov = safe_int(r['인센티브']), safe_int(r.get('시간수당', 0))
                row_inc, row_ov = safe_int(r['인센티브']), safe_int(r.get('시간수당', 0)); 
for i in range(1, 8): i_sums[i-1] += safe_int(r[f'item{i}'])
row_total = (row_inc + row_ov + sum([safe_int(r[f'item{i+1}']) * safe_int(it_p[i]) for i in range(7)])) if sal_cfg.get("apply_global") else safe_int(r['합계'])
                disp_inc = row_inc if is_ov_staff else row_inc + row_ov
                ov_td = f"<td>{row_ov:,}</td>" if is_ov_staff else ""
                disp_inc, ov_td = (row_inc if is_ov_staff else row_inc + row_ov), (f"<td>{row_ov:,}</td>" if is_ov_staff else "")
it_tds = "".join([f"<td>{safe_int(r[f'item{i}'])}</td>" for i in range(1, 8)])
r_html += f"<tr><td style='font-weight:bold;'>{md}</td><td>{disp_inc:,}</td>{ov_td}{it_tds}<td style='color:blue;'>{row_total:,}</td></tr>"
        
r_html += f"<tr class='total-row'><td>합계</td><td>{(t_inc if is_ov_staff else t_inc + t_ov):,}</td>" + (f"<td>{t_ov:,}</td>" if is_ov_staff else "") + "".join([f"<td>{s}</td>" for s in i_sums]) + f"<td>{total_sum_val:,}</td></tr>"
st.markdown(f'<table class="report-table"><tr>{"".join([f"<th>{x}</th>" for x in hds])}</tr>{r_html}</table>', unsafe_allow_html=True)
